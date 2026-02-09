# Path: xbrl_parser/serialization/constants.py
"""
Serialization Module Constants

Central repository for all serialization-related constants.

NO HARDCODED values should exist in other serialization files.
"""

# ==============================================================================
# SCHEMA VERSIONS
# ==============================================================================

# Current output schema version
CURRENT_SCHEMA_VERSION = "1.0"

# Supported schema versions for migration
SUPPORTED_SCHEMA_VERSIONS = ["1.0"]

# ==============================================================================
# OUTPUT FORMATS
# ==============================================================================

# Output format types
OUTPUT_FORMAT_JSON = "json"
OUTPUT_FORMAT_COMPACT_JSON = "compact_json"
OUTPUT_FORMAT_DEBUG = "debug"
OUTPUT_FORMAT_ANONYMIZED = "anonymized"

OUTPUT_FORMATS = [
    OUTPUT_FORMAT_JSON,
    OUTPUT_FORMAT_COMPACT_JSON,
    OUTPUT_FORMAT_DEBUG,
    OUTPUT_FORMAT_ANONYMIZED
]

# ==============================================================================
# JSON SERIALIZATION
# ==============================================================================

# JSON encoding
JSON_ENCODING = "utf-8"

# Default indent for pretty printing
JSON_INDENT = 2

# Maximum decimal places for numeric values
MAX_DECIMAL_PLACES = 10

# Date/time formats
ISO_DATE_FORMAT = "%Y-%m-%d"
ISO_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# ==============================================================================
# CHECKPOINT CONFIGURATION
# ==============================================================================

# Checkpoint file extension
CHECKPOINT_EXTENSION = ".checkpoint"

# Checkpoint format version
CHECKPOINT_VERSION = "1.0"

# Default checkpoint interval (facts processed)
DEFAULT_CHECKPOINT_INTERVAL = 5000

# Checkpoint compression
CHECKPOINT_COMPRESS = True

# Maximum checkpoint age (seconds)
MAX_CHECKPOINT_AGE = 86400  # 24 hours

# ==============================================================================
# FIELD INCLUSION
# ==============================================================================

# Fields to include in compact output
COMPACT_FIELDS = [
    'facts',
    'contexts',
    'units',
    'metadata'
]

# Fields to exclude from compact output
COMPACT_EXCLUDE_FIELDS = [
    'taxonomy',
    'validation',
    'statistics',
    'provenance',
    'errors'
]

# Fields to include in full output
FULL_OUTPUT_FIELDS = [
    'metadata',
    'taxonomy',
    'instance',
    'validation',
    'statistics',
    'provenance',
    'errors',
    'reliability',
    'quality_score'
]

# Fields to redact in anonymized output
ANONYMIZED_REDACT_FIELDS = [
    'entity_identifier',
    'company_name',
    'value',
    'entity'
]

# ==============================================================================
# COMPRESSION
# ==============================================================================

# Compression level (0-9)
DEFAULT_COMPRESSION_LEVEL = 6

# Compression formats
COMPRESSION_GZIP = "gzip"
COMPRESSION_NONE = "none"

# ==============================================================================
# FILE NAMING
# ==============================================================================

# Output file name patterns
OUTPUT_FILENAME_PATTERN = "{filing_id}_{timestamp}.json"
CHECKPOINT_FILENAME_PATTERN = "{filing_id}_checkpoint_{phase}.checkpoint"

# Timestamp format for filenames
FILENAME_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# ==============================================================================
# SIZE LIMITS
# ==============================================================================

# Maximum output file size before warning (bytes)
MAX_OUTPUT_SIZE_WARNING = 100 * 1024 * 1024  # 100MB

# Maximum checkpoint file size (bytes)
MAX_CHECKPOINT_SIZE = 50 * 1024 * 1024  # 50MB

# ==============================================================================
# MIGRATION
# ==============================================================================

# Migration status
MIGRATION_STATUS_SUCCESS = "success"
MIGRATION_STATUS_FAILED = "failed"
MIGRATION_STATUS_PARTIAL = "partial"

# Migration versions
MIGRATION_VERSIONS = {
    "1.0": {
        "description": "Initial schema version",
        "date": "2025-01-06"
    }
}

# ==============================================================================
# ERROR MESSAGES
# ==============================================================================

MSG_SERIALIZATION_FAILED = "Failed to serialize data to JSON"
MSG_DESERIALIZATION_FAILED = "Failed to deserialize JSON data"
MSG_CHECKPOINT_SAVE_FAILED = "Failed to save checkpoint"
MSG_CHECKPOINT_LOAD_FAILED = "Failed to load checkpoint"
MSG_MIGRATION_FAILED = "Failed to migrate data to current schema"
MSG_INVALID_SCHEMA_VERSION = "Invalid or unsupported schema version"
MSG_OUTPUT_TOO_LARGE = "Output file size exceeds recommended maximum"

# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    # Schema versions
    'CURRENT_SCHEMA_VERSION',
    'SUPPORTED_SCHEMA_VERSIONS',
    
    # Output formats
    'OUTPUT_FORMAT_JSON',
    'OUTPUT_FORMAT_COMPACT_JSON',
    'OUTPUT_FORMAT_DEBUG',
    'OUTPUT_FORMAT_ANONYMIZED',
    'OUTPUT_FORMATS',
    
    # JSON settings
    'JSON_ENCODING',
    'JSON_INDENT',
    'MAX_DECIMAL_PLACES',
    'ISO_DATE_FORMAT',
    'ISO_DATETIME_FORMAT',
    
    # Checkpoint settings
    'CHECKPOINT_EXTENSION',
    'CHECKPOINT_VERSION',
    'DEFAULT_CHECKPOINT_INTERVAL',
    'CHECKPOINT_COMPRESS',
    'MAX_CHECKPOINT_AGE',
    
    # Field inclusion
    'COMPACT_FIELDS',
    'COMPACT_EXCLUDE_FIELDS',
    'FULL_OUTPUT_FIELDS',
    'ANONYMIZED_REDACT_FIELDS',
    
    # Compression
    'DEFAULT_COMPRESSION_LEVEL',
    'COMPRESSION_GZIP',
    'COMPRESSION_NONE',
    
    # File naming
    'OUTPUT_FILENAME_PATTERN',
    'CHECKPOINT_FILENAME_PATTERN',
    'FILENAME_TIMESTAMP_FORMAT',
    
    # Size limits
    'MAX_OUTPUT_SIZE_WARNING',
    'MAX_CHECKPOINT_SIZE',
    
    # Migration
    'MIGRATION_STATUS_SUCCESS',
    'MIGRATION_STATUS_FAILED',
    'MIGRATION_STATUS_PARTIAL',
    'MIGRATION_VERSIONS',
    
    # Error messages
    'MSG_SERIALIZATION_FAILED',
    'MSG_DESERIALIZATION_FAILED',
    'MSG_CHECKPOINT_SAVE_FAILED',
    'MSG_CHECKPOINT_LOAD_FAILED',
    'MSG_MIGRATION_FAILED',
    'MSG_INVALID_SCHEMA_VERSION',
    'MSG_OUTPUT_TOO_LARGE',
]