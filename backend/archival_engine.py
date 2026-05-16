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
                # Increased limit to 100 pages to catch changes in large documents
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
        # 1. Exact Hash Check
        exact_match = ArchivalLedger.query.filter(
            (ArchivalLedger.srs_hash == new_file_hash) | 
            (ArchivalLedger.sdd_hash == new_file_hash) |
            (ArchivalLedger.spmp_hash == new_file_hash) |
            (ArchivalLedger.std_hash == new_file_hash) |
            (ArchivalLedger.ri_hash == new_file_hash)
        ).first()
        
        if exact_match:
            return "Exact Duplicate", 1.0, exact_match.project_title, exact_match.project_id, exact_match.version

        # 2. AI Semantic Similarity (BATCH OPTIMIZED)
        if not new_text or len(new_text) < 100: 
            return None, 0, None, None, None

        query = ArchivalLedger.query.filter(ArchivalLedger.status == 'archived')
        if current_project_id:
            past_records = query.filter(ArchivalLedger.project_id == current_project_id).all()
        else:
            past_records = query.all()

        if not past_records:
            return None, 0, None, None, None

        # Build the corpus
        corpus = [new_text]
        metadata_map = [] # To keep track of which index corresponds to which record/doc_type
        
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
            # Vectorize the entire corpus at once (extremely fast compared to looping pairs)
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(corpus)
            
            # Compare the first document (new_text) against all others
            cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            
            # Find the most similar document
            max_sim_idx = cosine_similarities.argmax()
            max_sim_score = cosine_similarities[max_sim_idx]
            
            if max_sim_score > 0.90:
                match_meta = metadata_map[max_sim_idx]
                logger.info(f"AI Batch Similarity Match: {max_sim_score:.4f} against {match_meta['title']} ({match_meta['dt'].upper()})")
                return "Semantic Duplicate", max_sim_score, match_meta['title'], match_meta['id'], match_meta['version']
                
        except Exception as e:
            logger.error(f"AI Batch Processing Failed: {e}")
            
        return None, 0, None, None, None

    def download_file(self, file_id, destination_path):
        try:
            file_metadata = self.service.files().get(fileId=file_id, fields='mimeType, name, size').execute()
            mime_type = file_metadata.get('mimeType')
            file_name = file_metadata.get('name')
            logger.info(f"Attempting to process: {file_name} (Type: {mime_type})")

            fh = io.BytesIO()
            final_ext = ".pdf"
            
            # Case 1: Native Google Docs/Sheets
            if 'google-apps.document' in mime_type or 'google-apps.spreadsheet' in mime_type:
                logger.info(f"Exporting Google Doc {file_name} to PDF...")
                request = self.service.files().export_media(fileId=file_id, mimeType='application/pdf')
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            # Case 2: MS Office Files (.docx, .xlsx)
            elif 'officedocument.wordprocessingml.document' in mime_type or 'officedocument.spreadsheetml.sheet' in mime_type:
                logger.info(f"Converting Office file {file_name} to PDF via temporary Google Doc upload...")
                
                # Download original bytes
                media_content = self.service.files().get_media(fileId=file_id).execute()
                
                # Upload as a temporary Google Doc
                temp_metadata = {
                    'name': f"TEMP_CONV_{file_name}",
                    'mimeType': 'application/vnd.google-apps.document' if 'document' in mime_type else 'application/vnd.google-apps.spreadsheet'
                }
                from googleapiclient.http import MediaIoBaseUpload
                temp_file = self.service.files().create(
                    body=temp_metadata,
                    media_body=MediaIoBaseUpload(io.BytesIO(media_content), mimetype=mime_type),
                    fields='id'
                ).execute()
                temp_id = temp_file.get('id')
                
                try:
                    # Export the temporary Google Doc as PDF
                    request = self.service.files().export_media(fileId=temp_id, mimeType='application/pdf')
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                finally:
                    # CLEANUP: Always delete the temporary conversion file
                    self.service.files().delete(fileId=temp_id).execute()
            
            # Case 3: Already a PDF
            elif 'pdf' in mime_type:
                logger.info(f"Downloading {file_name} as direct PDF...")
                request = self.service.files().get_media(fileId=file_id)
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            # Case 4: Other files (try direct download)
            else:
                logger.warning(f"Unknown mime-type {mime_type}, downloading as-is.")
                request = self.service.files().get_media(fileId=file_id)
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                final_ext = os.path.splitext(file_name)[1] or ".bin"

            content = fh.getvalue()
            if len(content) == 0:
                raise Exception("Downloaded content is empty.")

            # Fix extension if needed
            if not destination_path.lower().endswith(final_ext.lower()):
                destination_path = os.path.splitext(destination_path)[0] + final_ext

            with open(destination_path, 'wb') as f:
                f.write(content)
                
            logger.info(f"Successfully processed {file_name} as {final_ext}")
            return destination_path
        except Exception as e:
            logger.error(f"Download/Conversion Error for {file_id}: {e}")
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
        # Clean title and ID for folder naming
        clean_title = project_data.get('project_title', 'Untitled').replace(' ', '_').replace('/', '_')
        clean_id = str(project_id).replace(' ', '_').replace('/', '_')
        
        # New organized folder name: "Team_1_DriveSafe"
        folder_name = f"{clean_id}_{clean_title}" if clean_id and clean_id != 'None' else clean_title
        academic_year = project_data.get('academic_year')
        
        base_project_dir = os.path.join(self.archive_root, workbook_name, folder_name)
        os.makedirs(base_project_dir, exist_ok=True)
        
        # 1. Fetch the LATEST record for this project to compare against
        last_record = ArchivalLedger.query.filter_by(
            project_id=project_id,
            academic_year=academic_year,
            status='archived'
        ).order_by(ArchivalLedger.version.desc()).first()
        
        doc_types = ['srs', 'sdd', 'spmp', 'std', 'ri']
        results = {dt: {'path': None, 'hash': None, 'is_changed': False, 'bin': None} for dt in doc_types}
        error_msg = ""
        total_changed = 0

        # --- TEAM-LEVEL LINK DEDUPLICATION ---
        # Map file IDs to their processed results to avoid downloading the same file twice
        # if multiple document types point to the same Google Drive file.
        processed_file_ids = {}

        # 2. Process each document
        project_title = project_data.get('project_title', 'Untitled')
        for doc_type in doc_types:
            link = project_data.get(f'{doc_type}_link')
            file_id = self._extract_file_id(link)
            
            if file_id:
                # If this specific file ID was already processed in this session (e.g. SRS and SDD are same link)
                if file_id in processed_file_ids:
                    logger.info(f"Team Deduplication: {doc_type.upper()} uses same link as {processed_file_ids[file_id]['source']}. Reusing results.")
                    res = processed_file_ids[file_id]['data']
                    results[doc_type] = {
                        'path': res['path'], 'hash': res['hash'], 'text': res.get('text'), 
                        'bin': res.get('bin'), 'is_changed': res.get('is_changed', False)
                    }
                    if res.get('is_changed'): total_changed += 1
                    continue

                try:
                    # --- TURBO METADATA OPTIMIZATION ---
                    metadata = self._get_file_metadata(file_id)
                    if not metadata:
                        raise Exception("Could not reach Google Drive for metadata.")

                    changed = True
                    if last_record and last_record.archived_at:
                        raw_mod_time = metadata.get('modifiedTime')
                        mod_time = datetime.datetime.fromisoformat(raw_mod_time.replace('Z', '+00:00'))
                        
                        last_archive_time = last_record.archived_at.replace(tzinfo=datetime.timezone.utc)
                        if mod_time <= last_archive_time + datetime.timedelta(seconds=5):
                            logger.info(f"Turbo Skip: {doc_type.upper()} is up-to-date in vault.")
                            changed = False

                    if not changed:
                        results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                        results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash")
                        results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                        results[doc_type]['bin'] = None
                        # Cache for team-level deduplication
                        processed_file_ids[file_id] = {'source': doc_type, 'data': results[doc_type]}
                        continue
                    # --- END TURBO OPTIMIZATION ---

                    # Proceed with download if changed
                    doc_dir = os.path.join(base_project_dir, doc_type.upper())
                    os.makedirs(doc_dir, exist_ok=True)
                    
                    temp_path = os.path.join(doc_dir, f"COMPARE_{doc_type.upper()}.pdf")
                    actual_temp_path = self.download_file(file_id, temp_path)
                    
                    with open(actual_temp_path, "rb") as f:
                        file_binary = f.read()
                        results[doc_type]['bin'] = file_binary
                    
                    file_hash = self._compute_hash(actual_temp_path)
                    results[doc_type]['hash'] = file_hash
                    
                    # AI Text Extraction
                    file_text = self._extract_text_from_pdf(actual_temp_path)
                    results[doc_type]['text'] = file_text
                    
                    # 3. Check if this specific file changed compared to the last version
                    changed = True
                    if last_record:
                        last_hash = getattr(last_record, f"{doc_type}_hash")
                        if last_hash == file_hash:
                            logger.info(f"Hash Match: {doc_type.upper()} is identical. No new version.")
                            changed = False
                        else:
                            # If hash differs, check AI similarity
                            last_text = getattr(last_record, f"{doc_type}_text")
                            if file_text and last_text:
                                try:
                                    vectorizer = TfidfVectorizer().fit_transform([file_text, last_text])
                                    vectors = vectorizer.toarray()
                                    similarity = cosine_similarity(vectors)[0][1]
                                    logger.info(f"AI Similarity for {doc_type.upper()}: {similarity:.4f}")
                                    if similarity > 0.99:
                                        logger.info(f"AI: {doc_type.upper()} is 99%+ identical. Re-using last version.")
                                        changed = False
                                except: pass

                    # 4. Plagiarism Check (ONLY ON 2ND SESSION ONWARDS)
                    # If this is the FIRST time this project is being archived (no last_record),
                    # we skip the AI check against other projects to save time.
                    if last_record:
                        dup_type, score, orig_title, orig_project_id, _ = self.check_for_duplicates(file_hash, file_text, current_project_id=project_id)
                        if dup_type and orig_project_id != project_id:
                            logger.warning(f"PLAGIARISM: {doc_type.upper()} matches '{orig_title}'")
                            results[doc_type]['dup'] = f"Warning: Similar to {orig_title}"
                    else:
                        logger.info(f"AI FAST-TRACK: Skipping cross-project check for initial archival.")
                    
                    if changed:
                        total_changed += 1
                        results[doc_type]['is_changed'] = True
                        
                        # Calculate per-document version correctly
                        from sqlalchemy import func
                        prev_doc_versions = db.session.query(func.count(ArchivalLedger.id)).filter(
                            ArchivalLedger.project_id == project_id,
                            getattr(ArchivalLedger, f"{doc_type}_hash").isnot(None)
                        ).scalar()
                        
                        doc_v = (prev_doc_versions or 0) + 1
                        ext = os.path.splitext(actual_temp_path)[1]
                        final_name = f"{clean_title}_{doc_type.upper()}_v{doc_v}{ext}"
                        final_path = os.path.join(doc_dir, final_name)
                        
                        # Collision safety
                        v_safe = doc_v
                        while os.path.exists(final_path):
                            v_safe += 1
                            final_path = os.path.join(doc_dir, f"{clean_title}_{doc_type.upper()}_v{v_safe}{ext}")

                        os.rename(actual_temp_path, final_path)
                        results[doc_type]['path'] = os.path.relpath(final_path, self.archive_root)
                        results[doc_type]['bin'] = file_binary if len(file_binary) < 16*1024*1024 else None
                    else:
                        results[doc_type]['path'] = getattr(last_record, f"{doc_type}_local_path")
                        results[doc_type]['hash'] = getattr(last_record, f"{doc_type}_hash")
                        results[doc_type]['text'] = getattr(last_record, f"{doc_type}_text")
                        results[doc_type]['bin'] = None
                        if os.path.exists(actual_temp_path): os.remove(actual_temp_path)
                    
                    # Cache for team-level deduplication
                    processed_file_ids[file_id] = {'source': doc_type, 'data': results[doc_type]}
                        
                except Exception as e:
                    error_msg += f"{doc_type.upper()} Error: {str(e)}; "

        # 4. Final Decision: Save new version only if at least one file changed OR no previous record exists
        if total_changed == 0 and last_record:
            logger.info(f"No changes detected for project {project_title}. Skipping version increment.")
            return {
                'status': 'unchanged',
                'message': 'No changes detected (all files are semantically identical to latest version).',
                'version': last_record.version
            }

        current_version = (last_record.version if last_record else 0) + 1
        status = "archived" if not error_msg else "failed"

        if status == "archived":
            ledger_entry = ArchivalLedger(
                project_id=project_id,
                project_title=project_data.get('project_title'),
                academic_year=academic_year,
                workbook_name=workbook_name,
                srs_original_url=project_data.get('srs_link'),
                sdd_original_url=project_data.get('sdd_link'),
                spmp_original_url=project_data.get('spmp_link'),
                std_original_url=project_data.get('std_link'),
                ri_original_url=project_data.get('ri_link'),
                srs_local_path=results['srs']['path'],
                sdd_local_path=results['sdd']['path'],
                spmp_local_path=results['spmp']['path'],
                std_local_path=results['std']['path'],
                ri_local_path=results['ri']['path'],
                srs_hash=results['srs']['hash'],
                sdd_hash=results['sdd']['hash'],
                spmp_hash=results['spmp']['hash'],
                std_hash=results['std']['hash'],
                ri_hash=results['ri']['hash'],
                srs_binary=results['srs']['bin'],
                sdd_binary=results['sdd']['bin'],
                spmp_binary=results['spmp']['bin'],
                std_binary=results['std']['bin'],
                ri_binary=results['ri']['bin'],
                
                # AI Cache Storage
                srs_text=results['srs'].get('text'),
                sdd_text=results['sdd'].get('text'),
                spmp_text=results['spmp'].get('text'),
                std_text=results['std'].get('text'),
                ri_text=results['ri'].get('text'),

                status=status,
                version=current_version,
                batch_id=batch_id,
                error_message=error_msg.strip(),
                archived_at=datetime.datetime.utcnow()
            )
            db.session.add(ledger_entry)
            db.session.commit()
        
        return {
            'status': status, 
            'version': current_version,
            'paths': {dt: results[dt]['path'] for dt in doc_types},
            'error': error_msg.strip()
        }
