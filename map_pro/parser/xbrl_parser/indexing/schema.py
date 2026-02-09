# Path: xbrl_parser/indexing/schema.py
"""
SQLite Database Schema

Defines the database schema for indexing XBRL filings.

This module provides:
- Table definitions
- Index creation
- Schema initialization
- Schema migration support

Example:
    from ..indexing import DatabaseSchema
    
    schema = DatabaseSchema()
    schema.create_tables(conn)
    schema.create_indexes(conn)
"""

import logging
import sqlite3

from ..indexing.constants import (
    SCHEMA_VERSION,
    SCHEMA_VERSION_TABLE,
    TABLE_FILINGS,
    TABLE_FACTS,
    TABLE_CONTEXTS,
    TABLE_UNITS,
    TABLE_CONCEPTS,
    TABLE_RELATIONSHIPS,
    FILING_INDEXES,
    FACT_INDEXES,
    CONTEXT_INDEXES,
    CONCEPT_INDEXES,
    DB_JOURNAL_MODE
)


class DatabaseSchema:
    """
    Manage SQLite database schema.
    
    Creates and maintains the database schema for indexing
    XBRL filings and enabling fast queries.
    
    Example:
        schema = DatabaseSchema()
        
        # Initialize database
        conn = sqlite3.connect('index.db')
        schema.initialize(conn)
        
        # Check version
        version = schema.get_version(conn)
    """
    
    def __init__(self):
        """Initialize database schema manager."""
        self.logger = logging.getLogger(__name__)
        self.logger.debug("DatabaseSchema initialized")
    
    def initialize(self, conn: sqlite3.Connection) -> None:
        """
        Initialize database with schema.
        
        Args:
            conn: SQLite connection
        """
        self.logger.info("Initializing database schema")
        
        # set pragmas
        self._set_pragmas(conn)
        
        # Create schema version table
        self._create_version_table(conn)
        
        # Create tables
        self.create_tables(conn)
        
        # Create indexes
        self.create_indexes(conn)
        
        # Store schema version
        self._store_version(conn)
        
        conn.commit()
        self.logger.info("Database schema initialized")
    
    def _set_pragmas(self, conn: sqlite3.Connection) -> None:
        """set SQLite pragmas for optimal performance."""
        pragmas = [
            f"PRAGMA journal_mode={DB_JOURNAL_MODE}",
            "PRAGMA synchronous=NORMAL",
            "PRAGMA cache_size=-64000",  # 64MB cache
            "PRAGMA temp_store=MEMORY",
            "PRAGMA foreign_keys=ON"
        ]
        
        for pragma in pragmas:
            conn.execute(pragma)
        
        self.logger.debug("Database pragmas set")
    
    def create_tables(self, conn: sqlite3.Connection) -> None:
        """
        Create all database tables.
        
        Args:
            conn: SQLite connection
        """
        self.logger.info("Creating database tables")
        
        # Filings table
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_FILINGS} (
                filing_id TEXT PRIMARY KEY,
                entity_identifier TEXT,
                company_name TEXT,
                document_type TEXT,
                filing_date TEXT,
                period_end_date TEXT,
                market TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Facts table
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_FACTS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filing_id TEXT NOT NULL,
                concept TEXT NOT NULL,
                context_ref TEXT,
                unit_ref TEXT,
                value TEXT,
                decimals INTEGER,
                fact_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (filing_id) REFERENCES {TABLE_FILINGS}(filing_id)
            )
        """)
        
        # Contexts table
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_CONTEXTS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filing_id TEXT NOT NULL,
                context_id TEXT NOT NULL,
                entity_scheme TEXT,
                entity_identifier TEXT,
                period_type TEXT,
                period_start TEXT,
                period_end TEXT,
                instant TEXT,
                dimensions TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (filing_id) REFERENCES {TABLE_FILINGS}(filing_id)
            )
        """)
        
        # Units table
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_UNITS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filing_id TEXT NOT NULL,
                unit_id TEXT NOT NULL,
                unit_type TEXT,
                measures TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (filing_id) REFERENCES {TABLE_FILINGS}(filing_id)
            )
        """)
        
        # Concepts table
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_CONCEPTS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filing_id TEXT NOT NULL,
                concept_name TEXT NOT NULL,
                concept_type TEXT,
                period_type TEXT,
                data_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (filing_id) REFERENCES {TABLE_FILINGS}(filing_id)
            )
        """)
        
        # Relationships table
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_RELATIONSHIPS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filing_id TEXT NOT NULL,
                source_concept TEXT NOT NULL,
                target_concept TEXT NOT NULL,
                relationship_type TEXT,
                order_value REAL,
                weight REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (filing_id) REFERENCES {TABLE_FILINGS}(filing_id)
            )
        """)
        
        self.logger.info("Database tables created")
    
    def create_indexes(self, conn: sqlite3.Connection) -> None:
        """
        Create database indexes.
        
        Args:
            conn: SQLite connection
        """
        self.logger.info("Creating database indexes")
        
        # Filing indexes
        for idx in FILING_INDEXES:
            if idx == "idx_filing_id":
                continue  # Already primary key
            elif idx == "idx_entity_identifier":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_FILINGS}(entity_identifier)")
            elif idx == "idx_document_type":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_FILINGS}(document_type)")
            elif idx == "idx_filing_date":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_FILINGS}(filing_date)")
        
        # Fact indexes
        for idx in FACT_INDEXES:
            if idx == "idx_fact_filing_id":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_FACTS}(filing_id)")
            elif idx == "idx_fact_concept":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_FACTS}(concept)")
            elif idx == "idx_fact_context_ref":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_FACTS}(context_ref)")
            elif idx == "idx_fact_value":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_FACTS}(value)")
        
        # Context indexes
        for idx in CONTEXT_INDEXES:
            if idx == "idx_context_filing_id":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_CONTEXTS}(filing_id)")
            elif idx == "idx_context_period_start":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_CONTEXTS}(period_start)")
            elif idx == "idx_context_period_end":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_CONTEXTS}(period_end)")
        
        # Concept indexes
        for idx in CONCEPT_INDEXES:
            if idx == "idx_concept_name":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_CONCEPTS}(concept_name)")
            elif idx == "idx_concept_type":
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {TABLE_CONCEPTS}(concept_type)")
        
        self.logger.info("Database indexes created")
    
    def _create_version_table(self, conn: sqlite3.Connection) -> None:
        """Create schema version table."""
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (
                version TEXT PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def _store_version(self, conn: sqlite3.Connection) -> None:
        """Store current schema version."""
        conn.execute(
            f"INSERT OR REPLACE INTO {SCHEMA_VERSION_TABLE} (version) VALUES (?)",
            (SCHEMA_VERSION,)
        )
    
    def get_version(self, conn: sqlite3.Connection) -> str:
        """
        Get current schema version.
        
        Args:
            conn: SQLite connection
            
        Returns:
            Schema version string
        """
        cursor = conn.execute(
            f"SELECT version FROM {SCHEMA_VERSION_TABLE} ORDER BY applied_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row[0] if row else "0.0"


__all__ = ['DatabaseSchema']
