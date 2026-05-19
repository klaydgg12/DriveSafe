from flask import Blueprint, jsonify, request, current_app, session, has_request_context, send_file
from flask_login import login_required, current_user
import os
import io
import requests
import threading
import logging
import datetime
import traceback
from registry_sheets import RegistrySheetsService
from archival_engine import ArchivalEngine
from models import db
from google.oauth2.credentials import Credentials

registry_bp = Blueprint('registry', __name__)
logger = logging.getLogger(__name__)

# Global trackers for live project statuses
LIVE_STATUS_TRACKER = {}
LIVE_ERROR_TRACKER = {}

def get_user_creds():
    # Only access session if in request context
    if not has_request_context():
        return None
    token = session.get('access_token')
    if not token:
        return None
    try:
        return Credentials(token, scopes=[
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets"
        ])
    except Exception as e:
        logger.error(f"DEBUG: Failed to create credentials: {e}")
        return None

def get_services(requested_sheet_id=None, provided_user_creds=None, force_user=False):
    sheet_id = requested_sheet_id or (request.args.get('sheet_id') if has_request_context() else None) or os.getenv('SHEET_ID')
    user_creds = provided_user_creds or get_user_creds()
    
    # CRITICAL: Force User Identity for Archival tasks to ensure organizational permissions
    if force_user and not user_creds:
        raise Exception("Google Session Required: You must be logged in to archive internal documents.")

    sheets_service = RegistrySheetsService(
        user_credentials=user_creds,
        service_account_json_path=os.getenv('SERVICE_ACCOUNT_JSON') if not user_creds else None,
        sheet_id=sheet_id
    )
    engine = ArchivalEngine(
        user_credentials=user_creds,
        service_account_json_path=os.getenv('SERVICE_ACCOUNT_JSON') if not user_creds else None,
        archive_root=os.getenv('ARCHIVE_ROOT', 'Capstone_Archives')
    )
    return sheets_service, engine

