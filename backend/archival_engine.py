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
        
        self.sa_service = None
        if service_account_json_path:
            try:
                if service_account_json_path.strip().startswith('{'):
                    import json
                    info = json.loads(service_account_json_path)
                    sa_creds = service_account.Credentials.from_service_account_info(info, scopes=self.scope)
                else:
                    sa_creds = service_account.Credentials.from_service_account_file(service_account_json_path, scopes=self.scope)
                self.sa_service = build('drive', 'v3', credentials=sa_creds, cache_discovery=False)
                if not hasattr(self, 'service'):
                    self.service = self.sa_service
            except Exception as e:
                logger.error(f"Failed to init service account fallback: {e}")
        
        if not hasattr(self, 'service'):
             raise ValueError("No authentication method provided for ArchivalEngine")
             
        self.archive_root = archive_root
        self.session = requests.Session()
        
        # State tracker for Raw Byte Hashing
        self._last_source_hash = None
        logger.info(f"ArchivalEngine Master v25 Initialized (Raw Byte Pipeline)")

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
        FIELDS = 'id, name, mimeType, modifiedTime, md5Checksum, shortcutDetails, size'
        def _fetch(svc, fid):
            return svc.files().get(fileId=fid, fields=FIELDS, supportsAllDrives=True).execute()
        meta = None
        try:
            meta = _fetch(self.service, file_id)
        except:
            if self.sa_service:
                try: meta = _fetch(self.sa_service, file_id)
                except: meta = None
        
        if meta and meta.get('mimeType') == 'application/vnd.google-apps.shortcut':
            target_id = (meta.get('shortcutDetails') or {}).get('targetId')
            if target_id and target_id != meta.get('id'):
                try:
                    resolved = _fetch(self.service, target_id)
                    if resolved: return resolved
                except:
                    if self.sa_service:
                        try: return _fetch(self.sa_service, target_id)
                        except: pass
        return meta

    HINT_KEYWORDS = {
        'SRS':            ['srs', 'requirements specification', 'software requirements'],
        'SDD':            ['sdd', 'design description', 'software design'],
        'SPMP':           ['spmp', 'project management plan', 'management plan'],
        'STD':            ['std', 'test description', 'software test'],
        'RI':             ['ri', 'research instrument'],
        'RESEARCH_PAPER': ['research paper', 'research_paper', 'manuscript'],
        'USABILITY_TEST': ['usability', 'ucd', 'user testing'],
        'PRESENTATION':   ['presentation', 'slides', 'ppt', 'defense', 'pitch'],
        'README':         ['readme', 'read me', 'read_me'],
        'SOURCE_CODE':    ['source', 'code', 'src'],
        'DATABASE':       ['database', 'schema', 'db dump', 'sql'],
    }

    def _list_children(self, folder_id, service=None):
        svc = service or self.service
        try:
            res = svc.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType, modifiedTime, md5Checksum, shortcutDetails)",
                orderBy="modifiedTime desc", supportsAllDrives=True, includeItemsFromAllDrives=True,
                pageSize=200
            ).execute()
            return res.get('files', []) or []
        except Exception as e:
            logger.warning(f"   [LIST] failed for folder {folder_id}: {str(e)[:120]}")
            return []

    def _score_candidate(self, file_meta, keywords):
        name = (file_meta.get('name') or '').lower()
        mime = (file_meta.get('mimeType') or '').lower()
        if mime == 'application/vnd.google-apps.folder': return -1
        score = 0
        for kw in keywords:
            if kw and kw in name: score += 10
        if 'pdf' in mime: score += 5
        elif 'wordprocessingml' in mime or 'msword' in mime: score += 4
        elif 'google-apps.document' in mime: score += 4
        elif 'presentation' in mime or 'powerpoint' in mime: score += 3
        elif 'spreadsheet' in mime or 'excel' in mime: score += 2
        elif mime == 'application/vnd.google-apps.shortcut': score += 1
        if any(x in name for x in ['old', 'backup', 'archive', 'draft (old)', 'deprecated']): score -= 3
        return score

    def _resolve_folder(self, folder_id, target_hint=None, _depth=0):
        try:
            files = self._list_children(folder_id)
            if not files and self.sa_service:
                files = self._list_children(folder_id, service=self.sa_service)
            if not files: return None, None

            keywords = []
            if target_hint:
                keywords = self.HINT_KEYWORDS.get(target_hint.upper(), [target_hint.lower()])

            best = None
            best_score = -999
            for f in files:
                s = self._score_candidate(f, keywords)
                if s > best_score:
                    best_score = s
                    best = f

            if (best is None or best_score <= 0) and _depth < 1:
                subfolders = [f for f in files if f.get('mimeType') == 'application/vnd.google-apps.folder']
                def sub_priority(sf):
                    n = (sf.get('name') or '').lower()
                    p = 0
                    for kw in keywords:
                        if kw and kw in n: p += 5
                    if any(x in n for x in ['final', 'finalized', 'submission', 'submit']): p += 3
                    return p
                subfolders.sort(key=sub_priority, reverse=True)
                for sf in subfolders[:5]:
                    fid_sub, meta_sub = self._resolve_folder(sf['id'], target_hint=target_hint, _depth=_depth+1)
                    if fid_sub:
                        return fid_sub, meta_sub

            if not best: return None, None
            fid = best['id']
            if best.get('mimeType') == 'application/vnd.google-apps.shortcut':
                fid = (best.get('shortcutDetails') or {}).get('targetId') or fid
            return fid, best
        except Exception as e:
            return None, None

    def _extract_text_from_pdf(self, file_path):
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages[:50]: text += (page.extract_text() or "")
            return text
        except: return ""

    def validate_binary(self, data, is_pdf=True):
        if not data: return False
        head = data[:2048].lstrip().lower()
        if head.startswith(b'<!doctype html') or head.startswith(b'<html') or b'<html' in head[:512]:
            return False
        if is_pdf:
            if len(data) < 500: return False
            if not data.startswith(b'%PDF-'): return False
        else:
            if len(data) < 4: return False
        return True

    def _construct_url(self, file_id, original_url=None, is_google_doc=True, clean=False, inject_token=None):
        params = {'format': 'pdf'}
        if not is_google_doc:
            params = {'export': 'download', 'id': file_id, 'confirm': 't'}
            base_url = "https://drive.google.com/uc"
        else:
            base_url = f"https://docs.google.com/document/d/{file_id}/export"
        if inject_token: params['access_token'] = inject_token
        if not clean and original_url and '?' in str(original_url):
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
        strict_pdf_check = is_pdf_target and is_google

        logger.info(f"[{self.identity_label}] ARCHIVING: {file_name} (mime={mime_type or 'n/a'}, native={is_google})")
        final_data = None

        # 1. Mirror
        try:
            url = self._construct_url(file_id, original_url, is_google_doc=is_google, clean=False)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'application/pdf,application/octet-stream,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://docs.google.com/',
                'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Upgrade-Insecure-Requests': '1',
            }
            if self.creds:
                if hasattr(self.creds, 'valid') and not self.creds.valid: self.creds.refresh(requests.Session())
                headers['Authorization'] = f'Bearer {self.creds.token}'
            resp = self.session.get(url, headers=headers, timeout=60, allow_redirects=True)
            if resp.status_code == 200 and self.validate_binary(resp.content, is_pdf=strict_pdf_check):
                final_data = resp.content
        except: pass

        # 2. Token Injection
        if not final_data and self.creds:
            try:
                url = self._construct_url(file_id, original_url, is_google_doc=is_google, clean=True, inject_token=self.creds.token)
                resp = self.session.get(url, timeout=60, allow_redirects=True)
                if resp.status_code == 200 and self.validate_binary(resp.content, is_pdf=strict_pdf_check):
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
                if self.validate_binary(fh.getvalue(), is_pdf=strict_pdf_check): final_data = fh.getvalue()
            except Exception as e:
                logger.warning(f"   [API] get_media failed for {file_name}: {str(e)[:120]}")

        # 4. Service Account Override
        if not final_data and self.sa_service:
            try:
                fh = io.BytesIO()
                if is_google: request = self.sa_service.files().export_media(fileId=file_id, mimeType='application/pdf')
                else: request = self.sa_service.files().get_media(fileId=file_id, supportsAllDrives=True)
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done: _, done = downloader.next_chunk()
                if self.validate_binary(fh.getvalue(), is_pdf=strict_pdf_check): final_data = fh.getvalue()
            except Exception as e:
                logger.warning(f"   [SA] fallback failed for {file_name}: {str(e)[:120]}")

        if not final_data: raise Exception(f"Access Denied for {file_name} (mime={mime_type or 'unknown'})")

        # --- CRITICAL FIX: RAW SOURCE HASH ---
        # Hash the raw bytes downloaded BEFORE any lossy Google conversion occurs.
        # This guarantees deterministic hashes for uploaded docs (.docx, .md, .pptx)
        self._last_source_hash = hashlib.sha256(final_data).hexdigest()

        # Office/Text -> PDF conversion
        if is_pdf_target and not final_data.startswith(b'%PDF-'):
            lower_name = str(file_name).lower()
            is_office = final_data.startswith(b'PK\x03\x04') or lower_name.endswith(('.docx', '.doc'))
            is_text = (
                lower_name.endswith(('.md', '.markdown', '.txt', '.rst', '.readme'))
                or lower_name == 'readme'
                or 'text/' in (mime_type or '')
                or 'markdown' in (mime_type or '')
            )
            if is_office or is_text:
                upload_mime = 'text/plain' if (is_text and not is_office) else 'application/octet-stream'
                temp_meta = {'name': f"CONV_{int(time.time())}", 'mimeType': 'application/vnd.google-apps.document'}
                media = MediaIoBaseUpload(io.BytesIO(final_data), mimetype=upload_mime, resumable=True)
                try:
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
                except Exception as e:
                    logger.warning(f"   [CONVERT] upload-as-gdoc failed for {file_name}: {str(e)[:120]}")

        if is_pdf_target and not final_data.startswith(b'%PDF-'):
            raise Exception(f"PDF Conversion Locked ({file_name}, mime={mime_type or 'unknown'})")
            
        with open(destination_path, 'wb') as f: f.write(final_data)
        return final_data

    @staticmethod
    def _canonical_key(value, default=''):
        if value is None: return default
        s = str(value)
        s = s.replace('\xa0', ' ').replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
        s = re.sub(r'\s+', ' ', s)
        return s.strip().lower() or default

    def archive_project(self, project_data, workbook_name="Archives", batch_id=None, archived_by=None):
        project_id = self._canonical_key(project_data.get('project_id'), 'unknown')
        project_title = str(project_data.get('project_title', 'Untitled')).strip()
        clean_title = project_title.replace(' ', '_').replace('/', '_').replace('\\', '_')
        academic_year = self._canonical_key(project_data.get('academic_year'), 'general')

        base_project_dir = os.path.join(self.archive_root, workbook_name, academic_year, batch_id if batch_id else 'Direct', f"{project_id}_{clean_title}")
        os.makedirs(base_project_dir, exist_ok=True)

        last_record = ArchivalLedger.query.filter_by(
            project_id=project_id, academic_year=academic_year
        ).order_by(ArchivalLedger.version.desc()).first()

        if last_record:
            logger.info(f"   [LOCK-HIT] Found prior record for key='{project_id}@{academic_year}': v={last_record.version}, archived_at={last_record.archived_at}, workbook={last_record.workbook_name}")
        else:
            other = ArchivalLedger.query.filter_by(project_id=project_id).order_by(ArchivalLedger.version.desc()).first()
            if other:
                logger.warning(f"   [LOCK-MISS] No record for key='{project_id}@{academic_year}', BUT same project_id exists under academic_year='{other.academic_year}' (v={other.version}).")
            else:
                logger.info(f"   [FAST-PATH] No prior record for {project_id}@{academic_year}; skipping all dedup tiers (v1 cold archive).")

        doc_types = ['srs', 'sdd', 'spmp', 'std', 'ri', 'research_paper', 'usability_test', 'presentation', 'source_code', 'database', 'readme']
        results = {dt: {'path': None, 'hash': None, 'is_changed': False, 'is_backfill': False, 'bin': b'', 'ts': None, 'text': '', 'url': None} for dt in doc_types}
        total_changed = 0   
        backfilled = 0      
        error_msg = ""

        for doc_type in doc_types:
            link = project_data.get(f'{doc_type}_link')
            results[doc_type]['url'] = link
            
            if not link and last_record:
                old_path = getattr(last_record, f"{doc_type}_local_path", None)
                if old_path:
                    results[doc_type]['path'] = old_path
                    results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash", None)
                    results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text", None)
                    results[doc_type]['url'] = getattr(last_record, f"{doc_type}_original_url", None)
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
                results[doc_type]['ts'] = metadata.get('modifiedTime', 'Unknown') if metadata else 'Unknown'
                mime_type = metadata.get('mimeType', '').lower() if metadata else ''
                is_google_doc = 'google-apps' in mime_type
                
                # We reset the raw byte tracker before downloading
                self._last_source_hash = None

                doc_dir = os.path.join(base_project_dir, doc_type.upper())
                os.makedirs(doc_dir, exist_ok=True)
                temp_path = os.path.join(doc_dir, f"TEMP_{doc_type.upper()}.pdf")

                try:
                    final_bytes = self.download_file(file_id, temp_path, original_url=link)
                    new_text = self._extract_text_from_pdf(temp_path) or ""

                    # =============================================================
                    # CANONICAL CONTENT FINGERPRINT (Tier 1 hash)
                    # =============================================================
                    # Problem we are solving: Google's PDF export of a native gdoc is non-deterministic
                    # (fresh timestamp + document-id every call), so hashing the EXPORTED bytes makes
                    # Tier 1 miss every single time for SRS/SDD-style gdoc links. That's why your screenshot
                    # shows SRS at v2 with a different hash even though nothing changed.
                    #
                    # Fix: hash the CONTENT (alphanumeric-stripped extracted text), not the bytes. The
                    # content is invariant to Drive's metadata noise, so identical document content always
                    # produces the same hash regardless of how many times you re-archive or which sheet
                    # you launch from.
                    #
                    # For files where text extraction is unreliable (image-only PDFs, code, etc.) we fall
                    # back to the raw Drive bytes hash (deterministic for uploaded files).
                    #
                    # Hash is plain 64-char SHA-256 (fits the existing String(64) column). The schema
                    # cannot tell content-hashes from raw-hashes apart, but it doesn't need to: Tier 1
                    # just compares equality. When Tier 1 misses (e.g. legacy v1 row stored a raw-byte
                    # hash and the new run produces a content hash), Tier 2/3 catches the duplicate via
                    # text and soft-migrates the row to the new content-hash format.
                    text_clean_for_hash = re.sub(r'\W+', '', new_text).lower()
                    if len(text_clean_for_hash) >= 50:
                        new_hash = hashlib.sha256(text_clean_for_hash.encode('utf-8')).hexdigest()
                        hash_kind = "content"
                    else:
                        new_hash = self._last_source_hash or hashlib.sha256(final_bytes).hexdigest()
                        hash_kind = "raw-fallback"

                    if last_record:
                        # TIER 1: CANONICAL HASH MATCH
                        old_hash = getattr(last_record, f"{doc_type}_hash", None)
                        drive_md5 = metadata.get('md5Checksum') if metadata else "N/A"
                        logger.info(f"   [TIER-1] {doc_type.upper()} ({hash_kind}, text_len={len(text_clean_for_hash)}): old={(old_hash or 'NULL')[:16]}..., new={new_hash[:16]}..., drive_md5={drive_md5}")

                        if old_hash and new_hash == old_hash:
                            results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path", None)
                            results[doc_type]['hash'] = old_hash
                            results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text", None) or new_text
                            if os.path.exists(temp_path): os.remove(temp_path)
                            logger.info(f"   [DEDUP-HIT T1] {doc_type.upper()}: deterministic bit-identical with v{last_record.version}")
                            continue

                        # TIER 2 & 3: DNA & AI DEDUPLICATION 
                        old_text = getattr(last_record, f"{doc_type}_text", None) or ""
                        if not old_text:
                            old_path_disk = getattr(last_record, f"{doc_type}_local_path", None)
                            if old_path_disk:
                                abs_old = old_path_disk if os.path.isabs(old_path_disk) else os.path.join(self.archive_root, old_path_disk)
                                if os.path.exists(abs_old):
                                    old_text = self._extract_text_from_pdf(abs_old) or ""

                        def get_clean_text(t): return re.sub(r'\W+', '', str(t)).lower() if t else ""
                        new_clean = get_clean_text(new_text)
                        old_clean = get_clean_text(old_text)

                        is_dup = False
                        tier_hit = None
                        
                        # Tier 2: alphanumeric DNA
                        if new_clean and new_clean == old_clean:
                            is_dup = True
                            tier_hit = 'T2'
                        # Tier 3: AI Similarity
                        elif AI_AVAILABLE and new_clean and old_clean:
                            try:
                                vect = TfidfVectorizer(min_df=1)
                                tfidf = vect.fit_transform([old_text, new_text])
                                sim = float((tfidf * tfidf.T).toarray()[0, 1])
                                logger.info(f"   [TIER-3] {doc_type.upper()} cosine sim = {sim:.4f}")
                                if sim > 0.98:
                                    is_dup = True
                                    tier_hit = 'T3'
                            except Exception as e:
                                logger.warning(f"   [TIER-3] cosine failed for {doc_type.upper()}: {str(e)[:80]}")

                        if is_dup:
                            results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path", None)
                            
                            # SOFT MIGRATION: 
                            # If T2/T3 found it's a duplicate, we update the hash to the NEW Raw Byte Hash 
                            # in memory, so future runs hit Tier 1 instantly.
                            results[doc_type]['hash'] = new_hash 
                            
                            results[doc_type]['text'] = old_text or new_text
                            
                            # Soft Migration flag to write to database
                            results[doc_type]['is_backfill'] = True 
                            backfilled += 1
                            
                            if os.path.exists(temp_path): os.remove(temp_path)
                            logger.info(f"   [DEDUP-HIT {tier_hit}] {doc_type.upper()}: Soft-Migrating to raw-byte hash on v{last_record.version}")
                            continue

                    results[doc_type]['bin'] = final_bytes
                    results[doc_type]['hash'] = new_hash
                    results[doc_type]['text'] = new_text
                    
                    prev_hash_for_doc = getattr(last_record, f"{doc_type}_hash") if last_record else None
                    is_backfill = bool(last_record) and not prev_hash_for_doc
                    
                    if is_backfill:
                        backfilled += 1
                        results[doc_type]['is_backfill'] = True
                        file_version = last_record.version  
                        logger.info(f"   [BACKFILL] {doc_type.upper()} was missing in v{file_version}; filling without bump.")
                    else:
                        total_changed += 1
                        results[doc_type]['is_changed'] = True
                        file_version = (last_record.version if last_record else 0) + 1
                        
                    final_path = os.path.join(doc_dir, f"{clean_title}_{doc_type.upper()}_v{file_version}.pdf")
                    os.rename(temp_path, final_path)
                    results[doc_type]['path'] = os.path.relpath(final_path, self.archive_root)
                except Exception as e:
                    if last_record and getattr(last_record, f"{doc_type}_local_path", None):
                        results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path", None)
                        results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash", None)
                        results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text", None)
                    else: raise e
            except Exception as e:
                error_msg += f"{doc_type.upper()}: {str(e)[:50]}; "

        if total_changed == 0:
            if last_record and backfilled > 0:
                try:
                    MAX_BIN_SIZE_BF = 15 * 1024 * 1024
                    for dt in doc_types:
                        if not results[dt].get('is_backfill'): continue
                        setattr(last_record, f"{dt}_local_path", results[dt]['path'])
                        setattr(last_record, f"{dt}_hash", results[dt]['hash']) # Upgrades to raw hash
                        setattr(last_record, f"{dt}_original_url", results[dt]['url'])
                        if hasattr(last_record, f"{dt}_text"):
                            setattr(last_record, f"{dt}_text", results[dt]['text'])
                        if hasattr(last_record, f"{dt}_binary"):
                            b = results[dt].get('bin')
                            setattr(last_record, f"{dt}_binary", b if b and len(b) <= MAX_BIN_SIZE_BF else None)
                    db.session.commit()
                    logger.info(f"   [BACKFILL/MIGRATE] Saved {backfilled} update(s) to v{last_record.version} without version bump.")
                    return {'status': 'unchanged', 'version': last_record.version, 'backfilled': backfilled}
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Backfill update failed: {e}")
                    return {'status': 'unchanged', 'version': last_record.version, 'error': f"backfill failed: {str(e)[:80]}"}
            if last_record: return {'status': 'unchanged', 'version': last_record.version}
            else: return {'status': 'failed', 'error': error_msg.strip()}

        status = "partial" if error_msg else "archived"
        current_version = (last_record.version if last_record else 0) + 1
        MAX_BIN_SIZE = 15 * 1024 * 1024 
        def safe_bin(dt):
            b = results[dt].get('bin')
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
                source_code_original_url=results['source_code']['url'], github_original_url=project_data.get('github_link'),
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
                    source_code_original_url=results['source_code']['url'], github_original_url=project_data.get('github_link'),
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
                    readme_hash=results['readme']['hash']
                )
                db.session.add(disk_entry)
                db.session.commit()
                return {'status': status, 'version': current_version, 'error': error_msg.strip()}
            except Exception as e2:
                 db.session.rollback()
                 logger.error(f"   [DB-FATAL] Both primary and disk-only commits failed for {project_id}@{academic_year} v{current_version}: primary={str(e)[:200]} ; disk={str(e2)[:200]}", exc_info=True)
                 return {'status': 'failed', 'error': f"DB commit failed: {str(e2)[:120]}"}
