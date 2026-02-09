# Path: mat_acc/database/__init__.py
"""
mat_acc Database Module

Stores mat_acc_id identifiers and hierarchy structures for processed filings.

This module provides:
- Database models for filings, hierarchies, and nodes
- CRUD operations for storing and retrieving hierarchies
- Query methods for finding hierarchies by various criteria

Design Principles:
- Market and taxonomy agnostic (works with any XBRL filing)
- Statement codes generated dynamically
- Stores complete hierarchy structure with mat_acc_id for each node

Example:
    from database import initialize_database, session_scope
    from database import ProcessedFiling, StatementHierarchy, HierarchyNode

    # Initialize database
    initialize_database()

    # Store a hierarchy
    with session_scope() as session:
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        session.add(filing)

    # Query hierarchies
    with session_scope() as session:
        hierarchies = session.query(StatementHierarchy).filter_by(
            statement_type='BALANCE_SHEET'
        ).all()
"""

from database.models.base import (
    Base,
    initialize_engine,
    get_engine,
    get_session,
    session_scope,
    create_all_tables,
    drop_all_tables,
    reset_engine,
    get_database_type,
    get_connection_info,
)
from database.models.processed_filings import ProcessedFiling
from database.models.statement_hierarchies import StatementHierarchy
from database.models.hierarchy_nodes import HierarchyNode

from database.operations.filing_ops import FilingOperations
from database.operations.hierarchy_ops import HierarchyOperations

from database.integration.hierarchy_storage import (
    HierarchyStorage,
    process_filing_to_database,
)


def initialize_database(db_path: str = None) -> None:
    """
    Initialize the mat_acc database.

    Args:
        db_path: Optional path to SQLite database file.
                 If None, uses default from config.

    Example:
        # Use default path
        initialize_database()

        # Use custom path
        initialize_database('/path/to/mat_acc.db')
    """
    initialize_engine(db_path)
    create_all_tables()


__all__ = [
    # Initialization
    'initialize_database',
    'initialize_engine',
    'get_engine',
    'get_session',
    'session_scope',
    'create_all_tables',
    'drop_all_tables',
    'reset_engine',
    'get_database_type',
    'get_connection_info',
    # Models
    'Base',
    'ProcessedFiling',
    'StatementHierarchy',
    'HierarchyNode',
    # Operations
    'FilingOperations',
    'HierarchyOperations',
    # Integration
    'HierarchyStorage',
    'process_filing_to_database',
]
