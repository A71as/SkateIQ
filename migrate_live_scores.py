#!/usr/bin/env python3
"""
Database migration to add live scores support
Adds is_locked, game_status, live_home_score, live_away_score fields to predictions table
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./skateiq.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def run_migration():
    """Run the database migration"""
    engine = create_engine(DATABASE_URL)
    
    print("🔄 Running live scores database migration...")
    
    try:
        with engine.connect() as conn:
            # Check if columns already exist
            if "sqlite" in DATABASE_URL:
                # SQLite - Add columns one by one
                migrations = [
                    "ALTER TABLE predictions ADD COLUMN is_locked BOOLEAN DEFAULT FALSE NOT NULL",
                    "ALTER TABLE predictions ADD COLUMN game_status VARCHAR(20)",
                    "ALTER TABLE predictions ADD COLUMN live_home_score INTEGER",
                    "ALTER TABLE predictions ADD COLUMN live_away_score INTEGER"
                ]
            else:
                # PostgreSQL - Can add multiple columns at once
                migrations = [
                    """ALTER TABLE predictions 
                       ADD COLUMN is_locked BOOLEAN DEFAULT FALSE NOT NULL,
                       ADD COLUMN game_status VARCHAR(20),
                       ADD COLUMN live_home_score INTEGER,
                       ADD COLUMN live_away_score INTEGER"""
                ]
            
            for migration in migrations:
                try:
                    conn.execute(text(migration))
                    print(f"✅ Executed: {migration[:50]}...")
                except Exception as e:
                    if "already exists" in str(e) or "duplicate column" in str(e):
                        print(f"⚠️  Column already exists, skipping: {migration[:50]}...")
                    else:
                        raise e
            
            conn.commit()
            print("✅ Migration completed successfully!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()