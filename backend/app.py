from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import sqlite3
import io
import zipfile
import hashlib
import datetime
import os

from ai_engine import predict_category 

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

def init_db():
    conn = sqlite3.connect('drivesafe.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS backups 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  filename TEXT, 
                  date TEXT, 
                  file_count INTEGER, 
                  size_mb TEXT, 
                  md5 TEXT, 
                  status TEXT)''')
    conn.commit()
    conn.close()

# ... (Keep your /auth/google route here) ...
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

# ... (Keep your /drive/files route here) ...
# Inside backend/app.py

@app.route('/drive/files', methods=['GET'])
def list_files():
    print("\n--- DEBUG: STARTING FILE LIST CHECK ---") # Spy Print 1
    auth_header = request.headers.get('Authorization')
    if not auth_header: 
        print("--- DEBUG: FAILED - NO TOKEN ---")
        return jsonify({"error": "No token"}), 401
    
    token = auth_header.split(" ")[1]
    print(f"--- DEBUG: Token Received (First 10 chars): {token[:10]}...") # Spy Print 2

    try:
        creds = Credentials(token)
        service = build('drive', 'v3', credentials=creds)
        
        print("--- DEBUG: Calling Google Drive API... ---") # Spy Print 3
        
        # We try a very simple query first (No filters) to see if ANY connection works
        results = service.files().list(
            pageSize=10, 
            fields="files(id, name)" # Fetch minimum data
        ).execute()
        
        files = results.get('files', [])
        print(f"--- DEBUG: GOOGLE SAYS YOU HAVE {len(files)} FILES ---") # Spy Print 4
        
        for f in files:
            print(f"   -> Found file: {f['name']}")

        # If we get here, connection is GOOD. Now do the real logic.
        # ... (Run your AI logic here as before) ...
        
        stats = {"Academic": 0, "Personal": 0, "Other": 0}
        processed_files = []
        
        for f in files:
            # Re-predict for the frontend
            cat = predict_category(f['name'])
            if cat in stats: stats[cat] += 1
            else: stats["Other"] += 1
            f['category'] = cat
            processed_files.append(f)
            
        return jsonify({"files": processed_files, "ai_stats": stats})

    except Exception as e:
        print(f"--- DEBUG: CRITICAL ERROR: {str(e)} ---") # Spy Print 5
        # This will print the EXACT reason Google is rejecting you to the terminal
        return jsonify({"error": str(e)}), 400

# ... (Keep your /history route here) ...
@app.route('/history', methods=['GET'])
def get_history():
    try:
        conn = sqlite3.connect('drivesafe.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM backups ORDER BY id DESC LIMIT 5")
        rows = c.fetchall()
        history = [dict(row) for row in rows]
        conn.close()
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- NEW: THE BACKUP ENGINE ---
@app.route('/drive/backup', methods=['POST'])
def create_backup():
    auth_header = request.headers.get('Authorization')
    if not auth_header: return jsonify({"error": "No token"}), 401
    token = auth_header.split(" ")[1]

    try:
        creds = Credentials(token)
        service = build('drive', 'v3', credentials=creds)

        # 1. List files to backup (Limit to 10 for testing speed)
        results = service.files().list(pageSize=10, fields="files(id, name)").execute()
        files = results.get('files', [])

        if not files:
            return jsonify({"error": "No files found to backup"}), 404

        # 2. Create ZIP in Memory
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_filename = f"backup_{timestamp}.zip"
        zip_path = os.path.join(BACKUP_FOLDER, zip_filename)

        file_count = 0
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in files:
                try:
                    # Download file content
                    request_drive = service.files().get_media(fileId=file['id'])
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request_drive)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()

                    # Add to Zip
                    fh.seek(0)
                    zipf.writestr(file['name'], fh.read())
                    file_count += 1
                    print(f"Downloaded: {file['name']}")
                except Exception as e:
                    print(f"Skipped {file['name']}: {e}")

        # 3. Calculate MD5 & Size
        hasher = hashlib.md5()
        with open(zip_path, 'rb') as open_file:
            content = open_file.read()
            hasher.update(content)
        
        md5_hash = hasher.hexdigest()
        size_mb = f"{os.path.getsize(zip_path) / (1024 * 1024):.2f} MB"

        # 4. Save to Database
        conn = sqlite3.connect('drivesafe.db')
        c = conn.cursor()
        c.execute("INSERT INTO backups (filename, date, file_count, size_mb, md5, status) VALUES (?, ?, ?, ?, ?, ?)",
                  (zip_filename, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), file_count, size_mb, md5_hash, "Success"))
        conn.commit()
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