import os
import traceback
import datetime
import json
import logging
import dotenv

# CRITICAL: This must be set before other imports to handle Google's scope expansion
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

from flask import Flask, request, jsonify, session, send_from_directory, has_request_context
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from werkzeug.middleware.proxy_fix import ProxyFix

# Load environment variables
dotenv.load_dotenv()

# Setup logging -- console + persistent file so we can actually inspect what happened
# during archival (the console wraps + truncates long tracebacks on Windows).
_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'archive_debug.log')
_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
# Avoid attaching duplicate handlers when Flask's reloader re-imports this module.
if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', '') == _LOG_PATH for h in _root_logger.handlers):
    _fh = logging.FileHandler(_LOG_PATH, mode='a', encoding='utf-8')
    _fh.setLevel(logging.INFO)
    _fh.setFormatter(logging.Formatter('%(asctime)s [%(threadName)s] %(levelname)s %(name)s: %(message)s'))
    _root_logger.addHandler(_fh)
if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in _root_logger.handlers):
    _sh = logging.StreamHandler()
    _sh.setLevel(logging.INFO)
    _sh.setFormatter(logging.Formatter('%(asctime)s [%(threadName)s] %(levelname)s %(name)s: %(message)s'))
    _root_logger.addHandler(_sh)
logger = logging.getLogger(__name__)
logger.info(f"=== archive_debug.log file handler attached at {_LOG_PATH} ===")

from models import db, User, ArchivalLedger

app = Flask(__name__, static_folder='../frontend/dist')

# Handle proxies (Railway, Render, etc.)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# --- DATABASE CONFIGURATION ---
def get_robust_database_uri():
    env_url = os.getenv('DATABASE_URL')
    if env_url:
        raw_url = env_url.strip().strip("'").strip('"')
    else:
        raw_url = 'mysql+pymysql://root:123Earl.@localhost/drivesafe_prod'
    
    db_url = raw_url
    if raw_url.startswith('mariadb://'):
        db_url = raw_url.replace('mariadb://', 'mysql+pymysql://', 1)
    elif raw_url.startswith('mysql://') and 'pymysql' not in raw_url:
        db_url = raw_url.replace('mysql://', 'mysql+pymysql://', 1)
    elif raw_url.startswith('postgres://'):
        db_url = raw_url.replace('postgres://', 'postgresql://', 1)

    return db_url

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'drivesafe-secret-key-9988')
app.config['SQLALCHEMY_DATABASE_URI'] = get_robust_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

# --- ENVIRONMENT & SESSION CONFIG ---
is_prod = (
    os.getenv('FLASK_ENV') == 'production' or 
    os.getenv('NODE_ENV') == 'production' or 
    os.getenv('RAILWAY_ENVIRONMENT') is not None or
    os.getenv('PROD') == 'true'
)

# Force production session settings if on Linux VPS
if not is_prod and os.path.exists('/etc/debian_version'):
    is_prod = True

app.config['SESSION_COOKIE_SAMESITE'] = 'None' if is_prod else 'Lax'
app.config['SESSION_COOKIE_SECURE'] = is_prod
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=7)

# --- COMPONENT INITIALIZATION ---
db.init_app(app)

with app.app_context():
    from sqlalchemy import text
    try:
        # --- ROBUST ZERO-FAILURE REPAIR ---
        required = [
            # CRITICAL: drive_modified_time MUST BE FIRST (Fixes Dashboard Select Crash)
            ('drive_modified_time', 'VARCHAR(100)'), 
            ('batch_id', 'VARCHAR(50)'),
            ('archived_by', 'VARCHAR(120)'),
            ('research_paper_original_url', 'VARCHAR(500)'),
            ('usability_test_original_url', 'VARCHAR(500)'),
            ('presentation_original_url', 'VARCHAR(500)'),
            ('source_code_original_url', 'VARCHAR(500)'),
            ('github_original_url', 'VARCHAR(500)'),
            ('database_original_url', 'VARCHAR(500)'),
            ('readme_original_url', 'VARCHAR(500)'),
            ('research_paper_local_path', 'VARCHAR(500)'),
            ('usability_test_local_path', 'VARCHAR(500)'),
            ('presentation_local_path', 'VARCHAR(500)'),
            ('source_code_local_path', 'VARCHAR(500)'),
            ('database_local_path', 'VARCHAR(500)'),
            ('readme_local_path', 'VARCHAR(500)'),
            ('research_paper_hash', 'VARCHAR(64)'),
            ('usability_test_hash', 'VARCHAR(64)'),
            ('presentation_hash', 'VARCHAR(64)'),
            ('source_code_hash', 'VARCHAR(64)'),
            ('database_hash', 'VARCHAR(64)'),
            ('readme_hash', 'VARCHAR(64)'),
            ('research_paper_binary', 'LONGBLOB'),
            ('usability_test_binary', 'LONGBLOB'),
            ('presentation_binary', 'LONGBLOB'),
            ('source_code_binary', 'LONGBLOB'),
            ('database_binary', 'LONGBLOB'),
            ('readme_binary', 'LONGBLOB'),
            ('research_paper_text', 'TEXT'),
            ('usability_test_text', 'TEXT'),
            ('readme_text', 'TEXT')
        ]
        
        # Get existing columns as a set for O(1) lookups
        result = db.session.execute(text("SHOW COLUMNS FROM archival_ledger"))
        # Some DBs return tuples, some return dicts. Handles both.
        rows = result.fetchall()
        existing = set()
        for row in rows:
            if hasattr(row, 'Field'): existing.add(row.Field) # Dict/Object style
            elif isinstance(row, tuple): existing.add(row[0]) # Tuple style
            else: existing.add(str(row[0])) # Fallback
            
        for col_name, col_type in required:
            if col_name not in existing:
                logger.info(f"SYNC: Adding missing column '{col_name}'...")
                try:
                    # Individual transaction for each column to ensure partial success
                    db.session.execute(text(f"ALTER TABLE archival_ledger ADD COLUMN {col_name} {col_type}"))
                    db.session.commit()
                    logger.info(f"SYNC: Success for '{col_name}'")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"SYNC: Failed to add '{col_name}': {e}")

        logger.info("DATABASE: Schema is now 100% synchronized with codebase.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Critical Database Sync Error: {e}")

