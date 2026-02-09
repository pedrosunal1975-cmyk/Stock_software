# Path: database/__init__.py
"""
XBRL Coordination Database Module

Metadata coordination for XBRL filing processing pipeline.
Used by: searcher, downloader, extractor, and taxonomy modules.

Architecture:
- Database is METADATA store (filesystem is truth)
- File existence verification (always check reality)
- Market agnostic design
- Name preservation (exact from sources)

Usage:
    from database import initialize_database, session_scope
    from database.models import Entity, FilingSearch

    # Initialize database
    initialize_database()

    # Use session
    with session_scope() as session:
        entity = session.query(Entity).first()
        if entity.directory_exists:
            process_entity(entity)

PostgreSQL Initialization:
    from database import initialize_postgresql, check_postgresql_status

    # Full initialization (initdb + start + seed markets)
    result = initialize_postgresql()

    # Check status
    status = check_postgresql_status()
"""

from .core import (
    ConfigLoader,
    DataPathsManager,
    ensure_data_paths,
    validate_paths,
    get_logger,
    configure_logging,
)

from .models import (
    Base,
    initialize_engine,
    get_engine,
    get_session,
    session_scope,
    create_all_tables,
    drop_all_tables,
    Market,
    Entity,
    FilingSearch,
    DownloadedFiling,
    TaxonomyLibrary,
)

from .postgre_service import PostgreSQLService
from .postgre_setup import PostgreSQLSetup
from .postgre_initialize import (
    PostgreSQLInitializer,
    initialize_postgresql,
    check_postgresql_status,
)


def initialize_database(config: ConfigLoader = None) -> None:
    """
    Initialize database module.
    
    Performs complete initialization:
    1. Configure logging
    2. Ensure directories exist
    3. Initialize database engine
    4. Create tables if needed
    
    Args:
        config: Optional ConfigLoader instance
        
    Example:
        from database import initialize_database
        
        initialize_database()  # Uses .env configuration
    """
    logger = get_logger(__name__, 'core')
    
    # Configure logging
    configure_logging(config)
    logger.info("Database module initializing...")
    
    # Ensure data paths exist
    paths_result = ensure_data_paths()
    logger.info(
        f"Data paths: {len(paths_result['created'])} created, "
        f"{len(paths_result['existing'])} existing"
    )
    
    # Initialize database engine
    initialize_engine(config)
    logger.info("Database engine initialized")
    
    # Create tables (idempotent - safe to call multiple times)
    create_all_tables()
    logger.info("Database tables ready")
    
    logger.info("Database module initialized successfully")


__all__ = [
    # Core utilities
    'ConfigLoader',
    'DataPathsManager',
    'ensure_data_paths',
    'validate_paths',
    'get_logger',
    'configure_logging',
    # PostgreSQL service and setup
    'PostgreSQLService',
    'PostgreSQLSetup',
    # PostgreSQL initialization
    'PostgreSQLInitializer',
    'initialize_postgresql',
    'check_postgresql_status',
    # Database initialization
    'initialize_database',
    # Database utilities
    'initialize_engine',
    'get_engine',
    'get_session',
    'session_scope',
    'create_all_tables',
    'drop_all_tables',
    # Models
    'Market',
    'Entity',
    'FilingSearch',
    'DownloadedFiling',
    'TaxonomyLibrary',
]