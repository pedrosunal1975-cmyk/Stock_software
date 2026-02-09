# Path: downloader/constants.py
"""
Downloader Module Constants

Module-wide constants for download operations.
Market-specific constants go in extraction/handlers.

No hardcoded paths - all paths come from .env via config_loader.
"""

from pathlib import Path

# ============================================================================
# STATUS VALUES
# ============================================================================
STATUS_PENDING: str = 'pending'

# ============================================================================
# INCLUDED TAXONOMIES (Not downloadable - built into parsers/parent taxonomies)
# ============================================================================
# These taxonomies should be SKIPPED in downloads:
# - Transformation registries are built into iXBRL parsers
# - Small taxonomies (country, currency, etc.) are bundled in us-gaap/dei
INCLUDED_TAXONOMIES: set = {
    # Inline XBRL Transformation Registries (built into parser, not downloadable)
    'transformation',
    'inlinexbrl',
    'ixt',
    'ixt-sec',
    # Small taxonomies bundled in larger ones
    'country',
    'currency',
    'exch',
    'naics',
    'sic',
    'stpr',
}


def is_included_taxonomy(name: str) -> bool:
    """
    Check if taxonomy is included/built-in (not separately downloadable).

    Args:
        name: Taxonomy name

    Returns:
        True if this is an included taxonomy
    """
    return name.lower() in INCLUDED_TAXONOMIES


STATUS_DOWNLOADING: str = 'downloading'
STATUS_COMPLETED: str = 'completed'
STATUS_FAILED: str = 'failed'
STATUS_EXTRACTING: str = 'extracting'
STATUS_VERIFYING: str = 'verifying'

# ============================================================================
# HTTP STATUS CODES
# ============================================================================
HTTP_OK: int = 200
HTTP_PARTIAL_CONTENT: int = 206
HTTP_NOT_FOUND: int = 404
HTTP_TOO_MANY_REQUESTS: int = 429
HTTP_SERVER_ERROR: int = 500
HTTP_BAD_GATEWAY: int = 502
HTTP_SERVICE_UNAVAILABLE: int = 503
HTTP_GATEWAY_TIMEOUT: int = 504
RETRYABLE_STATUS_CODES: list = [
    HTTP_TOO_MANY_REQUESTS,
    HTTP_SERVER_ERROR,
    HTTP_BAD_GATEWAY,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_GATEWAY_TIMEOUT
]

# ============================================================================
# DOWNLOAD CONFIGURATION DEFAULTS
# ============================================================================
DEFAULT_CHUNK_SIZE: int = 8192  # 8KB chunks for streaming
DEFAULT_TIMEOUT: int = 300  # 5 minutes for large files
DEFAULT_CONNECT_TIMEOUT: int = 30  # 30 seconds for connection
DEFAULT_RETRY_ATTEMPTS: int = 3  # Maximum retry attempts
DEFAULT_MAX_RETRIES: int = DEFAULT_RETRY_ATTEMPTS  # Alias for backward compatibility
DEFAULT_RETRY_DELAY: float = 1.0  # Initial retry delay in seconds
DEFAULT_MAX_RETRY_DELAY: int = 60  # Maximum retry delay in seconds
DEFAULT_MAX_CONCURRENT: int = 3  # Maximum concurrent downloads

# ============================================================================
# DATABASE CONFIGURATION DEFAULTS
# ============================================================================
DEFAULT_DB_PORT: int = 5432
DEFAULT_DB_POOL_SIZE: int = 5
DEFAULT_DB_POOL_MAX_OVERFLOW: int = 10
DEFAULT_DB_POOL_TIMEOUT: int = 30
DEFAULT_DB_POOL_RECYCLE: int = 3600

# ============================================================================
# LOGGING DEFAULTS
# ============================================================================
DEFAULT_LOG_PROGRESS_INTERVAL: int = 100

