# Path: xbrl_parser/indexing/__init__.py
"""
Indexing Module

SQLite-based indexing and querying system for XBRL filings.

This module provides:
- IndexBuilder: Build SQLite indexes from parsed filings
- DatabaseSchema: Manage database schema
- QueryEngine: Query indexed data
- Constants: All configuration constants

Example:
    from ..indexing import IndexBuilder, QueryEngine
    
    # Build index
    builder = IndexBuilder('filings.db')
    for filing in filings:
        builder.index_filing(filing)
    builder.commit()
    builder.close()
    
    # Query index
    engine = QueryEngine('filings.db')
    filings = engine.get_filings_by_entity('0001234567')
    for filing in filings:
        print(filing['filing_id'])
    engine.close()
"""

from ..indexing.builder import IndexBuilder
from ..indexing.schema import DatabaseSchema
from ..indexing.query_engine import QueryEngine, QueryResult
from ..indexing import constants


__all__ = [
    # Builder
    'IndexBuilder',
    
    # Schema
    'DatabaseSchema',
    
    # Query engine
    'QueryEngine',
    'QueryResult',
    
    # Constants
    'constants',
]
