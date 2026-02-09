#!/usr/bin/env python3
# Path: database/postgre_initialize.py
"""
PostgreSQL Database Initialization Orchestrator

Coordinates complete PostgreSQL server initialization:
1. Verifies data directory exists (created by core/data_paths.py)
2. Runs initdb if data directory is empty
3. Starts PostgreSQL service
4. Creates database user and database (from .env)
5. Seeds markets table

Uses:
- postgre_service.py for service operations (start, stop, status)
- postgre_setup.py for user/database/schema setup

Usage:
    # As module
    from database.postgre_initialize import initialize_postgresql
    result = initialize_postgresql()

    # As script
    python -m database.postgre_initialize
"""

import sys
from typing import Dict, Optional

from database.core.config_loader import ConfigLoader
from database.core.logger import get_logger
from database.postgre_service import PostgreSQLService
from database.postgre_setup import PostgreSQLSetup

logger = get_logger(__name__, 'core')


class PostgreSQLInitializer:
    """
    Orchestrates PostgreSQL initialization.

    Coordinates between PostgreSQLService and PostgreSQLSetup
    to perform complete database initialization.
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        self.config = config if config else ConfigLoader()
        self.service = PostgreSQLService(self.config)
        self.setup = PostgreSQLSetup(self.config)

    def initialize(self, seed_markets: bool = True) -> Dict:
        """
        Complete PostgreSQL initialization.

        Steps:
        1. Verify data directory exists
        2. Run initdb if needed
        3. Start PostgreSQL
        4. Create user and database
        5. Seed markets (optional)

        Args:
            seed_markets: Whether to seed markets table

        Returns:
            Dictionary with initialization result
        """
        result = {
            'success': False,
            'steps': {},
            'message': ''
        }

        print("\n" + "=" * 70)
        print("POSTGRESQL INITIALIZATION")
        print("=" * 70)

        # Step 1: Check data directory exists
        print("\nStep 1: Checking data directory...")
        if not self.service.is_directory_exists():
            data_dir = self.service.get_data_directory()
            result['steps']['directory_check'] = {
                'success': False,
                'message': f'Data directory does not exist: {data_dir}'
            }
            result['message'] = 'Data directory not found. Run core/data_paths.py first.'
            print(f"  X Directory not found: {data_dir}")
            return result

        data_dir = self.service.get_data_directory()
        result['steps']['directory_check'] = {
            'success': True,
            'message': f'Data directory exists: {data_dir}'
        }
        print(f"  OK Directory exists: {data_dir}")

        # Step 2: Run initdb if needed
        print("\nStep 2: Checking initialization status...")
        if not self.service.is_directory_initialized():
            print("  Directory not initialized. Running initdb...")
            initdb_result = self.service.run_initdb()
            result['steps']['initdb'] = initdb_result

            if not initdb_result['success']:
                result['message'] = initdb_result['message']
                print(f"  X initdb failed: {initdb_result['message']}")
                return result

            print("  OK initdb completed successfully")
        else:
            result['steps']['initdb'] = {
                'success': True,
                'message': 'Already initialized (PG_VERSION exists)'
            }
            print("  OK Already initialized")

        # Step 3: Start PostgreSQL
        print("\nStep 3: Starting PostgreSQL...")

        # Check if fully ready (user and database exist)
        if self.service.can_connect():
            result['steps']['start'] = {
                'success': True,
                'message': 'PostgreSQL running with user/database ready'
            }
            print("  OK PostgreSQL already running with user/database")
        # Check if service running but user/db not yet created
        elif self.service.can_connect_as_postgres():
            result['steps']['start'] = {
                'success': True,
                'message': 'PostgreSQL running (user/database will be created)'
            }
            print("  OK PostgreSQL running (will create user/database)")
        else:
            # Need to start the service
            if self.service.is_service_running():
                print("  Service running but not accepting connections. Restarting...")
                self.service.stop()

            start_result = self.service.start()
            result['steps']['start'] = start_result

            if not start_result['success']:
                result['message'] = start_result['message']
                print(f"  X Failed to start: {start_result['message']}")
                return result

            # Verify we can connect as postgres (user/db created in next step)
            if not self.service.can_connect_as_postgres():
                result['steps']['start']['success'] = False
                result['message'] = 'PostgreSQL started but cannot connect as postgres'
                print("  X PostgreSQL started but cannot connect")
                return result

            print("  OK PostgreSQL started successfully")

        # Step 4: Create user and database
        print("\nStep 4: Creating user and database...")
        db_user = self.config.get('db_user')
        db_name = self.config.get('db_name')
        print(f"  User: {db_user}, Database: {db_name}")

        user_db_result = self.setup.create_user_and_database()
        result['steps']['create_user_database'] = user_db_result

        if not user_db_result['success']:
            result['message'] = user_db_result['message']
            print(f"  X Failed: {user_db_result['message']}")
            return result

        if user_db_result['user_created']:
            print(f"  OK Created user: {db_user}")
        else:
            print(f"  OK User already exists: {db_user}")

        if user_db_result['database_created']:
            print(f"  OK Created database: {db_name}")
        else:
            print(f"  OK Database already exists: {db_name}")

        # Step 5: Seed markets (optional)
        if seed_markets:
            print("\nStep 5: Seeding markets...")
            seed_result = self.setup.seed_markets()
            result['steps']['seed_markets'] = seed_result

            if seed_result['success']:
                print(f"  OK Markets: {seed_result['markets_added']} added, {seed_result['markets_existing']} existing")
            else:
                print(f"  X Failed to seed markets: {seed_result['message']}")

        result['success'] = True
        result['message'] = 'PostgreSQL initialized successfully'

        print("\n" + "=" * 70)
        print("POSTGRESQL READY")
        print("=" * 70 + "\n")

        return result


def initialize_postgresql(seed_markets: bool = True) -> Dict:
    """
    Convenience function to initialize PostgreSQL.

    Args:
        seed_markets: Whether to seed markets table

    Returns:
        Dictionary with initialization result
    """
    initializer = PostgreSQLInitializer()
    return initializer.initialize(seed_markets=seed_markets)


def check_postgresql_status() -> Dict:
    """
    Check PostgreSQL status without making changes.

    Returns:
        Dictionary with status information
    """
    service = PostgreSQLService()

    return {
        'data_directory': str(service.get_data_directory()),
        'directory_exists': service.is_directory_exists(),
        'directory_initialized': service.is_directory_initialized(),
        'service_running': service.is_service_running(),
        'can_connect': service.can_connect(),
        'postgresql_running': service.can_connect()  # Use actual connection test
    }


def main():
    """Main entry point for script execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Initialize PostgreSQL for Map Pro',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m database.postgre_initialize              # Full initialization
    python -m database.postgre_initialize --status     # Check status only
    python -m database.postgre_initialize --no-seed    # Skip market seeding
        """
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='Check status without making changes'
    )
    parser.add_argument(
        '--no-seed',
        action='store_true',
        help='Skip market seeding'
    )

    args = parser.parse_args()

    if args.status:
        status = check_postgresql_status()
        print("\nPostgreSQL Status:")
        print(f"  Data directory: {status['data_directory']}")
        print(f"  Directory exists: {status['directory_exists']}")
        print(f"  Directory initialized: {status['directory_initialized']}")
        print(f"  Service running: {status['service_running']}")
        print(f"  Can connect: {status['can_connect']}")
        sys.exit(0)

    result = initialize_postgresql(seed_markets=not args.no_seed)

    if result['success']:
        print("\n[SUCCESS] PostgreSQL initialization complete")
        sys.exit(0)
    else:
        print(f"\n[ERROR] {result['message']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