# ============================================================================
# FILE VALIDATION DEFAULTS
# ============================================================================
MIN_FILE_SIZE: int = 100  # Minimum bytes for valid file
MIN_ZIP_SIZE: int = 100  # Minimum bytes for valid ZIP
MAX_EXTRACTION_DEPTH: int = 25  # Maximum directory nesting depth
MAX_ARCHIVE_SIZE: int = 524288000  # 500MB default

# ============================================================================
# OPERATIONAL DEFAULTS
# ============================================================================
TEMP_RETENTION_HOURS: int = 0  # Immediate cleanup
MAX_SEARCH_DEPTH: int = 10  # Maximum depth for instance file search

# ============================================================================
# ARCHIVE EXTENSIONS
# ============================================================================
# Supported archive formats across all markets
ARCHIVE_EXTENSIONS: set = {
    '.zip',      # ZIP (most common - SEC, ESMA, FCA)
    '.tar',      # TAR (uncompressed)
    '.gz',       # GZIP (usually .tar.gz)
    '.tar.gz',   # TAR + GZIP (common for Linux/taxonomies)
    '.tgz',      # TAR + GZIP (alternative extension)
    '.tar.xz',   # TAR + XZ (high compression - taxonomies)
    '.tar.bz2',  # TAR + BZIP2 (older compression)
    '.bz2',      # BZIP2
    '.xz',       # XZ compression
}

# ZIP-specific extensions (for backward compatibility)
ZIP_EXTENSIONS: set = {'.zip'}

# TAR-based extensions (for TAR extractor routing)
TAR_EXTENSIONS: set = {
    '.tar',
    '.tar.gz',
    '.tgz',
    '.tar.xz',
    '.tar.bz2',
}

# Archive format to extractor mapping
ARCHIVE_FORMAT_MAP: dict = {
    '.zip': 'zip',
    '.tar': 'tar',
    '.tar.gz': 'tar',
    '.tgz': 'tar',
    '.tar.xz': 'tar',
    '.tar.bz2': 'tar',
    '.gz': 'tar',  # Assume tar.gz if just .gz
    '.bz2': 'tar',  # Assume tar.bz2 if just .bz2
    '.xz': 'tar',   # Assume tar.xz if just .xz
}

def get_archive_format(file_path: Path) -> str:
    """
    Detect archive format from file path.
    
    Args:
        file_path: Path to archive file
        
    Returns:
        Format identifier ('zip', 'tar', etc.)
        
    Raises:
        ValueError: If format not supported
        
    Example:
        format = get_archive_format(Path('filing.zip'))  # Returns: 'zip'
        format = get_archive_format(Path('filing.tar.gz'))  # Returns: 'tar'
        format = get_archive_format(Path('filing.tar.xz'))  # Returns: 'tar'
    """
    file_path = Path(file_path)
    
    # Check for compound extensions first (.tar.gz, .tar.xz, etc.)
    if file_path.name.endswith('.tar.gz') or file_path.name.endswith('.tgz'):
        return 'tar'
    if file_path.name.endswith('.tar.xz'):
        return 'tar'
    if file_path.name.endswith('.tar.bz2'):
        return 'tar'
    
    # Check simple extension
    suffix = file_path.suffix.lower()
    
    if suffix in ARCHIVE_FORMAT_MAP:
        return ARCHIVE_FORMAT_MAP[suffix]
    
    raise ValueError(f"Unsupported archive format: {suffix}")


# ============================================================================
# IPO LOGGING PREFIXES
# ============================================================================
LOG_INPUT: str = '[INPUT]'
LOG_PROCESS: str = '[PROCESS]'
LOG_OUTPUT: str = '[OUTPUT]'

# ============================================================================
# LOGGING COMPONENTS
# ============================================================================
LOGGER_CORE: str = 'downloader.core'
LOGGER_ENGINE: str = 'downloader.engine'
LOGGER_CLI: str = 'downloader.cli'
LOGGER_EXTRACTION: str = 'downloader.extraction'

# ============================================================================
# LOG FORMAT
# ============================================================================
LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT: str = '%Y-%m-%d %H:%M:%S'

