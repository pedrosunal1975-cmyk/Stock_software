# Path: library/cli/constants.py
"""
CLI Constants

Display constants, messages, and formatting for library CLI.
Centralizes all hardcoded strings and display parameters.

Architecture:
- No hardcoded strings in CLI code
- Consistent formatting across all commands
- Easy to customize display
"""

# ================================================================
# DISPLAY FORMATTING
# ================================================================

# Line separators
SEPARATOR_WIDTH = 80
SEPARATOR_LINE = "=" * SEPARATOR_WIDTH
SEPARATOR_THIN = "-" * SEPARATOR_WIDTH

# Indentation
INDENT_LEVEL_1 = "  "
INDENT_LEVEL_2 = "    "
INDENT_LEVEL_3 = "      "

# Status symbols
SYMBOL_SUCCESS = "✓"
SYMBOL_WARNING = "⚠"
SYMBOL_ERROR = "✗"
SYMBOL_INFO = "ℹ"
SYMBOL_BULLET = "•"

# ================================================================
# HEADER MESSAGES
# ================================================================

HEADER_LIBRARIES = "TAXONOMY LIBRARIES"
HEADER_PENDING = "PENDING TAXONOMY DOWNLOADS"
HEADER_STATISTICS = "LIBRARY STATISTICS"
HEADER_MANUAL_INSTRUCTIONS = "MANUAL TAXONOMY DOWNLOAD INSTRUCTIONS"
HEADER_SCANNING_FILING = "SCANNING FILING"
HEADER_CHECKING_LIBRARY = "CHECKING LIBRARY"

# ================================================================
# STATUS MESSAGES
# ================================================================

MSG_NO_PENDING = "No pending downloads."
MSG_LIBRARIES_BY_STATUS = "Libraries by status:"
MSG_FOUND_PENDING = "Found {count} pending downloads:"
MSG_COORDINATOR_NOT_IMPLEMENTED = "Coordinator not yet implemented."
MSG_WILL_SCAN_FILING = "This will scan the filing and show taxonomy requirements."

# ================================================================
# STATISTICS LABELS
# ================================================================

STATS_DIRECTORY_TITLE = "Directory Statistics:"
STATS_DATABASE_TITLE = "Database Statistics:"

STATS_LIBRARIES_COUNT = "Downloaded Libraries"
STATS_MANUAL_DOWNLOADS = "Manual Downloads"
STATS_PROCESSED_FILES = "Processed Files"
STATS_CACHE_FILES = "Cached Results"
STATS_TEMP_FILES = "Temporary Files"

# ================================================================
# LIBRARY DISPLAY FORMAT
# ================================================================

LIBRARY_DISPLAY_NAME = "{indent}{symbol} {name} v{version}"
LIBRARY_DISPLAY_URL = "{indent}URL: {url}"
LIBRARY_DISPLAY_MARKETS = "{indent}Markets: {markets}"

# ================================================================
# LIBRARY STATUS LABELS
# ================================================================

STATUS_LABEL_IN_DB = "In Database"
STATUS_LABEL_ON_DISK = "On Disk"
STATUS_LABEL_FILE_COUNT = "File Count"
STATUS_LABEL_IS_READY = "Is Ready"

# ================================================================
# ACTION REQUIRED MESSAGES
# ================================================================

ACTION_DOWNLOAD_REQUIRED = "Action Required: Download library"
ACTION_REINDEX_REQUIRED = "Action Required: Re-index library"
ACTION_READY_TO_USE = "Status: Ready for use"

# ================================================================
# MANUAL DOWNLOAD INSTRUCTIONS
# ================================================================

MANUAL_INSTRUCTIONS_TEMPLATE = """
If automatic download fails, you can manually download taxonomies:

1. Download the taxonomy ZIP file from the official source
2. Place it in the manual downloads directory:
   {manual_downloads_dir}

3. Run the library module to process it:
   python library.py --process-manual <filename>

4. The system will:
   - Extract the taxonomy
   - Validate contents
   - Register in database
   - Move original to processed directory

Common taxonomy sources:
  {symbol} SEC: {sec_url}
  {symbol} FASB: {fasb_url}
  {symbol} IFRS: {ifrs_url}
  {symbol} ESMA: {esma_url}
"""

# ================================================================
# TAXONOMY SOURCE URLS
# ================================================================

