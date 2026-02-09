# Path: database/models/base.py
"""
Database Base Model

SQLAlchemy declarative base and database engine configuration.
Provides foundation for all database models.

Architecture:
- Single declarative base for all models
- Database engine with connection pooling
- Session management utilities
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator

from database.core.config_loader import ConfigLoader
from database.core.logger import get_logger

logger = get_logger(__name__, 'models')

# SQLAlchemy declarative base
Base = declarative_base()

# Global engine and session factory
_engine = None
_SessionFactory = None


def initialize_engine(config: ConfigLoader = None) -> None:
    """
    Initialize database engine and session factory.
    
    Args:
        config: Optional ConfigLoader instance
    """
    global _engine, _SessionFactory
    
    if _engine is not None:
        logger.warning("Database engine already initialized")
        return
    
    if config is None:
        config = ConfigLoader()
    
    # Get database URL
    database_url = config.get_database_url()
    
    # Get pool configuration
    pool_size = config.get('pool_size')
    pool_max_overflow = config.get('pool_max_overflow')
    pool_timeout = config.get('pool_timeout')
    pool_recycle = config.get('pool_recycle')
    
    # Create engine with connection pooling
    _engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=pool_max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        echo=False,  # Set to True for SQL debugging
    )
    
    # Create session factory
    _SessionFactory = sessionmaker(bind=_engine)
    
    logger.info(f"Database engine initialized (pool_size={pool_size})")


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
            entity = session.query(Entity).first()
            # ... do work ...
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


__all__ = [
    'Base',
    'initialize_engine',
    'get_engine',
    'get_session',
    'session_scope',
    'create_all_tables',
    'drop_all_tables',
]