# ============================================================================
# DIRECTORY NAMES
# ============================================================================
TEMP_DIRNAME: str = 'temp'
ENTITIES_DIRNAME: str = 'entities'
FILINGS_DIRNAME: str = 'filings'

# ============================================================================
# ============================================================================
# VALIDATION PATTERNS - Market-Specific Instance File Discovery
# ============================================================================

# SEC (United States) - EDGAR XBRL filings
INSTANCE_PATTERNS_SEC: list = [
    '*-ins.xml',       # Standard XBRL instance (e.g., aapl-20231231-ins.xml)
    '*_htm.xml',       # iXBRL inline instance
    '*.htm',           # Pure iXBRL (HTML with XBRL tags)
    'instance.xml',    # Generic fallback
]

# ESMA (European Union) - ESEF filings
INSTANCE_PATTERNS_ESMA: list = [
    '*.html',          # ESEF iXBRL reports
    '*.xhtml',         # XHTML format
    '*-esef.html',     # ESEF-specific naming
    'report.html',     # Common European naming
    'instance.xml',    # Fallback
]

# FCA (United Kingdom) - UK filings
INSTANCE_PATTERNS_FCA: list = [
    '*.html',          # UK iXBRL reports
    '*.xhtml',         # XHTML format
    'instance.xml',    # Traditional XBRL
]

# Generic fallback for unknown markets
INSTANCE_PATTERNS_GENERIC: list = [
    'instance.xml',    # Most common generic name
    '*.xml',           # Any XML file
]

# Market registry - Maps market code to patterns
INSTANCE_PATTERNS_BY_MARKET: dict = {
    'sec': INSTANCE_PATTERNS_SEC,
    'esma': INSTANCE_PATTERNS_ESMA,
    'fca': INSTANCE_PATTERNS_FCA,
    'generic': INSTANCE_PATTERNS_GENERIC,
}

def get_instance_patterns(market: str) -> list:
    """
    Get instance file patterns for specific market.
    
    Args:
        market: Market code ('sec', 'esma', 'fca', etc.)
        
    Returns:
        List of file patterns for the market
        
    Example:
        patterns = get_instance_patterns('sec')
        # Returns: ['*-ins.xml', '*_htm.xml', '*.htm', 'instance.xml']
    """
    market_lower = market.lower() if market else 'generic'
    return INSTANCE_PATTERNS_BY_MARKET.get(market_lower, INSTANCE_PATTERNS_GENERIC)


# Legacy constant for backward compatibility (DO NOT USE - use get_instance_patterns instead)
INSTANCE_FILE_PATTERNS: list = INSTANCE_PATTERNS_SEC  # Deprecated

# ============================================================================
# ENVIRONMENT VARIABLE KEYS (for reference in config_loader.py)
# ============================================================================

# Directory Paths
ENV_DOWNLOADER_ROOT: str = 'DOWNLOADER_ROOT_DIR'
ENV_DOWNLOADER_ENTITIES: str = 'DOWNLOADER_ENTITIES_DIR'
ENV_DOWNLOADER_TEMP: str = 'DOWNLOADER_TEMP_DIR'
ENV_DOWNLOADER_LOG: str = 'DOWNLOADER_LOG_DIR'
ENV_DOWNLOADER_CACHE: str = 'DOWNLOADER_CACHE_DIR'

# Taxonomies path (from .env)
ENV_LIBRARY_TAXONOMIES: str = 'LIBRARY_TAXONOMIES_DIR'

# Download Configuration
ENV_REQUEST_TIMEOUT: str = 'DOWNLOADER_REQUEST_TIMEOUT'
ENV_CONNECT_TIMEOUT: str = 'DOWNLOADER_CONNECT_TIMEOUT'
ENV_READ_TIMEOUT: str = 'DOWNLOADER_READ_TIMEOUT'
ENV_RETRY_ATTEMPTS: str = 'DOWNLOADER_RETRY_ATTEMPTS'
ENV_RETRY_DELAY: str = 'DOWNLOADER_RETRY_DELAY'
ENV_MAX_RETRY_DELAY: str = 'DOWNLOADER_MAX_RETRY_DELAY'
ENV_MAX_CONCURRENT: str = 'DOWNLOADER_MAX_CONCURRENT'
ENV_CHUNK_SIZE: str = 'DOWNLOADER_CHUNK_SIZE'
ENV_ENABLE_RESUME: str = 'DOWNLOADER_ENABLE_RESUME'

