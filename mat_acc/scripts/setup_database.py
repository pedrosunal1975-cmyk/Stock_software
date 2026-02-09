#!/usr/bin/env python3
# Path: mat_acc/scripts/setup_database.py
"""
Database Setup Script

Creates the PostgreSQL database and tables for mat_acc.

Usage:
    python scripts/setup_database.py

Prerequisites:
    1. PostgreSQL is running
    2. User 'a' exists with password from .env
    3. User has permission to create databases

The script will:
    1. Create the mat_acc_db database (if not exists)
    2. Create all tables (processed_filings, statement_hierarchies, hierarchy_nodes)
    3. Verify the connection works
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_database_if_not_exists():
    """Create the mat_acc_db database if it doesn't exist."""
    try:
        import psycopg2
        from psycopg2 import sql
        from config_loader import ConfigLoader

        config = ConfigLoader()
        host = config.get('db_host', 'localhost')
        port = config.get('db_port', 5432)
        user = config.get('db_user', 'a')
        password = config.get('db_password', '')
        db_name = config.get('db_name', 'mat_acc_db')

        # Connect to default 'postgres' database to create our database
        logger.info(f"Connecting to PostgreSQL at {host}:{port}...")

        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()

        if exists:
            logger.info(f"Database '{db_name}' already exists")
        else:
            logger.info(f"Creating database '{db_name}'...")
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
            )
            logger.info(f"Database '{db_name}' created successfully")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        return False


def create_tables():
    """Create all database tables."""
    try:
        from database import initialize_database, get_connection_info

        logger.info("Initializing database engine...")
        initialize_database()

        info = get_connection_info()
        logger.info(f"Connected to: {info['type']} ({info['url']})")

        logger.info("Database tables created successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False


def verify_connection():
    """Verify we can query the database."""
    try:
        from database import session_scope
        from database.models.processed_filings import ProcessedFiling

        with session_scope() as session:
            # Try a simple query
            count = session.query(ProcessedFiling).count()
            logger.info(f"Connection verified. Current filings in database: {count}")

        return True

    except Exception as e:
        logger.error(f"Failed to verify connection: {e}")
        return False


def show_database_location():
    """Show where PostgreSQL data is stored."""
    try:
        import psycopg2
        from config_loader import ConfigLoader

        config = ConfigLoader()
        host = config.get('db_host', 'localhost')
        port = config.get('db_port', 5432)
        user = config.get('db_user', 'a')
        password = config.get('db_password', '')
        db_name = config.get('db_name', 'mat_acc_db')

        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name
        )
        cursor = conn.cursor()

        # Get data directory
        cursor.execute("SHOW data_directory")
        data_dir = cursor.fetchone()[0]

        logger.info(f"\nPostgreSQL Data Directory: {data_dir}")
        logger.info(f"Database Name: {db_name}")
        logger.info(f"Connection: postgresql://{user}:***@{host}:{port}/{db_name}")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.warning(f"Could not get data directory: {e}")


def main():
    """Main setup function."""
    print("=" * 60)
    print("mat_acc Database Setup")
    print("=" * 60)
    print()

    # Step 1: Create database
    print("[1/3] Creating database...")
    if not create_database_if_not_exists():
        print("ERROR: Failed to create database. Check PostgreSQL is running.")
        sys.exit(1)

    # Step 2: Create tables
    print("\n[2/3] Creating tables...")
    if not create_tables():
        print("ERROR: Failed to create tables.")
        sys.exit(1)

    # Step 3: Verify connection
    print("\n[3/3] Verifying connection...")
    if not verify_connection():
        print("ERROR: Failed to verify connection.")
        sys.exit(1)

    # Show location
    print("\n" + "=" * 60)
    show_database_location()

    print("\n" + "=" * 60)
    print("SUCCESS: Database setup complete!")
    print("=" * 60)
    print()
    print("You can now use the database with:")
    print()
    print("    from database import HierarchyStorage")
    print("    storage = HierarchyStorage()")
    print("    storage.initialize()")
    print()


if __name__ == '__main__':
    main()
