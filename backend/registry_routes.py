from flask import Blueprint, jsonify, request, current_app, session
from flask_login import login_required, current_user
import os
import requests
import threading
import logging
import datetime
from registry_sheets import RegistrySheetsService
from archival_engine import ArchivalEngine
from models import db
from google.oauth2.credentials import Credentials

registry_bp = Blueprint('registry', __name__)
logger = logging.getLogger(__name__)

# Global tracker for live project statuses (Real-time sync helper)
# Key: {sheet_id}_{year}_{row_index}, Value: status string
LIVE_STATUS_TRACKER = {}

def get_user_creds():
    token = session.get('access_token')
    if not token:
        return None
    return Credentials(token)

def get_services(requested_sheet_id=None, provided_user_creds=None):
    # Priority for Sheet ID
    sheet_id = requested_sheet_id
    if not sheet_id and request:
        try:
            if request.is_json:
                sheet_id = request.json.get('sheet_id')
            if not sheet_id:
                sheet_id = request.args.get('sheet_id')
        except: pass
            
    if not sheet_id:
        sheet_id = os.getenv('SHEET_ID')
        
    user_creds = provided_user_creds or get_user_creds()
    service_account_path = os.getenv('SERVICE_ACCOUNT_JSON')
    archive_root = os.getenv('ARCHIVE_ROOT', 'Capstone_Archives')
    
    sheets_service = RegistrySheetsService(
        service_account_json_path=service_account_path if not user_creds else None, 
        sheet_id=sheet_id,
        user_credentials=user_creds
    )
    
    engine = ArchivalEngine(
        service_account_json_path=service_account_path if not user_creds else None, 
        archive_root=archive_root,
        user_credentials=user_creds
    )
    return sheets_service, engine

@registry_bp.route('/api/registry/list-sheets', methods=['GET'])
@login_required
def list_sheets():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    try:
        user_creds = get_user_creds()
        service_account_path = os.getenv('SERVICE_ACCOUNT_JSON')
        sheets_service = RegistrySheetsService(
            service_account_json_path=service_account_path if not user_creds else None,
            user_credentials=user_creds
        )
        sheets = sheets_service.list_available_sheets()
        return jsonify(sheets)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@registry_bp.route('/api/registry/years', methods=['GET'])
@login_required
def get_years():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    try:
        sheets_service, _ = get_services()
        if not sheets_service.workbook:
             return jsonify({"error": "No Google Sheet selected"}), 400
        years = sheets_service.get_all_sheet_names()
        return jsonify(years)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@registry_bp.route('/api/registry/projects', methods=['GET'])
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
        
        # Merge with LIVE_STATUS_TRACKER for real-time feel
        for p in projects:
            tracker_key = f"{sheet_id}_{year}_{p['row_index']}"
            if tracker_key in LIVE_STATUS_TRACKER:
                p['status'] = LIVE_STATUS_TRACKER[tracker_key]

            # Add latest version info from DB
            last_record = ArchivalLedger.query.filter_by(
                project_id=p['project_id'],
                academic_year=year,
                status='archived'
            ).order_by(ArchivalLedger.version.desc()).first()
            p['latest_version'] = last_record.version if last_record else 0
            
        return jsonify(projects)
    except Exception as e:
        logger.error(f"Failed to fetch projects: {e}")
        return jsonify({"error": "Google Sheets is currently busy."}), 503

@registry_bp.route('/api/registry/validate', methods=['POST'])
@login_required
def validate_links():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    links = request.json.get('links', [])
    results = {}
    for link in links:
        if not link: 
            results[link] = "Empty"
            continue
        try:
            resp = requests.get(link, timeout=5, stream=True)
            results[link] = "Accessible" if resp.status_code == 200 else f"Error {resp.status_code}"
        except:
            results[link] = "Failed"
    return jsonify(results)

@registry_bp.route('/api/registry/archive', methods=['POST'])
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

    app = current_app._get_current_object()
    
    def process_task(app_context, project_list, creds, sid, wb_name):
        from concurrent.futures import ThreadPoolExecutor
        # Bumping to 20 workers for maximum Professor-speed! 
        # (Watch RAM usage on Hostinger)
        with ThreadPoolExecutor(max_workers=20) as executor:
            def process_single_project(p):
                tracker_key = f"{sid}_{p['academic_year']}_{p['row_index']}"
                LIVE_STATUS_TRACKER[tracker_key] = "Processing"
                with app_context.app_context():
                    try:
                        # Random small jitter to avoid simultaneous API bursts
                        import time, random
                        time.sleep(random.uniform(0.1, 0.8))

                        sheets_service, engine = get_services(requested_sheet_id=sid, provided_user_creds=creds)
                        sheets_service.update_status(p['academic_year'], p['row_index'], 'Processing')
                        
                        result = engine.archive_project(p, workbook_name=wb_name)
                        status = result['status'].capitalize()
                        if result['status'] == 'unchanged': status = 'Archived'
                        
                        LIVE_STATUS_TRACKER[tracker_key] = status
                        paths = result.get('paths', {})
                        sheets_service.update_status(
                            p['academic_year'], p['row_index'], status,
                            srs_path=paths.get('srs'), sdd_path=paths.get('sdd'),
                            spmp_path=paths.get('spmp'), std_path=paths.get('std'),
                            ri_path=paths.get('ri'), error_msg=result.get('error')
                        )
                    except Exception as e:
                        logger.error(f"Failed to process {p.get('project_title')}: {e}")
                        LIVE_STATUS_TRACKER[tracker_key] = "Failed"
                        try:
                            sheets_service, _ = get_services(requested_sheet_id=sid, provided_user_creds=creds)
                            sheets_service.update_status(p['academic_year'], p['row_index'], 'Failed', error_msg=str(e))
                        except: pass
                    finally:
                        db.session.remove()

            list(executor.map(process_single_project, project_list))

    thread = threading.Thread(target=process_task, args=(app, projects, user_creds, sheet_id, workbook_name))
    thread.start()
    return jsonify({"message": f"Started archival for {len(projects)} projects."}), 202

