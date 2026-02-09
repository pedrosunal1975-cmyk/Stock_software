# Path: searcher/constants.py
"""
Searcher Module Constants

Module-wide constants for search operations.
Market-specific constants go in markets/{market}/constants.py
"""

# Status Values
STATUS_PENDING: str = 'pending'
STATUS_COMPLETED: str = 'completed'
STATUS_FAILED: str = 'failed'
STATUS_IN_PROGRESS: str = 'in_progress'

# HTTP Status Codes
HTTP_OK: int = 200
HTTP_NOT_FOUND: int = 404
HTTP_TOO_MANY_REQUESTS: int = 429
HTTP_SERVER_ERROR: int = 500
HTTP_BAD_GATEWAY: int = 502
HTTP_SERVICE_UNAVAILABLE: int = 503
HTTP_GATEWAY_TIMEOUT: int = 504
RETRYABLE_STATUS_CODES: list[int] = [
    HTTP_TOO_MANY_REQUESTS,
    HTTP_SERVER_ERROR,
    HTTP_BAD_GATEWAY,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_GATEWAY_TIMEOUT
]

# IPO Logging Prefixes
LOG_INPUT: str = '[INPUT]'
LOG_PROCESS: str = '[PROCESS]'
LOG_OUTPUT: str = '[OUTPUT]'

# Logging Components
LOGGER_CORE: str = 'searcher.core'
LOGGER_ENGINE: str = 'searcher.engine'
LOGGER_MARKETS: str = 'searcher.markets'
LOGGER_CLI: str = 'searcher.cli'

# Log Format
LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT: str = '%Y-%m-%d %H:%M:%S'

# Response Dictionary Keys
KEY_FILING_URL: str = 'filing_url'
KEY_FORM_TYPE: str = 'form_type'
KEY_FILING_DATE: str = 'filing_date'
KEY_COMPANY_NAME: str = 'company_name'
KEY_ENTITY_ID: str = 'entity_id'
KEY_ACCESSION_NUMBER: str = 'accession_number'
KEY_MARKET_ID: str = 'market_id'
KEY_SEARCH_METADATA: str = 'search_metadata'

# Search Parameters
MIN_RESULTS: int = 1
MAX_RESULTS: int = 10

# Market Identifiers
MARKET_SEC: str = 'sec'
MARKET_UK_FRC: str = 'uk_frc'  # UK Companies House
MARKET_ESEF: str = 'esef'  # ESEF/UKSEF via filings.xbrl.org
SUPPORTED_MARKETS: list = [MARKET_SEC, MARKET_UK_FRC, MARKET_ESEF]

# Market Display Names
MARKET_NAMES: dict = {
    MARKET_SEC: 'SEC (United States)',
    MARKET_UK_FRC: 'Companies House (United Kingdom)',
    MARKET_ESEF: 'ESEF (European Single Electronic Format)'
}

# Market Seed Data for Database
MARKETS_SEED_DATA: list[dict] = [
    {
        'market_id': MARKET_SEC,
        'market_name': 'U.S. Securities and Exchange Commission',
        'market_country': 'USA',
        'api_base_url': 'https://data.sec.gov',
        'is_active': True,
        'rate_limit_per_minute': 10,
        'user_agent_required': True
    },
    {
        'market_id': MARKET_UK_FRC,
        'market_name': 'UK Companies House',
        'market_country': 'GBR',
        'api_base_url': 'https://api.companieshouse.gov.uk',
        'is_active': True,
        'rate_limit_per_minute': 120,
        'user_agent_required': False
    },
    {
        'market_id': MARKET_ESEF,
        'market_name': 'ESEF - European Single Electronic Format',
        'market_country': 'EUR',
        'api_base_url': 'https://filings.xbrl.org',
        'is_active': True,
        'rate_limit_per_minute': 60,
        'user_agent_required': False
    }
]

__all__ = [
    'STATUS_PENDING',
    'STATUS_COMPLETED',
    'STATUS_FAILED',
    'STATUS_IN_PROGRESS',
    'HTTP_OK',
    'HTTP_NOT_FOUND',
    'HTTP_TOO_MANY_REQUESTS',
    'HTTP_SERVER_ERROR',
    'HTTP_BAD_GATEWAY',
    'HTTP_SERVICE_UNAVAILABLE',
    'HTTP_GATEWAY_TIMEOUT',
    'RETRYABLE_STATUS_CODES',
    'LOG_INPUT',
    'LOG_PROCESS',
    'LOG_OUTPUT',
    'LOGGER_CORE',
    'LOGGER_ENGINE',
    'LOGGER_MARKETS',
    'LOGGER_CLI',
    'LOG_FORMAT',
    'LOG_DATE_FORMAT',
    'KEY_FILING_URL',
    'KEY_FORM_TYPE',
    'KEY_FILING_DATE',
    'KEY_COMPANY_NAME',
    'KEY_ENTITY_ID',
    'KEY_ACCESSION_NUMBER',
    'KEY_MARKET_ID',
    'KEY_SEARCH_METADATA',
    'MIN_RESULTS',
    'MAX_RESULTS',
    'MARKET_SEC',
    'MARKET_UK_FRC',
    'MARKET_ESEF',
    'SUPPORTED_MARKETS',
    'MARKET_NAMES',
    'MARKETS_SEED_DATA',
]