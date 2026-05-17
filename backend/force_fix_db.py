import os
import pymysql
from dotenv import load_dotenv

def force_fix():
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL not found in .env")
        return

    # Parse URL: mysql+pymysql://user:password@host/dbname
    try:
        parts = db_url.split('://')[1]
        user_pass, host_db = parts.split('@')
        user, password = user_pass.split(':')
        host, db_name = host_db.split('/')
        # Remove port if exists in host
        if ':' in host: host = host.split(':')[0]
    except Exception as e:
        print(f"Error parsing DATABASE_URL: {e}")
        return

    print(f"Connecting to database: {db_name} on {host}...")
    
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        with connection.cursor() as cursor:
            # List of all columns that SHOULD exist
            required_columns = [
                ('batch_id', 'VARCHAR(50)'),
                ('drive_modified_time', 'VARCHAR(100)'),
                ('source_code_original_url', 'VARCHAR(500)'),
                ('github_original_url', 'VARCHAR(500)'),
                ('database_original_url', 'VARCHAR(500)'),
                ('readme_original_url', 'VARCHAR(500)'),
                ('source_code_local_path', 'VARCHAR(500)'),
                ('database_local_path', 'VARCHAR(500)'),
                ('readme_local_path', 'VARCHAR(500)'),
                ('source_code_hash', 'VARCHAR(64)'),
                ('database_hash', 'VARCHAR(64)'),
                ('readme_hash', 'VARCHAR(64)'),
                ('source_code_binary', 'LONGBLOB'),
                ('database_binary', 'LONGBLOB'),
                ('readme_binary', 'LONGBLOB'),
                ('readme_text', 'TEXT')
            ]

            # Get existing columns
            cursor.execute("SHOW COLUMNS FROM archival_ledger")
            existing = [row['Field'] for row in cursor.fetchall()]

            for col_name, col_type in required_columns:
                if col_name not in existing:
                    print(f"Adding missing column: {col_name}...")
                    sql = f"ALTER TABLE archival_ledger ADD COLUMN {col_name} {col_type}"
                    cursor.execute(sql)
            
            connection.commit()
            print("Successfully synchronized all database columns!")
    finally:
        connection.close()

if __name__ == "__main__":
    force_fix()
