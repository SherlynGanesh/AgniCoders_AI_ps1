import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))
from backend.app.config import settings


def setup_database():
    print("==================================================")
    print("DUKAANMITRA — Database Setup")
    print("==================================================")
    print(f"Host: {settings.POSTGRES_HOST}")
    print(f"Port: {settings.POSTGRES_PORT}")
    print(f"User: {settings.POSTGRES_USER}")
    print(f"Target Database: {settings.POSTGRES_DB}")

    # 1. Connect to postgres admin database to check/create dukaanmitra
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        print("Connected successfully to PostgreSQL server.")
    except Exception as e:
        print(f"\n[ERROR] Failed to connect to PostgreSQL server: {e}")
        print("Please check your POSTGRES_PASSWORD in .env file.")
        sys.exit(1)

    # Check if target db exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (settings.POSTGRES_DB,))
    exists = cur.fetchone()
    if not exists:
        print(f"Database '{settings.POSTGRES_DB}' does not exist. Creating...")
        cur.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}";')
        print(f"Database '{settings.POSTGRES_DB}' created successfully.")
    else:
        print(f"Database '{settings.POSTGRES_DB}' already exists.")

    cur.close()
    conn.close()

    # 2. Connect to the target database and inspect extensions
    try:
        conn_target = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            dbname=settings.POSTGRES_DB
        )
        conn_target.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur_target = conn_target.cursor()
        print(f"Connected to '{settings.POSTGRES_DB}'.")

        # Check if pgvector is available
        cur_target.execute("SELECT * FROM pg_available_extensions WHERE name = 'vector';")
        vector_avail = cur_target.fetchone()

        if vector_avail:
            print("pgvector extension is available in PostgreSQL installation.")
            try:
                cur_target.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur_target.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
                version = cur_target.fetchone()[0]
                print(f"pgvector extension enabled successfully (version {version}).")
            except Exception as e:
                print(f"Warning: Could not enable vector extension: {e}")
        else:
            print("[INFO] pgvector is NOT installed in this PostgreSQL instance.")
            print("DukaanMitra's built-in Lexical Fallback & Hybrid Matcher will be utilized seamlessly.")

        cur_target.close()
        conn_target.close()
        print("\nDatabase setup complete!")

    except Exception as e:
        print(f"[ERROR] Error configuring target database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    setup_database()
