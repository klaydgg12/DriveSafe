from flask import Blueprint, jsonify, request, current_app, session, has_request_context
from flask_login import login_required, current_user
import os
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

# Global tracker for live project statuses (Real-time sync helper)
LIVE_STATUS_TRACKER = {}

def get_user_creds():
    # Only access session if in request context
    if not has_request_context():
        return None
    token = session.get('access_token')
    if not token:
        logger.warning("DEBUG: Access token missing from session")
        return None
    try:
        logger.info("DEBUG: Recreating Credentials from session token")
        return Credentials(token, scopes=[
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets"
        ])
    except Exception as e:
        logger.error(f"DEBUG: Failed to create credentials: {e}")
        return None

def get_services(requested_sheet_id=None, provided_user_creds=None):
    logger.info("DEBUG: Entering get_services")
    sheet_id = requested_sheet_id
    
    # Safely handle request context
    if not sheet_id and has_request_context():
        try:
            # Prefer args for GET requests
            sheet_id = request.args.get('sheet_id')
            if not sheet_id and request.is_json:
                sheet_id = request.json.get('sheet_id')
        except: pass
            
    if not sheet_id:
        sheet_id = os.getenv('SHEET_ID')
        
    logger.info(f"DEBUG: Target Sheet ID: {sheet_id}")
    user_creds = provided_user_creds or get_user_creds()
    service_account_path = os.getenv('SERVICE_ACCOUNT_JSON')
    archive_root = os.getenv('ARCHIVE_ROOT', 'Capstone_Archives')
    
    logger.info(f"DEBUG: User Creds Present: {user_creds is not None}")
    logger.info(f"DEBUG: Service Account Path Present: {service_account_path is not None}")

    try:
        sheets_service = RegistrySheetsService(
            user_credentials=user_creds,
            service_account_json_path=service_account_path if not user_creds else None,
            sheet_id=sheet_id
        )
        logger.info("DEBUG: RegistrySheetsService initialized")
    except Exception as e:
        logger.error(f"DEBUG: Failed to init RegistrySheetsService: {e}", exc_info=True)
        raise e
    
    try:
        engine = ArchivalEngine(
            user_credentials=user_creds,
            service_account_json_path=service_account_path if not user_creds else None,
            archive_root=archive_root
        )
        logger.info("DEBUG: ArchivalEngine initialized")
    except Exception as e:
        logger.error(f"DEBUG: Failed to init ArchivalEngine: {e}", exc_info=True)
        raise e

    return sheets_service, engine

@registry_bp.route('/list-sheets', methods=['GET'], strict_slashes=False)
@login_required
def list_sheets():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    try:
        logger.info("DEBUG: Requesting list_sheets")
        sheets_service, _ = get_services()
        logger.info("DEBUG: Calling sheets_service.list_available_sheets()")
        sheets = sheets_service.list_available_sheets()
        logger.info(f"DEBUG: list_available_sheets returned {len(sheets)} items")
        return jsonify(sheets)
    except Exception as e:
        logger.error(f"DEBUG: List sheets route error: {str(e)}", exc_info=True)
        error_detail = str(e)
        if "invalid_grant" in error_detail.lower():
            error_detail = "Your Google session has expired. Please log out and sign in again."
        elif "Drive API" in error_detail or "403" in error_detail:
            error_detail = "Google Drive API is either not enabled or permissions are missing."
            
        return jsonify({
            "error": error_detail, 
            "traceback": traceback.format_exc()
        }), 500

