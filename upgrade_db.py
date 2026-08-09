import sqlite3

def upgrade_db():
    conn = sqlite3.connect('llm_logs.db')
    cursor = conn.cursor()
    
    # Try adding the new columns one by one
    new_columns = [
        "ALTER TABLE request_logs ADD COLUMN original_token_count INTEGER DEFAULT 0",
        "ALTER TABLE request_logs ADD COLUMN compressed_token_count INTEGER DEFAULT 0",
        "ALTER TABLE request_logs ADD COLUMN tokens_saved_by_compression INTEGER DEFAULT 0"
    ]
    
    for cmd in new_columns:
        try:
            cursor.execute(cmd)
            print(f"Executed: {cmd}")
        except sqlite3.OperationalError as e:
            print(f"Skipped: {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade_db()
