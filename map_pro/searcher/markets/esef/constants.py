# Path: searcher/markets/esef/constants.py
"""
ESEF Market Constants

Constants for filings.xbrl.org API (ESEF/UKSEF filings).
NO HARDCODING in other files - all values come from here or config.
"""

# ==============================================================================
# MARKET IDENTIFICATION
# ==============================================================================

MARKET_ID = "esef"
MARKET_NAME = "ESEF - European Single Electronic Format"
MARKET_CODE = "ESEF"

# ==============================================================================
# SUPPORTED COUNTRIES
# ==============================================================================

# ISO 3166-1 alpha-2 country codes supported by filings.xbrl.org
COUNTRY_UK = "GB"
COUNTRY_GERMANY = "DE"
COUNTRY_FRANCE = "FR"
COUNTRY_NETHERLANDS = "NL"
COUNTRY_ITALY = "IT"
COUNTRY_SPAIN = "ES"
COUNTRY_SWEDEN = "SE"
COUNTRY_DENMARK = "DK"
COUNTRY_NORWAY = "NO"
COUNTRY_FINLAND = "FI"
COUNTRY_BELGIUM = "BE"
COUNTRY_AUSTRIA = "AT"
COUNTRY_IRELAND = "IE"
COUNTRY_PORTUGAL = "PT"
COUNTRY_POLAND = "PL"

# List of all supported countries for validation
SUPPORTED_COUNTRIES = [
    COUNTRY_UK,
    COUNTRY_GERMANY,
    COUNTRY_FRANCE,
    COUNTRY_NETHERLANDS,
    COUNTRY_ITALY,
    COUNTRY_SPAIN,
    COUNTRY_SWEDEN,
    COUNTRY_DENMARK,
    COUNTRY_NORWAY,
    COUNTRY_FINLAND,
    COUNTRY_BELGIUM,
    COUNTRY_AUSTRIA,
    COUNTRY_IRELAND,
    COUNTRY_PORTUGAL,
    COUNTRY_POLAND,
]

# Country display names
COUNTRY_NAMES = {
    COUNTRY_UK: "United Kingdom",
    COUNTRY_GERMANY: "Germany",
    COUNTRY_FRANCE: "France",
    COUNTRY_NETHERLANDS: "Netherlands",
    COUNTRY_ITALY: "Italy",
    COUNTRY_SPAIN: "Spain",
    COUNTRY_SWEDEN: "Sweden",
    COUNTRY_DENMARK: "Denmark",
    COUNTRY_NORWAY: "Norway",
    COUNTRY_FINLAND: "Finland",
    COUNTRY_BELGIUM: "Belgium",
    COUNTRY_AUSTRIA: "Austria",
    COUNTRY_IRELAND: "Ireland",
    COUNTRY_PORTUGAL: "Portugal",
    COUNTRY_POLAND: "Poland",
}

# ==============================================================================
# FILING/REPORT TYPES
# ==============================================================================

# Report types from filings.xbrl.org API
REPORT_TYPE_AFR = "AFR"  # Annual Financial Report
REPORT_TYPE_SFR = "SFR"  # Semi-annual Financial Report
REPORT_TYPE_IFR = "IFR"  # Interim Financial Report
REPORT_TYPE_QFR = "QFR"  # Quarterly Financial Report

# Valid report types
VALID_REPORT_TYPES = [
    REPORT_TYPE_AFR,
    REPORT_TYPE_SFR,
    REPORT_TYPE_IFR,
    REPORT_TYPE_QFR,
]

# Report type descriptions
REPORT_TYPE_DESCRIPTIONS = {
    REPORT_TYPE_AFR: "Annual Financial Report",
    REPORT_TYPE_SFR: "Semi-annual Financial Report",
    REPORT_TYPE_IFR: "Interim Financial Report",
    REPORT_TYPE_QFR: "Quarterly Financial Report",
}

# Form type aliases for user input normalization
FORM_TYPE_ALIASES = {
    # Annual
    "annual": REPORT_TYPE_AFR,
    "afr": REPORT_TYPE_AFR,
    "yearly": REPORT_TYPE_AFR,
    "10-k": REPORT_TYPE_AFR,  # SEC equivalent
    "10k": REPORT_TYPE_AFR,
    # Semi-annual
    "semiannual": REPORT_TYPE_SFR,
    "semi-annual": REPORT_TYPE_SFR,
    "sfr": REPORT_TYPE_SFR,
    "half-year": REPORT_TYPE_SFR,
    "halfyear": REPORT_TYPE_SFR,
    # Interim
    "interim": REPORT_TYPE_IFR,
    "ifr": REPORT_TYPE_IFR,
    # Quarterly
    "quarterly": REPORT_TYPE_QFR,
    "qfr": REPORT_TYPE_QFR,
    "10-q": REPORT_TYPE_QFR,  # SEC equivalent
    "10q": REPORT_TYPE_QFR,
}

# ==============================================================================
# JSON-API FIELD NAMES
# ==============================================================================

# Top-level response keys
KEY_DATA = "data"
KEY_INCLUDED = "included"
KEY_LINKS = "links"
KEY_META = "meta"

# Filing attributes (from API response)
ATTR_FILING_ID = "id"
ATTR_FILING_TYPE = "type"
ATTR_ATTRIBUTES = "attributes"
ATTR_RELATIONSHIPS = "relationships"

