import os
import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(20), default='teacher') # 'teacher' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class ArchivalLedger(db.Model):
    __tablename__ = 'archival_ledger'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(100), nullable=False) # The Team Code
    project_title = db.Column(db.String(255), nullable=False)
    academic_year = db.Column(db.String(50), nullable=False) # e.g., "2024-2025"
    workbook_name = db.Column(db.String(255), nullable=True) # The Google Sheet Name

    # Deliverable URLs
    srs_original_url = db.Column(db.String(500), nullable=True)
    sdd_original_url = db.Column(db.String(500), nullable=True)
    spmp_original_url = db.Column(db.String(500), nullable=True)
    std_original_url = db.Column(db.String(500), nullable=True)
    ri_original_url = db.Column(db.String(500), nullable=True)
    research_paper_original_url = db.Column(db.String(500), nullable=True)
    usability_test_original_url = db.Column(db.String(500), nullable=True)
    presentation_original_url = db.Column(db.String(500), nullable=True)
    source_code_original_url = db.Column(db.String(500), nullable=True)
    github_original_url = db.Column(db.String(500), nullable=True)
    database_original_url = db.Column(db.String(500), nullable=True)
    readme_original_url = db.Column(db.String(500), nullable=True)

    # Local storage paths
    srs_local_path = db.Column(db.String(500), nullable=True)
    sdd_local_path = db.Column(db.String(500), nullable=True)
    spmp_local_path = db.Column(db.String(500), nullable=True)
    std_local_path = db.Column(db.String(500), nullable=True)
    ri_local_path = db.Column(db.String(500), nullable=True)
    research_paper_local_path = db.Column(db.String(500), nullable=True)
    usability_test_local_path = db.Column(db.String(500), nullable=True)
    presentation_local_path = db.Column(db.String(500), nullable=True)
    source_code_local_path = db.Column(db.String(500), nullable=True)
    database_local_path = db.Column(db.String(500), nullable=True)
    readme_local_path = db.Column(db.String(500), nullable=True)

    # File integrity hashes (SHA-256)
    srs_hash = db.Column(db.String(64), nullable=True)
    sdd_hash = db.Column(db.String(64), nullable=True)
    spmp_hash = db.Column(db.String(64), nullable=True)
    std_hash = db.Column(db.String(64), nullable=True)
    ri_hash = db.Column(db.String(64), nullable=True)
    research_paper_hash = db.Column(db.String(64), nullable=True)
    usability_test_hash = db.Column(db.String(64), nullable=True)
    presentation_hash = db.Column(db.String(64), nullable=True)
    source_code_hash = db.Column(db.String(64), nullable=True)
    database_hash = db.Column(db.String(64), nullable=True)
    readme_hash = db.Column(db.String(64), nullable=True)

    # Binary Data (LONGBLOB)
    srs_binary = db.Column(db.LargeBinary(length=(2**32)-1), nullable=True)
    sdd_binary = db.Column(db.LargeBinary(length=(2**32)-1), nullable=True)
    spmp_binary = db.Column(db.LargeBinary(length=(2**32)-1), nullable=True)
    std_binary = db.Column(db.LargeBinary(length=(2**32)-1), nullable=True)
    ri_binary = db.Column(db.LargeBinary(length=(2**32)-1), nullable=True)
    research_paper_binary = db.Column(db.LargeBinary(length=(2**32)-1), nullable=True)
    usability_test_binary = db.Column(db.LargeBinary(length=(2**32)-1), nullable=True)
    presentation_binary = db.Column(db.LargeBinary(length=(2**32)-1), nullable=True)
    source_code_binary = db.Column(db.LargeBinary(length=(2**32)-1), nullable=True)
    database_binary = db.Column(db.LargeBinary(length=(2**32)-1), nullable=True)
    readme_binary = db.Column(db.LargeBinary(length=(2**32)-1), nullable=True)

    # AI Reading Cache (Plain text extraction)
    srs_text = db.Column(db.Text, nullable=True)
    sdd_text = db.Column(db.Text, nullable=True)
    spmp_text = db.Column(db.Text, nullable=True)
    std_text = db.Column(db.Text, nullable=True)
    ri_text = db.Column(db.Text, nullable=True)
    research_paper_text = db.Column(db.Text, nullable=True)
    usability_test_text = db.Column(db.Text, nullable=True)
    readme_text = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(50), default='pending')
    version = db.Column(db.Integer, default=1)
    batch_id = db.Column(db.String(50), nullable=True)
    archived_by = db.Column(db.String(120), nullable=True) # Email of the user who performed the archive
    drive_modified_time = db.Column(db.String(100), nullable=True) # Absolute Google Timestamp
    error_message = db.Column(db.Text, nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
