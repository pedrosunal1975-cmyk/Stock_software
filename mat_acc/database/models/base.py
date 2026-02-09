# Path: mat_acc/database/models/base.py
"""
Database Base Model

SQLAlchemy declarative base and database engine configuration.
Supports PostgreSQL (primary) and SQLite (testing only).

Architecture:
- Single declarative base for all models
- PostgreSQL with connection pooling for production
- SQLite in-memory for unit testing
- Session management utilities
"""

import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool


# Logger setup
logger = logging.getLogger(__name__)

# SQLAlchemy declarative base
Base = declarative_base()

# Global engine and session factory
_engine = None
_SessionFactory = None

# Database type tracking
_database_type = None  # 'postgresql' or 'sqlite'


def _get_postgresql_config() -> dict:
    """
    Get PostgreSQL configuration from config_loader.

    Returns:
        Dictionary with connection parameters
    """
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from config_loader import ConfigLoader
        config = ConfigLoader()

        return {
            'host': config.get('db_host', 'localhost'),
            'port': config.get('db_port', 5432),
            'database': config.get('db_name', 'mat_acc_db'),
            'user': config.get('db_user', ''),
            'password': config.get('db_password', ''),
            'pool_size': config.get('db_pool_size', 5),
            'max_overflow': config.get('db_pool_max_overflow', 10),
            'pool_timeout': config.get('db_pool_timeout', 30),
            'pool_recycle': config.get('db_pool_recycle', 3600),
        }
    except Exception as e:
        logger.warning(f"Could not load PostgreSQL config: {e}")
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'mat_acc_db',
            'user': 'a',
            'password': '',
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 3600,
        }


def _build_postgresql_url(config: dict) -> str:
    """
    Build PostgreSQL connection URL.

    Args:
        config: Dictionary with connection parameters

    Returns:
        PostgreSQL connection URL
    """
    return (
        f"postgresql://{config['user']}:{config['password']}@"
        f"{config['host']}:{config['port']}/{config['database']}"
    )


def initialize_engine(
    db_url: Optional[str] = None,
    use_sqlite: bool = False,
) -> None:
    """
    Initialize database engine and session factory.

    By default, connects to PostgreSQL using configuration from .env.
    Use use_sqlite=True or pass ':memory:' for testing.

    Args:
        db_url: Optional database URL. If None, uses PostgreSQL config.
                Special value ':memory:' creates SQLite in-memory database.
        use_sqlite: If True, forces SQLite mode (for testing).

    Example:
        # Use PostgreSQL (default)
        initialize_engine()

        # Use in-memory SQLite (for testing)
        initialize_engine(':memory:')

        # Use custom PostgreSQL URL
        initialize_engine('postgresql://user:pass@host:5432/dbname')
    """
    global _engine, _SessionFactory, _database_type

    if _engine is not None:
        logger.warning("Database engine already initialized")
        return

    # Determine database type and URL
    if db_url == ':memory:' or use_sqlite:
        # SQLite in-memory for testing
        _database_type = 'sqlite'
        database_url = 'sqlite:///:memory:'

        _engine = create_engine(
            database_url,
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
            echo=False,
        )
        logger.info("Database engine initialized: SQLite in-memory (testing)")

    elif db_url and db_url.startswith('sqlite'):
        # SQLite file database
        _database_type = 'sqlite'
        database_url = db_url

        # Ensure parent directory exists
        if ':///' in db_url:
            db_path = db_url.split('///')[1]
            if db_path != ':memory:':
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        _engine = create_engine(
            database_url,
            connect_args={'check_same_thread': False},
            echo=False,
        )
        logger.info(f"Database engine initialized: SQLite file")

    else:
        # PostgreSQL (production)
        _database_type = 'postgresql'

        if db_url:
            database_url = db_url
            config = {'pool_size': 5, 'max_overflow': 10, 'pool_timeout': 30, 'pool_recycle': 3600}
        else:
            config = _get_postgresql_config()
            database_url = _build_postgresql_url(config)

        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=config.get('pool_size', 5),
            max_overflow=config.get('max_overflow', 10),
            pool_timeout=config.get('pool_timeout', 30),
            pool_recycle=config.get('pool_recycle', 3600),
            echo=False,
        )
        logger.info(f"Database engine initialized: PostgreSQL ({config.get('host', 'localhost')}:{config.get('port', 5432)})")

    # Create session factory
    _SessionFactory = sessionmaker(bind=_engine)


def get_engine():
    """
    Get database engine.

    Returns:
        SQLAlchemy engine instance

    Raises:
        RuntimeError: If engine not initialized
    """
    if _engine is None:
        raise RuntimeError(
            "Database engine not initialized. "
            "Call initialize_engine() first."
        )
    return _engine


def get_session() -> Session:
    """
    Get new database session.

    Returns:
        SQLAlchemy session instance

    Raises:
        RuntimeError: If engine not initialized
    """
    if _SessionFactory is None:
        raise RuntimeError(
            "Session factory not initialized. "
            "Call initialize_engine() first."
        )
    return _SessionFactory()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Provide transactional scope for database operations.

    Yields:
        SQLAlchemy session

    Example:
        with session_scope() as session:
            filing = session.query(ProcessedFiling).first()
            session.commit()
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all_tables() -> None:
    """
    Create all database tables.

    Uses Base.metadata to create all registered tables.
    Safe to call multiple times (idempotent).
    """
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database tables created")


def drop_all_tables() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data!
    Only use in development/testing.
    """
    engine = get_engine()
    Base.metadata.drop_all(engine)
    logger.warning("All database tables dropped")


def reset_engine() -> None:
    """
    Reset the database engine.

    Used primarily for testing to allow re-initialization.
    """
    global _engine, _SessionFactory, _database_type
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None
    _database_type = None


def get_database_type() -> Optional[str]:
    """
    Get current database type.

    Returns:
        'postgresql', 'sqlite', or None if not initialized
    """
    return _database_type


def get_connection_info() -> dict:
    """
    Get current database connection info.

    Returns:
        Dictionary with connection details
    """
    if _engine is None:
        return {'status': 'not_initialized'}

    return {
        'status': 'connected',
        'type': _database_type,
        'url': str(_engine.url).replace(_engine.url.password or '', '***'),
    }


__all__ = [
    'Base',
    'initialize_engine',
    'get_engine',
    'get_session',
    'session_scope',
    'create_all_tables',
    'drop_all_tables',
    'reset_engine',
    'get_database_type',
    'get_connection_info',
]
