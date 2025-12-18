#!/usr/bin/env python
"""Verify all database tables were created successfully"""

import mysql.connector
from config import DB_CONFIG

def main():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Show all tables
        cursor.execute('SHOW TABLES')
        tables = cursor.fetchall()
        
        print("=" * 80)
        print("DATABASE TABLES")
        print("=" * 80)
        for table in tables:
            print(f"  - {table[0]}")
        print()
        
        # Describe each table
        for table in tables:
            table_name = table[0]
            cursor.execute(f'DESCRIBE {table_name}')
            columns = cursor.fetchall()
            
            print(f"=== {table_name.upper()} TABLE ===")
            print(f"{'Column':<20} {'Type':<30} {'Null':<6} {'Key':<6} {'Default':<15} {'Extra':<15}")
            print("-" * 100)
            for col in columns:
                field, type_, null, key, default, extra = col
                default = str(default) if default else 'NULL'
                print(f"{field:<20} {type_:<30} {null:<6} {key:<6} {default:<15} {extra:<15}")
            print()
        
        cursor.close()
        conn.close()
        
        print("=" * 80)
        print("All tables verified successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