# Extraction Configuration
ENV_MAX_ARCHIVE_SIZE: str = 'DOWNLOADER_MAX_ARCHIVE_SIZE'
ENV_VERIFY_EXTRACTION: str = 'DOWNLOADER_VERIFY_EXTRACTION'
ENV_PRESERVE_ZIP: str = 'DOWNLOADER_PRESERVE_ZIP'
ENV_MAX_EXTRACTION_DEPTH: str = 'DOWNLOADER_MAX_EXTRACTION_DEPTH'

# Validation Configuration
ENV_MIN_FILE_SIZE: str = 'DOWNLOADER_MIN_FILE_SIZE'
ENV_VERIFY_CHECKSUMS: str = 'DOWNLOADER_VERIFY_CHECKSUMS'
ENV_VERIFY_URL_BEFORE: str = 'DOWNLOADER_VERIFY_URL_BEFORE_DOWNLOAD'

# Logging Configuration
ENV_LOG_LEVEL: str = 'DOWNLOADER_LOG_LEVEL'
ENV_LOG_CONSOLE: str = 'DOWNLOADER_LOG_CONSOLE'
ENV_STORE_RAW_RESPONSES: str = 'DOWNLOADER_STORE_RAW_RESPONSES'
ENV_LOG_PROGRESS_INTERVAL: str = 'DOWNLOADER_LOG_PROGRESS_INTERVAL'

# Cleanup Configuration
ENV_CLEANUP_TEMP_ON_START: str = 'DOWNLOADER_CLEANUP_TEMP_ON_START'
ENV_CLEANUP_FAILED: str = 'DOWNLOADER_CLEANUP_FAILED_DOWNLOADS'
ENV_TEMP_RETENTION_HOURS: str = 'DOWNLOADER_TEMP_RETENTION_HOURS'

# Operational Settings
ENV_AUTO_RETRY: str = 'DOWNLOADER_AUTO_RETRY'
ENV_VERIFY_FILES_EXIST: str = 'DOWNLOADER_VERIFY_FILES_EXIST'
ENV_MAX_SEARCH_DEPTH: str = 'DOWNLOADER_MAX_SEARCH_DEPTH'

# Market-Specific Settings
ENV_SEC_USER_AGENT: str = 'DOWNLOADER_SEC_USER_AGENT'
ENV_UK_CH_API_KEY: str = 'SEARCHER_UK_CH_API_KEY'  # Reuse searcher's API key
ENV_UK_CH_USER_AGENT: str = 'SEARCHER_UK_CH_USER_AGENT'  # Reuse searcher's user agent

