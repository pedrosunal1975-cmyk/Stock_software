# Path: searcher/markets/sec/constants.py
"""
SEC Market Constants

SEC-specific constants for form types, patterns, API field names, and HTTP codes.
URLs, timeouts, and paths are in env file and loaded by config_loader.
"""

# CIK Format
CIK_LENGTH: int = 10
CIK_PADDING_CHAR: str = '0'

# XBRL ZIP File Patterns (Priority Order)
XBRL_ZIP_SUFFIXES: list[str] = [
    '_htm.zip',      # Most common pattern (highest priority)
    '_xbrl.zip',     # Alternative XBRL pattern
    '-xbrl.zip',     # Alternative with dash
    'r2.zip',        # Revision 2 pattern
    '.zip'           # Generic fallback (lowest priority)
]

# Minimum JSON size for valid index.json files
MIN_JSON_SIZE_BYTES: int = 500

# Retry Configuration
DEFAULT_MAX_RETRIES: int = 3

# Historical Constants
SEC_FOUNDING_YEAR: int = 1934  # Year SEC was established

# ============================================================================
# HTTP Status Codes
# ============================================================================

# Success codes
HTTP_OK: int = 200

# Client error codes
HTTP_BAD_REQUEST: int = 400
HTTP_UNAUTHORIZED: int = 401
HTTP_FORBIDDEN: int = 403
HTTP_NOT_FOUND: int = 404
HTTP_TOO_MANY_REQUESTS: int = 429

# Server error codes
HTTP_INTERNAL_SERVER_ERROR: int = 500
HTTP_BAD_GATEWAY: int = 502
HTTP_SERVICE_UNAVAILABLE: int = 503
HTTP_GATEWAY_TIMEOUT: int = 504

# ============================================================================
# SEC Form Types
# ============================================================================

FORM_10K: str = '10-K'
FORM_10K_A: str = '10-K/A'
FORM_10Q: str = '10-Q'
FORM_10Q_A: str = '10-Q/A'
FORM_8K: str = '8-K'
FORM_8K_A: str = '8-K/A'
FORM_20F: str = '20-F'
FORM_6K: str = '6-K'
FORM_DEF14A: str = 'DEF 14A'
FORM_S1: str = 'S-1'
FORM_S3: str = 'S-3'
FORM_S4: str = 'S-4'
FORM_424B2: str = '424B2'
FORM_424B5: str = '424B5'

# Filing Categories
ANNUAL_FILINGS: list[str] = [FORM_10K, FORM_10K_A, FORM_20F]
QUARTERLY_FILINGS: list[str] = [FORM_10Q, FORM_10Q_A]
CURRENT_FILINGS: list[str] = [FORM_8K, FORM_8K_A, FORM_6K]
MAJOR_FILING_TYPES: list[str] = ANNUAL_FILINGS + QUARTERLY_FILINGS + CURRENT_FILINGS

# Form Type Aliases (Flexible Input → Official Format)
FORM_TYPE_ALIASES: dict[str, str] = {
    '10k': FORM_10K,
    '10-k': FORM_10K,
    '10_k': FORM_10K,
    '10 k': FORM_10K,
    '10q': FORM_10Q,
    '10-q': FORM_10Q,
    '10_q': FORM_10Q,
    '10 q': FORM_10Q,
    '20f': FORM_20F,
    '20-f': FORM_20F,
    '20_f': FORM_20F,
    '20 f': FORM_20F,
    '8k': FORM_8K,
    '8-k': FORM_8K,
    '8_k': FORM_8K,
    '8 k': FORM_8K,
    's1': FORM_S1,
    's-1': FORM_S1,
    's_1': FORM_S1,
    's 1': FORM_S1,
    's3': FORM_S3,
    's-3': FORM_S3,
    's4': FORM_S4,
    's-4': FORM_S4,
    'def14a': FORM_DEF14A,
    'def 14a': FORM_DEF14A,
    'def-14a': FORM_DEF14A,
    'def_14a': FORM_DEF14A,
}