@registry_bp.route('/years', methods=['GET'], strict_slashes=False)
@login_required
def get_years():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    try:
        logger.info("DEBUG: get_years requested")
        sheets_service, _ = get_services()
        if not sheets_service or not sheets_service.workbook:
             logger.warning("DEBUG: get_years - no workbook selected")
             return jsonify({"error": "No Google Sheet selected or service unavailable"}), 400
        years = sheets_service.get_all_sheet_names()
        logger.info(f"DEBUG: get_years found {len(years)} sheets")
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
        projects = sheets_service.get_all_projects(year)
        
        for p in projects:
            tracker_key = f"{sheet_id}_{year}_{p['row_index']}"
            if tracker_key in LIVE_STATUS_TRACKER:
                p['status'] = LIVE_STATUS_TRACKER[tracker_key]

            last_record = ArchivalLedger.query.filter_by(
                project_id=p['project_id'],
                academic_year=year,
                status='archived'
            ).order_by(ArchivalLedger.version.desc()).first()
            p['latest_version'] = last_record.version if last_record else 0
            
        return jsonify(projects)
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
        query = ArchivalLedger.query.options(
            defer(ArchivalLedger.srs_binary), defer(ArchivalLedger.sdd_binary),
            defer(ArchivalLedger.spmp_binary), defer(ArchivalLedger.std_binary),
            defer(ArchivalLedger.ri_binary), defer(ArchivalLedger.srs_text),
            defer(ArchivalLedger.sdd_text), defer(ArchivalLedger.spmp_text),
            defer(ArchivalLedger.std_text), defer(ArchivalLedger.ri_text)
        )
        if academic_year: query = query.filter_by(academic_year=academic_year)
        if workbook_name: query = query.filter_by(workbook_name=workbook_name)
        records = query.order_by(ArchivalLedger.id.asc()).all()
        if not records: return jsonify([])
        last_hashes = defaultdict(lambda: defaultdict(lambda: None))
        doc_versions = defaultdict(lambda: defaultdict(int))
        grouped_data = {}
        for r in records:
            project_key = f"{r.project_id}_{r.project_title}"
            if project_key not in grouped_data:
                grouped_data[project_key] = {
                    "project_id": r.project_id, "project_title": r.project_title,
                    "academic_year": r.academic_year, "workbook_name": r.workbook_name,
                    "documents": { "srs": [], "sdd": [], "spmp": [], "std": [], "ri": [] }
                }
            target = grouped_data[project_key]
            for doc_type in ["srs", "sdd", "spmp", "std", "ri"]:
                path = getattr(r, f"{doc_type}_local_path")
                current_hash = getattr(r, f"{doc_type}_hash")
                if path and current_hash:
                    if current_hash != last_hashes[project_key][doc_type]:
                        last_hashes[project_key][doc_type] = current_hash
                        doc_versions[project_key][doc_type] += 1
                        target["documents"][doc_type].append({
                            "id": r.id, "version": doc_versions[project_key][doc_type],
                            "hash": current_hash, "timestamp": r.archived_at.strftime("%Y-%m-%d %H:%M:%S") if r.archived_at else None,
                            "status": r.status
                        })
        result = list(grouped_data.values())
        for project in result:
            for doc_type in project["documents"]: project["documents"][doc_type].reverse()
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
    
    user_creds = get_user_creds()
    sheet_id = request.json.get('sheet_id') or request.args.get('sheet_id') or os.getenv('SHEET_ID')
    
    try:
        sheets_service, _ = get_services(requested_sheet_id=sheet_id, provided_user_creds=user_creds)
        workbook_name = sheets_service.get_workbook_name()
    except:
        workbook_name = "Archives"

    app_obj = current_app._get_current_object()
    
    def process_task(app_context, project_list, creds, sid, wb_name):
        from concurrent.futures import ThreadPoolExecutor
        to_process = []
        for p in project_list:
            tracker_key = f"{sid}_{p['academic_year']}_{p['row_index']}"
            if LIVE_STATUS_TRACKER.get(tracker_key) != "Processing":
                to_process.append(p)
                LIVE_STATUS_TRACKER[tracker_key] = "Processing"
        
        if not to_process: return

        with app_context.app_context():
            try:
                sheets_service, _ = get_services(requested_sheet_id=sid, provided_user_creds=creds)
                from collections import defaultdict
                init_updates = defaultdict(list)
                for p in to_process:
                    init_updates[p['academic_year']].append({'row_index': p['row_index'], 'status': 'Processing'})
                for s_name, upds in init_updates.items():
                    sheets_service.batch_update_statuses(s_name, upds)
            except Exception as e:
                logger.error(f"Initial batch status update failed: {e}")
            finally:
                db.session.remove()

        with ThreadPoolExecutor(max_workers=8) as executor:
            def process_single_project(p):
                tracker_key = f"{sid}_{p['academic_year']}_{p['row_index']}"
                with app_context.app_context():
                    try:
                        import time, random
                        time.sleep(random.uniform(0.1, 2.0))
                        _, engine = get_services(requested_sheet_id=sid, provided_user_creds=creds)
                        result = engine.archive_project(p, workbook_name=wb_name)
                        status = result['status'].capitalize()
                        if result['status'] == 'unchanged': status = 'Archived'
                        LIVE_STATUS_TRACKER[tracker_key] = status
                        paths = result.get('paths', {})
                        return {
                            'sheet_name': p['academic_year'], 'row_index': p['row_index'], 'status': status,
                            'kwargs': {
                                'srs_path': paths.get('srs'), 'sdd_path': paths.get('sdd'), 'spmp_path': paths.get('spmp'),
                                'std_path': paths.get('std'), 'ri_path': paths.get('ri'), 'error_msg': result.get('error')
                            }
                        }
                    except Exception as e:
                        logger.error(f"Failed to process {p.get('project_title')}: {e}")
                        LIVE_STATUS_TRACKER[tracker_key] = "Failed"
                        return { 'sheet_name': p['academic_year'], 'row_index': p['row_index'], 'status': 'Failed', 'kwargs': {'error_msg': str(e)} }
                    finally:
                        db.session.remove()

            results = list(executor.map(process_single_project, to_process))
            from collections import defaultdict
            final_updates = defaultdict(list)
            for res in results:
                if res: final_updates[res['sheet_name']].append(res)
            
            if final_updates:
                with app_context.app_context():
                    try:
                        sheets_service, _ = get_services(requested_sheet_id=sid, provided_user_creds=creds)
                        for sheet_name, status_updates in final_updates.items():
                            sheets_service.batch_update_statuses(sheet_name, status_updates)
                    except Exception as e:
                        logger.error(f"Final batch update failed: {e}")
                    finally:
                        db.session.remove()

    thread = threading.Thread(target=process_task, args=(app_obj, projects, user_creds, sheet_id, workbook_name))
    thread.start()
    return jsonify({"message": f"Started archival for {len(projects)} projects."}), 202

