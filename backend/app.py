from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import mysql.connector
from mysql.connector import Error
import io
import zipfile
import hashlib
import datetime
import os

from ai_engine import predict_category
from config import DB_CONFIG

app = Flask(__name__)
CORS(app)

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.readonly"
]

# Ensure backup folder exists
BACKUP_FOLDER = "archives"
if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)

def get_db_connection():
    """Create and return a MySQL database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db():
    """Initialize MySQL database and create tables if they don't exist"""
    try:
        # First, connect without specifying database to create it if needed
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port']
        )
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.execute(f"USE {DB_CONFIG['database']}")
        
        # Create Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                google_id VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                profile_picture VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_google_id (google_id),
                INDEX idx_email (email)
            )
        ''')
        
        # Create Backups table with user_id foreign key
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                file_name VARCHAR(255),
                file_size BIGINT,
                file_count INT,
                md5_hash VARCHAR(255),
                md5_path VARCHAR(500),
                status ENUM('COMPLETED', 'FAILED', 'EXPIRED') DEFAULT 'COMPLETED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            )
        ''')
        
        # Create Analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                backup_id INT,
                academic_count INT DEFAULT 0,
                personal_count INT DEFAULT 0,
                other_count INT DEFAULT 0,
                analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (backup_id) REFERENCES backups(id) ON DELETE CASCADE,
                INDEX idx_backup_id (backup_id)
            )
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("MySQL database initialized successfully!")
        print("Created tables: users, backups, analytics")
    except Error as e:
        print(f"Error initializing MySQL database: {e}")

