import os
import sys
from sqlalchemy import text
from app.database.connection import engine

def run_migration():
    with engine.begin() as conn:
        # Check if audit_logs table exists
        result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'audit_logs');"))
        exists = result.scalar()
        
        if not exists:
            print("Creating audit_logs table...")
            conn.execute(text("""
                CREATE TABLE audit_logs (
                    id BIGSERIAL PRIMARY KEY,
                    admin_username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_user TEXT NOT NULL,
                    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
                    previous_value TEXT,
                    new_value TEXT,
                    ip_address TEXT
                );
            """))
            print("Table audit_logs created successfully.")
        else:
            print("Table audit_logs already exists.")
            # Check if ip_address column exists
            col_result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='audit_logs' and column_name='ip_address';"))
            if not col_result.fetchone():
                print("Adding ip_address column to audit_logs...")
                conn.execute(text("ALTER TABLE audit_logs ADD COLUMN ip_address TEXT;"))
                print("Column ip_address added successfully.")
            else:
                print("Column ip_address already exists.")
                
        print("Migration completed successfully.")

if __name__ == "__main__":
    run_migration()
