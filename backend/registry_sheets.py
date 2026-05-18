import gspread
from google.oauth2 import service_account
import os
import re
import json
import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RegistrySheetsService:
    def __init__(self, user_credentials=None, service_account_json_path=None, sheet_id=None):
        self.scope = [
            "https://www.googleapis.com/auth/drive.readonly", 
            "https://www.googleapis.com/auth/drive.file", 
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        self._header_cache = {} # Cache for worksheet headers
        
        if user_credentials:
            logger.info("Initializing RegistrySheetsService with User Credentials")
            self.client = gspread.authorize(user_credentials)
        elif service_account_json_path:
            logger.info("Initializing RegistrySheetsService with Service Account")
            try:
                if service_account_json_path.strip().startswith('{'):
                    info = json.loads(service_account_json_path)
                    self.creds = service_account.Credentials.from_service_account_info(info, scopes=self.scope)
                else:
                    self.creds = service_account.Credentials.from_service_account_file(service_account_json_path, scopes=self.scope)
                self.client = gspread.authorize(self.creds)
            except Exception as e:
                logger.error(f"Failed to authorize: {e}")
                raise e
        else:
            raise ValueError("No auth provided")
        
        self.sheet_id = sheet_id
        self.workbook = None
        if sheet_id:
            try:
                self.workbook = self.client.open_by_key(sheet_id)
            except Exception as e:
                logger.error(f"Failed to open sheet {sheet_id}: {e}")

    def _get_header_map(self, worksheet):
        cache_key = f"{self.sheet_id}_{worksheet.title}"
        if cache_key in self._header_cache: return self._header_cache[cache_key]

        try:
            headers = [h.strip().lower() for h in worksheet.row_values(1)]
            mapping = {}
            # EXTREME STRICTNESS to prevent RI/SRS overlap
            keywords = {
                'project_id': ['team code', 'group code', 'team id', 'team_id', 'group_id'],
                'student_id': ['id number', 'student number', 'id_number'],
                'project_title': ['project title', 'title', 'name of project'],
                'student_name': ['student name'],
                'srs_link': ['finalized software requirements specification', 'software requirements specification', 'srs'],
                'sdd_link': ['finalized software design description', 'software design description', 'sdd'],
                'spmp_link': ['finalized software project management plan', 'software project management plan', 'spmp'],
                'std_link': ['finalized software test document', 'software test document', 'std'],
                'ri_link': ['requirements inventory', 'ri file', 'ri_file', 'ri'],
                'research_paper_link': ['research paper (acm format)', 'research paper', 'acm format', 'rp'],
                'usability_test_link': ['usability test results', 'usability test', 'usability', 'ut'],
                'presentation_link': ['final presentation ppt', 'final presentation', 'presentation ppt', 'presentation_ppt', 'presentation', 'ppt'],
                'source_code_link': ['zipped source code', 'source code', 'zipped_source', 'src'],
                'github_link': ['github', 'gh'],
                'database_link': ['dumped database', 'sql dump', 'database dump', 'database', 'db'],
                'readme_link': ['readme', 'rm'],
                'status': ['status'],
                'error': ['error', 'error_message', 'remarks']
            }
            # 1. Map known keywords with high priority
            for key, synonyms in keywords.items():
                for i, header in enumerate(headers):
                    if any(syn == header or (len(syn) > 3 and syn in header) for syn in synonyms):
                        mapping[key] = i
                        break
            
            # 2. Dynamic Mapping: Any unmapped column that isn't a known field 
            # is treated as a potential deliverable link
            mapped_indices = set(mapping.values())
            for i, header in enumerate(headers):
                if i not in mapped_indices and header:
                    # Clean the header to use as a key
                    clean_key = re.sub(r'[^a-z0-9]', '_', header).strip('_')
                    if clean_key and not clean_key.endswith('_link'):
                        mapping[f"{clean_key}_link"] = i
            
            self._header_cache[cache_key] = mapping
            return mapping
        except Exception as e:
            logger.error(f"Header fetch failed: {e}")
            return {}

    def get_all_projects(self, sheet_name):
        """Fetch all rows and merge by FULL TEAM CODE with File-ID awareness"""
        if not self.workbook: return {'projects': [], 'available_docs': []}
        try:
            worksheet = self.workbook.worksheet(sheet_name)
            all_records = worksheet.get_all_values()
            if not all_records: return {'projects': [], 'available_docs': []}

            col_map = self._get_header_map(worksheet)
            team_groups = {}
            
            # Standard doc types for file ID processing
            standard_docs = ['srs', 'sdd', 'spmp', 'std', 'ri', 'source_code', 'github', 'database', 'readme', 'research_paper', 'usability_test', 'presentation']

            for idx, row in enumerate(all_records[1:], start=2):
                def get_val(key, default=''):
                    if key in col_map and col_map[key] < len(row):
                        val = str(row[col_map[key]]).strip()
                        if "copy & paste" in val.lower() or "filename:" in val.lower():
                            return default
                        return val
                    return default

                team_code = get_val('project_id')
                name = get_val('project_title')
                if not team_code and not name: continue

                def clean_link(url):
                    if not url: return ""
                    url = url.split('?')[0].replace("\\", "").rstrip('/')
                    match = re.search(r'/d/([a-zA-Z0-9_-]{25,})', url)
                    return match.group(1) if match else url

                # Process file IDs for standard and dynamic docs
                current_file_ids = {}
                project_data = {
                    'row_index': idx,
                    'project_id': team_code or "N/A",
                    'project_title': name or team_code or f"Team_{idx}",
                    'status': get_val('status', 'Pending'),
                    'error_message': get_val('error'),
                    'academic_year': sheet_name,
                    'conflicting_fields': [],
                }

                # Populate all mapped columns
                for key, col_idx in col_map.items():
                    if col_idx < len(row):
                        val = get_val(key)
                        project_data[key] = val
                        
                        # If it's a link column, extract file ID for conflict detection
                        if key.endswith('_link'):
                            doc_id = key.replace('_link', '')
                            current_file_ids[doc_id] = clean_link(val) if 'github' not in doc_id else val.lower().strip().rstrip('/')

                project_data['_file_ids'] = current_file_ids

                if not team_code and not any(current_file_ids.values()): continue

                merge_key = str(team_code).strip().lower() if team_code else f"ROW_{idx}"

                if merge_key in team_groups:
                    existing = team_groups[merge_key]
                    conflicts = set(existing.get('conflicting_fields', []))
                    
                    # Merge error messages
                    combined_error = existing.get('error_message', '')
                    new_error = project_data.get('error_message', '')
                    if new_error and new_error not in combined_error:
                        project_data['error_message'] = f"{combined_error} | {new_error}".strip(' | ')

                    # Detect conflicts in file IDs
                    for dt, fid in current_file_ids.items():
                        if fid and existing['_file_ids'].get(dt) and fid != existing['_file_ids'][dt]:
                            conflicts.add(dt)
                    project_data['conflicting_fields'] = list(conflicts)
                    team_groups[merge_key] = project_data
                else:
                    team_groups[merge_key] = project_data
                
            projects_list = sorted(team_groups.values(), key=lambda x: x['row_index'])
            available_docs = [key.replace('_link', '') for key in col_map.keys() if '_link' in key and key not in ['project_id', 'project_title', 'status', 'error', 'student_id', 'student_name']]
            return {'projects': projects_list, 'available_docs': available_docs}
        except Exception as e:
            logger.error(f"Error fetching projects: {e}")
            raise e

    def update_status(self, sheet_name, row_index, status, **kwargs):
        if not self.workbook: return
        try:
            worksheet = self.workbook.worksheet(sheet_name)
            col_map = self._get_header_map(worksheet)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updates = []
            def add_update(key, value):
                if key in col_map and value is not None:
                    col_letter = chr(65 + col_map[key])
                    updates.append({'range': f'{col_letter}{row_index}', 'values': [[value]]})
            add_update('status', status)
            add_update('last_updated', timestamp)
            add_update('error', kwargs.get('error_msg'))
            if updates: worksheet.batch_update(updates)
        except Exception as e: logger.error(f"Update failed: {e}")

    def batch_update_statuses(self, sheet_name, status_updates):
        if not status_updates or not self.workbook: return
        try:
            worksheet = self.workbook.worksheet(sheet_name)
            col_map = self._get_header_map(worksheet)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            all_updates = []
            for item in status_updates:
                row_index = item['row_index']
                status = item['status']
                kwargs = item.get('kwargs', {})
                def add_to_batch(key, value):
                    if key in col_map and value is not None:
                        col_letter = chr(65 + col_map[key])
                        all_updates.append({'range': f'{col_letter}{row_index}', 'values': [[value]]})
                add_to_batch('status', status)
                add_to_batch('last_updated', timestamp)
                add_to_batch('error', kwargs.get('error_msg'))
            if all_updates: worksheet.batch_update(all_updates)
        except Exception as e: logger.error(f"Batch update failed: {e}")

    def get_workbook_name(self):
        return self.workbook.title if self.workbook else "Unknown_Workbook"

    def get_all_sheet_names(self):
        return [ws.title for ws in self.workbook.worksheets()] if self.workbook else []

    def list_available_sheets(self):
        try:
            files = self.client.list_spreadsheet_files()
            return [{"id": f["id"], "name": f["name"]} for f in files]
        except Exception as e: raise Exception(f"Failed to list workbooks: {e}")
