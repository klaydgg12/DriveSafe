import os
import traceback
# CRITICAL: This must be set before other imports to handle Google's scope expansion
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from werkzeug.middleware.proxy_fix import ProxyFix
import datetime
import json
import os
import dotenv
import traceback

# Load environment variables
dotenv.load_dotenv()

from models import db, User, ArchivalLedger

app = Flask(__name__, 
            static_folder='../frontend/dist',
            static_url_path='/')

# Handle proxies (Railway, Render, etc.)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# --- DEBUG STATUS ROUTE (ABSOLUTE TOP) ---
@app.route('/api/debug-status', methods=['GET'])
def debug_status():
    db_ok = False
    try:
        db.session.execute(db.text('SELECT 1'))
        db_ok = True
    except: pass

    # Test Google API Connectivity
    drive_api_ok = "Not Tested"
    try:
        from registry_sheets import RegistrySheetsService
        # Check if service account is configured
        sa_path = os.getenv('SERVICE_ACCOUNT_JSON')
        if sa_path:
            svc = RegistrySheetsService(service_account_json_path=sa_path)
            svc.client.list_spreadsheet_files()
            drive_api_ok = "Service Account OK"
        else:
            drive_api_ok = "No Service Account Env Var"
    except Exception as e:
        drive_api_ok = f"Error: {str(e)}"

    return jsonify({
        "status": "active",
        "database": "connected" if db_ok else "disconnected",
        "drive_api_test": drive_api_ok,
        "session_keys": list(session.keys()),
        "path": request.path,
        "is_prod_detected": os.getenv('NODE_ENV') == 'production' or os.getenv('RAILWAY_ENVIRONMENT') is not None
    })

# --- FRONTEND ROUTES ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # Check if we are requesting a file that exists in the static folder
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Otherwise, serve index.html for React Router
    return send_from_directory(app.static_folder, 'index.html')

# --- AUTH ROUTES ---
@app.route('/auth/google', methods=['POST'])
def google_auth():
    code = request.json.get('code')
    try:
        from google_auth_oauthlib.flow import Flow 
        import json
        
        # Priority 1: GOOGLE_CLIENT_SECRET_JSON environment variable
        env_secret = os.getenv('GOOGLE_CLIENT_SECRET_JSON')
        if env_secret:
            logger.info("Using GOOGLE_CLIENT_SECRET_JSON from environment")
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
            # Fallback: physical file
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
        # ...
        service = build('oauth2', 'v2', credentials=flow.credentials)
        user_info = service.userinfo().get().execute()
        
        user = User.query.filter_by(email=user_info['email']).first()
        if not user:
            role = 'teacher' 
            user = User(email=user_info['email'], name=user_info['name'], role=role)
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
        print(f"AUTH ERROR: {str(e)}")
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

from werkzeug.exceptions import HTTPException

@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors (404, 405, etc.)
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code
    
    # Otherwise, it's a real server error (500)
    print("--- INTERNAL SERVER ERROR ---")
    traceback.print_exc()
    return jsonify({
        "error": str(e), 
        "traceback": traceback.format_exc()
    }), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # On Railway/VPS, the PORT is provided by the environment or defaults to 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
