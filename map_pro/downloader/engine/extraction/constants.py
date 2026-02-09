# Path: downloader/engine/extraction/constants.py
"""
Extraction Module Constants

Centralized constants for archive, XSD, and directory extraction.
NO HARDCODED VALUES in extraction handlers - all configuration here.
"""

# ============================================================================
# ARCHIVE EXTRACTION
# ============================================================================

# Archive size limits (bytes)
DEFAULT_MAX_ARCHIVE_SIZE = 500 * 1024 * 1024  # 500MB

# Archive read modes
ZIP_READ_MODE = 'r'
ZIP_WRITE_MODE = 'w'

# TAR compression modes
TAR_READ_MODE = 'r'
TAR_GZ_MODE = 'r:gz'
TAR_BZ2_MODE = 'r:bz2'
TAR_XZ_MODE = 'r:xz'

# Supported archive file extensions
ARCHIVE_EXTENSIONS_ZIP = '.zip'
ARCHIVE_EXTENSIONS_TAR = '.tar'
ARCHIVE_EXTENSIONS_TAR_GZ = '.tar.gz'
ARCHIVE_EXTENSIONS_TGZ = '.tgz'
ARCHIVE_EXTENSIONS_TAR_BZ2 = '.tar.bz2'
ARCHIVE_EXTENSIONS_TBZ2 = '.tbz2'
ARCHIVE_EXTENSIONS_TAR_XZ = '.tar.xz'
ARCHIVE_EXTENSIONS_TXZ = '.txz'

# Complete list of supported extensions
SUPPORTED_ARCHIVE_EXTENSIONS = {
    ARCHIVE_EXTENSIONS_ZIP,
    ARCHIVE_EXTENSIONS_TAR,
    ARCHIVE_EXTENSIONS_TAR_GZ,
    ARCHIVE_EXTENSIONS_TGZ,
    ARCHIVE_EXTENSIONS_TAR_BZ2,
    ARCHIVE_EXTENSIONS_TBZ2,
    ARCHIVE_EXTENSIONS_TAR_XZ,
    ARCHIVE_EXTENSIONS_TXZ,
}

# ============================================================================
# XML/XSD PARSING
# ============================================================================

# XML namespaces (standard - not taxonomy-specific)
XML_NAMESPACES = {
    'xs': 'http://www.w3.org/2001/XMLSchema',
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'link': 'http://www.xbrl.org/2003/linkbase',
    'xlink': 'http://www.w3.org/1999/xlink',
    'xbrli': 'http://www.xbrl.org/2003/instance',
}

# XPath expressions for finding imports/includes
XPATH_IMPORT = './/xs:import[@schemaLocation]'
XPATH_INCLUDE = './/xs:include[@schemaLocation]'
XPATH_LINKBASE_REF = './/{http://www.xbrl.org/2003/linkbase}linkbaseRef'

# XML attribute names
ATTR_SCHEMA_LOCATION = 'schemaLocation'
ATTR_HREF = '{http://www.w3.org/1999/xlink}href'

# ============================================================================
# XSD HANDLER DEFAULTS
# ============================================================================

# HTTP request timeout for XSD downloads (seconds)
XSD_DOWNLOAD_TIMEOUT = 30

# Maximum import depth to prevent infinite recursion
XSD_MAX_IMPORT_DEPTH = 10

# Default filename if cannot extract from URL
XSD_DEFAULT_FILENAME = 'schema.xsd'

# ============================================================================
# DIRECTORY HANDLER DEFAULTS
# ============================================================================

# HTTP request timeout for directory operations (seconds)
DIRECTORY_TIMEOUT = 30

# Maximum directory depth for recursive mirroring
DIRECTORY_MAX_DEPTH = 10

# ============================================================================
# HTML PARSING (Directory Listings)
# ============================================================================

# Links to skip in directory listings (parent, special links)
SKIP_DIRECTORY_LINKS = {
    '../',
    '..',
    '?',
    '/',
    '',
}

# File extensions to exclude from directory mirroring (optional filters)
EXCLUDE_FILE_EXTENSIONS = {
    # Can add extensions to skip if needed
    # Example: '.tmp', '.bak'
}

# ============================================================================
# FILE VALIDATION
# ============================================================================

# Minimum file size for valid download (bytes)
MIN_VALID_XSD_SIZE = 10

# Maximum file size for XSD files (bytes) - 10MB
MAX_XSD_FILE_SIZE = 10 * 1024 * 1024

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Archive extraction
    'DEFAULT_MAX_ARCHIVE_SIZE',
    'ZIP_READ_MODE',
    'ZIP_WRITE_MODE',
    'TAR_READ_MODE',
    'TAR_GZ_MODE',
    'TAR_BZ2_MODE',
    'TAR_XZ_MODE',
    'ARCHIVE_EXTENSIONS_ZIP',
    'ARCHIVE_EXTENSIONS_TAR',
    'ARCHIVE_EXTENSIONS_TAR_GZ',
    'ARCHIVE_EXTENSIONS_TGZ',
    'ARCHIVE_EXTENSIONS_TAR_BZ2',
    'ARCHIVE_EXTENSIONS_TBZ2',
    'ARCHIVE_EXTENSIONS_TAR_XZ',
    'ARCHIVE_EXTENSIONS_TXZ',
    'SUPPORTED_ARCHIVE_EXTENSIONS',
    
    # XML namespaces
    'XML_NAMESPACES',
    'XPATH_IMPORT',
    'XPATH_INCLUDE',
    'XPATH_LINKBASE_REF',
    'ATTR_SCHEMA_LOCATION',
    'ATTR_HREF',
    
    # XSD handler
    'XSD_DOWNLOAD_TIMEOUT',
    'XSD_MAX_IMPORT_DEPTH',
    'XSD_DEFAULT_FILENAME',
    
    # Directory handler
    'DIRECTORY_TIMEOUT',
    'DIRECTORY_MAX_DEPTH',
    
    # HTML parsing
    'SKIP_DIRECTORY_LINKS',
    'EXCLUDE_FILE_EXTENSIONS',
    
    # Validation
    'MIN_VALID_XSD_SIZE',
    'MAX_XSD_FILE_SIZE',
]