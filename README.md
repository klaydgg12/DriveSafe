# DriveSafe

DriveSafe is a planned automated Google Drive backup tool designed to help students and educators protect their academic files from data loss.

This project is being developed as a capstone project for the College of Computer Studies at Cebu Institute of Technology University.

## Tech Stack (Planned)

- **Frontend:** React with TypeScript - v18.3.1
- **Styling:** Tailwind CSS - v4.0
- **Build Tool:** Vite - v5.0+
- **Backend:** Node.js with Express (planned)
- **Database:** SQLite / MySQL - v8.0
- **Authentication:** Google OAuth 2.0
- **API:** Google Drive API v3
- **Version Control:** Git & GitHub

## Features (Planned)

- ✅ Google OAuth 2.0 secure authentication
- ✅ One-click automated backup (up to 100 files)
- ✅ ZIP archive creation and download
- ✅ Backup history (last 5 backups)
- ✅ MD5 checksum verification
- ✅ 7-day automatic deletion
- ✅ RA 10173 (Data Privacy Act) compliant

## Setup Instructions

### 1. Prerequisites

- Node.js 18+
- npm or yarn
- Google Cloud Project with Drive API enabled

### Frontend Setup (React + Vite)

```bash
# Clone the repository
git clone https://github.com/klaydgg12/DriveSafe.git
cd DriveSafe/web   # or /frontend depending on folder

# Install dependencies
npm install

# Running the frontend
npm run dev
```


### Backend Setup (Python + Flask)

```bash
Navigate to your backend folder:
cd backend

# 1. Create a virtual environment
python -m venv venv

# 2. Activate the virtual environment
Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# 3. Install required packages
pip install -r requirements.txt

# 4. Run the backend
python app.py
```

### 2. Environment Configuration

Create a `.env` file in the root directory:

```env
VITE_GOOGLE_CLIENT_ID=your_google_client_id_here.apps.googleusercontent.com
VITE_GOOGLE_CLIENT_SECRET=your_google_client_secret_here
VITE_GOOGLE_REDIRECT_URI=http://localhost:5173/auth/callback
VITE_API_BASE_URL=http://localhost:3000
VITE_MAX_FILES_PER_BACKUP=100
VITE_BACKUP_RETENTION_DAYS=7
VITE_MAX_BACKUP_HISTORY=5
```

### 3. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google Drive API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:5173/auth/callback`
6. Copy Client ID and Client Secret to `.env` file

## Database Schema (Planned)

**Users Table**

- user_id (PK)
- email
- google_id
- full_name
- created_at
- last_login

**Backups Table**

- backup_id (PK)
- user_id (FK)
- file_name
- file_size
- file_count
- md5_checksum
- status
- created_at
- expires_at

**Auth_Tokens Table**

- token_id (PK)
- user_id (FK)
- access_token
- refresh_token
- token_type
- expires_at
- created_at

## Team Members

| Name                    | Role                                           | CIT-U Email                 | GitHub        |
| ----------------------- | ---------------------------------------------- | --------------------------- | ------------- |
| Lyrech James E. Laspiñas| UI/UX - Frontend Developer / Backend Developer | lyrech.laspinas@cit.edu     | @lyrech       |
| Louis Drey F. Castañeto | UI/UX - Frontend Developer / Backend Developer | louisdrey.castaneto@cit.edu | @louisdrey    |
| John Earl F. Mandawe    | UI/UX - Frontend Developer / Backend Developer | johnearl.mandawe@cit.edu    | @johnearl     |
| Clyde Nixon Jumawan     | UI/UX - Frontend Developer / Backend Developer | clydenixon.jumawan@cit.edu  | @klaydgg12    |
| Mark Joenylle B. Cortes | UI/UX - Frontend Developer / Backend Developer | markjoenylle.cortes@cit.edu | @markjoenylle |

## Project Information

- **Institution:** Cebu Institute of Technology University
- **College:** College of Computer Studies
- **Program:** Bachelor of Science in Information Technology
- **Academic Year:** 2024-2025
- **Project Type:** Capstone Project

📝 **This repository will be updated as the DriveSafe system development progresses.**

**© 2025 DriveSafe Team. All Rights Reserved.**
