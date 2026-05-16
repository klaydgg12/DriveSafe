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
        """AI Plagiarism Check (Across different projects only)"""
        if not new_text or len(new_text) < 100: return None, 0, None, None, None
        
        # We only check for plagiarism against OTHER projects
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
            return self.service.files().get(fileId=file_id, fields='modifiedTime, md5Checksum').execute()
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

        for doc_type in doc_types:
            link = project_data.get(f'{doc_type}_link')
            file_id = self._extract_file_id(link)
            if not file_id: continue

            try:
                # 1. FETCH LIVE CLOCK FROM GOOGLE
                metadata = self._get_file_metadata(file_id)
                current_drive_ts = metadata.get('modifiedTime', 'Unknown')
                results[doc_type]['ts'] = current_drive_ts
                
                # 2. ABSOLUTE VERSIONING: If time is different, we archive it. Period.
                is_modified = True
                if last_record:
                    last_stored_ts = getattr(last_record, f"{doc_type}_modified_time")
                    if last_stored_ts == current_drive_ts:
                        # Only skip if the timestamp is EXACTLY the same as last time
                        is_modified = False
                        logger.info(f"UNCHANGED: {doc_type.upper()} timestamp matches vault.")

                if not is_modified:
                    results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                    results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash")
                    results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                    continue

                # 3. FORCE ARCHIVE NEW VERSION
                logger.info(f"FORCING VERSION: {doc_type.upper()} was edited in Drive! ({current_drive_ts})")
                
                # IMPORTANT: Pause to allow Google to update the PDF export
                import time
                time.sleep(8) 

                doc_dir = os.path.join(base_project_dir, doc_type.upper())
                os.makedirs(doc_dir, exist_ok=True)
                temp_path = os.path.join(doc_dir, f"TEMP_{doc_type.upper()}.pdf")
                self.download_file(file_id, temp_path)
                
                with open(temp_path, "rb") as f:
                    file_binary = f.read()
                    results[doc_type]['bin'] = file_binary
                
                results[doc_type]['hash'] = metadata.get('md5Checksum') or hashlib.sha256(file_binary).hexdigest()
                file_text = self._extract_text_from_pdf(temp_path)
                results[doc_type]['text'] = file_text

                total_changed += 1
                results[doc_type]['is_changed'] = True
                
                # Version naming
                from sqlalchemy import func
                prev_doc_v = db.session.query(func.count(ArchivalLedger.id)).filter(
                    ArchivalLedger.project_id == project_id,
                    getattr(ArchivalLedger, f"{doc_type}_hash").isnot(None)
                ).scalar()
                
                doc_v = (prev_doc_v or 0) + 1
                final_path = os.path.join(doc_dir, f"{clean_title}_{doc_type.upper()}_v{doc_v}.pdf")
                if os.path.exists(final_path): final_path = final_path.replace(".pdf", f"_{int(time.time())}.pdf")
                
                os.rename(temp_path, final_path)
                results[doc_type]['path'] = os.path.relpath(final_path, self.archive_root)
                    
            except Exception as e:
                logger.error(f"Error processing {doc_type}: {e}")

        if total_changed == 0 and last_record:
            return {'status': 'unchanged', 'message': 'No edits found in Google Drive since last archive.'}

        current_version = (last_record.version if last_record else 0) + 1
        
        new_entry = ArchivalLedger(
            project_id=project_id, project_title=project_data.get('project_title'),
            academic_year=academic_year, workbook_name=workbook_name,
            srs_modified_time=results['srs']['ts'], sdd_modified_time=results['sdd']['ts'],
            spmp_modified_time=results['spmp']['ts'], std_modified_time=results['std']['ts'],
            ri_modified_time=results['ri']['ts'], source_code_modified_time=results['source_code']['ts'],
            database_modified_time=results['database']['ts'], readme_modified_time=results['readme']['ts'],
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
            status='archived', version=current_version, batch_id=batch_id, archived_at=datetime.datetime.utcnow()
        )
        db.session.add(new_entry)
        db.session.commit()
        
        return {'status': 'archived', 'version': current_version, 'paths': {dt: results[dt]['path'] for dt in doc_types}}
