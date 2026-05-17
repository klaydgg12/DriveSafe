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
                'project_id': ['team code', 'group code', 'team id'],
                'student_id': ['id number', 'student number'],
                'project_title': ['project title', 'title'],
                'student_name': ['student name'],
                'srs_link': ['1. srs'],
                'spmp_link': ['2. spmp'],
                'sdd_link': ['3. sdd'],
                'std_link': ['4. std'],
                'ri_link': ['requirements inventory', 'ri file'],
                'source_code_link': ['5. source code'],
                'github_link': ['6. source code (github)'],
                'database_link': ['7. exported / dumped database'],
                'readme_link': ['8. readme'],
                'status': ['status'],
                'last_updated': ['timestamp', 'last updated'],
                'error': ['error message', 'error']
            }
            for key, synonyms in keywords.items():
                for i, header in enumerate(headers):
                    if any(syn in header for syn in synonyms):
                        mapping[key] = i
                        break
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

                current_file_ids = {
                    'srs': clean_link(get_val('srs_link')),
                    'sdd': clean_link(get_val('sdd_link')),
                    'spmp': clean_link(get_val('spmp_link')),
                    'std': clean_link(get_val('std_link')),
                    'ri': clean_link(get_val('ri_link')),
                    'source_code': clean_link(get_val('source_code_link')),
                    'github': get_val('github_link').lower().strip().rstrip('/'),
                    'database': clean_link(get_val('database_link')),
                    'readme': clean_link(get_val('readme_link'))
                }

                if not team_code and not any(current_file_ids.values()): continue

                project = {
                    'row_index': idx,
                    'project_id': team_code or "N/A",
                    'project_title': name or team_code or f"Team_{idx}",
                    'srs_link': get_val('srs_link'),
                    'sdd_link': get_val('sdd_link'),
                    'spmp_link': get_val('spmp_link'),
                    'std_link': get_val('std_link'),
                    'ri_link': get_val('ri_link'),
                    'source_code_link': get_val('source_code_link'),
                    'github_link': get_val('github_link'),
                    'database_link': get_val('database_link'),
                    'readme_link': get_val('readme_link'),
                    'status': get_val('status', 'Pending'),
                    'academic_year': sheet_name,
                    'conflicting_fields': [],
                    '_file_ids': current_file_ids
                }

                merge_key = str(team_code).strip().lower() if team_code else f"ROW_{idx}"

                if merge_key in team_groups:
                    existing = team_groups[merge_key]
                    conflicts = set(existing.get('conflicting_fields', []))
                    doc_types = ['srs', 'sdd', 'spmp', 'std', 'ri', 'source_code', 'github', 'database', 'readme']
                    for dt in doc_types:
                        if current_file_ids[dt] and existing['_file_ids'][dt] and current_file_ids[dt] != existing['_file_ids'][dt]:
                            conflicts.add(dt)
                    project['conflicting_fields'] = list(conflicts)
                    team_groups[merge_key] = project
                else:
                    team_groups[merge_key] = project
                
            projects_list = sorted(team_groups.values(), key=lambda x: x['row_index'])
            available_docs = [key.replace('_link', '') for key in col_map.keys() if '_link' in key]
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
