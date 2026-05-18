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
            # Synonyms list per logical column. Single-word synonyms like 'ri' or 'database'
            # are matched against the header on word boundaries (re.search r'\bri\b'), so they
            # won't accidentally hit substrings inside other words. Multi-word synonyms like
            # 'requirements inventory' are matched as plain substrings (faster + good enough).
            keywords = {
                'project_id': ['team code', 'group code', 'team id', 'team_id'],
                'student_id': ['id number', 'student number', 'id_number', 'student id'],
                'project_title': ['project title', 'title'],
                'student_name': ['student name'],
                'srs_link': ['software requirements specification', 'srs'],
                'sdd_link': ['software design description', 'sdd'],
                'spmp_link': ['software project management plan', 'spmp'],
                'std_link': ['software test document', 'std'],
                # Bare 'ri' is a 2-char token; word-boundary matching prevents false positives
                # like matching the 'ri' inside 'matrix' or 'requirements'. Order matters here:
                # the longer 'requirements inventory' is tried first so we never collapse SRS
                # into RI by accident.
                'ri_link': ['requirements inventory', 'ri file', 'ri_file', 'ri'],
                'research_paper_link': ['research paper', 'acm format', 'rp'],
                'usability_test_link': ['usability test results', 'usability test', 'usability', 'ut'],
                'presentation_link': ['final presentation', 'presentation ppt', 'presentation_ppt', 'presentation'],
                'source_code_link': ['zipped source code', 'source code', 'zipped_source'],
                'github_link': ['github'],
                'database_link': ['dumped database', 'sql dump', 'database dump', 'database', 'db'],
                'readme_link': ['readme', 'read me']
            }

            def _header_matches(header, syn):
                # Word-boundary regex for short / single-word synonyms to avoid collisions
                # (e.g. 'ri' inside 'requirements'). Multi-word phrases use plain substring.
                if ' ' in syn or '_' in syn:
                    return syn in header
                return re.search(r'\b' + re.escape(syn) + r'\b', header) is not None

            # Track which header indices are already taken so two logical columns can't
            # both bind to the same physical column (e.g. SRS vs RI both grabbing the same cell).
            taken_indices = set()
            for key, synonyms in keywords.items():
                for i, header in enumerate(headers):
                    if i in taken_indices:
                        continue
                    if any(_header_matches(header, syn) for syn in synonyms):
                        mapping[key] = i
                        taken_indices.add(i)
                        break

            # Dynamic fallback: any remaining un-mapped header that looks like a deliverable
            # column gets auto-registered as "<clean_header>_link" so future doc types added to
            # the sheet flow through to the dashboard and archival engine without code changes.
            stop_words = ['timestamp', 'id number', 'student name', 'date', 'last_updated', 'last updated', 'status', 'error']
            for i, header in enumerate(headers):
                if i in taken_indices or not header:
                    continue
                if any(sw in header for sw in stop_words):
                    continue
                clean_key = re.sub(r'[^a-z0-9]', '_', header).strip('_')
                if clean_key and f"{clean_key}_link" not in mapping:
                    mapping[f"{clean_key}_link"] = i
                    taken_indices.add(i)
            
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

                all_link_keys = [k for k in col_map.keys() if k.endswith('_link')]
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

                for lk in all_link_keys:
                    val = get_val(lk)
                    project_data[lk] = val
                    dt = lk[:-5]
                    if dt == 'github':
                        current_file_ids[dt] = val.lower().strip().rstrip('/')
                    else:
                        current_file_ids[dt] = clean_link(val)

                project_data['_file_ids'] = current_file_ids

                if not team_code and not any(current_file_ids.values()): continue
                merge_key = str(team_code).strip().lower() if team_code else f"ROW_{idx}"

                if merge_key in team_groups:
                    existing = team_groups[merge_key]
                    conflicts = set(existing.get('conflicting_fields', []))
                    combined_error = existing.get('error_message', '')
                    new_error = project_data.get('error_message', '')
                    if new_error and new_error not in combined_error:
                        project_data['error_message'] = f"{combined_error} | {new_error}".strip(' | ')

                    for dt in set(current_file_ids.keys()) | set(existing.get('_file_ids', {}).keys()):
                        cur = current_file_ids.get(dt)
                        prev = existing.get('_file_ids', {}).get(dt)
                        if cur and prev and cur != prev:
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
