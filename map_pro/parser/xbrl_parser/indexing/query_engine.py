# Path: xbrl_parser/indexing/query_engine.py
"""
Query Engine for Indexed XBRL Data

Provides query interface for SQLite-indexed XBRL filings.

This module provides:
- Query methods for filings, facts, contexts
- Filtering and pagination
- Query result caching
- Aggregation queries

Example:
    from ..indexing import QueryEngine
    
    # Open index
    engine = QueryEngine('/path/to/index.db')
    
    # Query filings
    filings = engine.get_filings_by_entity('0001234567')
    
    # Query facts
    facts = engine.get_facts_by_concept('Assets', limit=100)
    
    # Date range query
    filings = engine.get_filings_by_date_range('2023-01-01', '2023-12-31')
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime, date

from ..indexing.constants import (
    DB_TIMEOUT,
    DB_CHECK_SAME_THREAD,
    TABLE_FILINGS,
    TABLE_FACTS,
    TABLE_CONTEXTS,
    TABLE_UNITS,
    TABLE_CONCEPTS,
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT,
    DEFAULT_PAGE_SIZE,
    QUERY_TIMEOUT_SECONDS
)


class QueryResult:
    """
    Query result container.
    
    Attributes:
        rows: Result rows
        count: Total count (for pagination)
        page: Current page number
        page_size: Page size
        has_more: Whether more results available
    """
    
    def __init__(
        self,
        rows: list[dict[str, any]],
        count: Optional[int] = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE
    ):
        """Initialize query result."""
        self.rows = rows
        self.count = count if count is not None else len(rows)
        self.page = page
        self.page_size = page_size
        self.has_more = len(rows) == page_size
    
    def __len__(self) -> int:
        """Get number of rows."""
        return len(self.rows)
    
    def __iter__(self):
        """Iterate over rows."""
        return iter(self.rows)


class QueryEngine:
    """
    Query engine for indexed XBRL data.
    
    Provides methods to query SQLite-indexed filings, facts, and contexts.
    
    Example:
        # Create query engine
        engine = QueryEngine('filings.db')
        
        # Query filings
        filings = engine.get_filings_by_entity('0001234567')
        
        for filing in filings:
            print(f"Filing: {filing['filing_id']}")
            print(f"Date: {filing['filing_date']}")
        
        # Query facts with pagination
        facts = engine.get_facts_by_concept(
            'Assets',
            limit=50,
            offset=0
        )
        
        # Count results
        count = engine.count_filings_by_entity('0001234567')
    """
    
    def __init__(self, database_path: Path):
        """
        Initialize query engine.
        
        Args:
            database_path: Path to SQLite database
        """
        self.logger = logging.getLogger(__name__)
        self.database_path = Path(database_path)
        
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {database_path}")
        
        # Connect to database
        self.conn = sqlite3.connect(
            str(self.database_path),
            timeout=DB_TIMEOUT,
            check_same_thread=DB_CHECK_SAME_THREAD
        )
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts
        
        self.logger.info(f"QueryEngine initialized: {database_path}")
    
    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, any]:
        """Convert Row to dictionary."""
        return dict(row) if row else None
    
    def _rows_to_dicts(self, rows: list[sqlite3.Row]) -> list[dict[str, any]]:
        """Convert Rows to dictionaries."""
        return [dict(row) for row in rows]
    
    def get_filing_by_id(self, filing_id: str) -> Optional[dict[str, any]]:
        """
        Get filing by ID.
        
        Args:
            filing_id: Filing ID
            
        Returns:
            Filing dictionary or None
        """
        cursor = self.conn.execute(
            f"SELECT * FROM {TABLE_FILINGS} WHERE filing_id = ?",
            (filing_id,)
        )
        row = cursor.fetchone()
        return self._row_to_dict(row)
    
    def get_filings_by_entity(
        self,
        entity_identifier: str,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0
    ) -> QueryResult:
        """
        Get filings by entity identifier.
        
        Args:
            entity_identifier: Entity identifier (CIK, LEI, etc.)
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            QueryResult with filings
        """
        limit = min(limit, MAX_QUERY_LIMIT)
        
        cursor = self.conn.execute(f"""
            SELECT * FROM {TABLE_FILINGS}
            WHERE entity_identifier = ?
            ORDER BY filing_date DESC
            LIMIT ? OFFSET ?
        """, (entity_identifier, limit, offset))
        
        rows = self._rows_to_dicts(cursor.fetchall())
        
        # Get total count
        count_cursor = self.conn.execute(f"""
            SELECT COUNT(*) FROM {TABLE_FILINGS}
            WHERE entity_identifier = ?
        """, (entity_identifier,))
        count = count_cursor.fetchone()[0]
        
        return QueryResult(rows, count=count, page_size=limit)
    
    def get_filings_by_date_range(
        self,
        start_date: str,
        end_date: str,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0
    ) -> QueryResult:
        """
        Get filings by date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            QueryResult with filings
        """
        limit = min(limit, MAX_QUERY_LIMIT)
        
        cursor = self.conn.execute(f"""
            SELECT * FROM {TABLE_FILINGS}
            WHERE filing_date BETWEEN ? AND ?
            ORDER BY filing_date DESC
            LIMIT ? OFFSET ?
        """, (start_date, end_date, limit, offset))
        
        rows = self._rows_to_dicts(cursor.fetchall())
        
        # Get total count
        count_cursor = self.conn.execute(f"""
            SELECT COUNT(*) FROM {TABLE_FILINGS}
            WHERE filing_date BETWEEN ? AND ?
        """, (start_date, end_date))
        count = count_cursor.fetchone()[0]
        
        return QueryResult(rows, count=count, page_size=limit)
    
    def get_facts_by_filing(
        self,
        filing_id: str,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0
    ) -> QueryResult:
        """
        Get facts for a filing.
        
        Args:
            filing_id: Filing ID
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            QueryResult with facts
        """
        limit = min(limit, MAX_QUERY_LIMIT)
        
        cursor = self.conn.execute(f"""
            SELECT * FROM {TABLE_FACTS}
            WHERE filing_id = ?
            LIMIT ? OFFSET ?
        """, (filing_id, limit, offset))
        
        rows = self._rows_to_dicts(cursor.fetchall())
        
        # Get total count
        count_cursor = self.conn.execute(f"""
            SELECT COUNT(*) FROM {TABLE_FACTS}
            WHERE filing_id = ?
        """, (filing_id,))
        count = count_cursor.fetchone()[0]
        
        return QueryResult(rows, count=count, page_size=limit)
    
    def get_facts_by_concept(
        self,
        concept: str,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0
    ) -> QueryResult:
        """
        Get facts by concept name.
        
        Args:
            concept: Concept name
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            QueryResult with facts
        """
        limit = min(limit, MAX_QUERY_LIMIT)
        
        cursor = self.conn.execute(f"""
            SELECT * FROM {TABLE_FACTS}
            WHERE concept = ?
            LIMIT ? OFFSET ?
        """, (concept, limit, offset))
        
        rows = self._rows_to_dicts(cursor.fetchall())
        
        # Get total count
        count_cursor = self.conn.execute(f"""
            SELECT COUNT(*) FROM {TABLE_FACTS}
            WHERE concept = ?
        """, (concept,))
        count = count_cursor.fetchone()[0]
        
        return QueryResult(rows, count=count, page_size=limit)
    
    def search_facts(
        self,
        concept_pattern: str = None,
        value_pattern: str = None,
        filing_id: str = None,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0
    ) -> QueryResult:
        """
        Search facts with multiple criteria.
        
        Args:
            concept_pattern: SQL LIKE pattern for concept
            value_pattern: SQL LIKE pattern for value
            filing_id: Specific filing ID
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            QueryResult with facts
        """
        limit = min(limit, MAX_QUERY_LIMIT)
        
        # Build WHERE clause
        conditions = []
        params = []
        
        if concept_pattern:
            conditions.append("concept LIKE ?")
            params.append(f"%{concept_pattern}%")
        
        if value_pattern:
            conditions.append("value LIKE ?")
            params.append(f"%{value_pattern}%")
        
        if filing_id:
            conditions.append("filing_id = ?")
            params.append(filing_id)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Execute query
        cursor = self.conn.execute(f"""
            SELECT * FROM {TABLE_FACTS}
            WHERE {where_clause}
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        
        rows = self._rows_to_dicts(cursor.fetchall())
        
        # Get total count
        count_cursor = self.conn.execute(f"""
            SELECT COUNT(*) FROM {TABLE_FACTS}
            WHERE {where_clause}
        """, params)
        count = count_cursor.fetchone()[0]
        
        return QueryResult(rows, count=count, page_size=limit)
    
    def get_contexts_by_filing(
        self,
        filing_id: str,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0
    ) -> QueryResult:
        """
        Get contexts for a filing.
        
        Args:
            filing_id: Filing ID
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            QueryResult with contexts
        """
        limit = min(limit, MAX_QUERY_LIMIT)
        
        cursor = self.conn.execute(f"""
            SELECT * FROM {TABLE_CONTEXTS}
            WHERE filing_id = ?
            LIMIT ? OFFSET ?
        """, (filing_id, limit, offset))
        
        rows = self._rows_to_dicts(cursor.fetchall())
        
        return QueryResult(rows, page_size=limit)
    
    def count_filings_by_entity(self, entity_identifier: str) -> int:
        """
        Count filings for entity.
        
        Args:
            entity_identifier: Entity identifier
            
        Returns:
            Number of filings
        """
        cursor = self.conn.execute(f"""
            SELECT COUNT(*) FROM {TABLE_FILINGS}
            WHERE entity_identifier = ?
        """, (entity_identifier,))
        return cursor.fetchone()[0]
    
    def count_facts_by_filing(self, filing_id: str) -> int:
        """
        Count facts in filing.
        
        Args:
            filing_id: Filing ID
            
        Returns:
            Number of facts
        """
        cursor = self.conn.execute(f"""
            SELECT COUNT(*) FROM {TABLE_FACTS}
            WHERE filing_id = ?
        """, (filing_id,))
        return cursor.fetchone()[0]
    
    def get_statistics(self) -> dict[str, int]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with counts
        """
        stats = {}
        
        # Count filings
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM {TABLE_FILINGS}")
        stats['total_filings'] = cursor.fetchone()[0]
        
        # Count facts
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM {TABLE_FACTS}")
        stats['total_facts'] = cursor.fetchone()[0]
        
        # Count contexts
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM {TABLE_CONTEXTS}")
        stats['total_contexts'] = cursor.fetchone()[0]
        
        # Count unique entities
        cursor = self.conn.execute(f"""
            SELECT COUNT(DISTINCT entity_identifier) FROM {TABLE_FILINGS}
        """)
        stats['unique_entities'] = cursor.fetchone()[0]
        
        return stats
    
    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
        self.logger.info("QueryEngine closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


__all__ = ['QueryEngine', 'QueryResult']
