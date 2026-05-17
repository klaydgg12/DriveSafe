import os
import io
import re
import hashlib
import datetime
import logging
import pdfplumber
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from oauth2client.service_account import ServiceAccountCredentials
from models import db, ArchivalLedger

# AI Imports
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArchivalEngine:
    def __init__(self, user_credentials=None, service_account_json_path=None, archive_root='Capstone_Archives'):
        self.scope = [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        
        self.identity_label = "ROBOT (Service Account)"
        if user_credentials:
            self.service = build('drive', 'v3', credentials=user_credentials, cache_discovery=False)
            self.identity_label = "TEACHER (User OAuth)"
        elif service_account_json_path:
            from oauth2client.service_account import ServiceAccountCredentials
            if service_account_json_path.strip().startswith('{'):
                import json
                info = json.loads(service_account_json_path)
                self.creds = ServiceAccountCredentials.from_service_account_info(info, self.scope)
            else:
                self.creds = ServiceAccountCredentials.from_json_keyfile_name(service_account_json_path, self.scope)
            self.service = build('drive', 'v3', credentials=self.creds, cache_discovery=False)
        else:
             raise ValueError("No authentication method provided for ArchivalEngine")
             
        self.archive_root = archive_root
        logger.info(f"ArchivalEngine initialized using: {self.identity_label}")

    def _extract_file_id(self, url):
        if not url: return None, False
        url = str(url).replace('\\', '')
        # Folder pattern
        match_folder = re.search(r'folders/([a-zA-Z0-9_-]{25,})', url)
        if match_folder: return match_folder.group(1), True
        
        # File pattern
        match_file = re.search(r'/d/([a-zA-Z0-9_-]{25,})', url)
        if match_file: return match_file.group(1), False
        match_id = re.search(r'id=([a-zA-Z0-9_-]{25,})', url)
        if match_id: return match_id.group(1), False
        return None, False

    def _resolve_folder(self, folder_id, target_hint=None):
        try:
            query = f"'{folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query, 
                fields="files(id, name, mimeType, modifiedTime)",
                orderBy="modifiedTime desc"
            ).execute()
            files = results.get('files', [])
            if not files: return None, None
            
            if target_hint:
                hint = target_hint.lower()
                for f in files:
                    if hint in f['name'].lower(): return f['id'], f

            for f in files:
                if 'pdf' in f['mimeType'].lower(): return f['id'], f
            for f in files:
                if 'document' in f['mimeType'].lower(): return f['id'], f
            
            return files[0]['id'], files[0]
        except Exception as e:
            logger.error(f"Folder resolution failed for {folder_id}: {e}")
            return None, None

    def _compute_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _extract_text_from_pdf(self, file_path):
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages[:100]:
                    text += (page.extract_text() or "")
            return text
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ""

    def download_file(self, file_id, destination_path):
        try:
            # 1. Get metadata to determine type
            file_metadata = self.service.files().get(fileId=file_id, fields='mimeType, name').execute()
            mime_type = file_metadata.get('mimeType', '')
            file_name = file_metadata.get('name', 'unknown')
            
            logger.info(f"[{self.identity_label}] Downloading: {file_name} ({mime_type})")

            final_fh = io.BytesIO()
            
            # CASE A: Native Google Doc/Sheet
            if 'google-apps.document' in mime_type or 'google-apps.spreadsheet' in mime_type:
                try:
                    request = self.service.files().export_media(fileId=file_id, mimeType='application/pdf')
                    downloader = MediaIoBaseDownload(final_fh, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
                except Exception as e:
                    if "exportSizeLimitExceeded" in str(e):
                        raise Exception("File too large for Google to convert. Please upload as a PDF directly.")
                    raise e

            # CASE B: MS Office (.docx, .xlsx, .pptx) or Markdown (.md) - High-Fidelity Conversion
            elif 'officedocument' in mime_type or file_name.lower().endswith('.md') or 'markdown' in mime_type:
                logger.info(f"Performing High-Fidelity PDF conversion for {file_name}...")
                
                # Download raw bytes first
                raw_fh = io.BytesIO()
                downloader = MediaIoBaseDownload(raw_fh, self.service.files().get_media(fileId=file_id))
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                
                # Determine target upload mime
                if 'wordprocessingml.document' in mime_type: target_mime = 'application/vnd.google-apps.document'
                elif 'spreadsheetml.sheet' in mime_type: target_mime = 'application/vnd.google-apps.spreadsheet'
                elif 'presentationml.presentation' in mime_type: target_mime = 'application/vnd.google-apps.presentation'
                else: target_mime = 'application/vnd.google-apps.document'

                # Upload as temporary Google asset for conversion
                temp_meta = {
                    'name': f"DRIVESAFE_CONV_{int(time.time())}",
                    'mimeType': target_mime
                }
                upload_mime = 'text/plain' if file_name.lower().endswith('.md') else mime_type
                
                media = MediaIoBaseUpload(io.BytesIO(raw_fh.getvalue()), mimetype=upload_mime, resumable=True)
                temp_file = self.service.files().create(body=temp_meta, media_body=media, fields='id').execute()
                temp_id = temp_file.get('id')
                
                try:
                    time.sleep(3) # Wait for Google to format
                    request = self.service.files().export_media(fileId=temp_id, mimeType='application/pdf')
                    downloader = MediaIoBaseDownload(final_fh, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
                finally:
                    try: self.service.files().delete(fileId=temp_id).execute()
                    except: pass

            # CASE C: Binary File (PDF, ZIP, SQL, Images)
            else:
                request = self.service.files().get_media(fileId=file_id)
                downloader = MediaIoBaseDownload(final_fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()

            # --- VALIDATION ---
            data = final_fh.getvalue()
            if not data: raise Exception("Downloaded file is empty")
            
            with open(destination_path, 'wb') as f:
                f.write(data)
            
            return destination_path
        except Exception as e:
            logger.error(f"Download Error for {file_id}: {e}")
            raise e

    def _get_file_metadata(self, file_id):
        try:
            return self.service.files().get(fileId=file_id, fields='modifiedTime, md5Checksum, name, mimeType').execute()
        except: return None

    def archive_project(self, project_data, workbook_name="Archives", batch_id=None, archived_by=None):
        project_id = project_data.get('project_id', 'Unknown')
        project_title = project_data.get('project_title', 'Untitled')
        clean_title = str(project_title).replace(' ', '_').replace('/', '_')
        clean_id = str(project_id).replace(' ', '_').replace('/', '_')
        folder_name = f"{clean_id}_{clean_title}"
        academic_year = project_data.get('academic_year')
        
        base_project_dir = os.path.join(self.archive_root, workbook_name, folder_name)
        os.makedirs(base_project_dir, exist_ok=True)
        
        # Get the latest version in the vault
        last_record = ArchivalLedger.query.filter_by(
            project_id=project_id, academic_year=academic_year, status='archived'
        ).order_by(ArchivalLedger.version.desc()).first()
        
        doc_types = ['srs', 'sdd', 'spmp', 'std', 'ri', 'research_paper', 'usability_test', 'presentation', 'source_code', 'database', 'readme']
        results = {dt: {'path': None, 'hash': None, 'is_changed': False, 'bin': None, 'ts': None, 'text': None} for dt in doc_types}
        total_changed = 0
        error_msg = ""
        processed_file_ids = {}

        for doc_type in doc_types:
            link = project_data.get(f'{doc_type}_link')
            raw_id, is_folder = self._extract_file_id(link)
            if not raw_id: continue
            
            file_id = raw_id
            if is_folder:
                file_id, _ = self._resolve_folder(raw_id, target_hint=doc_type.upper())
                if not file_id:
                    error_msg += f"{doc_type.upper()}: Folder is empty; "
                    continue

            if file_id in processed_file_ids:
                results[doc_type] = processed_file_ids[file_id]['data']
                if results[doc_type].get('is_changed'): total_changed += 1
                continue

            try:
                metadata = self._get_file_metadata(file_id)
                if not metadata:
                    error_msg += f"{doc_type.upper()}: Permission Denied (Link is not shared); "
                    continue

                current_drive_ts = metadata.get('modifiedTime', 'Unknown')
                results[doc_type]['ts'] = current_drive_ts

                is_modified = True
                if last_record and last_record.archived_at and current_drive_ts != 'Unknown':
                    try:
                        drive_dt = datetime.datetime.fromisoformat(current_drive_ts.replace('Z', '+00:00'))
                        vault_dt = last_record.archived_at.replace(tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=3)
                        if drive_dt <= vault_dt:
                            is_modified = False
                    except: pass

                if not is_modified:
                    results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                    results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash")
                    results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                    processed_file_ids[file_id] = {'data': results[doc_type]}
                    continue

                doc_dir = os.path.join(base_project_dir, doc_type.upper())
                os.makedirs(doc_dir, exist_ok=True)
                temp_path = os.path.join(doc_dir, f"TEMP_{doc_type.upper()}.pdf")

                self.download_file(file_id, temp_path)
                
                with open(temp_path, "rb") as f:
                    file_binary = f.read()
                    results[doc_type]['bin'] = file_binary

                results[doc_type]['hash'] = metadata.get('md5Checksum') or hashlib.sha256(file_binary).hexdigest()
                
                if doc_type in ['srs', 'sdd', 'spmp', 'std', 'ri', 'research_paper', 'usability_test', 'readme']:
                    results[doc_type]['text'] = self._extract_text_from_pdf(temp_path)

                # Semantic Merge
                if last_record:
                    last_text = getattr(last_record, f"{doc_type}_text")
                    if results[doc_type]['text'] and last_text:
                        vectorizer = TfidfVectorizer().fit_transform([results[doc_type]['text'], last_text])
                        sim = cosine_similarity(vectorizer)[0][1]
                        if sim > 0.999:
                            results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                            results[doc_type]['is_changed'] = False
                            processed_file_ids[file_id] = {'data': results[doc_type]}
                            if os.path.exists(temp_path): os.remove(temp_path)
                            continue

                total_changed += 1
                results[doc_type]['is_changed'] = True

                from sqlalchemy import func
                prev_doc_v = db.session.query(func.count(ArchivalLedger.id)).filter(
                    ArchivalLedger.project_id == project_id,
                    getattr(ArchivalLedger, f"{doc_type}_hash").isnot(None)
                ).scalar()

                doc_v = (prev_doc_v or 0) + 1
                final_path = os.path.join(doc_dir, f"{clean_title}_{doc_type.upper()}_v{doc_v}.pdf")
                os.rename(temp_path, final_path)
                results[doc_type]['path'] = os.path.relpath(final_path, self.archive_root)
                processed_file_ids[file_id] = {'data': results[doc_type]}

            except Exception as e:
                logger.error(f"Error processing {doc_type}: {e}")
                err_str = str(e)
                if "File too large" in err_str:
                    error_msg += f"{doc_type.upper()}: {err_str}; "
                elif "403" in err_str or "permission" in err_str.lower():
                    error_msg += f"{doc_type.upper()}: Permission Denied; "
                else:
                    error_msg += f"{doc_type.upper()} System Error; "

        if total_changed == 0 and last_record:
            return {'status': 'unchanged', 'message': 'No edits found.', 'version': last_record.version}

        if error_msg:
            status = "partial" if total_changed > 0 else "failed"
        else:
            status = "archived"
        
        current_version = (last_record.version if last_record else 0) + (1 if status in ["archived", "partial"] else 0)

        try:
            ledger_entry = ArchivalLedger(
                project_id=project_id, project_title=project_title,
                academic_year=academic_year, workbook_name=workbook_name,
                archived_by=archived_by,
                srs_original_url=project_data.get('srs_link'), sdd_original_url=project_data.get('sdd_link'),
                spmp_original_url=project_data.get('spmp_link'), std_original_url=project_data.get('std_link'),
                ri_original_url=project_data.get('ri_link'), 
                research_paper_original_url=project_data.get('research_paper_link'),
                usability_test_original_url=project_data.get('usability_test_link'),
                presentation_original_url=project_data.get('presentation_link'),
                source_code_original_url=project_data.get('source_code_link'), 
                github_original_url=project_data.get('github_link'), 
                database_original_url=project_data.get('database_link'),
                readme_original_url=project_data.get('readme_link'),
                
                srs_local_path=results['srs']['path'], sdd_local_path=results['sdd']['path'],
                spmp_local_path=results['spmp']['path'], std_local_path=results['std']['path'],
                ri_local_path=results['ri']['path'],
                research_paper_local_path=results['research_paper']['path'],
                usability_test_local_path=results['usability_test']['path'],
                presentation_local_path=results['presentation']['path'],
                source_code_local_path=results['source_code']['path'], 
                database_local_path=results['database']['path'], 
                readme_local_path=results['readme']['path'],
                
                srs_hash=results['srs']['hash'], sdd_hash=results['sdd']['hash'],
                spmp_hash=results['spmp']['hash'], std_hash=results['std']['hash'],
                ri_hash=results['ri']['hash'],
                research_paper_hash=results['research_paper']['hash'],
                usability_test_hash=results['usability_test']['hash'],
                presentation_hash=results['presentation']['hash'],
                source_code_hash=results['source_code']['hash'], 
                database_hash=results['database']['hash'], 
                readme_hash=results['readme']['hash'],
                
                srs_binary=results['srs']['bin'], sdd_binary=results['sdd']['bin'],
                spmp_binary=results['spmp']['bin'], std_binary=results['std']['bin'],
                ri_binary=results['ri']['bin'],
                research_paper_binary=results['research_paper']['bin'],
                usability_test_binary=results['usability_test']['bin'],
                presentation_binary=results['presentation']['bin'],
                source_code_binary=results['source_code']['bin'], 
                database_binary=results['database']['bin'], 
                readme_binary=results['readme']['bin'],
                
                srs_text=results['srs']['text'], sdd_text=results['sdd']['text'],
                spmp_text=results['spmp']['text'], std_text=results['std']['text'],
                ri_text=results['ri']['text'], 
                research_paper_text=results['research_paper']['text'],
                usability_test_text=results['usability_test']['text'],
                readme_text=results['readme']['text'],
                
                status=status, version=current_version, batch_id=batch_id,
                error_message=error_msg.strip(), archived_at=datetime.datetime.utcnow()
            )
            db.session.add(ledger_entry)
            db.session.commit()
        except Exception as save_err:
            logger.error(f"CRITICAL DATABASE ERROR: {save_err}")
            db.session.rollback()
            return {'status': 'failed', 'version': current_version, 'error': f"Database save failed. {save_err}"}
        
        return {'status': status, 'version': current_version, 'paths': {dt: results[dt]['path'] for dt in doc_types}, 'error': error_msg.strip()}
