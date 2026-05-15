# DriveSafe Project Instructions

## Tech Stack
- **Frontend:** React JS (TypeScript), Vite, Tailwind CSS 4.
- **Backend:** Python Flask, REST API.
- **Database:** MariaDB / MySQL.
- **Storage:** LONGBLOB (MySQL `LargeBinary`).

## Deployment
- **Platform:** Hostinger VPS (Private Domain).
- **CI/CD:** GitHub Actions (`.github/workflows/deploy.yml`) using SSH deployment.
- **Server:** Python Flask running on the VPS.

## Conventions
- Database models are defined in `backend/models.py`.
- Files are stored both as binary in the database and locally on the server.