TAXONOMY_SOURCE_SEC = "https://xbrl.sec.gov/"
TAXONOMY_SOURCE_FASB = "https://xbrl.fasb.org/"
TAXONOMY_SOURCE_IFRS = "https://www.ifrs.org/"
TAXONOMY_SOURCE_ESMA = "https://www.esma.europa.eu/"

# ================================================================
# ERROR MESSAGES
# ================================================================

ERROR_LISTING_LIBRARIES = "Error listing libraries: {error}"
ERROR_LISTING_PENDING = "Error listing pending: {error}"
ERROR_SHOWING_STATISTICS = "Error showing statistics: {error}"
ERROR_CHECKING_LIBRARY = "Error checking library: {error}"
ERROR_IMPORT_FAILED = "Cannot import required modules: {error}"
ERROR_DB_INIT_FAILED = "Database initialization failed: {error}"

# ================================================================
# FIELD WIDTHS (for aligned display)
# ================================================================

FIELD_WIDTH_LABEL = 25
FIELD_WIDTH_VALUE = 50

# ================================================================
# HELPER FUNCTIONS
# ================================================================

def format_header(title: str) -> str:
    """
    Format header with separators.
    
    Args:
        title: Header title
        
    Returns:
        Formatted header string
    """
    return f"\n{SEPARATOR_LINE}\n{title}\n{SEPARATOR_LINE}"


def format_field(label: str, value: str, indent: str = INDENT_LEVEL_1) -> str:
    """
    Format field for display.
    
    Args:
        label: Field label
        value: Field value
        indent: Indentation level
        
    Returns:
        Formatted field string
    """
    return f"{indent}{label}: {value}"


def format_error(error: Exception) -> str:
    """
    Format error message.
    
    Args:
        error: Exception object
        
    Returns:
        Formatted error string
    """
    return f"Error: {str(error)}"


__all__ = [
    'SEPARATOR_LINE',
    'SEPARATOR_THIN',
    'SEPARATOR_WIDTH',
    'INDENT_LEVEL_1',
    'INDENT_LEVEL_2',
    'INDENT_LEVEL_3',
    'SYMBOL_SUCCESS',
    'SYMBOL_WARNING',
    'SYMBOL_ERROR',
    'SYMBOL_INFO',
    'SYMBOL_BULLET',
    'HEADER_LIBRARIES',
    'HEADER_PENDING',
    'HEADER_STATISTICS',
    'HEADER_MANUAL_INSTRUCTIONS',
    'HEADER_SCANNING_FILING',
    'HEADER_CHECKING_LIBRARY',
    'MSG_NO_PENDING',
    'MSG_LIBRARIES_BY_STATUS',
    'MSG_FOUND_PENDING',
    'MSG_COORDINATOR_NOT_IMPLEMENTED',
    'MSG_WILL_SCAN_FILING',
    'STATS_DIRECTORY_TITLE',
    'STATS_DATABASE_TITLE',
    'STATS_LIBRARIES_COUNT',
    'STATS_MANUAL_DOWNLOADS',
    'STATS_PROCESSED_FILES',
    'STATS_CACHE_FILES',
    'STATS_TEMP_FILES',
    'LIBRARY_DISPLAY_NAME',
    'LIBRARY_DISPLAY_URL',
    'LIBRARY_DISPLAY_MARKETS',
    'STATUS_LABEL_IN_DB',
    'STATUS_LABEL_ON_DISK',
    'STATUS_LABEL_FILE_COUNT',
    'STATUS_LABEL_IS_READY',
    'ACTION_DOWNLOAD_REQUIRED',
    'ACTION_REINDEX_REQUIRED',
    'ACTION_READY_TO_USE',
    'MANUAL_INSTRUCTIONS_TEMPLATE',
    'TAXONOMY_SOURCE_SEC',
    'TAXONOMY_SOURCE_FASB',
    'TAXONOMY_SOURCE_IFRS',
    'TAXONOMY_SOURCE_ESMA',
    'ERROR_LISTING_LIBRARIES',
    'ERROR_LISTING_PENDING',
    'ERROR_SHOWING_STATISTICS',
    'ERROR_CHECKING_LIBRARY',
    'ERROR_IMPORT_FAILED',
    'ERROR_DB_INIT_FAILED',
    'FIELD_WIDTH_LABEL',
    'FIELD_WIDTH_VALUE',
    'format_header',
    'format_field',
    'format_error',
]