from flask import Flask, request, jsonify
from flask_cors import CORS
from google_auth_oauthlib.flow import Flow
import os
import sqlite3 

app = Flask(__name__)
CORS(app)  # Allow React to talk to this server

# This must match the filename of the JSON you downloaded
CLIENT_SECRETS_FILE = "client_secret.json"

# This scope allows us to READ files only.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.readonly"
]

@app.route('/auth/google', methods=['POST'])
def google_auth():
    code = request.json.get('code')
    
    try:
        # Create the flow using your client_secret.json
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri='postmessage'  # IMPORTANT: Must be 'postmessage' for React popup flow
        )
        
        # Exchange the "code" for actual "tokens" (Access & Refresh tokens)
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # SUCCESS!
        # In a real app, you would save credentials.refresh_token to your database here.
        
        print(f"Access Token: {credentials.token}")
        print(f"Refresh Token: {credentials.refresh_token}")

        return jsonify({
            "message": "Login Successful",
            "access_token": credentials.token,
            "user_email": "You can allow getting email in scopes to fill this"
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 400
def init_db():
    conn = sqlite3.connect('drivesafe.db')
    c = conn.cursor()
    
    # Create Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            profile_pic TEXT
        )
    ''')
    
    # Create Backups Table (To track history)
    c.execute('''
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            filename TEXT,
            file_count INTEGER,
            total_size_mb REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_email) REFERENCES users(email)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    # Run on port 5000
    init_db()
    app.run(debug=True, port=5000)