# Path: mat_acc/database/models/__init__.py
"""
Database Models for mat_acc.

Provides SQLAlchemy models for storing:
- Processed filings (source filing metadata)
- Statement hierarchies (statement structure)
- Hierarchy nodes (individual nodes with mat_acc_id)
"""

from database.models.base import (
    Base,
    initialize_engine,
    get_engine,
    get_session,
    session_scope,
    create_all_tables,
    drop_all_tables,
)
from database.models.processed_filings import ProcessedFiling
from database.models.statement_hierarchies import StatementHierarchy
from database.models.hierarchy_nodes import HierarchyNode


__all__ = [
    'Base',
    'initialize_engine',
    'get_engine',
    'get_session',
    'session_scope',
    'create_all_tables',
    'drop_all_tables',
    'ProcessedFiling',
    'StatementHierarchy',
    'HierarchyNode',
]
