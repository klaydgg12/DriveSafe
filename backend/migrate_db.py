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
    load_dotenv()
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            logger.info("Starting Per-File Precision Migration...")
            
            # List of new columns to add
            columns = [
                'srs_modified_time', 'sdd_modified_time', 'spmp_modified_time', 
                'std_modified_time', 'ri_modified_time', 'source_code_modified_time',
                'database_modified_time', 'readme_modified_time'
            ]
            
            for col in columns:
                result = db.session.execute(text(f"SHOW COLUMNS FROM archival_ledger LIKE '{col}'")).fetchone()
                if not result:
                    logger.info(f"Adding column '{col}'...")
                    db.session.execute(text(f"ALTER TABLE archival_ledger ADD COLUMN {col} VARCHAR(100)"))
                    db.session.commit()
            
            # Drop old redundant column if it exists
            try:
                db.session.execute(text("ALTER TABLE archival_ledger DROP COLUMN drive_modified_time"))
                db.session.commit()
                logger.info("Dropped old 'drive_modified_time' column.")
            except:
                pass

            logger.info("Migration successful: Per-file precision enabled.")
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            db.session.rollback()

if __name__ == "__main__":
    migrate()
