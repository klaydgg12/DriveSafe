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
    if not has_request_context(): return None
    token = session.get('access_token')
    if not token: return None
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
    if force_user and not user_creds: raise Exception("Google Session Required: Please login again.")
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
    try:
        sheets_service, _ = get_services()
        return jsonify(sheets_service.list_available_sheets())
    except Exception as e: return jsonify({"error": str(e)}), 500

@registry_bp.route('/years', methods=['GET'], strict_slashes=False)
@login_required
def get_years():
    try:
        sheets_service, _ = get_services()
        return jsonify(sheets_service.get_all_sheet_names())
    except Exception as e: return jsonify({"error": str(e)}), 500

@registry_bp.route('/projects', methods=['GET'], strict_slashes=False)
@login_required
def get_pending():
    year = request.args.get('year')
    sheet_id = request.args.get('sheet_id') or os.getenv('SHEET_ID')
    if not year: return jsonify({"error": "Year required"}), 400
    try:
        from models import ArchivalLedger
        sheets_service, _ = get_services(requested_sheet_id=sheet_id)
        result = sheets_service.get_all_projects(year)
        all_records = ArchivalLedger.query.filter_by(academic_year=year).order_by(ArchivalLedger.id.desc()).all()
        record_map = {str(r.project_id).strip().lower(): r for r in all_records}

        for p in result['projects']:
            pid_norm = str(p['project_id']).strip().lower()
            tracker_key = f"{sheet_id}_{year}_{p['row_index']}"
            last_record = record_map.get(pid_norm)
            p['status'] = LIVE_STATUS_TRACKER.get(tracker_key) or (last_record.status.capitalize() if last_record else 'Pending')
            p['error_message'] = LIVE_ERROR_TRACKER.get(tracker_key) or (last_record.error_message if last_record else '')
            p['latest_version'] = last_record.version if last_record else 0
            p['latest_id'] = last_record.id if last_record else None
        return jsonify(result)
    except Exception as e: return jsonify({"error": str(e)}), 500

@registry_bp.route('/archive', methods=['POST'])
@login_required
def archive_selected():
    projects = request.json.get('projects', [])
    sheet_id = request.json.get('sheet_id') or os.getenv('SHEET_ID')
    if not projects: return jsonify({"error": "No projects"}), 400
    import uuid
    batch_id = str(uuid.uuid4())[:13]
    user_creds = get_user_creds()
    user_email = current_user.email
    try:
        sheets_service, _ = get_services(requested_sheet_id=sheet_id, provided_user_creds=user_creds, force_user=True)
        workbook_name = sheets_service.get_workbook_name()
    except Exception as e: return jsonify({"error": str(e)}), 401
    for p in projects:
        key = f"{sheet_id}_{p['academic_year']}_{p['row_index']}"
        LIVE_STATUS_TRACKER[key] = "Processing"
        if key in LIVE_ERROR_TRACKER: del LIVE_ERROR_TRACKER[key]
    app_obj = current_app._get_current_object()
    def process_task(app_context, project_list, creds, sid, wb_name, archived_by_email):
        with app_context.app_context():
            from models import db
            try:
                for p in project_list:
                    key = f"{sid}_{p['academic_year']}_{p['row_index']}"
                    try:
                        _, engine = get_services(requested_sheet_id=sid, provided_user_creds=creds, force_user=True)
                        res = engine.archive_project(p, workbook_name=wb_name, batch_id=batch_id, archived_by=archived_by_email)
                        LIVE_STATUS_TRACKER[key] = res['status'].capitalize() if res['status'] != 'unchanged' else 'Archived'
                        if res.get('error'): LIVE_ERROR_TRACKER[key] = res['error']
                    except Exception as e:
                        LIVE_STATUS_TRACKER[key] = "Failed"
                        LIVE_ERROR_TRACKER[key] = str(e)
                    finally: db.session.remove()
            finally:
                for p in project_list:
                    k = f"{sid}_{p['academic_year']}_{p['row_index']}"
                    if LIVE_STATUS_TRACKER.get(k) == "Processing": LIVE_STATUS_TRACKER[k] = "Failed"
    threading.Thread(target=process_task, args=(app_obj, projects, user_creds, sheet_id, workbook_name, user_email)).start()
    return jsonify({"message": "Archival started"}), 202