# Form Type Descriptions (For CLI Display)
FORM_TYPE_DESCRIPTIONS: dict[str, str] = {
    FORM_10K: 'Annual report',
    FORM_10Q: 'Quarterly report',
    FORM_20F: 'Foreign issuer annual report',
    FORM_8K: 'Current report',
    FORM_DEF14A: 'Proxy statement',
    FORM_S1: 'IPO registration',
    FORM_10K_A: 'Annual report (amended)',
    FORM_10Q_A: 'Quarterly report (amended)',
    FORM_S3: 'Registration statement',
    FORM_S4: 'Registration statement (merger)',
    FORM_424B2: 'Prospectus',
    FORM_424B5: 'Prospectus supplement'
}

# Validation Patterns
CIK_PATTERN: str = r'^\d{1,10}$'
TICKER_PATTERN: str = r'^[A-Z]{1,5}$'

# CLI Prompt Messages
CLI_COMPANY_PROMPT: str = """SEC Company Identifier:
  You can enter either:
    * Stock ticker (e.g., AAPL, MSFT, GOOGL)
    * CIK number (e.g., 0000320193 for Apple)
"""

CLI_FORM_TYPE_PROMPT: str = """SEC Filing Types:
  Common types:
    10-K   = Annual report
    10-Q   = Quarterly report
    20-F   = Foreign issuer annual report
    8-K    = Current report
    DEF 14A = Proxy statement
    S-1    = IPO registration
"""

# Error Messages
ERROR_INVALID_CIK: str = 'Invalid CIK format'
ERROR_INVALID_TICKER: str = 'Invalid ticker format'
ERROR_COMPANY_NOT_FOUND: str = 'Company not found'
ERROR_NO_FILINGS: str = 'No filings found'
ERROR_NO_ZIP: str = 'No XBRL ZIP file found in filing'
ERROR_API_FAILED: str = 'SEC API request failed'

# HTTP Headers
HEADER_USER_AGENT: str = 'User-Agent'
HEADER_ACCEPT: str = 'Accept'
HEADER_ACCEPT_ENCODING: str = 'Accept-Encoding'

__all__ = [
    # CIK Constants
    'CIK_LENGTH',
    'CIK_PADDING_CHAR',
    # ZIP Patterns
    'XBRL_ZIP_SUFFIXES',
    'MIN_JSON_SIZE_BYTES',
    # Retry Configuration
    'DEFAULT_MAX_RETRIES',
    # Historical
    'SEC_FOUNDING_YEAR',
    # HTTP Status Codes
    'HTTP_OK',
    'HTTP_BAD_REQUEST',
    'HTTP_UNAUTHORIZED',
    'HTTP_FORBIDDEN',
    'HTTP_NOT_FOUND',
    'HTTP_TOO_MANY_REQUESTS',
    'HTTP_INTERNAL_SERVER_ERROR',
    'HTTP_BAD_GATEWAY',
    'HTTP_SERVICE_UNAVAILABLE',
    'HTTP_GATEWAY_TIMEOUT',
    # Form Types
    'FORM_10K',
    'FORM_10K_A',
    'FORM_10Q',
    'FORM_10Q_A',
    'FORM_8K',
    'FORM_8K_A',
    'FORM_20F',
    'FORM_6K',
    'FORM_DEF14A',
    'FORM_S1',
    'FORM_S3',
    'FORM_S4',
    'FORM_424B2',
    'FORM_424B5',
    'ANNUAL_FILINGS',
    'QUARTERLY_FILINGS',
    'CURRENT_FILINGS',
    'MAJOR_FILING_TYPES',
    'FORM_TYPE_ALIASES',
    'FORM_TYPE_DESCRIPTIONS',
    # Validation
    'CIK_PATTERN',
    'TICKER_PATTERN',
    # CLI Messages
    'CLI_COMPANY_PROMPT',
    'CLI_FORM_TYPE_PROMPT',
    # Error Messages
    'ERROR_INVALID_CIK',
    'ERROR_INVALID_TICKER',
    'ERROR_COMPANY_NOT_FOUND',
    'ERROR_NO_FILINGS',
    'ERROR_NO_ZIP',
    'ERROR_API_FAILED',
    # HTTP Headers
    'HEADER_USER_AGENT',
    'HEADER_ACCEPT',
    'HEADER_ACCEPT_ENCODING',
]
