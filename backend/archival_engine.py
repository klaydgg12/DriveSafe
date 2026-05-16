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
        if not url: return None
        match = re.search(r'/d/([a-zA-Z0-9_-]{25,})', url)
        if match: return match.group(1)
        match = re.search(r'id=([a-zA-Z0-9_-]{25,})', url)
        if match: return match.group(1)
        return None

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
        """
        Deduplication Engine: Returns (type, score, original_title, original_project_id, version)
        """
        exact_match = ArchivalLedger.query.filter(
            (ArchivalLedger.srs_hash == new_file_hash) | 
            (ArchivalLedger.sdd_hash == new_file_hash) |
            (ArchivalLedger.spmp_hash == new_file_hash) |
            (ArchivalLedger.std_hash == new_file_hash) |
            (ArchivalLedger.ri_hash == new_file_hash)
        ).first()
        
        if exact_match:
            return "Exact Duplicate", 1.0, exact_match.project_title, exact_match.project_id, exact_match.version

        if not new_text or len(new_text) < 100: 
            return None, 0, None, None, None

        query = ArchivalLedger.query.filter(ArchivalLedger.status == 'archived')
        if current_project_id:
            past_records = query.filter(ArchivalLedger.project_id == current_project_id).all()
        else:
            past_records = query.all()

        if not past_records:
            return None, 0, None, None, None

        corpus = [new_text]
        metadata_map = [] 
        
        for record in past_records:
            for dt in ['srs', 'sdd', 'spmp', 'std', 'ri']:
                past_text = getattr(record, f"{dt}_text")
                if past_text and len(past_text) > 100:
                    corpus.append(past_text)
                    metadata_map.append({
                        'title': record.project_title,
                        'id': record.project_id,
                        'version': record.version,
                        'dt': dt
                    })

        if len(corpus) <= 1:
            return None, 0, None, None, None

        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(corpus)
            cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            max_sim_idx = cosine_similarities.argmax()
            max_sim_score = cosine_similarities[max_sim_idx]
            
            if max_sim_score > 0.999:
                match_meta = metadata_map[max_sim_idx]
                return "Semantic Duplicate", max_sim_score, match_meta['title'], match_meta['id'], match_meta['version']
                
        except Exception as e:
            logger.error(f"AI Batch Processing Failed: {e}")
            
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
            logger.error(f"Download Error for {file_id}: {e}")
            raise e

    def _get_file_metadata(self, file_id):
        try:
            return self.service.files().get(
                fileId=file_id, 
                fields='mimeType, name, modifiedTime, md5Checksum'
            ).execute()
        except Exception as e:
            logger.error(f"Failed to fetch metadata for {file_id}: {e}")
            return None

    def archive_project(self, project_data, workbook_name="Archives", batch_id=None):
        project_id = project_data.get('project_id', 'Unknown')
        clean_title = project_data.get('project_title', 'Untitled').replace(' ', '_').replace('/', '_')
        clean_id = str(project_id).replace(' ', '_').replace('/', '_')
        folder_name = f"{clean_id}_{clean_title}" if clean_id and clean_id != 'None' else clean_title
        academic_year = project_data.get('academic_year')
        
        base_project_dir = os.path.join(self.archive_root, workbook_name, folder_name)
        os.makedirs(base_project_dir, exist_ok=True)
        
        last_record = ArchivalLedger.query.filter_by(
            project_id=project_id,
            academic_year=academic_year,
            status='archived'
        ).order_by(ArchivalLedger.version.desc()).first()
        
        doc_types = ['srs', 'sdd', 'spmp', 'std', 'ri', 'source_code', 'database', 'readme']
        results = {dt: {'path': None, 'hash': None, 'is_changed': False, 'bin': None, 'ts': None} for dt in doc_types}
        error_msg = ""
        total_changed = 0
        processed_file_ids = {}

        for doc_type in doc_types:
            link = project_data.get(f'{doc_type}_link')
            file_id = self._extract_file_id(link)
            
            if file_id:
                if file_id in processed_file_ids:
                    res = processed_file_ids[file_id]['data']
                    results[doc_type] = res
                    if res.get('is_changed'): total_changed += 1
                    continue

                try:
                    # 1. GRANULAR METADATA FETCH
                    metadata = self._get_file_metadata(file_id)
                    current_drive_ts = metadata.get('modifiedTime', 'Unknown')
                    results[doc_type]['ts'] = current_drive_ts
                    
                    # 2. GRANULAR TIMESTAMP VERSIONING
                    is_modified = True
                    if last_record:
                        last_stored_ts = getattr(last_record, f"{doc_type}_modified_time")
                        
                        # IF THE CLOCK HAS MOVED, IT IS A NEW VERSION. 100% SENSITIVE.
                        if last_stored_ts == current_drive_ts:
                            logger.info(f"SKIP: {doc_type.upper()} timestamp matches vault ({current_drive_ts}).")
                            is_modified = False
                        else:
                            logger.info(f"CHANGE: {doc_type.upper()} modified in Drive! (Vault: {last_stored_ts} -> Drive: {current_drive_ts})")
                            import time
                            time.sleep(5) # Allow Google Doc to bake PDF

                    if not is_modified:
                        results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                        results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash")
                        results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                        results[doc_type]['bin'] = None
                        processed_file_ids[file_id] = {'data': results[doc_type]}
                        continue

                    # 3. PROCESS THE NEW VERSION
                    doc_dir = os.path.join(base_project_dir, doc_type.upper())
                    os.makedirs(doc_dir, exist_ok=True)
                    temp_path = os.path.join(doc_dir, f"COMPARE_{doc_type.upper()}.pdf")
                    actual_temp_path = self.download_file(file_id, temp_path)
                    
                    with open(actual_temp_path, "rb") as f:
                        file_binary = f.read()
                        results[doc_type]['bin'] = file_binary
                    
                    file_hash = metadata.get('md5Checksum') or self._compute_hash(actual_temp_path)
                    results[doc_type]['hash'] = file_hash
                    
                    file_text = ""
                    if doc_type in ['srs', 'sdd', 'spmp', 'std', 'ri', 'readme']:
                        file_text = self._extract_text_from_pdf(actual_temp_path)
                    results[doc_type]['text'] = file_text

                    if last_record and file_text:
                        dup_type, score, orig_title, _, _ = self.check_for_duplicates(file_hash, file_text, current_project_id=project_id)
                    
                    total_changed += 1
                    results[doc_type]['is_changed'] = True
                    
                    from sqlalchemy import func
                    prev_doc_versions = db.session.query(func.count(ArchivalLedger.id)).filter(
                        ArchivalLedger.project_id == project_id,
                        getattr(ArchivalLedger, f"{doc_type}_hash").isnot(None)
                    ).scalar()
                    
                    doc_v = (prev_doc_versions or 0) + 1
                    ext = os.path.splitext(actual_temp_path)[1]
                    final_name = f"{clean_title}_{doc_type.upper()}_v{doc_v}{ext}"
                    final_path = os.path.join(doc_dir, final_name)
                    
                    os.rename(actual_temp_path, final_path)
                    results[doc_type]['path'] = os.path.relpath(final_path, self.archive_root)
                    processed_file_ids[file_id] = {'data': results[doc_type]}
                        
                except Exception as e:
                    error_msg += f"{doc_type.upper()} Error: {str(e)}; "

        if total_changed == 0 and last_record:
            return {'status': 'unchanged', 'message': 'No changes detected in Google Drive timestamps.', 'version': last_record.version}

        current_version = (last_record.version if last_record else 0) + 1
        status = "archived" if not error_msg else "failed"

        if status == "archived":
            ledger_entry = ArchivalLedger(
                project_id=project_id, project_title=project_data.get('project_title'),
                academic_year=academic_year, workbook_name=workbook_name,
                srs_modified_time=results['srs']['ts'], sdd_modified_time=results['sdd']['ts'],
                spmp_modified_time=results['spmp']['ts'], std_modified_time=results['std']['ts'],
                ri_modified_time=results['ri']['ts'], source_code_modified_time=results['source_code']['ts'],
                database_modified_time=results['database']['ts'], readme_modified_time=results['readme']['ts'],
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
        
        return {'status': status, 'version': current_version, 'paths': {dt: results[dt]['path'] for dt in doc_types}, 'error': error_msg.strip()}
