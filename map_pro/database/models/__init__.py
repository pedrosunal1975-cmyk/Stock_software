# Path: database/models/__init__.py
"""
Database Models Module

All database models for XBRL coordination system.
Five-table design: markets, entities, filing_searches, 
downloaded_filings, taxonomy_libraries.
"""

from .base import (
    Base,
    initialize_engine,
    get_engine,
    get_session,
    session_scope,
    create_all_tables,
    drop_all_tables,
)
from .markets import Market
from .entities import Entity
from .filing_searches import FilingSearch
from .downloaded_filings import DownloadedFiling
from .taxonomy_libraries import TaxonomyLibrary

__all__ = [
    # Base utilities
    'Base',
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