@registry_bp.route('/api/registry/download/<int:ledger_id>/<doc_type>', methods=['GET'])
@login_required
def download_from_db(ledger_id, doc_type):
    from models import ArchivalLedger
    from flask import send_file
    import io
    record = ArchivalLedger.query.get_or_404(ledger_id)
    preview = request.args.get('preview') == '1'
    
    path_field = f"{doc_type}_local_path"
    binary_field = f"{doc_type}_binary"
    hash_field = f"{doc_type}_hash"
    
    binary_data = getattr(record, binary_field, None)
    file_path = getattr(record, path_field, '')
    target_hash = getattr(record, hash_field, None)
    
    if not binary_data and target_hash:
        source_record = ArchivalLedger.query.filter(
            ArchivalLedger.project_id == record.project_id,
            getattr(ArchivalLedger, hash_field) == target_hash,
            getattr(ArchivalLedger, binary_field).isnot(None)
        ).order_by(ArchivalLedger.id.asc()).first()
        if source_record: binary_data = getattr(source_record, binary_field)

    if not binary_data: return jsonify({"error": "File not found"}), 404

    ext = os.path.splitext(file_path)[1] if file_path else ".pdf"
    clean_title = record.project_title.replace(' ', '_').replace('/', '_')
    filename = f"{clean_title}_{doc_type.upper()}_v{record.version}{ext}"

    return send_file(
        io.BytesIO(binary_data),
        mimetype='application/pdf',
        as_attachment=not preview,
        download_name=filename,
        max_age=0 if preview else None
    )

@registry_bp.route('/api/registry/reset', methods=['POST'])
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
    except Exception as e: return jsonify({"error": str(e)}), 500

@registry_bp.route('/api/registry/ledger/grouped', methods=['GET'])
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
        logger.error(f"Ledger Group Error: {e}")
        return jsonify([])

@registry_bp.route('/api/registry/ledger/workbooks', methods=['GET'])
@login_required
def get_ledger_workbooks():
    if current_user.role != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    try:
        from models import ArchivalLedger, db
        workbooks = db.session.query(ArchivalLedger.workbook_name).distinct().all()
        return jsonify([w[0] for w in workbooks if w and w[0]])
    except: return jsonify([])

@registry_bp.route('/api/registry/ledger/tabs', methods=['GET'])
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
    except: return jsonify([])

@registry_bp.route('/api/registry/ledger', methods=['GET'])
@login_required
def get_ledger():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    
    from models import ArchivalLedger
    from sqlalchemy.orm import defer
    
    # We use defer() to skip the heavy binary columns during listing. 
    # This makes the API much faster.
    records = ArchivalLedger.query.options(
        defer(ArchivalLedger.srs_binary), 
        defer(ArchivalLedger.sdd_binary),
        defer(ArchivalLedger.spmp_binary),
        defer(ArchivalLedger.std_binary),
        defer(ArchivalLedger.ri_binary),
        defer(ArchivalLedger.srs_text),
        defer(ArchivalLedger.sdd_text),
        defer(ArchivalLedger.spmp_text),
        defer(ArchivalLedger.std_text),
        defer(ArchivalLedger.ri_text)
    ).order_by(ArchivalLedger.id.desc()).all()
    
    return jsonify([{
        "id": r.id,
        "project_id": r.project_id,
        "project_title": r.project_title,
        "academic_year": r.academic_year,
        "workbook_name": r.workbook_name,
        "status": r.status,
        "version": r.version,
        "archived_at": r.archived_at.strftime("%Y-%m-%d %H:%M:%S") if r.archived_at else None
    } for r in records])

@registry_bp.route('/api/registry/ledger/<int:ledger_id>', methods=['DELETE'])
@login_required
def delete_ledger_record(ledger_id):
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    
    from models import ArchivalLedger
    record = ArchivalLedger.query.get_or_404(ledger_id)
    
    try:
        # Delete from Database first to ensure it's removed even if disk cleanup fails
        db.session.delete(record)
        db.session.commit()
        return jsonify({"message": "Successfully removed record"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"DELETE ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@registry_bp.route('/api/registry/stats', methods=['GET'])
@login_required
def get_stats():
    if current_user.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
    
    from models import ArchivalLedger
    import os
    
    # 1. Total Archived Count (unique projects)
    archived_count = db.session.query(ArchivalLedger.project_id).distinct().count()
    
    # 2. Pending Count (from first available year of default sheet)
    pending_count = 0
    service_account_ok = False
    try:
        sheets_service, _ = get_services()
        years = sheets_service.get_all_sheet_names()
        if years:
            all_projects = sheets_service.get_all_projects(years[0])
            pending_count = len([p for p in all_projects if p['status'].lower() == 'pending'])
        service_account_ok = True
    except Exception as e:
        logger.error(f"Stats Error: {e}")

    return jsonify({
        "archived_count": archived_count,
        "pending_count": pending_count,
        "service_account_configured": service_account_ok and os.path.exists(os.getenv('SERVICE_ACCOUNT_JSON', '')),
        "last_sync": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
