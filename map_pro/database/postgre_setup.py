# Path: database/postgre_setup.py
"""
PostgreSQL User, Database, and Schema Setup

Handles PostgreSQL setup operations:
- Creating user (role) with password
- Creating database owned by user
- Seeding markets table

Uses configuration from .env via database/core/config_loader.py.
"""

import subprocess
from typing import Dict, Optional

from database.core.config_loader import ConfigLoader
from database.core.logger import get_logger

logger = get_logger(__name__, 'core')


class PostgreSQLSetup:
    """Manages PostgreSQL user, database, and schema setup."""

    def __init__(self, config: Optional[ConfigLoader] = None):
        self.config = config if config else ConfigLoader()

    def create_user_and_database(self) -> Dict:
        """
        Create PostgreSQL user and database from .env configuration.

        Creates:
        - PostgreSQL role (user) with password
        - Database owned by that user

        Uses DB_USER, DB_PASSWORD, DB_NAME from .env configuration.

        Returns:
            Dictionary with result:
                - success: bool
                - message: str
                - user_created: bool
                - database_created: bool
        """
        db_user = self.config.get('db_user')
        db_password = self.config.get('db_password')
        db_name = self.config.get('db_name')

        if not all([db_user, db_password, db_name]):
            return {
                'success': False,
                'message': 'Missing DB_USER, DB_PASSWORD, or DB_NAME in configuration',
                'user_created': False,
                'database_created': False
            }

        logger.info(f"Creating PostgreSQL user '{db_user}' and database '{db_name}'...")

        user_created = False
        database_created = False

        try:
            # Step 1: Check if user exists, create if not
            user_exists = self._check_user_exists(db_user)

            if not user_exists:
                create_result = self._create_user(db_user, db_password)
                if not create_result['success']:
                    return {
                        'success': False,
                        'message': create_result['message'],
                        'user_created': False,
                        'database_created': False
                    }
                user_created = True
                logger.info(f"User '{db_user}' created successfully")
            else:
                logger.info(f"User '{db_user}' already exists")

            # Step 2: Check if database exists, create if not
            db_exists = self._check_database_exists(db_name)

            if not db_exists:
                create_result = self._create_database(db_name, db_user)
                if not create_result['success']:
                    return {
                        'success': False,
                        'message': create_result['message'],
                        'user_created': user_created,
                        'database_created': False
                    }
                database_created = True
                logger.info(f"Database '{db_name}' created successfully")
            else:
                logger.info(f"Database '{db_name}' already exists")

            # Step 3: Grant all privileges
            self._grant_privileges(db_name, db_user)
            logger.info(f"Privileges granted to '{db_user}' on '{db_name}'")

            return {
                'success': True,
                'message': f"User '{db_user}' and database '{db_name}' ready",
                'user_created': user_created,
                'database_created': database_created
            }

        except subprocess.TimeoutExpired:
            logger.error("Command timed out")
            return {
                'success': False,
                'message': 'Command timed out',
                'user_created': user_created,
                'database_created': database_created
            }
        except Exception as e:
            logger.error(f"Error creating user/database: {e}")
            return {
                'success': False,
                'message': f'Error: {e}',
                'user_created': user_created,
                'database_created': database_created
            }

    def _check_user_exists(self, username: str) -> bool:
        """Check if PostgreSQL user exists."""
        result = subprocess.run(
            ['sudo', '-u', 'postgres', 'psql', '-tAc',
             f"SELECT 1 FROM pg_roles WHERE rolname='{username}'"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip() == '1'

    def _create_user(self, username: str, password: str) -> Dict:
        """Create PostgreSQL user."""
        logger.info(f"Creating user: {username}")
        result = subprocess.run(
            ['sudo', '-u', 'postgres', 'psql', '-c',
             f"CREATE USER {username} WITH PASSWORD '{password}' CREATEDB;"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            logger.error(f"Failed to create user: {result.stderr}")
            return {'success': False, 'message': f'Failed to create user: {result.stderr}'}
        return {'success': True}

    def _check_database_exists(self, dbname: str) -> bool:
        """Check if PostgreSQL database exists."""
        result = subprocess.run(
            ['sudo', '-u', 'postgres', 'psql', '-tAc',
             f"SELECT 1 FROM pg_database WHERE datname='{dbname}'"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip() == '1'

    def _create_database(self, dbname: str, owner: str) -> Dict:
        """Create PostgreSQL database."""
        logger.info(f"Creating database: {dbname}")
        result = subprocess.run(
            ['sudo', '-u', 'postgres', 'psql', '-c',
             f"CREATE DATABASE {dbname} OWNER {owner};"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            logger.error(f"Failed to create database: {result.stderr}")
            return {'success': False, 'message': f'Failed to create database: {result.stderr}'}
        return {'success': True}

    def _grant_privileges(self, dbname: str, username: str) -> None:
        """Grant privileges on database to user."""
        subprocess.run(
            ['sudo', '-u', 'postgres', 'psql', '-c',
             f"GRANT ALL PRIVILEGES ON DATABASE {dbname} TO {username};"],
            capture_output=True,
            text=True,
            timeout=30
        )

    def seed_markets(self) -> Dict:
        """
        Seed markets table with supported markets.

        Uses market data from searcher.constants.MARKETS_SEED_DATA.
        Idempotent - safe to run multiple times.

        Returns:
            Dictionary with result:
                - success: bool
                - message: str
                - markets_added: int
                - markets_existing: int
        """
        logger.info("Seeding markets table...")

        try:
            # Import here to avoid circular imports and ensure DB is ready
            from database import initialize_database, session_scope
            from database.models import Market
            from searcher.constants import MARKETS_SEED_DATA

            # Initialize database (creates tables if needed)
            initialize_database()

            markets_added = 0
            markets_existing = 0

            with session_scope() as session:
                for market_data in MARKETS_SEED_DATA:
                    existing = session.query(Market).filter_by(
                        market_id=market_data['market_id']
                    ).first()

                    if existing:
                        logger.info(f"Market '{market_data['market_id']}' already exists")
                        markets_existing += 1
                    else:
                        market = Market(**market_data)
                        session.add(market)
                        logger.info(f"Added market '{market_data['market_id']}': {market_data['market_name']}")
                        markets_added += 1

                session.commit()

            logger.info(f"Markets seeding complete: {markets_added} added, {markets_existing} existing")

            return {
                'success': True,
                'message': 'Markets seeded successfully',
                'markets_added': markets_added,
                'markets_existing': markets_existing
            }

        except Exception as e:
            logger.error(f"Failed to seed markets: {e}")
            return {
                'success': False,
                'message': f'Failed to seed markets: {e}',
                'markets_added': 0,
                'markets_existing': 0
            }
