import os
# CRITICAL: This must be set before other imports to handle Google's scope expansion
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import datetime
import dotenv
import re

# Load environment variables
dotenv.load_dotenv()

from models import db, User, ArchivalLedger

app = Flask(__name__, 
            static_folder='../frontend/dist',
            static_url_path='/')

# --- DATABASE CONFIGURATION ---
def get_robust_database_uri():
    # Priority 1: Use DATABASE_URL from environment
    raw_url = os.getenv('DATABASE_URL', 'mysql+pymysql://root:123Earl.@localhost/drivesafe_prod').strip().strip("'").strip('"')
    
    # Validation
    if not raw_url or len(raw_url) < 10 or "://" not in raw_url:
        print("⚠️ [DATABASE] Invalid or missing DATABASE_URL. Falling back to SQLite.", flush=True)
        return 'sqlite:///drivesafe.db'
    
    db_url = raw_url
    # Ensure MySQL/MariaDB use pymysql driver
    if raw_url.startswith('mariadb://'):
        db_url = raw_url.replace('mariadb://', 'mysql+pymysql://', 1)
    elif raw_url.startswith('mysql://') and 'pymysql' not in raw_url:
        db_url = raw_url.replace('mysql://', 'mysql+pymysql://', 1)
    # Fix for Postgres if needed (Render often uses postgres://)
    elif raw_url.startswith('postgres://'):
        db_url = raw_url.replace('postgres://', 'postgresql://', 1)

    # Log connection (masked for security)
    masked = db_url.split('@')[-1] if '@' in db_url else db_url
    print(f"✅ [DATABASE] Connecting to: {db_url.split('://')[0]}://****@{masked}", flush=True)
    return db_url

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'drivesafe-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = get_robust_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True

# --- COMPONENT INITIALIZATION ---
db.init_app(app)
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
app.register_blueprint(registry_bp)

# --- DATABASE INITIALIZATION ---
@app.before_request
def create_tables():
    if not hasattr(app, '_db_initialized'):
        with app.app_context():
            db.create_all()
        app._db_initialized = True

# --- FRONTEND ROUTES ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# --- AUTH ROUTES ---
@app.route('/auth/google', methods=['POST'])
def google_auth():
    code = request.json.get('code')
    try:
        from google_auth_oauthlib.flow import Flow 
        import json
        secret_path = os.path.join(os.path.dirname(__file__), "client_secret.json")
        
        if not os.path.exists(secret_path):
            env_secret = os.getenv('GOOGLE_CLIENT_SECRET_JSON')
            if env_secret:
                with open(secret_path, 'w') as f:
                    json.loads(env_secret) 
                    f.write(env_secret)
            else:
                return jsonify({"error": "client_secret.json not found on backend."}), 400

        flow = Flow.from_client_secrets_file(
            secret_path, 
            scopes=[
                "openid", 
                "email", 
                "profile", 
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://spreadsheets.google.com/feeds"
            ], 
            redirect_uri='postmessage'
        )
        flow.fetch_token(code=code)
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

import traceback

@app.errorhandler(Exception)
def handle_exception(e):
    print("--- INTERNAL SERVER ERROR ---")
    traceback.print_exc()
    return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # On Railway/VPS, the PORT is provided by the environment or defaults to 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
