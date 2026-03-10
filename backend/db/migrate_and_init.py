import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB
from db.postgres import init_db, engine
from db.schema import create_schema, create_materialized_views

def create_database():
    """Create the database if it doesn't exist."""
    print(f"Connecting to PostgreSQL server at {POSTGRES_HOST}:{POSTGRES_PORT} with user {POSTGRES_USER}...")
    try:
        # Connect to the default 'postgres' database to check/create the target database
        conn = psycopg2.connect(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{POSTGRES_DB}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creating database {POSTGRES_DB}...")
            cursor.execute(f"CREATE DATABASE {POSTGRES_DB}")
            print(f"Database {POSTGRES_DB} created successfully.")
        else:
            print(f"Database {POSTGRES_DB} already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)

def run_migrations():
    """Initialize all tables and materialized views."""
    print(f"\nInitializing SQLAlchemy models (users, saved_layouts)...")
    try:
        init_db()
        print("SQLAlchemy models initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize SQLAlchemy models: {e}")
    
    print(f"\nInitializing raw and enriched analytical tables and indexes...")
    try:
        create_schema()
        print("Analytical tables created successfully.")
    except Exception as e:
        print(f"Failed to create analytical tables: {e}")
        
    print(f"\nCreating materialized views...")
    try:
        # Note: the MV creation requires options_enriched to have columns set up.
        # It won't fail if the table is empty.
        create_materialized_views()
        print("Materialized views created successfully.")
    except Exception as e:
        print(f"Failed to create materialized views: {e}")

def verify_tables():
    """List all created tables to verify."""
    print("\nVerifying created tables...")
    try:
        conn = psycopg2.connect(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"Found {len(tables)} tables in database {POSTGRES_DB}:")
        for table in tables:
            print(f"  - {table[0]}")
            
        cursor.close()
        conn.close()
        return len(tables) > 0
    except Exception as e:
        print(f"Error verifying tables: {e}")
        return False

if __name__ == "__main__":
    create_database()
    run_migrations()
    
    if verify_tables():
        print("\nDatabase initialization and migration completed successfully! ✅")
    else:
        print("\nDatabase initialization might have failed, no tables found. ❌")
        sys.exit(1)
