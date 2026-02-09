# Path: downloader/engine/constants.py
"""
Downloader Engine Constants

Centralized constants for distribution detection and download orchestration.
NO HARDCODED VALUES in engine modules - all configuration here.
"""

# ============================================================================
# DISTRIBUTION TYPE DETECTION
# ============================================================================

# Archive content types (ZIP, TAR, etc.)
ARCHIVE_CONTENT_TYPES = {
    'application/zip',
    'application/x-zip-compressed',
    'application/x-tar',
    'application/gzip',
    'application/x-gzip',
    'application/x-compressed',
    'application/x-bzip2',
    'application/x-xz',
}

# XSD/XML content types (Individual schema files)
XSD_CONTENT_TYPES = {
    'text/xml',
    'application/xml',
    'application/xsd+xml',
    'application/xsd',
}

# iXBRL/XHTML content types (Single file downloads - no extraction needed)
IXBRL_CONTENT_TYPES = {
    'application/xhtml+xml',
}

# iXBRL file extensions (for URL-based detection when content-type is ambiguous)
IXBRL_EXTENSIONS = {'.xhtml', '.html', '.htm'}

# Directory listing content types (HTML directory indexes)
DIRECTORY_CONTENT_TYPES = {
    'text/html',
    'text/html; charset=utf-8',
    'text/html; charset=iso-8859-1',
}

# Distribution type identifiers
DIST_TYPE_ARCHIVE = 'archive'
DIST_TYPE_XSD = 'xsd'
DIST_TYPE_DIRECTORY = 'directory'
DIST_TYPE_IXBRL = 'ixbrl'  # Single file iXBRL/XHTML - just copy, no extraction
DIST_TYPE_UNKNOWN = 'unknown'

# ============================================================================
# DETECTION DEFAULTS
# ============================================================================

# HTTP request timeout for detection (seconds)
DETECTION_TIMEOUT = 10

# Maximum redirects to follow during detection
DETECTION_MAX_REDIRECTS = 3

# ============================================================================
# URL PATTERN GENERATION
# ============================================================================

# Common file extensions for archives
ARCHIVE_EXTENSIONS = {'.zip', '.tar.gz', '.tar', '.tgz', '.tar.xz', '.tar.bz2'}

# Common file extensions for schemas
SCHEMA_EXTENSIONS = {'.xsd', '.xml'}

# Common XSD entry point patterns (agnostic - no taxonomy names)
XSD_ENTRY_PATTERNS = [
    '{base}.xsd',
    '{base}-entire.xsd',
    '{base}-sub.xsd',
    '{base}-entry.xsd',
]

# ============================================================================
# HTTP/PROTOCOL HANDLER CONSTANTS
# ============================================================================

# Connection timeouts (seconds)
DEFAULT_CONNECT_TIMEOUT = 30

# HTTP Connection pooling
MAX_CONCURRENT_CONNECTIONS = 10
FORCE_CLOSE_CONNECTIONS = True

# HTTP Headers - Default values
DEFAULT_USER_AGENT = 'MapProDownloader/1.0'
DEFAULT_ACCEPT_HEADER = '*/*'
DEFAULT_ACCEPT_ENCODING = 'gzip, deflate'

# HTTP Header keys
HEADER_USER_AGENT = 'User-Agent'
HEADER_ACCEPT = 'Accept'
HEADER_ACCEPT_ENCODING = 'Accept-Encoding'
HEADER_RANGE = 'Range'

# ============================================================================
# RETRY MANAGER CONSTANTS
# ============================================================================

# Maximum retry delay cap (seconds) - prevents excessive backoff
MAX_RETRY_DELAY = 60.0

# ============================================================================
# VALIDATOR CONSTANTS
# ============================================================================

# Valid URL schemes for downloads
VALID_URL_SCHEMES = ('http', 'https')

# ============================================================================
# PATH RESOLVER CONSTANTS
# ============================================================================

# Default company name when unknown
UNKNOWN_COMPANY_NAME = 'UNKNOWN'

# Directory structure names
FILINGS_SUBDIRECTORY = 'filings'

# Filesystem normalization - unsafe characters to replace
UNSAFE_PATH_CHARS = {'/', '\\'}

# Replacement character for spaces and unsafe chars
PATH_REPLACEMENT_CHAR = '_'

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Distribution types
    'ARCHIVE_CONTENT_TYPES',
    'XSD_CONTENT_TYPES',
    'IXBRL_CONTENT_TYPES',
    'IXBRL_EXTENSIONS',
    'DIRECTORY_CONTENT_TYPES',
    'DIST_TYPE_ARCHIVE',
    'DIST_TYPE_XSD',
    'DIST_TYPE_DIRECTORY',
    'DIST_TYPE_IXBRL',
    'DIST_TYPE_UNKNOWN',
    
    # Detection defaults
    'DETECTION_TIMEOUT',
    'DETECTION_MAX_REDIRECTS',
    
    # URL patterns
    'ARCHIVE_EXTENSIONS',
    'SCHEMA_EXTENSIONS',
    'XSD_ENTRY_PATTERNS',
    
    # HTTP/Protocol handler
    'DEFAULT_CONNECT_TIMEOUT',
    'MAX_CONCURRENT_CONNECTIONS',
    'FORCE_CLOSE_CONNECTIONS',
    'DEFAULT_USER_AGENT',
    'DEFAULT_ACCEPT_HEADER',
    'DEFAULT_ACCEPT_ENCODING',
    'HEADER_USER_AGENT',
    'HEADER_ACCEPT',
    'HEADER_ACCEPT_ENCODING',
    'HEADER_RANGE',
    
    # Retry manager
    'MAX_RETRY_DELAY',
    
    # Validator
    'VALID_URL_SCHEMES',
    
    # Path resolver
    'UNKNOWN_COMPANY_NAME',
    'FILINGS_SUBDIRECTORY',
    'UNSAFE_PATH_CHARS',
    'PATH_REPLACEMENT_CHAR',
]