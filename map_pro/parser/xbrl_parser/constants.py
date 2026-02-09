# Path: parser/xbrl_parser/constants.py
"""
Constants for XBRL Parser Module

All configuration values, patterns, and thresholds used across the parser.
Follows the no-hardcoded-values principle.
"""

# ============================================================================
# ENTRY POINT DETECTION - EXHIBIT PATTERNS
# ============================================================================

# Patterns for identifying exhibit files (to exclude from instance consideration)
EXHIBIT_PATTERNS = [
    r'^ex\d',                    # ex101.htm, ex231.htm
    r'exhibit',                  # any file with 'exhibit' in name
    r'^aciq\d-\d+ex',           # aciq4-24ex311.htm
    r'ex\d+-',                  # ex10-18.htm
    r'-ex\d+',                  # file-ex32.htm
    r'^\d+-[kq]exhibit',        # 10-kexhibit32109272025.htm
    r'^[a-z]{1,5}ex\d+',        # vex311.htm, msftex32.htm (ticker + ex + number)
]

# ============================================================================
# ENTRY POINT DETECTION - FILE FILTERS
# ============================================================================

# Linkbase file suffixes to exclude
LINKBASE_SUFFIXES = ['_def', '_cal', '_lab', '_pre', '_ref', '_ftn']

# Non-XBRL file extensions to exclude
NON_XBRL_EXTENSIONS = ['.jpg', '.png', '.gif', '.css', '.js', '.pdf']

# Filename patterns to exclude
EXCLUDED_FILENAMES = ['readme', 'filelist', 'meta']

# ============================================================================
# ENTRY POINT DETECTION - FILE SIZE THRESHOLDS
# ============================================================================

# File size thresholds in KB
SIZE_LARGE_THRESHOLD = 500      # Main instances typically >500KB
SIZE_MEDIUM_THRESHOLD = 200     # Medium files get partial credit
SIZE_SMALL_PENALTY = 50         # Files <50KB penalized (likely exhibits)

# ============================================================================
# ENTRY POINT DETECTION - SCORING WEIGHTS
# ============================================================================

# Positive indicators
SCORE_IXBRL_FORMAT = 20         # HTML/XHTML format
SCORE_DATE_PATTERN = 25         # Contains YYYYMMDD pattern
SCORE_SHORT_FILENAME = 10       # Filename < 20 chars
SCORE_SCHEMA_MATCH = 40         # Matches .xsd base name (CRITICAL)
SCORE_LARGE_FILE = 30           # File size > 500KB
SCORE_MEDIUM_FILE = 20          # File size > 200KB
SCORE_XML_INSTANCE = 15         # XML with -ins suffix
SCORE_XML_FORMAT = 10           # Standard XML format
SCORE_TICKER_PATTERN = 5        # Ticker-like pattern
SCORE_SIMPLE_FILENAME = 5       # Few hyphens/underscores
SCORE_EXTRACTED_DIR = 30        # In 'extracted' directory

# Penalties (negative scores)
PENALTY_SMALL_FILE = -10        # File size < 50KB
PENALTY_LONG_FILENAME = -10     # Filename > 30 chars
PENALTY_FORM_TYPE = -5          # Form type in middle of name
PENALTY_MANY_UNDERSCORES = -3   # More than 2 underscores

# ============================================================================
# ENTRY POINT DETECTION - FILENAME PATTERNS
# ============================================================================

# Ticker/standard instance patterns
TICKER_PATTERNS = [
    r'^[a-z]{2,5}-\d',          # 2-5 letter ticker + dash + number
    r'^filing',                  # filing.xml, filing-20231231.htm
    r'^instance',                # instance.xml
]

# ============================================================================
# ENTRY POINT DETECTION - THRESHOLDS
# ============================================================================

# Maximum filename lengths
MAX_SIMPLE_FILENAME_LENGTH = 20  # Short filenames get bonus
MAX_FILENAME_LENGTH = 30         # Long filenames get penalty

# Hyphen/underscore limits
MAX_SIMPLE_HYPHENS = 1           # Simple filenames have ≤1 hyphen
MAX_UNDERSCORES_PENALTY = 2      # Too many underscores = penalty