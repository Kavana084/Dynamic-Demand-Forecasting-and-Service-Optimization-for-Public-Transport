import os
from db_utils import init_db

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transit_data.db")

def reset_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"✔ Deleted old database at {DB_PATH}")
    else:
        print("Database not found, nothing to delete.")
        
    # Reinitialize a fresh database
    init_db()
    print("✔ Database reset complete. Fresh start!")

if __name__ == "__main__":
    reset_database()
