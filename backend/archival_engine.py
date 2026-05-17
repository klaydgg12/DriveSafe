import os
import io
import re
import hashlib
import datetime
import logging
import pdfplumber
import time
import requests
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
        self.creds = None
        if user_credentials:
            self.creds = user_credentials
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

    def check_for_duplicates(self, new_file_hash, new_text, current_project_id=None):
        """AI Plagiarism Check (Across different projects only)"""
        if not new_text or len(new_text) < 100: return None, 0, None, None, None
        
        query = ArchivalLedger.query.filter(
            ArchivalLedger.status == 'archived',
            ArchivalLedger.project_id != current_project_id
        ).all()

        if not query: return None, 0, None, None, None

        corpus = [new_text]
        metadata_map = [] 
        for record in query:
            for dt in ['srs', 'sdd', 'spmp', 'std', 'ri']:
                past_text = getattr(record, f"{dt}_text")
                if past_text and len(past_text) > 100:
                    corpus.append(past_text)
                    metadata_map.append({'title': record.project_title, 'id': record.project_id})

        if len(corpus) <= 1: return None, 0, None, None, None

        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(corpus)
            cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            max_sim_idx = cosine_similarities.argmax()
            max_sim_score = cosine_similarities[max_sim_idx]
            
            if max_sim_score > 0.999:
                match_meta = metadata_map[max_sim_idx]
                return "Semantic Duplicate", max_sim_score, match_meta['title'], match_meta['id'], 0
        except: pass
        return None, 0, None, None, None

    def download_file(self, file_id, destination_path):
        try:
            # 1. ATTEMPT WITH TEACHER IDENTITY (API)
            try:
                file_metadata = self.service.files().get(fileId=file_id, fields='mimeType, name').execute()
                mime_type = file_metadata.get('mimeType', '')
                file_name = file_metadata.get('name', 'unknown')
            except Exception as api_meta_err:
                if "403" in str(api_meta_err):
                    logger.info(f"[{self.identity_label}] Metadata 403. Switching to Public Fallback...")
                    return self._public_download_fallback(file_id, destination_path)
                raise api_meta_err

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
                    if "exportSizeLimitExceeded" in str(e) or "403" in str(e):
                        logger.info(f"[{self.identity_label}] Export failed. Trying Browser-Mirror HTTP Export...")
                        return self._public_download_fallback(file_id, destination_path, is_export=True, is_sheet='spreadsheet' in mime_type)
                    raise e
            # CASE B: Binary File
            else:
                try:
                    request = self.service.files().get_media(fileId=file_id)
                    downloader = MediaIoBaseDownload(final_fh, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
                except Exception as e:
                    if "403" in str(e):
                        return self._public_download_fallback(file_id, destination_path)
                    raise e

            with open(destination_path, 'wb') as f:
                f.write(final_fh.getvalue())
            return destination_path
        except Exception as e:
            logger.error(f"Download Error for {file_id}: {e}")
            raise e

    def _public_download_fallback(self, file_id, destination_path, is_export=False, is_sheet=False):
        try:
            if is_export:
                url = f"https://docs.google.com/document/d/{file_id}/export?format=pdf"
                if is_sheet: url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=pdf"
            else:
                url = f"https://drive.google.com/uc?export=download&id={file_id}"
            
            headers = {}
            if self.creds:
                 if hasattr(self.creds, 'valid') and not self.creds.valid:
                      self.creds.refresh(requests.Session())
                 if hasattr(self.creds, 'token'):
                      headers = {'Authorization': f'Bearer {self.creds.token}'}

            resp = requests.get(url, headers=headers, timeout=60, stream=True)
            if resp.status_code == 403:
                 resp = requests.get(url, timeout=60, stream=True)

            if resp.status_code == 200:
                with open(destination_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk: f.write(chunk)
                return destination_path
            else:
                raise Exception(f"Public Download Failed (Status {resp.status_code})")
        except Exception as e:
            raise Exception(f"Access Denied. Ensure link is set to 'Anyone with link can view'. ({str(e)[:50]})")

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
        
        # Get the latest version in the vault (Including partial successes)
        last_record = ArchivalLedger.query.filter(
            ArchivalLedger.project_id == project_id,
            ArchivalLedger.academic_year == academic_year,
            ArchivalLedger.status.in_(['archived', 'partial'])
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
                    error_msg += f"{doc_type.upper()}: Access Denied (Link is not shared); "
                    continue

                current_drive_ts = metadata.get('modifiedTime', 'Unknown')
                results[doc_type]['ts'] = current_drive_ts

                # --- STEP 1: Fast Timestamp Check ---
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

                # --- STEP 2: Process New Version ---
                doc_dir = os.path.join(base_project_dir, doc_type.upper())
                os.makedirs(doc_dir, exist_ok=True)
                temp_path = os.path.join(doc_dir, f"TEMP_{doc_type.upper()}.pdf")

                self.download_file(file_id, temp_path)
                
                with open(temp_path, "rb") as f:
                    file_binary = f.read()
                
                new_hash = metadata.get('md5Checksum') or hashlib.sha256(file_binary).hexdigest()
                
                # --- STEP 3: STRICT HASH DEDUPLICATION ---
                if last_record:
                    last_hash = getattr(last_record, f"{doc_type}_hash")
                    if new_hash == last_hash:
                        logger.info(f"DEDUPLICATED: {doc_type.upper()} bytes are identical to vault. Skipping.")
                        results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                        results[doc_type]['hash'] = last_hash
                        results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                        results[doc_type]['bin'] = None
                        processed_file_ids[file_id] = {'data': results[doc_type]}
                        if os.path.exists(temp_path): os.remove(temp_path)
                        continue

                results[doc_type]['bin'] = file_binary
                results[doc_type]['hash'] = new_hash
                
                if doc_type in ['srs', 'sdd', 'spmp', 'std', 'ri', 'research_paper', 'usability_test', 'readme']:
                    results[doc_type]['text'] = self._extract_text_from_pdf(temp_path)

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
                id_tag = f"[{self.identity_label.split(' ')[0]}]" 
                
                if "File too large" in err_str:
                    error_msg += f"{id_tag} {doc_type.upper()}: File is too massive for Google's converter. Student must upload as a PDF; "
                elif "403" in err_str or "permission" in err_str.lower():
                    error_msg += f"{id_tag} {doc_type.upper()}: Access Denied. Student must change link to 'Anyone with link can view'; "
                else:
                    error_msg += f"{id_tag} {doc_type.upper()}: {err_str[:50]}; "

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
