# Path: database/constants.py
"""
Database Module Constants

All constant values used throughout the database module.
No magic numbers or hardcoded strings in the codebase.

Design Philosophy:
- Single source of truth for all constants
- Clear naming conventions
- Grouped by functional area
"""

from typing import List

# Database Schema Version
# =======================
SCHEMA_VERSION: str = 'v1.0.0'

# Database Status Values
# ======================
STATUS_PENDING: str = 'pending'
STATUS_COMPLETED: str = 'completed'
STATUS_FAILED: str = 'failed'
STATUS_NOT_NEEDED: str = 'not_needed'
STATUS_DOWNLOADING: str = 'downloading'
STATUS_VERIFIED: str = 'verified'
STATUS_ACTIVE: str = 'active'
STATUS_INACTIVE: str = 'inactive'

# All valid status values
VALID_DOWNLOAD_STATUSES: List[str] = [
    STATUS_PENDING,
    STATUS_DOWNLOADING,
    STATUS_COMPLETED,
    STATUS_FAILED
]

VALID_EXTRACTION_STATUSES: List[str] = [
    STATUS_PENDING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_NOT_NEEDED
]

# Field Length Limits
# ===================
# Small identifiers and codes
MAX_MARKET_ID_LENGTH: int = 10
MAX_STATUS_LENGTH: int = 20
MAX_COUNTRY_CODE_LENGTH: int = 3

# Medium text fields
MAX_MARKET_NAME_LENGTH: int = 100
MAX_COMPANY_NAME_LENGTH: int = 255
MAX_FORM_TYPE_LENGTH: int = 50
MAX_MARKET_ENTITY_ID_LENGTH: int = 100
MAX_ACCESSION_NUMBER_LENGTH: int = 100
MAX_TAXONOMY_NAME_LENGTH: int = 100
MAX_TAXONOMY_VERSION_LENGTH: int = 50

# Hash and SHA256
MAX_SHA256_LENGTH: int = 64

# Default Values
# ==============
DEFAULT_BOOLEAN_FALSE: bool = False
DEFAULT_BOOLEAN_TRUE: bool = True
DEFAULT_RATE_LIMIT: int = 10
DEFAULT_FILE_COUNT: int = 0

# Logging Configuration
# =====================
LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT: str = '%Y-%m-%d %H:%M:%S'

# Logger names by component
LOGGER_CORE: str = 'database.core'
LOGGER_MODELS: str = 'database.models'
LOGGER_MIGRATIONS: str = 'database.migrations'

# File Extensions
# ===============
# Relevant file extensions for taxonomy libraries
TAXONOMY_EXTENSIONS: set = {'.xsd', '.xml', '.html', '.htm', '.xbri'}

# Directory Names
# ===============
LOGS_SUBDIRECTORY: str = 'logs'
POSTGRESQL_SUBDIRECTORY: str = 'postgresql_data'
MIGRATIONS_SUBDIRECTORY: str = 'migrations'

# File Verification
# =================
# Maximum depth for recursive file search
MAX_DIRECTORY_DEPTH: int = 25

# Cleanup Configuration
# =====================
# Days to retain old search results before cleanup
DEFAULT_CLEANUP_DAYS: int = 90

# Maximum search results to store per query
DEFAULT_MAX_SEARCH_RESULTS: int = 1000

# Module Names
# ============
MODULE_DATABASE: str = 'database'
MODULE_SEARCHER: str = 'searcher'
MODULE_DOWNLOADER: str = 'downloader'
MODULE_EXTRACTOR: str = 'extractor'
MODULE_TAXONOMY: str = 'taxonomy'

# Environment Variable Keys
# =========================
ENV_DB_HOST: str = 'DB_HOST'
ENV_DB_PORT: str = 'DB_PORT'
ENV_DB_NAME: str = 'DB_NAME'
ENV_DB_USER: str = 'DB_USER'
ENV_DB_PASSWORD: str = 'DB_PASSWORD'
ENV_DB_ROOT_DIR: str = 'DB_ROOT_DIR'
ENV_DB_LOG_DIR: str = 'DB_LOG_DIR'
ENV_DB_LOG_LEVEL: str = 'DB_LOG_LEVEL'
ENV_DB_LOG_CONSOLE: str = 'DB_LOG_CONSOLE'
ENV_DB_POSTGRESQL_DATA_DIR: str = 'DB_POSTGRESQL_DATA_DIR'
ENV_DATA_ENTITIES_DIR: str = 'DATA_ENTITIES_DIR'
ENV_DATA_TAXONOMIES_DIR: str = 'DATA_TAXONOMIES_DIR'

