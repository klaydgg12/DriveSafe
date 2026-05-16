import os
import logging
from flask import Flask
from models import db, ArchivalLedger
from sqlalchemy import text
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    # Load environment variables
    load_dotenv()
    
    app = Flask(__name__)
    # Correct key is SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize DB
    db.init_app(app)
    
    with app.app_context():
        try:
            logger.info("Checking for 'batch_id' column in 'archival_ledger' table...")
            
            # Check if column exists
            # Using raw SQL for the check to be database-agnostic
            result = db.session.execute(text("SHOW COLUMNS FROM archival_ledger LIKE 'batch_id'")).fetchone()
            
            if not result:
                logger.info("Column 'batch_id' not found. Adding it now...")
                db.session.execute(text("ALTER TABLE archival_ledger ADD COLUMN batch_id VARCHAR(50) AFTER version"))
                db.session.commit()
                logger.info("Migration successful: 'batch_id' column added.")
            else:
                logger.info("Column 'batch_id' already exists. Skipping.")
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            db.session.rollback()

if __name__ == "__main__":
    migrate()