@registry_bp.route('/reset', methods=['POST'])
@login_required
def reset_project_status():
    if current_user.role != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    project = request.json.get('project')
    if not project: return jsonify({"error": "No project"}), 400
    try:
        sheets_service, _ = get_services()
        sheets_service.update_status(
            project['academic_year'], project['row_index'], 'Pending', 
            srs_path='', sdd_path='', spmp_path='', std_path='', ri_path='', error_msg=''
        )
        return jsonify({"message": "Reset successful"})
    except Exception as e: return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@registry_bp.route('/ledger/<int:id>', methods=['DELETE', 'OPTIONS'], strict_slashes=False)
@login_required
def delete_ledger_item(id):
    if request.method == 'OPTIONS':
        return '', 204
    if current_user.role != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    try:
        from models import ArchivalLedger, db
        # Use session.get for SQLAlchemy 2.0 compatibility
        item = db.session.get(ArchivalLedger, id)
        if not item: 
            logger.warning(f"DELETE FAILED: Item {id} not found in database")
            return jsonify({"error": "Item not found"}), 404
        
        db.session.delete(item)
        db.session.commit()
        logger.info(f"DELETE SUCCESS: Item {id} removed by {current_user.email}")
        return jsonify({"message": "Item deleted successfully"})
    except Exception as e:
        db.session.rollback()
        logger.error(f"DELETE ERROR on item {id}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@registry_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    if current_user.role != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    from models import ArchivalLedger
    archived_count = db.session.query(ArchivalLedger.project_id).distinct().count()
    pending_count = 0
    service_account_ok = False
    try:
        sheets_service, _ = get_services()
        years = sheets_service.get_all_sheet_names()
        if years:
            all_projects = sheets_service.get_all_projects(years[0])
            pending_count = len([p for p in all_projects if p['status'].lower() == 'pending'])
        service_account_ok = True
    except: pass
    return jsonify({
        "archived_count": archived_count, "pending_count": pending_count,
        "service_account_configured": service_account_ok and os.path.exists(os.getenv('SERVICE_ACCOUNT_JSON', '')),
        "last_sync": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
