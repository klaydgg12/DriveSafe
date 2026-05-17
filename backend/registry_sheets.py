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

# Expected Columns Mapping (0-indexed)
COL_PROJECT_ID = 0
COL_PROJECT_TITLE = 1
COL_SRS_LINK = 2
COL_SDD_LINK = 3
COL_SPMP_LINK = 4
COL_STD_LINK = 5
COL_RI_LINK = 6
COL_STATUS = 7
COL_LAST_UPDATED = 8
COL_SRS_PATH = 9
COL_SDD_PATH = 10
COL_SPMP_PATH = 11
COL_STD_PATH = 12
COL_RI_PATH = 13
COL_ERROR = 14

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
                # Support both a file path and the actual JSON string
                if service_account_json_path.strip().startswith('{'):
                    logger.info("Detected Service Account JSON string")
                    info = json.loads(service_account_json_path)
                    self.creds = service_account.Credentials.from_service_account_info(info, scopes=self.scope)
                else:
                    logger.info(f"Detected Service Account file path: {service_account_json_path}")
                    self.creds = service_account.Credentials.from_service_account_file(service_account_json_path, scopes=self.scope)
                
                self.client = gspread.authorize(self.creds)
            except Exception as e:
                logger.error(f"Failed to authorize service account: {e}")
                raise e
        else:
            raise ValueError("No authentication method provided for RegistrySheetsService")
        
        self.sheet_id = sheet_id
        self.workbook = None
        if sheet_id:
            try:
                self.workbook = self.client.open_by_key(sheet_id)
            except Exception as e:
                logger.error(f"Failed to open sheet {sheet_id}: {e}")

    def _get_header_map(self, worksheet):
        """Scan the first row to map column names to their 0-based indices. Cached per worksheet."""
        cache_key = f"{self.sheet_id}_{worksheet.title}"
        if cache_key in self._header_cache:
            return self._header_cache[cache_key]

        try:
            headers = [h.strip().lower() for h in worksheet.row_values(1)]
        except Exception as e:
            logger.error(f"Failed to fetch headers for {worksheet.title}: {e}")
            return {}

        mapping = {}
        # Define keywords to search for in headers (Highly robust to match user's custom format)
        keywords = {
            'project_id': ['team id', 'team_id', 'group code', 'team code'],
            'project_title': ['project title', 'title'],
            'student_name': ['student name', 'representative name'],
            'student_id': ['student id', 'id number', 'id'],
            'timestamp': ['timestamp'],
            'status': ['status'],
            'last_updated': ['last updated'],
            'error': ['error message', 'error'],
            
            # Deliverable columns (Dynamic positioning)
            'srs_link': ['1. srs', 'srs link'],
            'spmp_link': ['2. spmp', 'spmp link'],
            'sdd_link': ['3. sdd', 'sdd link'],
            'std_link': ['4. std', 'std link'],
            'ri_link': ['requirements inventory', 'ri link'],
            'source_code_link': ['5. source code', 'zipped source'],
            'github_link': ['6. source code (github)', 'github link'],
            'database_link': ['7. exported / dumped database', 'sql dump'],
            'readme_link': ['8. readme', 'readme link']
        }

        for key, synonyms in keywords.items():
            for i, header in enumerate(headers):
                if any(syn in header for syn in synonyms):
                    mapping[key] = i
                    break
        
        self._header_cache[cache_key] = mapping
        return mapping

    def get_all_projects(self, sheet_name):
        """Fetch all rows and merge by TEAM ID with granular link conflict detection"""
        try:
            worksheet = self.workbook.worksheet(sheet_name)
            all_records = worksheet.get_all_values()
            if not all_records: return {'projects': [], 'available_docs': []}

            col_map = self._get_header_map(worksheet)
            
            # Dictionary to keep the latest entry for each Team Code
            team_groups = {}
            
            for idx, row in enumerate(all_records[1:], start=2):
                def get_val(key, default=''):
                    if key in col_map and col_map[key] < len(row):
                        val = str(row[col_map[key]]).strip()
                        if "copy & paste" in val.lower() or "filename:" in val.lower():
                            return default
                        return val
                    return default

                # Identify the Team
                raw_team_id = get_val('project_id')
                # Remove spaces and case for perfect merging
                team_clean = re.sub(r'\s+', '', str(raw_team_id)).lower() if raw_team_id else ""
                
                name = get_val('project_title')
                
                # FUNCTION to extract File ID for perfect link matching
                def clean_link(url):
                    if not url: return ""
                    # Remove all parameters (?usp=...) and backslashes
                    url = url.split('?')[0].replace("\\", "").rstrip('/')
                    match = re.search(r'/d/([a-zA-Z0-9_-]{25,})', url)
                    return match.group(1) if match else url

                current_ids = {
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

                has_links = any(current_ids.values())
                if not team_clean and not name and not has_links:
                    continue

                # Merge Key is primarily the TEAM ID
                merge_key = team_clean if team_clean else f"ROW_{idx}"

                # Prepare the project object
                project = {
                    'row_index': idx,
                    'project_id': raw_team_id or "N/A",
                    'project_title': name or raw_team_id or f"Team_{idx}",
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
                    '_id_map': current_ids
                }

                if merge_key in team_groups:
                    # MERGE with conflict detection
                    existing = team_groups[merge_key]
                    conflicts = set(existing.get('conflicting_fields', []))
                    
                    doc_types = ['srs', 'sdd', 'spmp', 'std', 'ri', 'source_code', 'github', 'database', 'readme']
                    for dt in doc_types:
                        if current_ids[dt] and existing['_id_map'][dt] and current_ids[dt] != existing['_id_map'][dt]:
                            conflicts.add(dt)
                    
                    project['conflicting_fields'] = list(conflicts)
                    team_groups[merge_key] = project
                else:
                    team_groups[merge_key] = project
                
            # Convert dictionary back to a sorted list based on original row order
            available_docs = [key.replace('_link', '') for key in col_map.keys() if '_link' in key]

            return {'projects': projects_list, 'available_docs': available_docs}
        except Exception as e:
            logger.error(f"Error fetching projects: {e}")
            raise e

    def update_status(self, sheet_name, row_index, status, **kwargs):
        """Update row details using dynamic column detection"""
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
        add_update('srs_path', kwargs.get('srs_path'))
        add_update('sdd_path', kwargs.get('sdd_path'))
        add_update('spmp_path', kwargs.get('spmp_path'))
        add_update('std_path', kwargs.get('std_path'))
        add_update('ri_path', kwargs.get('ri_path'))
        add_update('source_code_path', kwargs.get('source_code_path'))
        add_update('database_path', kwargs.get('database_path'))
        add_update('readme_path', kwargs.get('readme_path'))
        add_update('error', kwargs.get('error_msg'))
        
        if updates:
            worksheet.batch_update(updates)
            logger.info(f"Updated row {row_index} dynamically in {sheet_name}")

    def batch_update_statuses(self, sheet_name, status_updates):
        """
        Update multiple rows in one call.
        status_updates: list of dicts like {'row_index': 2, 'status': 'Archived', 'kwargs': {...}}
        """
        if not status_updates: return
        
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
            add_to_batch('srs_path', kwargs.get('srs_path'))
            add_to_batch('sdd_path', kwargs.get('sdd_path'))
            add_to_batch('spmp_path', kwargs.get('spmp_path'))
            add_to_batch('std_path', kwargs.get('std_path'))
            add_to_batch('ri_path', kwargs.get('ri_path'))
            add_to_batch('source_code_path', kwargs.get('source_code_path'))
            add_to_batch('database_path', kwargs.get('database_path'))
            add_to_batch('readme_path', kwargs.get('readme_path'))
            add_to_batch('error', kwargs.get('error_msg'))

        if all_updates:
            # gspread supports batch_update on the worksheet
            worksheet.batch_update(all_updates)
            logger.info(f"Batch updated {len(status_updates)} rows in {sheet_name}")

    def get_workbook_name(self):
        """Get the title of the spreadsheet"""
        return self.workbook.title if self.workbook else "Unknown_Workbook"

    def get_all_sheet_names(self):
        """List all worksheet names in the workbook (e.g., '2024-2025', '2025-2026')"""
        return [ws.title for ws in self.workbook.worksheets()]

    def list_available_sheets(self):
        """List all Google Sheets files the service account can access"""
        try:
            # This requires the "Google Drive API" to be enabled in Cloud Console
            files = self.client.list_spreadsheet_files()
            return [{"id": f["id"], "name": f["name"]} for f in files]
        except Exception as e:
            error_msg = str(e)
            if "Drive API" in error_msg or "403" in error_msg:
                raise Exception("Google Drive API is not enabled. Please enable it in the Google Cloud Console.")
            raise Exception(f"Failed to list workbooks: {error_msg}")