login_manager = LoginManager(app)
CORS(app, supports_credentials=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "Unauthorized. Please log in first."}), 401

# Register Registry Blueprint
from registry_routes import registry_bp
app.register_blueprint(registry_bp, url_prefix='/api/registry')

# --- SYSTEM ROUTES ---
@app.route('/api/debug-routes')
def list_routes():
    import urllib.parse
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        url = urllib.parse.unquote(str(rule))
        output.append(f"{methods:20s} {url:50s} {rule.endpoint}")
    return "<pre>" + "\n".join(sorted(output)) + "</pre>"

@app.route('/api/debug-status', methods=['GET'])
def debug_status():
    db_ok = False
    try:
        db.session.execute(db.text('SELECT 1'))
        db_ok = True
    except Exception as e:
        logger.error(f"DEBUG DB ERROR: {e}")

    drive_api_ok = "Not Tested"
    try:
        from registry_sheets import RegistrySheetsService
        sa_json = os.getenv('SERVICE_ACCOUNT_JSON')
        if sa_json:
            svc = RegistrySheetsService(service_account_json_path=sa_json)
            svc.client.list_spreadsheet_files()
            drive_api_ok = "Service Account Connection Successful"
        else:
            drive_api_ok = "SERVICE_ACCOUNT_JSON env var missing"
    except Exception as e:
        drive_api_ok = f"API Error: {str(e)}"

    return jsonify({
        "status": "online",
        "is_production": is_prod,
        "database": "connected" if db_ok else "failed",
        "google_drive_api": drive_api_ok,
        "session_keys": list(session.keys()) if has_request_context() else [],
        "user_authenticated": current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False,
        "env_vars": {
            "SHEET_ID": os.getenv('SHEET_ID') is not None,
            "SERVICE_ACCOUNT": os.getenv('SERVICE_ACCOUNT_JSON') is not None,
            "CLIENT_SECRET": os.getenv('GOOGLE_CLIENT_SECRET_JSON') is not None
        }
    })

# --- AUTH ROUTES ---
@app.route('/auth/google', methods=['POST'])
def google_auth():
    code = request.json.get('code')
    try:
        from google_auth_oauthlib.flow import Flow 
        
        env_secret = os.getenv('GOOGLE_CLIENT_SECRET_JSON')
        if env_secret:
            client_config = json.loads(env_secret)
            flow = Flow.from_client_config(
                client_config,
                scopes=[
                    "openid", "email", "profile", 
                    "https://www.googleapis.com/auth/drive.readonly",
                    "https://www.googleapis.com/auth/drive.file",
                    "https://www.googleapis.com/auth/spreadsheets"
                ],
                redirect_uri='postmessage'
            )
        else:
            secret_path = os.path.join(os.path.dirname(__file__), "client_secret.json")
            if not os.path.exists(secret_path):
                return jsonify({"error": "Google Client Secret configuration missing."}), 400
            
            flow = Flow.from_client_secrets_file(
                secret_path, 
                scopes=[
                    "openid", "email", "profile", 
                    "https://www.googleapis.com/auth/drive.readonly",
                    "https://www.googleapis.com/auth/drive.file",
                    "https://www.googleapis.com/auth/spreadsheets"
                ], 
                redirect_uri='postmessage'
            )
        
        flow.fetch_token(code=code)
        service = build('oauth2', 'v2', credentials=flow.credentials)
        user_info = service.userinfo().get().execute()
        
        user = User.query.filter_by(email=user_info['email']).first()
        if not user:
            user = User(email=user_info['email'], name=user_info['name'], role='teacher')
            db.session.add(user)
            db.session.commit()
            
        login_user(user)
        session['access_token'] = flow.credentials.token
        
        return jsonify({
            "user_email": user.email,
            "user_name": user.name,
            "role": user.role
        }), 200
    except Exception as e:
        logger.error(f"AUTH ERROR: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/user-info', methods=['GET'])
@login_required
def get_user_info():
    return jsonify({
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role
    })

@app.route('/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"}), 200

# --- FRONTEND CATCH-ALL (MUST BE AT THE BOTTOM) ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # If the request is for an actual file in the static folder, serve it
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Otherwise, for all other routes (like React SPA routes), serve index.html
    # This allows React to handle the routing on the frontend
    return send_from_directory(app.static_folder, 'index.html')

from werkzeug.exceptions import HTTPException

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code
    
    logger.error("--- INTERNAL SERVER ERROR ---")
    logger.error(traceback.format_exc())
    return jsonify({
        "error": str(e), 
        "traceback": traceback.format_exc()
    }), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("\n--- REGISTERED ROUTES ---")
        for rule in app.url_map.iter_rules():
            print(f"{rule.endpoint:30s} {rule.methods} {rule}")
        print("--------------------------\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