@registry_bp.route('/list-sheets', methods=['GET'], strict_slashes=False)
@login_required
def list_sheets():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    try:
        sheets_service, _ = get_services()
        sheets = sheets_service.list_available_sheets()
        return jsonify(sheets)
    except Exception as e:
        logger.error(f"DEBUG: List sheets route error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@registry_bp.route('/years', methods=['GET'], strict_slashes=False)
@login_required
def get_years():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    try:
        sheets_service, _ = get_services()
        years = sheets_service.get_all_sheet_names()
        return jsonify(years)
    except Exception as e:
        logger.error(f"DEBUG: get_years error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@registry_bp.route('/projects', methods=['GET'], strict_slashes=False)
@login_required
def get_pending():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    
    year = request.args.get('year')
    sheet_id = request.args.get('sheet_id') or os.getenv('SHEET_ID')
    if not year:
        return jsonify({"error": "Year is required"}), 400
        
    try:
        from models import ArchivalLedger
        sheets_service, _ = get_services(requested_sheet_id=sheet_id)
        result = sheets_service.get_all_projects(year)
        projects = result['projects']
        available_docs = result['available_docs']
        
        # --- OPTIMIZED BULK FETCH ---
        all_records = ArchivalLedger.query.filter_by(academic_year=year).order_by(ArchivalLedger.id.desc()).all()
        
        # Map by normalized project_id for instant case-insensitive lookup
        record_map = {}
        for r in all_records:
            pid_norm = str(r.project_id).strip().lower()
            if pid_norm not in record_map:
                record_map[pid_norm] = r

        for p in projects:
            pid_norm = str(p['project_id']).strip().lower()
            tracker_key = f"{sheet_id}_{year}_{p['row_index']}"
            
            # 1. Get latest record from pre-fetched map
            last_record = record_map.get(pid_norm)

            # 2. DEFAULT STATUS
            db_status = last_record.status.capitalize() if last_record else 'Pending'
            p['status'] = LIVE_STATUS_TRACKER.get(tracker_key) or db_status
            
            if tracker_key in LIVE_ERROR_TRACKER:
                p['error_message'] = LIVE_ERROR_TRACKER[tracker_key]

            p['latest_version'] = last_record.version if last_record else 0
            p['latest_id'] = last_record.id if last_record else None
            
            if p['status'].lower() in ['failed', 'partial'] and not p.get('error_message'):
                if last_record: p['error_message'] = last_record.error_message
            
        return jsonify({
            'projects': projects,
            'available_docs': available_docs
        })
    except Exception as e:
        logger.error(f"Failed to fetch projects: {e}", exc_info=True)
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@registry_bp.route('/ledger/workbooks', methods=['GET'], strict_slashes=False)
@login_required
def get_ledger_workbooks():
    if current_user.role != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    try:
        from models import ArchivalLedger, db
        workbooks = db.session.query(ArchivalLedger.workbook_name).distinct().all()
        clean_list = sorted(list(set([str(w[0]).strip() for w in workbooks if w and w[0] and str(w[0]).strip()])))
        return jsonify(clean_list)
    except Exception as e:
        logger.error(f"DEBUG: get_ledger_workbooks error: {str(e)}\n{traceback.format_exc()}", exc_info=True)
        return jsonify([])

@registry_bp.route('/ledger/tabs', methods=['GET'], strict_slashes=False)
@login_required
def get_ledger_tabs():
    if current_user.role != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    workbook_name = request.args.get('workbook')
    try:
        from models import ArchivalLedger, db
        query = db.session.query(ArchivalLedger.academic_year)
        if workbook_name: query = query.filter(ArchivalLedger.workbook_name == workbook_name)
        years = query.distinct().all()
        return jsonify([y[0] for y in years if y and y[0]])
    except Exception as e:
        logger.error(f"DEBUG: get_ledger_tabs error: {str(e)}\n{traceback.format_exc()}", exc_info=True)
        return jsonify([])

@registry_bp.route('/ledger/grouped', methods=['GET'], strict_slashes=False)
@login_required
def get_grouped_ledger():
    if current_user.role != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    try:
        from models import ArchivalLedger
        from sqlalchemy.orm import defer
        from collections import defaultdict
        academic_year = request.args.get('year')
        workbook_name = request.args.get('workbook')
        
        doc_types = ['srs','sdd','spmp','std','ri','research_paper','usability_test','presentation','source_code','database','readme']
        defer_cols = []
        for dt in doc_types:
            defer_cols.append(defer(getattr(ArchivalLedger, f"{dt}_binary")))
            if hasattr(ArchivalLedger, f"{dt}_text"):
                defer_cols.append(defer(getattr(ArchivalLedger, f"{dt}_text")))
        
        query = ArchivalLedger.query.options(*defer_cols)
        if academic_year: query = query.filter_by(academic_year=academic_year)
        if workbook_name: query = query.filter_by(workbook_name=workbook_name)
        records = query.order_by(ArchivalLedger.id.asc()).all()
        if not records: return jsonify([])
        
        doc_versions = defaultdict(lambda: defaultdict(int))
        grouped_data = {}
        for r in records:
            # UNIFY BY ID + TITLE to keep N/A projects separate
            pid_safe = str(r.project_id).strip().lower()
            title_safe = str(r.project_title).strip().lower()
            project_key = f"{pid_safe}_{title_safe}"
            
            if project_key not in grouped_data:
                grouped_data[project_key] = {
                    "project_id": r.project_id, "project_title": r.project_title,
                    "academic_year": r.academic_year, "workbook_name": r.workbook_name,
                    "db_ids": [],
                    "documents": { dt: [] for dt in ["srs", "sdd", "spmp", "std", "ri", "research_paper", "usability_test", "presentation", "source_code", "database", "readme"] }
                }
            
            target = grouped_data[project_key]
            target["db_ids"].append(int(r.id))

            for doc_type in target["documents"]:
                path = getattr(r, f"{doc_type}_local_path")
                if r.status in ['archived', 'partial'] and path:
                    doc_versions[project_key][doc_type] += 1
                    target["documents"][doc_type].append({
                        "id": int(r.id),
                        "version": doc_versions[project_key][doc_type],
                        "hash": getattr(r, f"{doc_type}_hash"), 
                        "timestamp": r.archived_at.isoformat() + 'Z' if r.archived_at else None,
                        "status": r.status
                    })
        result = list(grouped_data.values())
        for project in result:
            for dt in project["documents"]: project["documents"][dt].reverse()
        return jsonify(result)
    except Exception as e:
        logger.error(f"DEBUG: get_grouped_ledger error: {str(e)}\n{traceback.format_exc()}", exc_info=True)
        return jsonify([])

@registry_bp.route('/validate', methods=['POST'], strict_slashes=False)
@login_required
def validate_links():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    
    links = list(set(request.json.get('links', [])))
    results = {}
    
    from concurrent.futures import ThreadPoolExecutor

    def check_link(link):
        if not link: return link, "Empty"
        try:
            resp = requests.head(link, timeout=3, allow_redirects=True)
            status = "Accessible" if resp.status_code in [200, 301, 302] else f"Error {resp.status_code}"
            return link, status
        except:
            try:
                resp = requests.get(link, timeout=3, stream=True)
                status = "Accessible" if resp.status_code == 200 else "Failed"
                return link, status
            except:
                return link, "Failed"

    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_link = {executor.submit(check_link, link): link for link in links}
        for future in future_to_link:
            link, status = future.result()
            results[link] = status

    return jsonify(results)

@registry_bp.route('/archive', methods=['POST'])
@login_required
def archive_selected():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    projects = request.json.get('projects', [])
    if not projects:
        return jsonify({"error": "No projects selected"}), 400
    
    import uuid
    batch_id = str(uuid.uuid4())[:13]
    
    user_creds = get_user_creds()
    user_email = current_user.email
    sheet_id = request.json.get('sheet_id') or request.args.get('sheet_id') or os.getenv('SHEET_ID')
    
    try:
        sheets_service, _ = get_services(requested_sheet_id=sheet_id, provided_user_creds=user_creds, force_user=True)
        workbook_name = sheets_service.get_workbook_name()
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    # 1. MARK AS PROCESSING IMMEDIATELY (In Main Thread to prevent dashboard race)
    for p in projects:
        tracker_key = f"{sheet_id}_{p['academic_year']}_{p['row_index']}"
        LIVE_STATUS_TRACKER[tracker_key] = "Processing"
        # Clear old errors for a fresh attempt
        if tracker_key in LIVE_ERROR_TRACKER: del LIVE_ERROR_TRACKER[tracker_key]

    app_obj = current_app._get_current_object()
    
    def process_task(app_context, project_list, creds, sid, wb_name, archived_by_email):
        # SERIAL BREATHE STRATEGY: Process projects one-by-one for 100% stability
        with app_context.app_context():
            from models import ArchivalLedger, db
            try:
                for p in project_list:
                    tracker_key = f"{sid}_{p['academic_year']}_{p['row_index']}"
                    try:
                        import time, random
                        # Small random breathe between projects
                        time.sleep(random.uniform(0.1, 1.0))
                        
                        if not creds: raise Exception("Auth session expired.")
                        _, engine = get_services(requested_sheet_id=sid, provided_user_creds=creds, force_user=True)
                        
                        result = engine.archive_project(p, workbook_name=wb_name, batch_id=batch_id, archived_by=archived_by_email)
                        status = result['status'].capitalize()
                        if result['status'] == 'unchanged': status = 'Archived'
                        
                        LIVE_STATUS_TRACKER[tracker_key] = status
                        if result.get('error'): LIVE_ERROR_TRACKER[tracker_key] = result['error']
                        
                    except Exception as e:
                        err_msg = str(e)
                        logger.error(f"SERIAL ARCHIVAL ERROR for {p.get('project_id')}: {err_msg}")
                        LIVE_STATUS_TRACKER[tracker_key] = "Failed"
                        LIVE_ERROR_TRACKER[tracker_key] = err_msg
                        
                        try:
                            fail_entry = ArchivalLedger(
                                project_id=p['project_id'], 
                                project_title=p.get('project_title', 'Untitled'),
                                academic_year=p['academic_year'],
                                workbook_name=wb_name,
                                status='failed',
                                error_message=err_msg,
                                archived_at=datetime.datetime.utcnow()
                            )
                            db.session.add(fail_entry)
                            db.session.commit()
                        except: db.session.rollback()
                    finally:
                        db.session.remove() # Clean up session after each project
            finally:
                # --- FINALIZER ---
                # Ensure no project is left in 'Processing' if the main loop breaks
                for p in project_list:
                    key = f"{sid}_{p['academic_year']}_{p['row_index']}"
                    if LIVE_STATUS_TRACKER.get(key) == "Processing":
                        LIVE_STATUS_TRACKER[key] = "Failed"
                        LIVE_ERROR_TRACKER[key] = "Process interrupted."

    thread = threading.Thread(target=process_task, args=(app_obj, projects, user_creds, sheet_id, workbook_name, user_email))
    thread.start()
    return jsonify({"message": f"Started archival for {len(projects)} projects."}), 202

@registry_bp.route('/reset', methods=['POST'])
@login_required
def reset_project_status():
    if current_user.role != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    project = request.json.get('project')
    if not project: return jsonify({"error": "No project"}), 400
    try:
        from models import ArchivalLedger, db
        last_record = ArchivalLedger.query.filter_by(
            project_id=project['project_id'],
            academic_year=project['academic_year']
        ).order_by(ArchivalLedger.id.desc()).first()
        
        if last_record:
            db.session.delete(last_record)
            db.session.commit()
            
        return jsonify({"message": "Status reset to Pending (Local only)"})
    except Exception as e: 
        db.session.rollback()
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@registry_bp.route('/transactions', methods=['GET'], strict_slashes=False)
@login_required
def get_transactions():
    if current_user.role != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    try:
        from models import ArchivalLedger
        from sqlalchemy.orm import defer
        from collections import defaultdict
        
        # Optimized fetch
        doc_types = ['srs','sdd','spmp','std','ri','research_paper','usability_test','presentation','source_code','database','readme']
        defer_cols = []
        for dt in doc_types:
            bin_col = f"{dt}_binary"
            txt_col = f"{dt}_text"
            if hasattr(ArchivalLedger, bin_col):
                defer_cols.append(defer(getattr(ArchivalLedger, bin_col)))
            if hasattr(ArchivalLedger, txt_col):
                defer_cols.append(defer(getattr(ArchivalLedger, txt_col)))
        
        records = ArchivalLedger.query.options(*defer_cols).order_by(ArchivalLedger.archived_at.asc()).all()

        if not records: return jsonify([])

        # Hierarchy: Workbook -> Sheet -> Batch (Transaction)
        hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        for r in records:
            wb = r.workbook_name or "Unknown_Workbook"
            sh = r.academic_year or "Unknown_Sheet"
            bid = r.batch_id or "Direct_Archive"
            hierarchy[wb][sh][bid].append(r)

        result = []
        for wb_name, sheets in hierarchy.items():
            wb_data = {"name": wb_name, "sheets": []}
            for sh_name, batches in sheets.items():
                sh_data = {"name": sh_name, "transactions": []}
                
                # Sort batches by the time of the first record in them
                sorted_batch_ids = sorted(batches.keys(), key=lambda b: batches[b][0].archived_at)
                
                for idx, bid in enumerate(sorted_batch_ids):
                    batch_records = batches[bid]
                    tx_data = {
                        "transaction_id": bid,
                        "transaction_label": f"Transaction {idx + 1}",
                        "timestamp": batch_records[0].archived_at.isoformat() + 'Z',
                        "archived_by": batch_records[0].archived_by,
                        "project_count": len(batch_records),
                        "projects": []
                    }
                    for pr in batch_records:
                        tx_data["projects"].append({
                            "id": pr.id,
                            "project_id": pr.project_id,
                            "project_title": pr.project_title,
                            "status": pr.status,
                            "version": pr.version,
                            "error": pr.error_message
                        })
                    sh_data["transactions"].append(tx_data)
                
                # Show newest transaction first in the list
                sh_data["transactions"].reverse()
                wb_data["sheets"].append(sh_data)
            result.append(wb_data)

        return jsonify(result)
    except Exception as e:
        logger.error(f"DEBUG: get_transactions error: {str(e)}\n{traceback.format_exc()}", exc_info=True)
        return jsonify([])

@registry_bp.route('/ledger/<int:id>', methods=['DELETE', 'OPTIONS'], strict_slashes=False)
@login_required
def delete_ledger_item(id):
    if request.method == 'OPTIONS':
        return '', 204
    if current_user.role != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    try:
        from models import ArchivalLedger, db
        item = db.session.get(ArchivalLedger, id)
        if not item: return jsonify({"error": "Item not found"}), 404
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Item deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

_EXT_MIME = {
    '.pdf':  'application/pdf',
    '.zip':  'application/zip',
    '.tar':  'application/x-tar',
    '.gz':   'application/gzip',
    '.rar':  'application/vnd.rar',
    '.7z':   'application/x-7z-compressed',
    '.sql':  'application/sql',
    '.db':   'application/octet-stream',
    '.sqlite': 'application/octet-stream',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xls':  'application/vnd.ms-excel',
    '.csv':  'text/csv',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.doc':  'application/msword',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.ppt':  'application/vnd.ms-powerpoint',
    '.txt':  'text/plain',
    '.md':   'text/markdown',
}

@registry_bp.route('/download/<int:id>/<string:doc_type>', methods=['GET'], strict_slashes=False)
@login_required
def download_file(id, doc_type):
    from models import ArchivalLedger, db
    try:
        record = db.session.get(ArchivalLedger, id)
        if not record: return jsonify({"error": "Record not found"}), 404
        is_preview = request.args.get('preview') == '1'
        local_path_rel = getattr(record, f"{doc_type}_local_path")
        # Derive the real on-disk extension so we serve the file with a correct mime
        # type. Previously everything was sent as application/pdf which made the
        # browser try to render .zip / .sql files as PDFs -> "Failed to load PDF".
        ext = '.pdf'
        if local_path_rel:
            ext = os.path.splitext(local_path_rel)[1].lower() or '.pdf'
        mime = _EXT_MIME.get(ext, 'application/octet-stream')
        filename = f"{record.project_title}_{doc_type.upper()}{ext}"
        # If user clicked Preview but the file is not browser-renderable inline,
        # force download instead so they actually get the file rather than a blank
        # PDF viewer error page.
        force_download = (not is_preview) or (mime not in ('application/pdf', 'text/plain', 'text/markdown', 'text/csv'))
        if local_path_rel:
            archive_root = os.getenv('ARCHIVE_ROOT', 'Capstone_Archives')
            full_path = os.path.join(archive_root, local_path_rel)
            if os.path.exists(full_path):
                return send_file(full_path, mimetype=mime, as_attachment=force_download, download_name=filename)
        content = getattr(record, f"{doc_type}_binary")
        if content:
            return send_file(io.BytesIO(content), mimetype=mime, as_attachment=force_download, download_name=filename)
        return jsonify({"error": "File content not found"}), 404
    except Exception as e: return jsonify({"error": str(e)}), 500

@registry_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    if current_user.role != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    from models import ArchivalLedger
    archived_count = db.session.query(ArchivalLedger.project_id).filter(ArchivalLedger.status.in_(['archived', 'partial'])).distinct().count()
    pending_count = 0
    service_account_ok = False
    try:
        sheets_service, _ = get_services()
        years = sheets_service.get_all_sheet_names()
        if years:
            result = sheets_service.get_all_projects(years[0])
            projects = result.get('projects', [])
            # Re-calculate status using DB just like the dashboard does
            from models import ArchivalLedger
            all_records = ArchivalLedger.query.filter_by(academic_year=years[0]).order_by(ArchivalLedger.id.desc()).all()
            record_map = {str(r.project_id).strip().lower(): r for r in all_records}
            
            p_count = 0
            for p in projects:
                pid_norm = str(p['project_id']).strip().lower()
                last_record = record_map.get(pid_norm)
                status = last_record.status.lower() if last_record else 'pending'
                if status == 'pending': p_count += 1
            pending_count = p_count
        service_account_ok = True
    except Exception as e:
        logger.error(f"Stats Error: {e}")
    
    return jsonify({
        "archived_count": archived_count,
        "pending_count": pending_count,
        "service_account_configured": service_account_ok and os.path.exists(os.getenv('SERVICE_ACCOUNT_JSON', '')),
        "last_sync": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
