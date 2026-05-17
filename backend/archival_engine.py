import os
import io
import re
import hashlib
import datetime
import logging
import pdfplumber
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
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
            "https://www.googleapis.com/auth/drive.file"
        ]
        
        if user_credentials:
            self.service = build('drive', 'v3', credentials=user_credentials)
        elif service_account_json_path:
            from oauth2client.service_account import ServiceAccountCredentials
            self.creds = ServiceAccountCredentials.from_json_keyfile_name(service_account_json_path, self.scope)
            self.service = build('drive', 'v3', credentials=self.creds)
        else:
             raise ValueError("No authentication method provided for ArchivalEngine")
             
        self.archive_root = archive_root

    def _extract_file_id(self, url):
        if not url: return None, False
        # Folder pattern
        match_folder = re.search(r'folders/([a-zA-Z0-9_-]{25,})', url)
        if match_folder: return match_folder.group(1), True
        
        # File pattern
        match_file = re.search(r'/d/([a-zA-Z0-9_-]{25,})', url)
        if match_file: return match_file.group(1), False
        match_id = re.search(r'id=([a-zA-Z0-9_-]{25,})', url)
        if match_id: return match_id.group(1), False
        return None, False

    def _resolve_folder(self, folder_id):
        """Find the best file inside a Google Drive folder"""
        try:
            query = f"'{folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query, 
                fields="files(id, name, mimeType, modifiedTime)",
                orderBy="modifiedTime desc"
            ).execute()
            files = results.get('files', [])
            if not files: return None, None
            
            # Prefer PDFs, then Google Docs
            for f in files:
                if 'pdf' in f['mimeType'].lower(): return f['id'], f
            for f in files:
                if 'document' in f['mimeType'].lower(): return f['id'], f
            
            # Fallback to the first file
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
            file_metadata = self.service.files().get(fileId=file_id, fields='mimeType, name').execute()
            mime_type = file_metadata.get('mimeType')
            file_name = file_metadata.get('name')
            logger.info(f"Downloading: {file_name}")

            fh = io.BytesIO()
            if 'google-apps.document' in mime_type or 'google-apps.spreadsheet' in mime_type:
                request = self.service.files().export_media(fileId=file_id, mimeType='application/pdf')
            else:
                request = self.service.files().get_media(fileId=file_id)

            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

            with open(destination_path, 'wb') as f:
                f.write(fh.getvalue())
            return destination_path
        except Exception as e:
            logger.error(f"Download Error: {e}")
            raise e

    def _get_file_metadata(self, file_id):
        try:
            return self.service.files().get(fileId=file_id, fields='modifiedTime, md5Checksum, name, mimeType').execute()
        except: return None

    def archive_project(self, project_data, workbook_name="Archives", batch_id=None):
        project_id = project_data.get('project_id', 'Unknown')
        clean_title = project_data.get('project_title', 'Untitled').replace(' ', '_').replace('/', '_')
        clean_id = str(project_id).replace(' ', '_').replace('/', '_')
        folder_name = f"{clean_id}_{clean_title}"
        academic_year = project_data.get('academic_year')
        
        base_project_dir = os.path.join(self.archive_root, workbook_name, folder_name)
        os.makedirs(base_project_dir, exist_ok=True)
        
        # Get the latest version in the vault
        last_record = ArchivalLedger.query.filter_by(
            project_id=project_id, academic_year=academic_year, status='archived'
        ).order_by(ArchivalLedger.version.desc()).first()
        
        doc_types = ['srs', 'sdd', 'spmp', 'std', 'ri', 'source_code', 'database', 'readme']
        results = {dt: {'path': None, 'hash': None, 'is_changed': False, 'bin': None, 'ts': None} for dt in doc_types}
        total_changed = 0
        error_msg = ""
        processed_file_ids = {}

        for doc_type in doc_types:
            link = project_data.get(f'{doc_type}_link')
            raw_id, is_folder = self._extract_file_id(link)
            if not raw_id: continue
            
            file_id = raw_id
            if is_folder:
                logger.info(f"Resolving Folder: {raw_id} for {doc_type.upper()}")
                file_id, folder_meta = self._resolve_folder(raw_id)
                if not file_id:
                    error_msg += f"{doc_type.upper()}: Folder is empty; "
                    continue
                logger.info(f"Folder Resolved: Using file '{folder_meta['name']}' ({file_id})")

            if file_id in processed_file_ids:
                res = processed_file_ids[file_id]['data']
                results[doc_type] = res
                if res.get('is_changed'): total_changed += 1
                continue

            try:
                # 1. FETCH LIVE CLOCK FROM GOOGLE
                metadata = self._get_file_metadata(file_id)
                if not metadata:
                    error_msg += f"{doc_type.upper()}: Access Denied; "
                    continue

                current_drive_ts = metadata.get('modifiedTime', 'Unknown')
                results[doc_type]['ts'] = current_drive_ts

                # 2. RELIABLE TIMESTAMP VERSIONING
                is_modified = True
                if last_record and last_record.archived_at and current_drive_ts != 'Unknown':
                    try:
                        drive_dt = datetime.datetime.fromisoformat(current_drive_ts.replace('Z', '+00:00'))
                        vault_dt = last_record.archived_at.replace(tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=3)
                        if drive_dt <= vault_dt:
                            is_modified = False
                            logger.info(f"UNCHANGED: {doc_type.upper()} matches vault timestamp.")
                    except: pass

                if not is_modified:
                    results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                    results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash")
                    results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                    results[doc_type]['bin'] = None
                    processed_file_ids[file_id] = {'data': results[doc_type]}
                    continue

                # 3. PROCESS THE NEW VERSION
                import time
                time.sleep(5) 

                doc_dir = os.path.join(self.archive_root, workbook_name, folder_name, doc_type.upper())
                os.makedirs(doc_dir, exist_ok=True)
                temp_path = os.path.join(doc_dir, f"TEMP_{doc_type.upper()}.pdf")

                try:
                    self.download_file(file_id, temp_path)
                except Exception as down_err:
                    err_str = str(down_err)
                    if "exportSizeLimitExceeded" in err_str:
                        error_msg += f"{doc_type.upper()}: File too large for Auto-PDF; "
                    else:
                        error_msg += f"{doc_type.upper()} Download Error; "
                    continue

                with open(temp_path, "rb") as f:
                    file_binary = f.read()
                    results[doc_type]['bin'] = file_binary

                file_hash = metadata.get('md5Checksum') or hashlib.sha256(file_binary).hexdigest()
                results[doc_type]['hash'] = file_hash

                file_text = ""
                if doc_type in ['srs', 'sdd', 'spmp', 'std', 'ri', 'readme']:
                    file_text = self._extract_text_from_pdf(temp_path)
                results[doc_type]['text'] = file_text

                # SEMANTIC DEDUPLICATION (TEAM LEVEL)
                if last_record:
                    last_text = getattr(last_record, f"{doc_type}_text")
                    if file_text and last_text:
                        vectorizer = TfidfVectorizer().fit_transform([file_text, last_text])
                        sim = cosine_similarity(vectorizer)[0][1]
                        if sim > 0.999: # 99.9% identical
                            logger.info(f"SEMANTIC MATCH: {doc_type.upper()} is identical to last version content. Skipping.")
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
                logger.error(f"Error processing {doc_type}: {e}", exc_info=True)
                error_msg += f"{doc_type.upper()} System Error; "

        if total_changed == 0 and last_record:
            return {'status': 'unchanged', 'message': 'No edits found in Google Drive since last archive.', 'version': last_record.version}

        current_version = (last_record.version if last_record else 0) + 1
        status = "archived" if not error_msg else "failed"

        try:
            ledger_entry = ArchivalLedger(
                project_id=project_id, project_title=project_data.get('project_title'),
                academic_year=academic_year, workbook_name=workbook_name,
                srs_original_url=project_data.get('srs_link'), sdd_original_url=project_data.get('sdd_link'),
                spmp_original_url=project_data.get('spmp_link'), std_original_url=project_data.get('std_link'),
                ri_original_url=project_data.get('ri_link'), source_code_original_url=project_data.get('source_code_link'),
                github_original_url=project_data.get('github_link'), database_original_url=project_data.get('database_link'),
                readme_original_url=project_data.get('readme_link'),
                srs_local_path=results['srs']['path'], sdd_local_path=results['sdd']['path'],
                spmp_local_path=results['spmp']['path'], std_local_path=results['std']['path'],
                ri_local_path=results['ri']['path'], source_code_local_path=results['source_code']['path'],
                database_local_path=results['database']['path'], readme_local_path=results['readme']['path'],
                srs_hash=results['srs']['hash'], sdd_hash=results['sdd']['hash'],
                spmp_hash=results['spmp']['hash'], std_hash=results['std']['hash'],
                ri_hash=results['ri']['hash'], source_code_hash=results['source_code']['hash'],
                database_hash=results['database']['hash'], readme_hash=results['readme']['hash'],
                srs_binary=results['srs']['bin'], sdd_binary=results['sdd']['bin'],
                spmp_binary=results['spmp']['bin'], std_binary=results['std']['bin'],
                ri_binary=results['ri']['bin'], source_code_binary=results['source_code']['bin'],
                database_binary=results['database']['bin'], readme_binary=results['readme']['bin'],
                srs_text=results['srs'].get('text'), sdd_text=results['sdd'].get('text'),
                spmp_text=results['spmp'].get('text'), std_text=results['std'].get('text'),
                ri_text=results['ri'].get('text'), readme_text=results['readme'].get('text'),
                status=status, version=current_version, batch_id=batch_id,
                error_message=error_msg.strip(), archived_at=datetime.datetime.utcnow()
            )
            db.session.add(ledger_entry)
            db.session.commit()
        except Exception as save_err:
            logger.error(f"CRITICAL DATABASE ERROR: {save_err}")
            db.session.rollback()
            return {'status': 'failed', 'version': current_version, 'error': f"Database save failed. Schema mismatch or database error."}
        
        return {'status': status, 'version': current_version, 'paths': {dt: results[dt]['path'] for dt in doc_types}, 'error': error_msg.strip()}
