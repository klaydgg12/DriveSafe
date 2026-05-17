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
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
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
            from google.oauth2 import service_account
            if service_account_json_path.strip().startswith('{'):
                import json
                info = json.loads(service_account_json_path)
                self.creds = service_account.Credentials.from_service_account_info(info, scopes=self.scope)
            else:
                self.creds = service_account.Credentials.from_service_account_file(service_account_json_path, scopes=self.scope)
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
                clean_hint = hint.replace('finalized', '').replace('software', '').strip()
                for f in files:
                    if clean_hint in f['name'].lower(): return f['id'], f

            for f in files:
                if 'pdf' in f['mimeType'].lower(): return f['id'], f
            for f in files:
                if 'document' in f['mimeType'].lower(): return f['id'], f
            
            return files[0]['id'], files[0]
        except Exception as e:
            logger.error(f"Folder resolution failed for {folder_id}: {e}")
            return None, None

    def _compute_hash(self, file_data):
        return hashlib.sha256(file_data).hexdigest()

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
        """
        ULTIMATE MULTI-PATH DOWNLOAD WITH PUBLIC FALLBACK
        """
        try:
            # 1. Fetch Metadata
            meta = self.service.files().get(fileId=file_id, fields='mimeType, name, size').execute()
            mime_type = meta.get('mimeType', '').lower()
            file_name = meta.get('name', 'unknown')
            is_google = 'google-apps' in mime_type
            is_pdf_target = destination_path.lower().endswith('.pdf')
            
            logger.info(f"[{self.identity_label}] Archiving: {file_name} ({mime_type})")

            # --- PHASE 1: ATTEMPT OFFICIAL API ---
            final_data = None
            try:
                fh = io.BytesIO()
                if is_google:
                    request = self.service.files().export_media(fileId=file_id, mimeType='application/pdf')
                else:
                    request = self.service.files().get_media(fileId=file_id)
                
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done: _, done = downloader.next_chunk()
                final_data = fh.getvalue()
            except Exception as e:
                logger.warning(f"API Attempt failed for {file_name}: {e}")

            # --- PHASE 2: BROWSER-MIRROR FALLBACK (Authenticated) ---
            if not final_data or (is_pdf_target and not final_data.startswith(b'%PDF-')):
                logger.info(f"[{self.identity_label}] Falling back to HTTP Mirror for {file_name}...")
                try:
                    if not self.creds.valid: self.creds.refresh(requests.Session())
                    url = f"https://docs.google.com/document/d/{file_id}/export?format=pdf" if is_google else f"https://drive.google.com/uc?export=download&id={file_id}"
                    resp = requests.get(url, headers={'Authorization': f'Bearer {self.creds.token}'}, timeout=60)
                    if resp.status_code == 200: final_data = resp.content
                except: pass

            # --- PHASE 3: PUBLIC FALLBACK (Unauthenticated) ---
            if not final_data or (is_pdf_target and not final_data.startswith(b'%PDF-')):
                logger.info(f"[{self.identity_label}] Falling back to 100% Public Download for {file_name}...")
                try:
                    url = f"https://drive.google.com/uc?export=download&id={file_id}"
                    resp = requests.get(url, timeout=60)
                    if resp.status_code == 200: final_data = resp.content
                except: pass

            # --- FINAL VALIDATION & CONVERSION ---
            if not final_data: raise Exception("All download paths failed. File is unreachable.")

            # If it's a Word/MD file that came down as raw bytes, FORCE conversion
            if is_pdf_target and not final_data.startswith(b'%PDF-'):
                if final_data.startswith(b'PK\x03\x04') or file_name.lower().endswith(('.docx', '.doc', '.md', '.txt')):
                    logger.info(f"FORCING CONVERSION for non-PDF raw data: {file_name}")
                    temp_meta = {'name': f"CONV_{int(time.time())}", 'mimeType': 'application/vnd.google-apps.document'}
                    upload_mime = 'text/plain' if file_name.endswith('.md') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    media = MediaIoBaseUpload(io.BytesIO(final_data), mimetype=upload_mime, resumable=True)
                    temp_file = self.service.files().create(body=temp_meta, media_body=media, fields='id').execute()
                    t_id = temp_file.get('id')
                    try:
                        time.sleep(5)
                        req = self.service.files().export_media(fileId=t_id, mimeType='application/pdf')
                        fh = io.BytesIO()
                        dld = MediaIoBaseDownload(fh, req)
                        d_done = False
                        while not d_done: _, d_done = dld.next_chunk()
                        final_data = fh.getvalue()
                    finally:
                        try: self.service.files().delete(fileId=t_id).execute()
                        except: pass

            # LAST CHANCE CHECK
            if is_pdf_target and not final_data.startswith(b'%PDF-'):
                snippet = final_data[:100].decode('utf-8', errors='ignore')
                if "<html" in snippet.lower():
                     raise Exception("Google blocked export. File too large or restricted. Student must upload direct PDF.")
                raise Exception("Corrupted document: Content is not a valid PDF.")

            with open(destination_path, 'wb') as f:
                f.write(final_data)
            
            return final_data
        except Exception as e:
            logger.error(f"Ultimate Download Failure for {file_id}: {e}")
            raise e

    def _get_file_metadata(self, file_id):
        try:
            return self.service.files().get(fileId=file_id, fields='modifiedTime, md5Checksum, name, mimeType').execute()
        except: return None

    def archive_project(self, project_data, workbook_name="Archives", batch_id=None, archived_by=None):
        project_id = project_data.get('project_id', 'Unknown')
        project_title = project_data.get('project_title', 'Untitled')
        clean_title = str(project_title).replace(' ', '_').replace('/', '_').replace('\\', '_')
        clean_id = str(project_id).replace(' ', '_').replace('/', '_').replace('\\', '_')
        folder_name = f"{clean_id}_{clean_title}"
        academic_year = project_data.get('academic_year')
        
        base_project_dir = os.path.join(self.archive_root, workbook_name, folder_name)
        os.makedirs(base_project_dir, exist_ok=True)
        
        # Latest record (Any status)
        last_record = ArchivalLedger.query.filter(
            ArchivalLedger.project_id == project_id,
            ArchivalLedger.academic_year == academic_year,
            ArchivalLedger.status.in_(['archived', 'partial'])
        ).order_by(ArchivalLedger.id.desc()).first()
        
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
                    error_msg += f"{doc_type.upper()}: Access Denied (Link is private); "
                    continue

                current_drive_ts = metadata.get('modifiedTime', 'Unknown')
                results[doc_type]['ts'] = current_drive_ts

                is_modified = True
                if last_record and last_record.archived_at and current_drive_ts != 'Unknown':
                    try:
                        drive_dt = datetime.datetime.fromisoformat(current_drive_ts.replace('Z', '+00:00'))
                        vault_dt = last_record.archived_at.replace(tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=3)
                        if drive_dt <= vault_dt: is_modified = False
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

                # DOWNLOAD & CONVERT - CRITICAL: Assign returned bytes to the bin results!
                final_bytes = self.download_file(file_id, temp_path)
                results[doc_type]['bin'] = final_bytes

                new_hash = hashlib.sha256(final_bytes).hexdigest()
                
                # STRICT HASH DEDUPLICATION
                if last_record:
                    last_hash = getattr(last_record, f"{doc_type}_hash")
                    if new_hash == last_hash:
                        results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                        results[doc_type]['hash'] = last_hash
                        results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                        results[doc_type]['bin'] = None
                        processed_file_ids[file_id] = {'data': results[doc_type]}
                        if os.path.exists(temp_path): os.remove(temp_path)
                        continue

                results[doc_type]['hash'] = new_hash
                if doc_type in ['srs', 'sdd', 'spmp', 'std', 'ri', 'research_paper', 'usability_test', 'readme']:
                    results[doc_type]['text'] = self._extract_text_from_pdf(temp_path)

                total_changed += 1
                results[doc_type]['is_changed'] = True
                
                prev_doc_v = db.session.query(db.func.count(ArchivalLedger.id)).filter(
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
                id_tag = f"[{self.identity_label.split(' ')[0]}]" 
                error_msg += f"{id_tag} {doc_type.upper()}: {str(e)[:70]}; "

        if total_changed == 0 and last_record:
            return {'status': 'unchanged', 'message': 'No edits found.', 'version': last_record.version}

        status = "partial" if error_msg and total_changed > 0 else ("failed" if error_msg else "archived")
        current_version = (last_record.version if last_record else 0) + (1 if status in ["archived", "partial"] else 0)

        MAX_BIN_SIZE = 15 * 1024 * 1024 
        def safe_bin(dt):
            b = results[dt]['bin']
            if b and len(b) > MAX_BIN_SIZE: return None
            return b

        try:
            ledger_entry = ArchivalLedger(
                project_id=project_id, project_title=project_title, academic_year=academic_year,
                workbook_name=workbook_name, archived_by=archived_by, batch_id=batch_id,
                status=status, version=current_version, archived_at=datetime.datetime.utcnow(),
                error_message=error_msg.strip(),
                srs_original_url=project_data.get('srs_link'), sdd_original_url=project_data.get('sdd_link'),
                spmp_original_url=project_data.get('spmp_link'), std_original_url=project_data.get('std_link'),
                ri_original_url=project_data.get('ri_link'), research_paper_original_url=project_data.get('research_paper_link'),
                usability_test_original_url=project_data.get('usability_test_link'), presentation_original_url=project_data.get('presentation_link'),
                source_code_original_url=project_data.get('source_code_link'), github_original_url=project_data.get('github_link'),
                database_original_url=project_data.get('database_link'), readme_original_url=project_data.get('readme_link'),
                srs_local_path=results['srs']['path'], sdd_local_path=results['sdd']['path'],
                spmp_local_path=results['spmp']['path'], std_local_path=results['std']['path'],
                ri_local_path=results['ri']['path'], research_paper_local_path=results['research_paper']['path'],
                usability_test_local_path=results['usability_test']['path'], presentation_local_path=results['presentation']['path'],
                source_code_local_path=results['source_code']['path'], database_local_path=results['database']['path'],
                readme_local_path=results['readme']['path'],
                srs_hash=results['srs']['hash'], sdd_hash=results['sdd']['hash'],
                spmp_hash=results['spmp']['hash'], std_hash=results['std']['hash'],
                ri_hash=results['ri']['hash'], research_paper_hash=results['research_paper']['hash'],
                usability_test_hash=results['usability_test']['hash'], presentation_hash=results['presentation']['hash'],
                source_code_hash=results['source_code']['hash'], database_hash=results['database']['hash'],
                readme_hash=results['readme']['hash'],
                srs_binary=safe_bin('srs'), sdd_binary=safe_bin('sdd'),
                spmp_binary=safe_bin('spmp'), std_binary=safe_bin('std'),
                ri_binary=safe_bin('ri'), research_paper_binary=safe_bin('research_paper'),
                usability_test_binary=safe_bin('usability_test'), presentation_binary=safe_bin('presentation'),
                source_code_binary=safe_bin('source_code'), database_binary=safe_bin('database'),
                readme_binary=safe_bin('readme'),
                srs_text=results['srs']['text'], sdd_text=results['sdd']['text'],
                spmp_text=results['spmp']['text'], std_text=results['std']['text'],
                ri_text=results['ri']['text'], research_paper_text=results['research_paper']['text'],
                usability_test_text=results['usability_test']['text'], readme_text=results['readme']['text']
            )
            db.session.add(ledger_entry)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            try:
                disk_entry = ArchivalLedger(
                    project_id=project_id, project_title=project_title, academic_year=academic_year,
                    workbook_name=workbook_name, archived_by=archived_by, batch_id=batch_id,
                    status=status, version=current_version, archived_at=datetime.datetime.utcnow(),
                    error_message=f"{error_msg.strip()} (Note: Database overloaded; serving from disk)".strip(),
                    srs_original_url=project_data.get('srs_link'), sdd_original_url=project_data.get('sdd_link'),
                    spmp_original_url=project_data.get('spmp_link'), std_original_url=project_data.get('std_link'),
                    ri_original_url=project_data.get('ri_link'), research_paper_original_url=project_data.get('research_paper_link'),
                    usability_test_original_url=project_data.get('usability_test_link'), presentation_original_url=project_data.get('presentation_link'),
                    source_code_original_url=project_data.get('source_code_link'), github_original_url=project_data.get('github_link'),
                    database_original_url=project_data.get('database_link'), readme_original_url=project_data.get('readme_link'),
                    srs_local_path=results['srs']['path'], sdd_local_path=results['sdd']['path'],
                    spmp_local_path=results['spmp']['path'], std_local_path=results['std']['path'],
                    ri_local_path=results['ri']['path'], research_paper_local_path=results['research_paper']['path'],
                    usability_test_local_path=results['usability_test']['path'], presentation_local_path=results['presentation']['path'],
                    source_code_local_path=results['source_code']['path'], database_local_path=results['database']['path'],
                    readme_local_path=results['readme']['path'],
                    srs_hash=results['srs']['hash'], sdd_hash=results['sdd']['hash'],
                    spmp_hash=results['spmp']['hash'], std_hash=results['std']['hash'],
                    ri_hash=results['ri']['hash'], research_paper_hash=results['research_paper']['hash'],
                    usability_test_hash=results['usability_test']['hash'], presentation_hash=results['presentation']['hash'],
                    source_code_hash=results['source_code']['hash'], database_hash=results['database']['hash'],
                    readme_hash=results['readme']['hash']
                )
                db.session.add(disk_entry)
                db.session.commit()
            except: 
                db.session.rollback()
                return {'status': 'failed', 'version': current_version, 'error': f"Critical Database Error"}
        
        return {'status': status, 'version': current_version, 'paths': {dt: results[dt]['path'] for dt in doc_types}, 'error': error_msg.strip()}
