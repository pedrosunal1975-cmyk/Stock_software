# Path: library/constants.py
"""
Library Module Constants

All constants used throughout the library module.
Organized into logical groups for clarity.
"""

# ============================================================================
# ENVIRONMENT VARIABLE KEYS
# ============================================================================

ENV_LIBRARY_TAXONOMIES_ROOT = 'LIBRARY_TAXONOMIES_ROOT'
ENV_LIBRARY_TAXONOMIES_LIBRARIES = 'LIBRARY_TAXONOMIES_LIBRARIES'
ENV_LIBRARY_PARSED_FILES_DIR = 'LIBRARY_PARSED_FILES_DIR'
ENV_LIBRARY_MANUAL_DOWNLOADS = 'LIBRARY_MANUAL_DOWNLOADS'
ENV_LIBRARY_CACHE_DIR = 'LIBRARY_CACHE_DIR'
ENV_LIBRARY_TEMP_DIR = 'LIBRARY_TEMP_DIR'
ENV_LIBRARY_LOG_DIR = 'LIBRARY_LOG_DIR'

ENV_LIBRARY_MONITOR_INTERVAL = 'LIBRARY_MONITOR_INTERVAL'
ENV_LIBRARY_AUTO_CREATE = 'LIBRARY_AUTO_CREATE'
ENV_LIBRARY_MIN_FILES_THRESHOLD = 'LIBRARY_MIN_FILES_THRESHOLD'
ENV_LIBRARY_CACHE_TTL = 'LIBRARY_CACHE_TTL'
ENV_LIBRARY_MAX_RETRIES = 'LIBRARY_MAX_RETRIES'

ENV_DB_HOST = 'DB_HOST'
ENV_DB_PORT = 'DB_PORT'
ENV_DB_NAME = 'DB_NAME'
ENV_DB_USER = 'DB_USER'
ENV_DB_PASSWORD = 'DB_PASSWORD'


# ============================================================================
# IPO LOGGING PREFIXES
# ============================================================================

LOG_INPUT = '[INPUT]'
LOG_PROCESS = '[PROCESS]'
LOG_OUTPUT = '[OUTPUT]'


# ============================================================================
# FILE NAMES AND PATTERNS
# ============================================================================

PARSED_JSON_FILENAME = 'parsed.json'
TAXONOMY_NAMESPACE_KEY = 'taxonomy_namespaces'
FACTS_KEY = 'facts'
METADATA_KEY = 'metadata'


# ============================================================================
# LIBRARY STATUS CONSTANTS
# ============================================================================

LIBRARY_STATUS_ACTIVE = 'active'
LIBRARY_STATUS_PENDING = 'pending'
LIBRARY_STATUS_FAILED = 'failed'
LIBRARY_STATUS_DOWNLOADING = 'downloading'


# ============================================================================
# VALIDATION STATUS CONSTANTS
# ============================================================================

VALIDATION_STATUS_HEALTHY = 'healthy'
VALIDATION_STATUS_PENDING = 'pending'
VALIDATION_STATUS_CORRUPTED = 'corrupted'
VALIDATION_STATUS_UNKNOWN = 'unknown'


# ============================================================================
# OPERATIONAL THRESHOLDS
# ============================================================================

MIN_FILES_THRESHOLD = 10
CACHE_TTL_SECONDS = 3600
MAX_RETRY_ATTEMPTS = 3
DEFAULT_MONITOR_INTERVAL = 60


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Environment keys
    'ENV_LIBRARY_TAXONOMIES_ROOT',
    'ENV_LIBRARY_TAXONOMIES_LIBRARIES',
    'ENV_LIBRARY_PARSED_FILES_DIR',
    'ENV_LIBRARY_MANUAL_DOWNLOADS',
    'ENV_LIBRARY_CACHE_DIR',
    'ENV_LIBRARY_TEMP_DIR',
    'ENV_LIBRARY_LOG_DIR',
    'ENV_LIBRARY_MONITOR_INTERVAL',
    'ENV_LIBRARY_AUTO_CREATE',
    'ENV_LIBRARY_MIN_FILES_THRESHOLD',
    'ENV_LIBRARY_CACHE_TTL',
    'ENV_LIBRARY_MAX_RETRIES',
    'ENV_DB_HOST',
    'ENV_DB_PORT',
    'ENV_DB_NAME',
    'ENV_DB_USER',
    'ENV_DB_PASSWORD',
    
    # Logging
    'LOG_INPUT',
    'LOG_PROCESS',
    'LOG_OUTPUT',
    
    # File names
    'PARSED_JSON_FILENAME',
    'TAXONOMY_NAMESPACE_KEY',
    'FACTS_KEY',
    'METADATA_KEY',
    
    # Status constants
    'LIBRARY_STATUS_ACTIVE',
    'LIBRARY_STATUS_PENDING',
    'LIBRARY_STATUS_FAILED',
    'LIBRARY_STATUS_DOWNLOADING',
    'VALIDATION_STATUS_HEALTHY',
    'VALIDATION_STATUS_PENDING',
    'VALIDATION_STATUS_CORRUPTED',
    'VALIDATION_STATUS_UNKNOWN',
    
    # Thresholds
    'MIN_FILES_THRESHOLD',
    'CACHE_TTL_SECONDS',
    'MAX_RETRY_ATTEMPTS',
    'DEFAULT_MONITOR_INTERVAL',
]