# Database Connection Pool
# ========================
ENV_DB_POOL_SIZE: str = 'DB_POOL_SIZE'
ENV_DB_POOL_MAX_OVERFLOW: str = 'DB_POOL_MAX_OVERFLOW'
ENV_DB_POOL_TIMEOUT: str = 'DB_POOL_TIMEOUT'
ENV_DB_POOL_RECYCLE: str = 'DB_POOL_RECYCLE'

DEFAULT_POOL_SIZE: int = 5
DEFAULT_POOL_MAX_OVERFLOW: int = 10
DEFAULT_POOL_TIMEOUT: int = 30
DEFAULT_POOL_RECYCLE: int = 3600


__all__ = [
    'SCHEMA_VERSION',
    'STATUS_PENDING',
    'STATUS_COMPLETED',
    'STATUS_FAILED',
    'STATUS_NOT_NEEDED',
    'STATUS_DOWNLOADING',
    'STATUS_VERIFIED',
    'STATUS_ACTIVE',
    'STATUS_INACTIVE',
    'VALID_DOWNLOAD_STATUSES',
    'VALID_EXTRACTION_STATUSES',
    'MAX_MARKET_ID_LENGTH',
    'MAX_STATUS_LENGTH',
    'MAX_COUNTRY_CODE_LENGTH',
    'MAX_MARKET_NAME_LENGTH',
    'MAX_COMPANY_NAME_LENGTH',
    'MAX_FORM_TYPE_LENGTH',
    'MAX_MARKET_ENTITY_ID_LENGTH',
    'MAX_ACCESSION_NUMBER_LENGTH',
    'MAX_TAXONOMY_NAME_LENGTH',
    'MAX_TAXONOMY_VERSION_LENGTH',
    'MAX_SHA256_LENGTH',
    'DEFAULT_BOOLEAN_FALSE',
    'DEFAULT_BOOLEAN_TRUE',
    'DEFAULT_RATE_LIMIT',
    'DEFAULT_FILE_COUNT',
    'LOG_FORMAT',
    'LOG_DATE_FORMAT',
    'LOGGER_CORE',
    'LOGGER_MODELS',
    'LOGGER_MIGRATIONS',
    'TAXONOMY_EXTENSIONS',
    'LOGS_SUBDIRECTORY',
    'POSTGRESQL_SUBDIRECTORY',
    'MIGRATIONS_SUBDIRECTORY',
    'MAX_DIRECTORY_DEPTH',
    'DEFAULT_CLEANUP_DAYS',
    'DEFAULT_MAX_SEARCH_RESULTS',
    'MODULE_DATABASE',
    'MODULE_SEARCHER',
    'MODULE_DOWNLOADER',
    'MODULE_EXTRACTOR',
    'MODULE_TAXONOMY',
    'ENV_DB_HOST',
    'ENV_DB_PORT',
    'ENV_DB_NAME',
    'ENV_DB_USER',
    'ENV_DB_PASSWORD',
    'ENV_DB_ROOT_DIR',
    'ENV_DB_LOG_DIR',
    'ENV_DB_LOG_LEVEL',
    'ENV_DB_LOG_CONSOLE',
    'ENV_DB_POSTGRESQL_DATA_DIR',
    'ENV_DATA_ENTITIES_DIR',
    'ENV_DATA_TAXONOMIES_DIR',
    'ENV_DB_POOL_SIZE',
    'ENV_DB_POOL_MAX_OVERFLOW',
    'ENV_DB_POOL_TIMEOUT',
    'ENV_DB_POOL_RECYCLE',
    'DEFAULT_POOL_SIZE',
    'DEFAULT_POOL_MAX_OVERFLOW',
    'DEFAULT_POOL_TIMEOUT',
    'DEFAULT_POOL_RECYCLE',
]