# ============================================================================
# EXPORTS
# ============================================================================
__all__ = [
    # Included Taxonomies
    'INCLUDED_TAXONOMIES',
    'is_included_taxonomy',

    # Status Values
    'STATUS_PENDING',
    'STATUS_DOWNLOADING',
    'STATUS_COMPLETED',
    'STATUS_FAILED',
    'STATUS_EXTRACTING',
    'STATUS_VERIFYING',
    
    # HTTP Status Codes
    'HTTP_OK',
    'HTTP_PARTIAL_CONTENT',
    'HTTP_NOT_FOUND',
    'HTTP_TOO_MANY_REQUESTS',
    'HTTP_SERVER_ERROR',
    'HTTP_BAD_GATEWAY',
    'HTTP_SERVICE_UNAVAILABLE',
    'HTTP_GATEWAY_TIMEOUT',
    'RETRYABLE_STATUS_CODES',
    
    # Download Configuration Defaults
    'DEFAULT_CHUNK_SIZE',
    'DEFAULT_TIMEOUT',
    'DEFAULT_CONNECT_TIMEOUT',
    'DEFAULT_RETRY_ATTEMPTS',
    'DEFAULT_MAX_RETRIES',
    'DEFAULT_RETRY_DELAY',
    'DEFAULT_MAX_RETRY_DELAY',
    'DEFAULT_MAX_CONCURRENT',

    # Database Configuration Defaults
    'DEFAULT_DB_PORT',
    'DEFAULT_DB_POOL_SIZE',
    'DEFAULT_DB_POOL_MAX_OVERFLOW',
    'DEFAULT_DB_POOL_TIMEOUT',
    'DEFAULT_DB_POOL_RECYCLE',

    # Logging Defaults
    'DEFAULT_LOG_PROGRESS_INTERVAL',

    # File Validation Defaults
    'MIN_FILE_SIZE',
    'MIN_ZIP_SIZE',
    'MAX_EXTRACTION_DEPTH',
    'MAX_ARCHIVE_SIZE',
    
    # Operational Defaults
    'TEMP_RETENTION_HOURS',
    'MAX_SEARCH_DEPTH',
    
    # Archive Extensions
    'ARCHIVE_EXTENSIONS',
    'ZIP_EXTENSIONS',
    'TAR_EXTENSIONS',
    'ARCHIVE_FORMAT_MAP',
    'get_archive_format',
    
    # IPO Logging Prefixes
    'LOG_INPUT',
    'LOG_PROCESS',
    'LOG_OUTPUT',
    
    # Logging Components
    'LOGGER_CORE',
    'LOGGER_ENGINE',
    'LOGGER_CLI',
    'LOGGER_EXTRACTION',
    
    # Log Format
    'LOG_FORMAT',
    'LOG_DATE_FORMAT',
    
    # Directory Names
    'TEMP_DIRNAME',
    'ENTITIES_DIRNAME',
    'FILINGS_DIRNAME',
    
    # Instance File Patterns (Market-Specific)
    'INSTANCE_PATTERNS_SEC',
    'INSTANCE_PATTERNS_ESMA',
    'INSTANCE_PATTERNS_FCA',
    'INSTANCE_PATTERNS_GENERIC',
    'INSTANCE_PATTERNS_BY_MARKET',
    'get_instance_patterns',
    'INSTANCE_FILE_PATTERNS',  # Deprecated - use get_instance_patterns()
    
    # Environment Variable Keys
    'ENV_DOWNLOADER_ROOT',
    'ENV_DOWNLOADER_ENTITIES',
    'ENV_DOWNLOADER_TEMP',
    'ENV_DOWNLOADER_LOG',
    'ENV_DOWNLOADER_CACHE',
    'ENV_LIBRARY_TAXONOMIES',
    'ENV_REQUEST_TIMEOUT',
    'ENV_CONNECT_TIMEOUT',
    'ENV_READ_TIMEOUT',
    'ENV_RETRY_ATTEMPTS',
    'ENV_RETRY_DELAY',
    'ENV_MAX_RETRY_DELAY',
    'ENV_MAX_CONCURRENT',
    'ENV_CHUNK_SIZE',
    'ENV_ENABLE_RESUME',
    'ENV_MAX_ARCHIVE_SIZE',
    'ENV_VERIFY_EXTRACTION',
    'ENV_PRESERVE_ZIP',
    'ENV_MAX_EXTRACTION_DEPTH',
    'ENV_MIN_FILE_SIZE',
    'ENV_VERIFY_CHECKSUMS',
    'ENV_VERIFY_URL_BEFORE',
    'ENV_LOG_LEVEL',
    'ENV_LOG_CONSOLE',
    'ENV_STORE_RAW_RESPONSES',
    'ENV_LOG_PROGRESS_INTERVAL',
    'ENV_CLEANUP_TEMP_ON_START',
    'ENV_CLEANUP_FAILED',
    'ENV_TEMP_RETENTION_HOURS',
    'ENV_AUTO_RETRY',
    'ENV_VERIFY_FILES_EXIST',
    'ENV_MAX_SEARCH_DEPTH',
    'ENV_SEC_USER_AGENT',
]