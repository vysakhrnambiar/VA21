#!/usr/bin/env python3
import sqlite3
import os

def apply_changes():
    print("Applying database schema changes...")
    
    # Get the path to the database
    db_path = 'scheduled_calls.db'
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found.")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column already exists to avoid errors
        cursor.execute("PRAGMA table_info(scheduled_calls)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'company_name_for_agent' not in columns:
            print("Adding company_name_for_agent column to scheduled_calls table...")
            cursor.execute("ALTER TABLE scheduled_calls ADD COLUMN company_name_for_agent TEXT")
            print("Column added successfully.")
        else:
            print("Column company_name_for_agent already exists, no changes needed.")
        
        conn.commit()
        conn.close()
        
        print("Database schema update completed successfully.")
        return True
    except Exception as e:
        print(f"Error updating database schema: {str(e)}")
        return False

if __name__ == "__main__":
    apply_changes()