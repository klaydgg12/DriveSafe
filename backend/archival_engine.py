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

# AI Import for Tier 3
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

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
        self.identity_label = "TEACHER" if user_credentials else "ROBOT"
        self.creds = user_credentials
        
        if user_credentials:
            self.service = build('drive', 'v3', credentials=user_credentials, cache_discovery=False)
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
        logger.info(f"ArchivalEngine Master v22 Initialized (Content-Strict Protocol)")

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
                fields='id, name, mimeType, modifiedTime, md5Checksum, shortcutDetails, size',
                supportsAllDrives=True
            ).execute()
        except: return None

    def _resolve_folder(self, folder_id, target_hint=None):
        try:
            query = f"'{folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query, 
                fields="files(id, name, mimeType, modifiedTime, md5Checksum, shortcutDetails)", 
                orderBy="modifiedTime desc",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            files = results.get('files', [])
            if not files: return None, None
            
            selected_file = None
            if target_hint:
                hint = target_hint.lower().replace('finalized', '').replace('software', '').strip()
                for f in files:
                    if hint in f['name'].lower(): 
                        selected_file = f
                        break
            
            if not selected_file:
                for f in files:
                    if 'pdf' in f['mimeType'].lower() or 'document' in f['mimeType'].lower():
                        selected_file = f
                        break
            
            if not selected_file: selected_file = files[0]
            fid = selected_file['id']
            if selected_file.get('mimeType') == 'application/vnd.google-apps.shortcut':
                fid = selected_file.get('shortcutDetails', {}).get('targetId') or fid
                return fid, self._get_file_metadata(fid)
            return fid, selected_file
        except Exception as e:
            logger.error(f"Folder resolution failed for {folder_id}: {e}")
            return None, None

    def _extract_text_from_pdf(self, file_path):
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages[:50]: 
                    text += (page.extract_text() or "")
            return text
        except: return ""

    def validate_binary(self, data, is_pdf=True):
        if not data or len(data) < 500: return False
        content_sample = data[:2000].lower()
        if b'<html' in content_sample:
            if any(x in content_sample for x in [b'google login', b'sign in', b'access denied']):
                return False
        if is_pdf and not data.startswith(b'%PDF-'): return False
        return True

    def _construct_url(self, file_id, original_url=None, is_google_doc=True, inject_token=None):
        params = {'format': 'pdf'}
        if not is_google_doc:
            params = {'export': 'download', 'id': file_id, 'confirm': 't'}
            base_url = "https://drive.google.com/uc"
        else:
            base_url = f"https://docs.google.com/document/d/{file_id}/export"
        if inject_token: params['access_token'] = inject_token
        if original_url and '?' in str(original_url):
            try:
                parsed = urlparse(str(original_url))
                query = parse_qs(parsed.query)
                for key in ['ouid', 'rtpof', 'authuser', 'usp']:
                    if key in query: params[key] = query[key][0]
            except: pass
        return f"{base_url}?{urlencode(params)}"

    def download_file(self, file_id, destination_path, original_url=None):
        meta = self._get_file_metadata(file_id)
        if meta and meta.get('id'): file_id = meta.get('id')
        
        mime_type = meta.get('mimeType', '').lower() if meta else 'unknown'
        file_name = meta.get('name', 'unknown') if meta else 'Document'
        is_google = 'google-apps' in mime_type or (original_url and 'docs.google.com' in str(original_url))
        is_pdf_target = destination_path.lower().endswith('.pdf')
        
        logger.info(f"[{self.identity_label}] DOWNLOADING: {file_name}")
        final_data = None
        
        # 1. Mirror
        try:
            url = self._construct_url(file_id, original_url, is_google_doc=is_google)
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
            if self.creds:
                if hasattr(self.creds, 'valid') and not self.creds.valid: 
                    try: self.creds.refresh(requests.Session())
                    except: pass
                headers['Authorization'] = f'Bearer {self.creds.token}'
            resp = self.session.get(url, headers=headers, timeout=60, allow_redirects=True)
            if resp.status_code == 200 and self.validate_binary(resp.content, is_pdf=is_pdf_target):
                final_data = resp.content
        except: pass

        # 2. Token Injection
        if not final_data and self.creds:
            try:
                url = self._construct_url(file_id, original_url, is_google_doc=is_google, inject_token=self.creds.token)
                resp = self.session.get(url, timeout=60, allow_redirects=True)
                if resp.status_code == 200 and self.validate_binary(resp.content, is_pdf=is_pdf_target):
                    final_data = resp.content
            except: pass

        # 3. API
        if not final_data:
            try:
                fh = io.BytesIO()
                if is_google: request = self.service.files().export_media(fileId=file_id, mimeType='application/pdf')
                else: request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done: _, done = downloader.next_chunk()
                if self.validate_binary(fh.getvalue(), is_pdf=is_pdf_target): final_data = fh.getvalue()
            except: pass

        if not final_data: raise Exception("Access Denied (Google Lock)")

        # Word to PDF conversion
        if is_pdf_target and not final_data.startswith(b'%PDF-'):
            if final_data.startswith(b'PK\x03\x04') or str(file_name).lower().endswith(('.docx', '.doc')):
                temp_meta = {'name': f"CONV_{int(time.time())}", 'mimeType': 'application/vnd.google-apps.document'}
                media = MediaIoBaseUpload(io.BytesIO(final_data), mimetype='application/octet-stream', resumable=True)
                temp_file = self.service.files().create(body=temp_meta, media_body=media, fields='id', supportsAllDrives=True).execute()
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
                    try: self.service.files().delete(fileId=t_id, supportsAllDrives=True).execute()
                    except: pass

        if is_pdf_target and not final_data.startswith(b'%PDF-'): raise Exception("PDF Conversion Locked")
        with open(destination_path, 'wb') as f: f.write(final_data)
        return final_data

    def archive_project(self, project_data, workbook_name="Archives", batch_id=None, archived_by=None):
        project_id = str(project_data.get('project_id', 'Unknown')).strip().lower()
        project_title = project_data.get('project_title', 'Untitled')
        clean_title = str(project_title).replace(' ', '_').replace('/', '_').replace('\\', '_')
        academic_year = project_data.get('academic_year', 'General').strip()
        
        base_project_dir = os.path.join(self.archive_root, workbook_name, academic_year, batch_id if batch_id else 'Direct', f"{project_id}_{clean_title}")
        os.makedirs(base_project_dir, exist_ok=True)
        
        # --- GLOBAL HISTORY (Ignore workbook here to find existing records for deduplication) ---
        last_record = ArchivalLedger.query.filter_by(
            project_id=project_id, academic_year=academic_year
        ).order_by(ArchivalLedger.version.desc()).first()
        
        doc_types = ['srs', 'sdd', 'spmp', 'std', 'ri', 'research_paper', 'usability_test', 'presentation', 'source_code', 'database', 'readme']
        results = {dt: {'path': None, 'hash': None, 'is_changed': False, 'bin': b'', 'ts': None, 'text': '', 'url': None} for dt in doc_types}
        total_changed = 0
        error_msg = ""

        for doc_type in doc_types:
            link = project_data.get(f'{doc_type}_link')
            results[doc_type]['url'] = link
            
            # --- TIER 0: GAP-FILLING PERSISTENCE (Crucial for sheet switching) ---
            if not link and last_record:
                old_path = getattr(last_record, f"{doc_type}_local_path")
                if old_path:
                    logger.info(f"   [INHERITING] {doc_type.upper()} inherited from global project history.")
                    results[doc_type]['path'] = old_path
                    results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash")
                    results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                    results[doc_type]['url'] = getattr(last_record, f"{doc_type}_original_url")
                    continue
            
            if not link: continue
            
            raw_id, is_folder = self._extract_file_id(link)
            if not raw_id: continue
            
            file_id = raw_id
            metadata = None
            if is_folder: file_id, metadata = self._resolve_folder(raw_id, target_hint=doc_type.upper())
            else: metadata = self._get_file_metadata(file_id)
            if not file_id: continue

            try:
                # --- TIER 1: METADATA FINGERPRINT (MD5 & Time) ---
                drive_md5 = metadata.get('md5Checksum') if metadata else None
                results[doc_type]['ts'] = metadata.get('modifiedTime', 'Unknown') if metadata else 'Unknown'
                is_google_doc = doc_type in ['srs', 'sdd', 'spmp', 'std', 'ri', 'research_paper', 'usability_test', 'readme']
                
                is_modified = True
                if last_record:
                    vault_hash = getattr(last_record, f"{doc_type}_hash")
                    if drive_md5 and vault_hash and drive_md5 == vault_hash:
                        is_modified = False
                    else:
                        try:
                            drive_dt = datetime.datetime.fromisoformat(results[doc_type]['ts'].replace('Z', '+00:00'))
                            vault_dt = last_record.archived_at.replace(tzinfo=datetime.timezone.utc)
                            if (drive_dt - vault_dt).total_seconds() <= 5: 
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
                    
                    if last_record:
                        # --- TIER 2: BIT MATCH (Strict SHA-256) ---
                        old_hash = getattr(last_record, f"{doc_type}_hash")
                        if new_hash == old_hash:
                            logger.info(f"   [TIER 2 SKIP] Bit match for {doc_type.upper()}.")
                            results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                            results[doc_type]['hash'] = old_hash
                            results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                            if os.path.exists(temp_path): os.remove(temp_path)
                            continue

                        # --- TIER 3: CONTENT DNA (Alphanumeric Match) ---
                        if is_google_doc:
                            new_text = self._extract_text_from_pdf(temp_path)
                            old_text = getattr(last_record, f"{doc_type}_text")
                            
                            def get_clean_text(t):
                                return re.sub(r'\W+', '', t).lower() if t else ""
                                
                            new_clean = get_clean_text(new_text)
                            old_clean = get_clean_text(old_text)
                            
                            is_match = False
                            if new_clean == old_clean:
                                is_match = True
                                logger.info(f"   [TIER 3 SKIP] Alphanumeric match for {doc_type.upper()}.")
                            elif AI_AVAILABLE and new_clean and old_clean:
                                try:
                                    vect = TfidfVectorizer(min_df=1)
                                    tfidf = vect.fit_transform([old_text, new_text])
                                    sim = (tfidf * tfidf.T).toarray()[0,1]
                                    if sim > 0.995:
                                        is_match = True
                                        logger.info(f"   [TIER 3 SKIP] AI Similarity {sim:.2%}.")
                                except: pass
                                
                            if is_match:
                                results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                                results[doc_type]['hash'] = old_hash
                                results[doc_type]['text'] = old_text
                                if os.path.exists(temp_path): os.remove(temp_path)
                                continue

                    # CONTENT IS NEW
                    new_text = new_text if 'new_text' in locals() else (self._extract_text_from_pdf(temp_path) if is_google_doc else "")
                    results[doc_type]['bin'] = final_bytes
                    results[doc_type]['hash'] = new_hash
                    results[doc_type]['text'] = new_text
                    total_changed += 1
                    results[doc_type]['is_changed'] = True
                    current_rev = last_record.version if last_record else 0
                    final_path = os.path.join(doc_dir, f"{clean_title}_{doc_type.upper()}_v{current_rev+1}.pdf")
                    os.rename(temp_path, final_path)
                    results[doc_type]['path'] = os.path.relpath(final_path, self.archive_root)
                except Exception as e:
                    # RECOVER FROM VAULT on failure, but don't mark as changed
                    if last_record and getattr(last_record, f"{doc_type}_local_path"):
                        results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                        results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash")
                        results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                        logger.info(f"   [RESILIENCE] {doc_type.upper()} failure, using vault copy (No version jump).")
                    else: raise e
            except Exception as e:
                error_msg += f"{doc_type.upper()}: {str(e)[:50]}; "

        # --- THE VERSION GATEKEEPER (SMOKING GUN FIX) ---
        # If total_changed is 0, it means EVERYTHING was either inherited, identical, or recovered.
        # We must NOT create a new record in this case.
        if total_changed == 0:
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
                srs_original_url=results['srs']['url'], sdd_original_url=results['sdd']['url'],
                spmp_original_url=results['spmp']['url'], std_original_url=results['std']['url'],
                ri_original_url=results['ri']['url'], research_paper_original_url=results['research_paper']['url'],
                usability_test_original_url=results['usability_test']['url'], presentation_original_url=results['presentation']['url'],
                source_code_original_url=results['source_code']['url'], github_original_url=results['github_link'] if results['readme']['url'] else None,
                database_original_url=results['database']['url'], readme_original_url=results['readme']['url'],
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
                    srs_original_url=results['srs']['url'], sdd_original_url=results['sdd']['url'],
                    spmp_original_url=results['spmp']['url'], std_original_url=results['std']['url'],
                    ri_original_url=results['ri']['url'], research_paper_original_url=results['research_paper']['url'],
                    usability_test_original_url=results['usability_test']['url'], presentation_original_url=results['presentation']['url'],
                    source_code_original_url=results['source_code']['url'], database_original_url=results['database']['url'],
                    readme_original_url=results['readme']['url'],
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
