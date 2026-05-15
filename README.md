# DriveSafe: Intelligent Capstone Archival System

DriveSafe is a specialized, AI-assisted archival system designed for the College of Computer Studies at Cebu Institute of Technology - University. It automates the transition of academic projects from student-owned Google Drive storage to a permanent, institutional "Binary Vault."

## 🚀 Core Features

- **Binary Vault Archival:** Directly extracts raw PDF bytes from Google Drive and stores them as `LONGBLOB` data in MariaDB, ensuring institutional independence from student cloud accounts.
- **IntelliTrack Dashboard:** A React-based interface for faculty to monitor, verify, and batch-archive capstone deliverables.
- **AI-Powered Deduplication:** Uses **TF-IDF Vectorization** and **Cosine Similarity** to detect duplicate submissions and maintain archive integrity.
- **Cryptographic Versioning:** Implements **SHA-256** hashing to track bit-level revisions and prevent "link rot."
- **Registry Pipeline:** Seamlessly integrates with Google Sheets for project metadata and real-time status tracking.

## 🛠 Tech Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** Flask 3.x
- **ORM:** Flask-SQLAlchemy (MariaDB / SQLite)
- **AI/ML:** Scikit-learn (TF-IDF), PDFPlumber
- **APIs:** Google Drive API v3, Google Sheets API v4 (gspread)

### Frontend
- **Framework:** React 19 (TypeScript)
- **Build Tool:** Vite 7.x
- **Styling:** TailwindCSS 4.x
- **Auth:** @react-oauth/google (OAuth 2.0)

## 📋 Installation & Setup

### 1. Prerequisites
- Node.js 18+
- Python 3.11+
- Google Cloud `client_secret.json` (OAuth Client ID) placed in `/backend`

### 2. Backend Setup
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
# Configure .env based on .env.example
python app.py
```

### 3. Frontend Setup
```powershell
cd frontend
npm install
# Configure VITE_GOOGLE_CLIENT_ID in your environment
npm run dev
```

## 🧪 Testing & Deployment

To participate in the testing phase from the perspective of a teacher/registrar, please follow these steps:

### 1. Access the System
Go to: [https://archival-drivesafe.online/](https://archival-drivesafe.online/)

### 2. Bypass Google Verification Warning
Since the app is currently in the testing phase, Google may display a "Google hasn’t verified this app" warning. To proceed:
1.  Click **"Advanced"** on the warning screen.
2.  Click **"Go to archival-drivesafe.online (unsafe)"** at the bottom.
3.  Grant the requested permissions to allow the system to scan your Drive for Registry Sheets and Deliverables.

### 3. Prepare your Google Drive
Ensure that you have a Registry Workbook in your Drive to track. You can use this template:
[DriveSafe Registry Template](https://docs.google.com/spreadsheets/d/1bBeQwl1RWLuQy_3-fDoUUxsvpQlyzjE0dcEmJZCDbQs/edit?usp=sharing)
*(Make sure to "Make a copy" to your own Drive if you want to edit it).*

### 4. Test the Archiving Pipeline
1.  **Add Links:** In your copy of the Google Sheet, add links to your project’s SDD, SRS, SPMP, or any other `.docx` or `.pdf` file links in the designated columns.
2.  **Login:** Sign in to DriveSafe using your Google account.
3.  **Sync:** Refresh the **Capstone Archiver** dashboard.
4.  **Archive:** Select the projects you wish to archive and click the "Archive" button. The system will extract the files, verify them via SHA-256, and store them in the Binary Vault.

## 🔐 Administrative Tools
- **Set Teacher Role:** `python backend/set_teacher.py`
- **Set Student Role:** `python backend/set_student.py`

## 🌐 Production Deployment (Hostinger VPS)

DriveSafe is deployed on a **Hostinger VPS** using an **Ubuntu** environment.

### 🏛 Architecture
- **Web Server:** Nginx (acting as a reverse proxy on Port 443).
- **Application Server:** Waitress (WSGI server running on Port 8080).
- **Process Manager:** Systemd (managing the `drivesafe.service`).
- **Database:** MariaDB (Production) with `LONGBLOB` binary storage.

### 🛠 Deployment & Maintenance
To update the production server with the latest changes from GitHub, SSH into your VPS and run:

```bash
# 1. Navigate to the backend directory
cd /var/www/drivesafe/backend

# 2. Force pull the latest code from GitHub
git fetch origin main
git reset --hard origin/main

# 3. Restart the system service (This clears ghost processes)
sudo systemctl restart drivesafe

# 4. Verify the service is running
sudo systemctl status drivesafe
```

### 🚨 Critical Troubleshooting
- **404 Not Found on API:** This usually means the Nginx proxy is misconfigured or the Flask Blueprint registration has a path mismatch. Ensure Nginx `proxy_pass` does not have a trailing slash if the Flask route includes the full path.
- **Address already in use:** If the service fails to start, use `sudo fuser -k 8080/tcp` to manually kill any stuck processes.
- **Database Mismatches:** Ensure your `.env` on the VPS has the correct `DATABASE_URL` for the MariaDB instance.

---
**© 2025-2026 CEBU INSTITUTE OF TECHNOLOGY UNIVERSITY - College of Computer Studies**
