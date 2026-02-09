# Path: searcher/markets/uk/constants.py
"""
UK Companies House Constants

All UK market-specific values centralized here.
NO HARDCODING in other files.
"""

# ==============================================================================
# MARKET IDENTIFICATION
# ==============================================================================

MARKET_ID = "uk_frc"  # Lowercase for searcher module consistency
MARKET_NAME = "United Kingdom - Financial Reporting Council"
MARKET_CODE = "UK"

# ==============================================================================
# COMPANY NUMBER FORMAT
# ==============================================================================

# Company number patterns (6-8 characters)
COMPANY_NUMBER_MIN_LENGTH = 6
COMPANY_NUMBER_MAX_LENGTH = 8
COMPANY_NUMBER_PATTERN = r'^[A-Z0-9]{6,8}$'

# Prefixes for different jurisdictions
PREFIX_ENGLAND_WALES = ""       # No prefix
PREFIX_SCOTLAND = "SC"
PREFIX_NORTHERN_IRELAND = "NI"
PREFIX_EUROPEAN_SE = "SE"
PREFIX_OVERSEAS = "FC"

# ==============================================================================
# FILING TYPES (ACCOUNTS)
# ==============================================================================

# Account types
FILING_TYPE_FULL_ACCOUNTS = "AA"          # Full accounts
FILING_TYPE_ABRIDGED_ACCOUNTS = "AC"      # Abridged accounts
FILING_TYPE_DORMANT_ACCOUNTS = "AD"       # Dormant company accounts
FILING_TYPE_GROUP_ACCOUNTS = "AG"         # Group accounts

# Valid filing categories
CATEGORY_ACCOUNTS = "accounts"
CATEGORY_ANNUAL_RETURN = "annual-return"
CATEGORY_CONFIRMATION_STATEMENT = "confirmation-statement"

# ==============================================================================
# ACCOUNTING STANDARDS
# ==============================================================================

STANDARD_IFRS = "IFRS"
STANDARD_FRS_101 = "FRS 101"
STANDARD_FRS_102 = "FRS 102"
STANDARD_FRS_105 = "FRS 105"
STANDARD_UK_GAAP = "UK GAAP"

VALID_STANDARDS = [
    STANDARD_IFRS,
    STANDARD_FRS_101,
    STANDARD_FRS_102,
    STANDARD_FRS_105,
    STANDARD_UK_GAAP
]

# ==============================================================================
# API CONFIGURATION
# ==============================================================================

# API timeouts (seconds)
DEFAULT_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 120

# Rate limits
RATE_LIMIT_REQUESTS = 600        # Requests per window
RATE_LIMIT_WINDOW = 300          # Window in seconds (5 minutes)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2                  # Seconds
BACKOFF_FACTOR = 2               # Exponential backoff multiplier

# HTTP status codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR = 500

# ==============================================================================
# FILE FORMATS
# ==============================================================================

# Supported document formats
# Companies House Document API returns these content types
FORMAT_IXBRL = "application/xhtml+xml"  # iXBRL (inline XBRL in XHTML)
FORMAT_PDF = "application/pdf"
FORMAT_XML = "application/xml"

# Preferred format priority (iXBRL first for XBRL parsing)
FORMAT_PRIORITY = [
    FORMAT_IXBRL,                # Prefer iXBRL for parsing
    FORMAT_XML,                  # Fallback to XML
    FORMAT_PDF                   # Last resort (not parseable)
]

# ==============================================================================
# CLI/UI MESSAGES
# ==============================================================================

MSG_ENTER_COMPANY_NUMBER = "Enter UK company number (e.g., 00000006, SC123456)"
MSG_INVALID_COMPANY_NUMBER = "Invalid company number format"
MSG_COMPANY_NOT_FOUND = "Company not found in Companies House"
MSG_NO_ACCOUNTS_FOUND = "No accounts found for this company"
MSG_RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Waiting..."
MSG_API_KEY_INVALID = "Invalid API key. Check credentials."

# ==============================================================================
# ERROR CODES
# ==============================================================================

ERR_INVALID_COMPANY_NUMBER = "UK001"
ERR_COMPANY_NOT_FOUND = "UK002"
ERR_NO_FILINGS = "UK003"
ERR_API_UNAUTHORIZED = "UK004"
ERR_RATE_LIMIT = "UK005"
ERR_DOWNLOAD_FAILED = "UK006"
ERR_INVALID_FILING_TYPE = "UK007"


__all__ = [
    # Market identification
    'MARKET_ID',
    'MARKET_NAME',
    'MARKET_CODE',

    # Company number
    'COMPANY_NUMBER_MIN_LENGTH',
    'COMPANY_NUMBER_MAX_LENGTH',
    'COMPANY_NUMBER_PATTERN',
    'PREFIX_SCOTLAND',
    'PREFIX_NORTHERN_IRELAND',

    # Filing types
    'FILING_TYPE_FULL_ACCOUNTS',
    'FILING_TYPE_ABRIDGED_ACCOUNTS',
    'CATEGORY_ACCOUNTS',

    # Standards
    'VALID_STANDARDS',

    # API config
    'DEFAULT_TIMEOUT',
    'RATE_LIMIT_REQUESTS',
    'RATE_LIMIT_WINDOW',
    'MAX_RETRIES',

    # File formats
    'FORMAT_IXBRL',
    'FORMAT_PRIORITY',

    # Messages
    'MSG_ENTER_COMPANY_NUMBER',
    'MSG_COMPANY_NOT_FOUND',

    # Error codes
    'ERR_INVALID_COMPANY_NUMBER',
    'ERR_COMPANY_NOT_FOUND',
]
