from app import app
from models import db
from sqlalchemy import text

def migrate():
    with app.app_context():
        print("Checking for missing columns...")
        columns_to_add = [
            ("srs_text", "LONGTEXT"),
            ("sdd_text", "LONGTEXT"),
            ("spmp_text", "LONGTEXT"),
            ("std_text", "LONGTEXT"),
            ("ri_text", "LONGTEXT"),
            ("workbook_name", "VARCHAR(255)")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                db.session.execute(text(f"ALTER TABLE archival_ledger ADD COLUMN {col_name} {col_type}"))
                db.session.commit()
                print(f"✅ Added column: {col_name}")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print(f"ℹ️ Column {col_name} already exists.")
                else:
                    print(f"❌ Error adding {col_name}: {e}")

if __name__ == "__main__":
    migrate()