# Filing attribute fields
FIELD_COUNTRY = "country"
FIELD_DATE_ADDED = "date_added"
FIELD_PERIOD_END = "period_end"
FIELD_REPORT_URL = "report_url"
FIELD_VIEWER_URL = "viewer_url"
FIELD_JSON_URL = "json_url"
FIELD_PACKAGE_URL = "package_url"
FIELD_REPORT_TYPE = "report_type"
FIELD_OAM_ID = "oam_id"
FIELD_LEI = "lei"
FIELD_ENTITY_NAME = "entity_name"
FIELD_PROCESSED = "processed"

# Entity relationship fields
FIELD_ENTITY = "entity"
FIELD_ENTITY_ID = "entity_id"
FIELD_ENTITY_DATA = "data"

# Pagination fields
FIELD_PAGE_NUMBER = "page[number]"
FIELD_PAGE_SIZE = "page[size]"
FIELD_TOTAL_PAGES = "total_pages"
FIELD_TOTAL_COUNT = "total_count"

# ==============================================================================
# API CONFIGURATION
# ==============================================================================

# Timeouts (seconds)
DEFAULT_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 120

# Rate limits
RATE_LIMIT_REQUESTS = 60  # Requests per minute (conservative)
RATE_LIMIT_WINDOW = 60  # Window in seconds

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # Seconds
BACKOFF_FACTOR = 2  # Exponential backoff multiplier

# Pagination defaults
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

# ==============================================================================
# HTTP STATUS CODES
# ==============================================================================

HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR = 500

# ==============================================================================
# FILE FORMATS
# ==============================================================================

# Supported document formats from filings.xbrl.org
FORMAT_IXBRL = "application/xhtml+xml"
FORMAT_ZIP = "application/zip"
FORMAT_JSON = "application/json"

# File extensions
EXT_XHTML = ".xhtml"
EXT_HTML = ".html"
EXT_ZIP = ".zip"
EXT_JSON = ".json"

# ==============================================================================
# URL PATTERNS
# ==============================================================================

# filings.xbrl.org base URL (loaded from config, this is fallback)
DEFAULT_BASE_URL = "https://filings.xbrl.org"

# API endpoints
ENDPOINT_FILINGS = "/api/filings"
ENDPOINT_ENTITIES = "/api/entities"

# ==============================================================================
# CLI/UI MESSAGES
# ==============================================================================

MSG_ENTER_IDENTIFIER = "Enter company identifier (LEI, name, or ticker)"
MSG_ENTER_COUNTRY = "Enter country code (e.g., GB, DE, FR)"
MSG_INVALID_COUNTRY = "Invalid country code"
MSG_COMPANY_NOT_FOUND = "Company not found in ESEF filings"
MSG_NO_FILINGS_FOUND = "No filings found for this company"
MSG_RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Waiting..."

# ==============================================================================
# ERROR CODES
# ==============================================================================

ERR_INVALID_COUNTRY = "ESEF001"
ERR_COMPANY_NOT_FOUND = "ESEF002"
ERR_NO_FILINGS = "ESEF003"
ERR_API_ERROR = "ESEF004"
ERR_RATE_LIMIT = "ESEF005"
ERR_DOWNLOAD_FAILED = "ESEF006"
ERR_INVALID_REPORT_TYPE = "ESEF007"

# ==============================================================================
# IDENTIFIER PATTERNS
# ==============================================================================

# LEI (Legal Entity Identifier) pattern - 20 alphanumeric characters
LEI_PATTERN = r'^[A-Z0-9]{20}$'
LEI_LENGTH = 20

# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    # Market identification
    'MARKET_ID',
    'MARKET_NAME',
    'MARKET_CODE',

    # Countries
    'COUNTRY_UK',
    'COUNTRY_GERMANY',
    'COUNTRY_FRANCE',
    'SUPPORTED_COUNTRIES',
    'COUNTRY_NAMES',

    # Report types
    'REPORT_TYPE_AFR',
    'REPORT_TYPE_SFR',
    'VALID_REPORT_TYPES',
    'REPORT_TYPE_DESCRIPTIONS',
    'FORM_TYPE_ALIASES',

    # JSON-API fields
    'KEY_DATA',
    'KEY_INCLUDED',
    'ATTR_ATTRIBUTES',
    'FIELD_COUNTRY',
    'FIELD_PERIOD_END',
    'FIELD_REPORT_URL',
    'FIELD_LEI',
    'FIELD_ENTITY_NAME',

    # API config
    'DEFAULT_TIMEOUT',
    'RATE_LIMIT_REQUESTS',
    'MAX_RETRIES',
    'DEFAULT_PAGE_SIZE',
    'MAX_PAGE_SIZE',

    # HTTP
    'HTTP_OK',
    'HTTP_NOT_FOUND',
    'HTTP_TOO_MANY_REQUESTS',

    # Formats
    'FORMAT_IXBRL',
    'FORMAT_ZIP',

    # URLs
    'DEFAULT_BASE_URL',
    'ENDPOINT_FILINGS',

    # Messages
    'MSG_ENTER_IDENTIFIER',
    'MSG_COMPANY_NOT_FOUND',
    'MSG_NO_FILINGS_FOUND',

    # Errors
    'ERR_INVALID_COUNTRY',
    'ERR_COMPANY_NOT_FOUND',
    'ERR_NO_FILINGS',

    # Patterns
    'LEI_PATTERN',
    'LEI_LENGTH',
]