@app.route('/auth/google', methods=['POST'])
def google_auth():
    code = request.json.get('code')
    try:
        flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri='postmessage')
        flow.fetch_token(code=code)
        # Fetch basic user profile
        service = build('oauth2', 'v2', credentials=flow.credentials)
        user_info = service.userinfo().get().execute()

        return jsonify({
            "access_token": flow.credentials.token,
            "user_email": user_info.get("email"),
            "user_name": user_info.get("name"),
            "user_picture": user_info.get("picture")
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/drive/files', methods=['GET'])
def list_files():
    print("\n--- DEBUG: STARTING FILE LIST CHECK ---") 
    auth_header = request.headers.get('Authorization')
    if not auth_header: 
        return jsonify({"error": "No token"}), 401
    
    token = auth_header.split(" ")[1]

    try:
        creds = Credentials(token)
        service = build('drive', 'v3', credentials=creds)
        
        print("--- DEBUG: Calling Google Drive API... ---")
        
        results = service.files().list(
            pageSize=20, 
            fields="files(id, name, mimeType, size)" 
        ).execute()
        
        files = results.get('files', [])
        print(f"--- DEBUG: GOOGLE SAYS YOU HAVE {len(files)} FILES ---")
        
        stats = {"Academic": 0, "Personal": 0, "Other": 0}
        processed_files = []
        
        for f in files:
            cat = predict_category(f['name'])
            if cat in stats: stats[cat] += 1
            else: stats["Other"] += 1
            f['category'] = cat
            processed_files.append(f)
            
        return jsonify({"files": processed_files, "ai_stats": stats})

    except Exception as e:
        print(f"--- DEBUG: CRITICAL ERROR: {str(e)} ---")
        return jsonify({"error": str(e)}), 400

@app.route('/history', methods=['GET'])
def get_history():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM backups ORDER BY id DESC LIMIT 5")
        history = cursor.fetchall()
        
        # Convert datetime objects to strings for JSON serialization
        for record in history:
            if 'created_at' in record and record['created_at']:
                record['created_at'] = record['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if 'expires_at' in record and record['expires_at']:
                record['expires_at'] = record['expires_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.close()
        conn.close()
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/drive/backup/download/<filename>', methods=['GET'])
def download_backup(filename):
    try:
        filename = os.path.basename(filename)
        file_path = os.path.join(BACKUP_FOLDER, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- MODIFIED: SMART ORGANIZED BACKUP ---
@app.route('/drive/backup', methods=['POST'])
def create_backup():
    auth_header = request.headers.get('Authorization')
    if not auth_header: return jsonify({"error": "No token"}), 401
    token = auth_header.split(" ")[1]

    try:
        creds = Credentials(token)
        service = build('drive', 'v3', credentials=creds)

        # 1. List 100 files
        results = service.files().list(
            pageSize=20, 
            fields="files(id, name, mimeType)"
        ).execute()
        files = results.get('files', [])

        if not files:
            return jsonify({"error": "No files found to backup"}), 404

        # 2. Create ZIP in Memory
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_filename = f"backup_{timestamp}.zip"
        zip_path = os.path.join(BACKUP_FOLDER, zip_filename)

        file_count = 0
        stats = {"Academic": 0, "Personal": 0, "Other": 0}
        
        # MIME types for Google Docs export
        GOOGLE_DOCS_MIMES = {
            'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.google-apps.drawing': 'image/png',
            'application/vnd.google-apps.script': 'application/vnd.google-apps.script+json',
        }
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in files:
                try:
                    # --- NEW: AI CATEGORIZATION ---
                    category = predict_category(file['name'])
                    
                    # Track category stats
                    if category in stats:
                        stats[category] += 1
                    else:
                        stats["Other"] += 1 
                    
                    mime_type = file.get('mimeType', '')
                    
                    # Handle Google Docs Export
                    if mime_type in GOOGLE_DOCS_MIMES:
                        export_mime = GOOGLE_DOCS_MIMES[mime_type]
                        request_drive = service.files().export_media(fileId=file['id'], mimeType=export_mime)
                        
                        if 'wordprocessingml' in export_mime: file_ext = '.docx'
                        elif 'spreadsheetml' in export_mime: file_ext = '.xlsx'
                        elif 'presentationml' in export_mime: file_ext = '.pptx'
                        elif export_mime == 'image/png': file_ext = '.png'
                        else: file_ext = ''
                        
                        filename_with_ext = file['name'] + file_ext if not file['name'].endswith(file_ext) else file['name']
                    else:
                        request_drive = service.files().get_media(fileId=file['id'])
                        filename_with_ext = file['name']
                    
                    # Download File Stream
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request_drive)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()

                    # --- NEW: SAVE INTO FOLDER ---
                    # e.g., "Academic/Thesis.docx"
                    archive_path = f"{category}/{filename_with_ext}"
                    
                    fh.seek(0)
                    zipf.writestr(archive_path, fh.read())
                    
                    file_count += 1
                    print(f"Downloaded: {archive_path}")
                    
                except Exception as e:
                    print(f"Skipped {file['name']}: {e}")

        # 3. Calculate MD5 & Size
        hasher = hashlib.md5()
        with open(zip_path, 'rb') as open_file:
            content = open_file.read()
            hasher.update(content)
        
        md5_hash = hasher.hexdigest()
        size_mb = f"{os.path.getsize(zip_path) / (1024 * 1024):.2f} MB"

        # 4. Calculate file size in bytes
        file_size_bytes = os.path.getsize(zip_path)
        
        # 5. Calculate expiration date (7 days from now)
        expires_at = datetime.datetime.now() + datetime.timedelta(days=7)
        
        # 6. Save to Database (Note: user_id should be set when user auth is implemented)
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO backups (user_id, file_name, file_size, file_count, md5_hash, status, expires_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (None, zip_filename, file_size_bytes, file_count, md5_hash, 'COMPLETED', expires_at)
            )
            backup_id = cursor.lastrowid
            
            # 7. Save analytics data
            cursor.execute(
                """INSERT INTO analytics (backup_id, academic_count, personal_count, other_count) 
                   VALUES (%s, %s, %s, %s)""",
                (backup_id, stats.get('Academic', 0), stats.get('Personal', 0), stats.get('Other', 0))
            )
            
            conn.commit()
            cursor.close()
            conn.close()

        return jsonify({
            "message": "Backup Complete",
            "filename": zip_filename,
            "size": size_mb,
            "md5": md5_hash
        })

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)