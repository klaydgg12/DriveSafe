import os
import io
import re
import hashlib
import datetime
import logging
import pdfplumber
import time
import requests
from urllib.parse import urlparse, parse_qs, urlencode
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from models import db, ArchivalLedger

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
        
        self.identity_label = "ROBOT"
        self.creds = None
        if user_credentials:
            self.creds = user_credentials
            self.service = build('drive', 'v3', credentials=user_credentials, cache_discovery=False)
            self.identity_label = "TEACHER"
        elif service_account_json_path:
            try:
                if service_account_json_path.strip().startswith('{'):
                    import json
                    info = json.loads(service_account_json_path)
                    self.creds = service_account.Credentials.from_service_account_info(info, scopes=self.scope)
                else:
                    self.creds = service_account.Credentials.from_service_account_file(service_account_json_path, scopes=self.scope)
                self.service = build('drive', 'v3', credentials=self.creds, cache_discovery=False)
            except Exception as e:
                logger.error(f"Failed to init service account: {e}")
        
        if not hasattr(self, 'service'):
             raise ValueError("No authentication method provided for ArchivalEngine")
             
        self.archive_root = archive_root
        self.session = requests.Session()
        logger.info(f"ArchivalEngine Master v13 Initialized (Critical Update Detection Fix)")

    def _extract_file_id(self, url_or_id):
        if not url_or_id: return None, False
        s = str(url_or_id).replace('\\', '')
        match_folder = re.search(r'folders/([a-zA-Z0-9_-]{25,})', s)
        if match_folder: return match_folder.group(1), True
        match_file = re.search(r'/d/([a-zA-Z0-9_-]{25,})', s)
        if match_file: return match_file.group(1), False
        match_id = re.search(r'id=([a-zA-Z0-9_-]{25,})', s)
        if match_id: return match_id.group(1), False
        if len(s) >= 25 and '/' not in s and '.' not in s: return s, False
        return None, False

    def _get_file_metadata(self, file_id):
        try:
            return self.service.files().get(
                fileId=file_id, 
                fields='modifiedTime, md5Checksum, name, mimeType, size'
            ).execute()
        except: return None

    def _resolve_folder(self, folder_id, target_hint=None):
        try:
            query = f"'{folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query, fields="files(id, name, mimeType, modifiedTime, md5Checksum)", orderBy="modifiedTime desc"
            ).execute()
            files = results.get('files', [])
            if not files: return None, None
            if target_hint:
                hint = target_hint.lower().replace('finalized', '').replace('software', '').strip()
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

    def validate_binary(self, data, is_pdf=True):
        if not data or len(data) < 500: return False
        content_sample = data[:2000].lower()
        if b'<html' in content_sample:
            if any(x in content_sample for x in [b'google login', b'sign in', b'access denied']):
                return False
        if is_pdf and not data.startswith(b'%PDF-'): return False
        return True

    def _construct_url(self, file_id, original_url=None, is_google_doc=True, clean=False):
        params = {'format': 'pdf'}
        if not is_google_doc:
            params = {'export': 'download', 'id': file_id, 'confirm': 't'}
            base_url = "https://drive.google.com/uc"
        else:
            base_url = f"https://docs.google.com/document/d/{file_id}/export"

        if not clean and original_url and '?' in str(original_url):
            try:
                parsed = urlparse(str(original_url))
                query = parse_qs(parsed.query)
                for key in ['ouid', 'rtpof', 'authuser', 'usp']:
                    if key in query: params[key] = query[key][0]
            except: pass
            
        return f"{base_url}?{urlencode(params)}"

    def download_file(self, file_id, destination_path, original_url=None):
        try:
            meta = self._get_file_metadata(file_id)
            mime_type = meta.get('mimeType', '').lower() if meta else 'unknown'
            file_name = meta.get('name', 'unknown') if meta else 'Document'
            is_google = 'google-apps' in mime_type or (original_url and 'docs.google.com' in str(original_url))
            is_pdf_target = destination_path.lower().endswith('.pdf')
            
            logger.info(f"[{self.identity_label}] DOWNLOADING: {file_name}")

            final_data = None
            for attempt in range(2):
                try:
                    url = self._construct_url(file_id, original_url, is_google_doc=is_google, clean=(attempt == 1))
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                        'Accept': 'application/pdf,application/octet-stream,*/*',
                    }
                    if self.creds:
                        if hasattr(self.creds, 'valid') and not self.creds.valid: 
                            try: self.creds.refresh(requests.Session())
                            except: pass
                        headers['Authorization'] = f'Bearer {self.creds.token}'
                    
                    resp = self.session.get(url, headers=headers, timeout=60, allow_redirects=True)
                    if resp.status_code == 200 and self.validate_binary(resp.content, is_pdf=is_pdf_target):
                        final_data = resp.content
                        break
                except: pass

            if not final_data:
                try:
                    fh = io.BytesIO()
                    if is_google: request = self.service.files().export_media(fileId=file_id, mimeType='application/pdf')
                    else: request = self.service.files().get_media(fileId=file_id)
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done: _, done = downloader.next_chunk()
                    if self.validate_binary(fh.getvalue(), is_pdf=is_pdf_target):
                         final_data = fh.getvalue()
                except: pass

            if not final_data:
                raise Exception("Access Denied (Locked)")

            # Word to PDF conversion
            if is_pdf_target and not final_data.startswith(b'%PDF-'):
                if final_data.startswith(b'PK\x03\x04') or str(file_name).lower().endswith(('.docx', '.doc')):
                    temp_meta = {'name': f"CONV_{int(time.time())}", 'mimeType': 'application/vnd.google-apps.document'}
                    media = MediaIoBaseUpload(io.BytesIO(final_data), mimetype='application/octet-stream', resumable=True)
                    temp_file = self.service.files().create(body=temp_meta, media_body=media, fields='id').execute()
                    t_id = temp_file.get('id')
                    try:
                        time.sleep(5)
                        req = self.service.files().export_media(fileId=t_id, mimeType='application/pdf')
                        fh = io.BytesIO()
                        dld = MediaIoBaseDownload(fh, req)
                        d_done = False
                        while not d_done: _, d_done = dld.next_chunk()
                        data = fh.getvalue()
                        if data.startswith(b'%PDF-'): final_data = data
                    finally:
                        try: self.service.files().delete(fileId=t_id).execute()
                        except: pass

            if is_pdf_target and not final_data.startswith(b'%PDF-'):
                raise Exception("PDF Conversion Locked")

            with open(destination_path, 'wb') as f: f.write(final_data)
            return final_data
        except Exception as e:
            raise e

    def archive_project(self, project_data, workbook_name="Archives", batch_id=None, archived_by=None):
        project_id = str(project_data.get('project_id', 'Unknown')).strip().lower()
        project_title = project_data.get('project_title', 'Untitled')
        clean_title = str(project_title).replace(' ', '_').replace('/', '_').replace('\\', '_')
        academic_year = project_data.get('academic_year')
        
        base_project_dir = os.path.join(self.archive_root, workbook_name, academic_year, batch_id if batch_id else 'Direct', f"{project_id}_{clean_title}")
        os.makedirs(base_project_dir, exist_ok=True)
        
        last_record = ArchivalLedger.query.filter_by(
            project_id=project_id, academic_year=academic_year
        ).order_by(ArchivalLedger.version.desc()).first()
        
        doc_types = ['srs', 'sdd', 'spmp', 'std', 'ri', 'research_paper', 'usability_test', 'presentation', 'source_code', 'database', 'readme']
        results = {dt: {'path': None, 'hash': None, 'is_changed': False, 'bin': b'', 'ts': None, 'text': ''} for dt in doc_types}
        total_changed = 0
        error_msg = ""
        recovered_from_vault = 0

        for doc_type in doc_types:
            link = project_data.get(f'{doc_type}_link')
            raw_id, is_folder = self._extract_file_id(link)
            if not raw_id: continue
            
            file_id = raw_id
            metadata = None
            if is_folder: file_id, metadata = self._resolve_folder(raw_id, target_hint=doc_type.upper())
            else: metadata = self._get_file_metadata(file_id)

            if not file_id:
                error_msg += f"{doc_type.upper()}: Not found; "
                continue

            try:
                # --- CRITICAL: ACCURATE DEDUPLICATION ---
                drive_md5 = metadata.get('md5Checksum') if metadata else None
                results[doc_type]['ts'] = metadata.get('modifiedTime', 'Unknown') if metadata else 'Unknown'
                
                is_modified = True
                if last_record:
                    vault_hash = getattr(last_record, f"{doc_type}_hash")
                    # LAYER 0: Binary Check (Best for non-Docs)
                    if drive_md5 and vault_hash and drive_md5 == vault_hash:
                        is_modified = False
                    else:
                        # LAYER 1: Timestamp Check (Strict 2s Jitter)
                        try:
                            drive_dt = datetime.datetime.fromisoformat(results[doc_type]['ts'].replace('Z', '+00:00'))
                            vault_dt = last_record.archived_at.replace(tzinfo=datetime.timezone.utc)
                            # FIX: Only mark as unmodified if Google Time is NOT newer than Vault Time
                            if (drive_dt - vault_dt).total_seconds() <= 2: 
                                is_modified = False
                        except: pass

                if not is_modified:
                    results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                    results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash")
                    results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                    continue

                doc_dir = os.path.join(base_project_dir, doc_type.upper())
                os.makedirs(doc_dir, exist_ok=True)
                temp_path = os.path.join(doc_dir, f"TEMP_{doc_type.upper()}.pdf")

                try:
                    final_bytes = self.download_file(file_id, temp_path, original_url=link)
                    new_hash = hashlib.sha256(final_bytes).hexdigest()
                    
                    if last_record and new_hash == getattr(last_record, f"{doc_type}_hash"):
                        # Double-check: if the PDF byte hash is actually the same, skip versioning
                        results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                        results[doc_type]['hash'] = new_hash
                        results[doc_type]['bin'] = b''
                        if os.path.exists(temp_path): os.remove(temp_path)
                        continue

                    results[doc_type]['bin'] = final_bytes
                    results[doc_type]['hash'] = new_hash
                    total_changed += 1
                    results[doc_type]['is_changed'] = True
                    current_rev = last_record.version if last_record else 0
                    final_path = os.path.join(doc_dir, f"{clean_title}_{doc_type.upper()}_v{current_rev+1}.pdf")
                    os.rename(temp_path, final_path)
                    results[doc_type]['path'] = os.path.relpath(final_path, self.archive_root)
                except Exception as e:
                    # --- RESILIENCE ONLY FOR FAILURES, NOT UPDATES ---
                    if last_record and getattr(last_record, f"{doc_type}_local_path"):
                        # If download failed but a change WAS detected, this is bad. 
                        # We use the old file so the registry doesn't crash, but we must warn the user.
                        logger.warning(f"   [RESILIENCE] {doc_type.upper()} update failed, using old version.")
                        results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                        results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash")
                        results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                        recovered_from_vault += 1
                        error_msg += f"{doc_type.upper()}: Update failed, reused old file; "
                    else:
                        raise e

            except Exception as e:
                error_msg += f"{doc_type.upper()}: {str(e)[:30]}; "

        if total_changed == 0 and recovered_from_vault == 0:
            if last_record: return {'status': 'unchanged', 'version': last_record.version}
            else: return {'status': 'failed', 'error': error_msg.strip()}

        status = "partial" if error_msg else "archived"
        current_version = (last_record.version if last_record else 0) + 1

        MAX_BIN_SIZE = 15 * 1024 * 1024 
        def safe_bin(dt):
            b = results[dt]['bin']
            return b if b and len(b) <= MAX_BIN_SIZE else None

        try:
            entry = ArchivalLedger(
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
                readme_binary=safe_bin('readme')
            )
            db.session.add(entry)
            db.session.commit()
            return {'status': status, 'version': current_version, 'error': error_msg.strip()}
        except Exception as e:
            db.session.rollback()
            try:
                disk_entry = ArchivalLedger(
                    project_id=project_id, project_title=project_title, academic_year=academic_year,
                    workbook_name=workbook_name, archived_by=archived_by, batch_id=batch_id,
                    status=status, version=current_version, archived_at=datetime.datetime.utcnow(),
                    error_message=f"{error_msg.strip()} (Disk Only)".strip(),
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
                return {'status': status, 'version': current_version, 'error': error_msg.strip()}
            except:
                 db.session.rollback()
                 return {'status': 'failed', 'error': "Fatal DB Error"}
