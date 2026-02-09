# Path: xbrl_parser/indexing/constants.py
"""
Indexing Constants

Central repository for indexing and query system constants.

This module provides:
- SQLite database configuration
- Query limits and defaults
- Index optimization settings
- Cache configuration
"""

# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================

# SQLite database filename
DATABASE_FILENAME = "xbrl_index.db"
QUERY_CACHE_DATABASE = "query_cache.db"

# Connection settings
DB_TIMEOUT = 30  # Seconds to wait for lock
DB_CHECK_SAME_THREAD = False  # Allow multi-threading
DB_ISOLATION_LEVEL = None  # Autocommit mode

# Journal mode
DB_JOURNAL_MODE = "WAL"  # Write-Ahead Logging for better concurrency

# ==============================================================================
# SCHEMA VERSION
# ==============================================================================

SCHEMA_VERSION = "1.0"
SCHEMA_VERSION_TABLE = "schema_version"

# ==============================================================================
# TABLE NAMES
# ==============================================================================

TABLE_FILINGS = "filings"
TABLE_FACTS = "facts"
TABLE_CONTEXTS = "contexts"
TABLE_UNITS = "units"
TABLE_CONCEPTS = "concepts"
TABLE_RELATIONSHIPS = "relationships"

# ==============================================================================
# INDEXING CONFIGURATION
# ==============================================================================

# Batch sizes
DEFAULT_BATCH_SIZE = 1000
MAX_BATCH_SIZE = 10000
MIN_BATCH_SIZE = 100

# Index rebuild threshold
INDEX_REBUILD_THRESHOLD = 10000  # Rows before rebuilding indexes

# Commit frequency
COMMIT_FREQUENCY = 5000  # Number of inserts before commit

# ==============================================================================
# QUERY LIMITS
# ==============================================================================

# Default query limits
DEFAULT_QUERY_LIMIT = 100
MAX_QUERY_LIMIT = 10000

# Pagination
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000

# Query timeout
QUERY_TIMEOUT_SECONDS = 30

# ==============================================================================
# QUERY CACHE
# ==============================================================================

# Cache settings
ENABLE_QUERY_CACHE = True
CACHE_MAX_ENTRIES = 1000
CACHE_TTL_SECONDS = 3600  # 1 hour
CACHE_CLEANUP_INTERVAL = 600  # 10 minutes

# ==============================================================================
# INDEX OPTIMIZATION
# ==============================================================================

# Indexes to create
FILING_INDEXES = [
    "idx_filing_id",
    "idx_entity_identifier",
    "idx_document_type",
    "idx_filing_date",
]

FACT_INDEXES = [
    "idx_fact_filing_id",
    "idx_fact_concept",
    "idx_fact_context_ref",
    "idx_fact_value",
]

CONTEXT_INDEXES = [
    "idx_context_filing_id",
    "idx_context_period_start",
    "idx_context_period_end",
]

CONCEPT_INDEXES = [
    "idx_concept_name",
    "idx_concept_type",
]

# VACUUM settings
AUTO_VACUUM = "INCREMENTAL"
VACUUM_ON_CLOSE = False

# ==============================================================================
# COMPRESSION
# ==============================================================================

# JSON compression for large text fields
COMPRESS_LARGE_FIELDS = True
COMPRESSION_THRESHOLD_BYTES = 1024  # Compress fields larger than 1KB
COMPRESSION_ALGORITHM = "gzip"

# ==============================================================================
# QUERY PATTERNS
# ==============================================================================

# Commonly used query patterns
QUERY_FILING_BY_ID = "SELECT * FROM filings WHERE filing_id = ?"
QUERY_FACTS_BY_FILING = "SELECT * FROM facts WHERE filing_id = ? LIMIT ?"
QUERY_FACTS_BY_CONCEPT = "SELECT * FROM facts WHERE concept = ? LIMIT ?"
QUERY_FILINGS_BY_ENTITY = "SELECT * FROM filings WHERE entity_identifier = ? LIMIT ?"
QUERY_FILINGS_BY_DATE_RANGE = """
    SELECT * FROM filings 
    WHERE filing_date BETWEEN ? AND ? 
    ORDER BY filing_date DESC 
    LIMIT ?
"""

# ==============================================================================
# STATISTICS
# ==============================================================================

# Statistics collection
COLLECT_STATISTICS = True
STATISTICS_UPDATE_FREQUENCY = 100  # Updates per statistics calculation

# ==============================================================================
# ERROR MESSAGES
# ==============================================================================

ERR_DB_CONNECTION_FAILED = "Failed to connect to database"
ERR_SCHEMA_VERSION_MISMATCH = "Schema version mismatch"
ERR_INDEX_BUILD_FAILED = "Failed to build index"
ERR_QUERY_FAILED = "Query execution failed"
ERR_INVALID_QUERY = "Invalid query parameters"
ERR_CACHE_FULL = "Query cache is full"

# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    # Database
    'DATABASE_FILENAME',
    'QUERY_CACHE_DATABASE',
    'DB_TIMEOUT',
    'DB_JOURNAL_MODE',
    
    # Schema
    'SCHEMA_VERSION',
    'TABLE_FILINGS',
    'TABLE_FACTS',
    'TABLE_CONTEXTS',
    'TABLE_UNITS',
    'TABLE_CONCEPTS',
    
    # Batching
    'DEFAULT_BATCH_SIZE',
    'MAX_BATCH_SIZE',
    'COMMIT_FREQUENCY',
    
    # Query limits
    'DEFAULT_QUERY_LIMIT',
    'MAX_QUERY_LIMIT',
    'DEFAULT_PAGE_SIZE',
    'QUERY_TIMEOUT_SECONDS',
    
    # Cache
    'ENABLE_QUERY_CACHE',
    'CACHE_MAX_ENTRIES',
    'CACHE_TTL_SECONDS',
    
    # Indexes
    'FILING_INDEXES',
    'FACT_INDEXES',
    'CONTEXT_INDEXES',
    
    # Compression
    'COMPRESS_LARGE_FIELDS',
    'COMPRESSION_THRESHOLD_BYTES',
]