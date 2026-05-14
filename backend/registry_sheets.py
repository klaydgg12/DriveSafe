import gspread
from google.oauth2 import service_account
import os
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
        # Define keywords to search for in headers
        keywords = {
            'project_id': ['project id', 'id', 'team id', 'team_id'],
            'project_title': ['project title', 'title', 'project_title'],
            'srs_link': ['srs link', 'srs', 'srs_link'],
            'sdd_link': ['sdd link', 'sdd', 'sdd_link'],
            'spmp_link': ['spmp link', 'spmp', 'spmp_link'],
            'std_link': ['std link', 'std', 'std_link'],
            'ri_link': ['ri link', 'ri', 'ri_link', 'requirements inventory'],
            'status': ['status'],
            'last_updated': ['last updated', 'updated at', 'timestamp'],
            'srs_path': ['srs path', 'srs_local'],
            'sdd_path': ['sdd path', 'sdd_local'],
            'spmp_path': ['spmp path', 'spmp_local'],
            'std_path': ['std path', 'std_local'],
            'ri_path': ['ri path', 'ri_local'],
            'error': ['error', 'message', 'error message']
        }

        for key, synonyms in keywords.items():
            for i, header in enumerate(headers):
                if any(syn in header for syn in synonyms):
                    mapping[key] = i
                    break
        
        self._header_cache[cache_key] = mapping
        return mapping

    def get_all_projects(self, sheet_name):
        """Fetch all rows using dynamic header mapping"""
        try:
            worksheet = self.workbook.worksheet(sheet_name)
            all_records = worksheet.get_all_values()
            if not all_records: return []

            col_map = self._get_header_map(worksheet)
            projects = []
            
            for idx, row in enumerate(all_records[1:], start=2):
                def get_val(key, default=''):
                    if key in col_map and col_map[key] < len(row):
                        return row[col_map[key]]
                    return default

                project = {
                    'row_index': idx,
                    'project_id': get_val('project_id'),
                    'project_title': get_val('project_title', 'Untitled'),
                    'srs_link': get_val('srs_link'),
                    'sdd_link': get_val('sdd_link'),
                    'spmp_link': get_val('spmp_link'),
                    'std_link': get_val('std_link'),
                    'ri_link': get_val('ri_link'),
                    'status': get_val('status', 'Pending'),
                    'academic_year': sheet_name
                }
                projects.append(project)
            return projects
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
        # We use the underlying gspread client's auth session to call Drive API
        # Or just use gspread's openall() which might be slow if there are many files.
        # list_spreadsheet_files() is better.
        files = self.client.list_spreadsheet_files()
        return [{"id": f["id"], "name": f["name"]} for f in files]