@registry_bp.route('/reset', methods=['POST'])
@login_required
def reset_project_status():
    project = request.json.get('project')
    if not project: return jsonify({"error": "No project"}), 400
    try:
        from models import ArchivalLedger, db
        last_record = ArchivalLedger.query.filter_by(project_id=project['project_id'], academic_year=project['academic_year']).order_by(ArchivalLedger.id.desc()).first()
        if last_record:
            db.session.delete(last_record)
            db.session.commit()
        return jsonify({"message": "Status reset"})
    except Exception as e: return jsonify({"error": str(e)}), 500

@registry_bp.route('/transactions', methods=['GET'], strict_slashes=False)
@login_required
def get_transactions():
    try:
        from models import ArchivalLedger
        from sqlalchemy.orm import defer
        from collections import defaultdict
        records = ArchivalLedger.query.options(
            *[defer(getattr(ArchivalLedger, f"{dt}_{suffix}")) for dt in ['srs','sdd','spmp','std','ri','research_paper','usability_test','presentation','source_code','database','readme'] for suffix in ['binary','text']]
        ).order_by(ArchivalLedger.archived_at.asc()).all()
        hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for r in records: hierarchy[r.workbook_name or "Unknown"][r.academic_year or "General"][r.batch_id or "Direct"].append(r)
        result = []
        for wb_n, sheets in hierarchy.items():
            wb_d = {"name": wb_n, "sheets": []}
            for sh_n, batches in sheets.items():
                sh_d = {"name": sh_n, "transactions": []}
                sorted_bids = sorted(batches.keys(), key=lambda b: batches[b][0].archived_at)
                for idx, bid in enumerate(sorted_bids):
                    recs = batches[bid]
                    sh_d["transactions"].append({
                        "transaction_id": bid, "transaction_label": f"Transaction {idx + 1}",
                        "timestamp": recs[0].archived_at.isoformat() + 'Z', "archived_by": recs[0].archived_by,
                        "project_count": len(recs),
                        "projects": [{"id": pr.id, "project_id": pr.project_id, "project_title": pr.project_title, "status": pr.status, "version": pr.version, "error": pr.error_message} for pr in recs]
                    })
                sh_d["transactions"].reverse()
                wb_d["sheets"].append(sh_d)
            result.append(wb_d)
        return jsonify(result)
    except Exception as e: return jsonify([])

@registry_bp.route('/download/<int:id>/<string:doc_type>', methods=['GET'], strict_slashes=False)
@login_required
def download_file(id, doc_type):
    from models import ArchivalLedger, db
    try:
        record = db.session.get(ArchivalLedger, id)
        if not record: return jsonify({"error": "No record"}), 404
        is_preview = request.args.get('preview') == '1'
        filename = f"{record.project_title}_{doc_type.upper()}.pdf"
        local_path = getattr(record, f"{doc_type}_local_path")
        if local_path:
            full_path = os.path.join(os.getenv('ARCHIVE_ROOT', 'Capstone_Archives'), local_path)
            if os.path.exists(full_path): return send_file(full_path, mimetype='application/pdf', as_attachment=not is_preview, download_name=filename)
        content = getattr(record, f"{doc_type}_binary")
        if content: return send_file(io.BytesIO(content), mimetype='application/pdf', as_attachment=not is_preview, download_name=filename)
        return jsonify({"error": "No content"}), 404
    except Exception as e: return jsonify({"error": str(e)}), 500

@registry_bp.route('/ledger/<int:id>', methods=['DELETE'], strict_slashes=False)
@login_required
def delete_ledger_item(id):
    try:
        from models import ArchivalLedger, db
        item = db.session.get(ArchivalLedger, id)
        if item:
            db.session.delete(item)
            db.session.commit()
        return jsonify({"message": "Deleted"})
    except: return jsonify({"error": "Delete failed"}), 500

@registry_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    from models import ArchivalLedger
    archived_count = db.session.query(ArchivalLedger.project_id).filter(ArchivalLedger.status.in_(['archived', 'partial'])).distinct().count()
    pending_count = 0
    try:
        sheets_service, _ = get_services()
        years = sheets_service.get_all_sheet_names()
        if years:
            result = sheets_service.get_all_projects(years[0])
            all_records = ArchivalLedger.query.filter_by(academic_year=years[0]).order_by(ArchivalLedger.id.desc()).all()
            record_map = {str(r.project_id).strip().lower(): r for r in all_records}
            p_count = 0
            for p in result['projects']:
                pid_norm = str(p['project_id']).strip().lower()
                last_record = record_map.get(pid_norm)
                if not last_record or last_record.status.lower() == 'pending': p_count += 1
            pending_count = p_count
    except: pass
    return jsonify({"archived_count": archived_count, "pending_count": pending_count, "service_account_configured": True, "last_sync": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
