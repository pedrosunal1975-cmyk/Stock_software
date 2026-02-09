# Path: database/setup.py
"""
Database Setup Script

Initialize the XBRL coordination database.
Creates all required tables and verifies configuration.

Usage:
    python -m database.setup
    
    # Or with custom config
    python -m database.setup --config /path/to/.env
"""

import sys
import argparse
from pathlib import Path

from database import (
    initialize_database,
    validate_paths,
    get_logger,
    session_scope,
    Market,
)


def setup_database(config_path: Path = None) -> bool:
    """
    Setup database with initial configuration.
    
    Args:
        config_path: Optional path to .env file
        
    Returns:
        True if setup successful
    """
    from database.core import ConfigLoader
    
    # Load configuration
    config = ConfigLoader(env_file=config_path) if config_path else None
    
    # Initialize database
    try:
        print("Initializing database module...")
        initialize_database(config)
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False
    
    # Validate paths
    print("\nValidating paths...")
    health = validate_paths()
    
    if health['status'] == 'healthy':
        print("✓ All paths validated successfully")
    else:
        print(f"⚠ Path validation status: {health['status']}")
        if health['issues']:
            print("  Issues:")
            for issue in health['issues']:
                print(f"    - {issue}")
    
    # Verify database connection
    print("\nVerifying database connection...")
    try:
        with session_scope() as session:
            # Count existing markets
            market_count = session.query(Market).count()
            print(f"✓ Database connection successful ({market_count} markets registered)")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("Database setup complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Register markets using market registry")
    print("2. Use database from searcher, downloader, extractor modules")
    print("\nExample:")
    print("  from database import session_scope, Entity")
    print("  with session_scope() as session:")
    print("      entities = session.query(Entity).all()")
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup XBRL Coordination Database"
    )
    parser.add_argument(
        '--config',
        type=Path,
        help="Path to .env configuration file"
    )
    
    args = parser.parse_args()
    
    success = setup_database(args.config)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()