# Path: xbrl_parser/market/constants.py
"""
Market-Specific Constants

Central repository for all market-specific validation constants.

ORGANIZATION:
- Each market has its own clearly marked section
- To modify a market: Find its section, make changes
- Changes to one market do NOT affect other markets
- NO HARDCODED values should exist in other market files

SUPPORTED MARKETS:
- US SEC (Securities and Exchange Commission)
- EU ESEF (European Single Electronic Format)
- UK FRC (Financial Reporting Council)
"""

# ==============================================================================
# MARKET IDENTIFIERS
# ==============================================================================

# Market identification codes
MARKET_US_SEC = "US_SEC"
MARKET_EU_ESEF = "EU_ESEF"
MARKET_UK_FRC = "UK_FRC"
MARKET_UNKNOWN = "UNKNOWN"

ALL_MARKETS = [MARKET_US_SEC, MARKET_EU_ESEF, MARKET_UK_FRC]

# ==============================================================================
# US SEC (Securities and Exchange Commission) CONSTANTS
# ==============================================================================

class US_SEC:
    """US SEC-specific constants - modify this section for SEC rules."""
    
    # Market identifier
    MARKET_ID = MARKET_US_SEC
    
    # Taxonomy namespaces (for detection)
    NAMESPACES = [
        "http://fasb.org/us-gaap/",
        "http://xbrl.sec.gov/",
        "http://xbrl.us/",
    ]
    
    # Required taxonomy elements
    REQUIRED_ELEMENTS = [
        "DocumentType",
        "EntityRegistrantName",
        "EntityCentralIndexKey",
    ]
    
    # Document types
    VALID_DOCUMENT_TYPES = [
        "10-K", "10-Q", "8-K", "20-F", "40-F",
        "S-1", "S-3", "S-4", "S-8",
        "DEF 14A", "DEFA14A",
        "485BPOS", "N-CSR", "N-Q"
    ]
    
    # CIK format validation
    CIK_LENGTH = 10
    CIK_PATTERN = r"^\d{10}$"
    
    # Filing date rules
    ALLOW_FUTURE_DATES = False
    MAX_PERIOD_LENGTH_DAYS = 395  # Slightly over 1 year for fiscal periods
    
    # Calculation validation
    REQUIRE_CALCULATION_LINKBASES = True
    ALLOW_CALCULATION_INCONSISTENCIES = False
    
    # Dimensional validation
    MAX_DIMENSIONS_PER_FACT = 8
    REQUIRE_TYPED_DIMENSIONS = False
    
    # Deprecated element warnings
    WARN_DEPRECATED_ELEMENTS = True
    DEPRECATED_TAXONOMY_YEARS = 3  # Warn if using taxonomy >3 years old
    
    # Error codes (SEC-specific)
    ERR_MISSING_CIK = "SEC_001"
    ERR_INVALID_CIK_FORMAT = "SEC_002"
    ERR_MISSING_DOCUMENT_TYPE = "SEC_003"
    ERR_INVALID_DOCUMENT_TYPE = "SEC_004"
    ERR_FUTURE_FILING_DATE = "SEC_005"
    ERR_PERIOD_TOO_LONG = "SEC_006"
    ERR_DEPRECATED_ELEMENT = "SEC_007"
    ERR_MISSING_REQUIRED_ELEMENT = "SEC_008"
    
    # Messages
    MSG_MISSING_CIK = "Missing required EntityCentralIndexKey"
    MSG_INVALID_CIK = "CIK must be 10 digits"
    MSG_MISSING_DOCTYPE = "Missing required DocumentType"
    MSG_INVALID_DOCTYPE = "Invalid document type for SEC filing"
    MSG_FUTURE_DATE = "Filing date cannot be in the future"
    MSG_PERIOD_TOO_LONG = "Period length exceeds maximum allowed"
    MSG_DEPRECATED = "Element from deprecated taxonomy version"
    MSG_MISSING_ELEMENT = "Missing required SEC element"


# ==============================================================================
# EU ESEF (European Single Electronic Format) CONSTANTS
# ==============================================================================

class EU_ESEF:
    """EU ESEF-specific constants - modify this section for ESEF rules."""
    
    # Market identifier
    MARKET_ID = MARKET_EU_ESEF
    
    # Taxonomy namespaces (for detection)
    NAMESPACES = [
        "http://xbrl.ifrs.org/taxonomy/",
        "http://www.esma.europa.eu/taxonomy/",
        "http://www.eurofiling.info/",
    ]
    
    # Required taxonomy elements
    REQUIRED_ELEMENTS = [
        "NameOfReportingEntityOrOtherMeansOfIdentification",
        "DomicileOfEntity",
        "LegalFormOfEntity",
    ]
    
    # ESEF filing requirements
    REQUIRE_INLINE_XBRL = True
    REQUIRE_EXTENSION_TAXONOMY = True
    
    # LEI validation (Legal Entity Identifier)
    LEI_LENGTH = 20
    LEI_PATTERN = r"^[A-Z0-9]{18}[0-9]{2}$"
    
    # Language requirements
    VALID_LANGUAGES = [
        "en", "de", "fr", "es", "it", "nl", "pl", "pt", "ro", "sv",
        "bg", "cs", "da", "el", "et", "fi", "ga", "hr", "hu", "lt",
        "lv", "mt", "sk", "sl"
    ]
    
    # Anchoring requirements (ESEF-specific)
    REQUIRE_ANCHORING = True
    MIN_ANCHORED_ELEMENTS_PERCENT = 80
    
    # Calculation validation
    REQUIRE_CALCULATION_LINKBASES = True
    ALLOW_CALCULATION_INCONSISTENCIES = False
    
    # Dimensional validation
    MAX_DIMENSIONS_PER_FACT = 10
    REQUIRE_TYPED_DIMENSIONS = False
    
    # XHTML requirements
    REQUIRE_XHTML_DOCUMENT = True
    VALID_XHTML_VERSION = "XHTML 1.0"
    
    # Error codes (ESEF-specific)
    ERR_MISSING_LEI = "ESEF_001"
    ERR_INVALID_LEI_FORMAT = "ESEF_002"
    ERR_MISSING_INLINE_XBRL = "ESEF_003"
    ERR_NO_EXTENSION_TAXONOMY = "ESEF_004"
    ERR_INVALID_LANGUAGE = "ESEF_005"
    ERR_INSUFFICIENT_ANCHORING = "ESEF_006"
    ERR_MISSING_XHTML = "ESEF_007"
    ERR_MISSING_REQUIRED_ELEMENT = "ESEF_008"
    
    # Messages
    MSG_MISSING_LEI = "Missing required Legal Entity Identifier"
    MSG_INVALID_LEI = "LEI must be 20 characters (18 alphanumeric + 2 digits)"
    MSG_NO_IXBRL = "ESEF filing must use Inline XBRL format"
    MSG_NO_EXTENSION = "ESEF filing requires extension taxonomy"
    MSG_INVALID_LANG = "Language not in ESEF supported list"
    MSG_LOW_ANCHORING = "Insufficient anchoring to IFRS taxonomy"
    MSG_NO_XHTML = "ESEF filing requires XHTML document"
    MSG_MISSING_ELEMENT = "Missing required ESEF element"


# ==============================================================================
# UK FRC (Financial Reporting Council) CONSTANTS
# ==============================================================================

class UK_FRC:
    """UK FRC-specific constants - modify this section for FRC rules."""
    
    # Market identifier
    MARKET_ID = MARKET_UK_FRC
    
    # Taxonomy namespaces (for detection)
    NAMESPACES = [
        "http://xbrl.frc.org.uk/",
        "http://www.xbrl.org/uk/",
        "http://www.companieshouse.gov.uk/",
    ]
    
    # Required taxonomy elements
    REQUIRED_ELEMENTS = [
        "EntityCurrentLegalOrRegisteredName",
        "EntityRegistrationNumber",
        "DateAuthorisationFinancialStatementsForIssue",
    ]
    
    # FRC filing requirements
    REQUIRE_INLINE_XBRL = True
    REQUIRE_COMPANIES_HOUSE_NUMBER = True
    
    # Companies House number validation
    CH_NUMBER_MIN_LENGTH = 6
    CH_NUMBER_MAX_LENGTH = 8
    CH_NUMBER_PATTERN = r"^[A-Z0-9]{6,8}$"
    
    # Accounting standards
    VALID_ACCOUNTING_STANDARDS = [
        "FRS 101", "FRS 102", "FRS 103", "FRS 104", "FRS 105",
        "IFRS", "UK GAAP"
    ]
    
    # Period requirements
    ALLOW_FUTURE_DATES = False
    MAX_PERIOD_LENGTH_DAYS = 395
    
    # Calculation validation
    REQUIRE_CALCULATION_LINKBASES = True
    ALLOW_CALCULATION_INCONSISTENCIES = False
    
    # Dimensional validation
    MAX_DIMENSIONS_PER_FACT = 8
    REQUIRE_TYPED_DIMENSIONS = False
    
    # Audit requirements
    REQUIRE_AUDIT_INFORMATION = True
    VALID_AUDIT_OPINIONS = [
        "Unqualified", "Qualified", "Adverse", "Disclaimer"
    ]
    
    # Error codes (FRC-specific)
    ERR_MISSING_CH_NUMBER = "FRC_001"
    ERR_INVALID_CH_NUMBER = "FRC_002"
    ERR_MISSING_AUTH_DATE = "FRC_003"
    ERR_INVALID_STANDARD = "FRC_004"
    ERR_FUTURE_AUTH_DATE = "FRC_005"
    ERR_MISSING_AUDIT_INFO = "FRC_006"
    ERR_INVALID_AUDIT_OPINION = "FRC_007"
    ERR_MISSING_REQUIRED_ELEMENT = "FRC_008"
    
    # Messages
    MSG_MISSING_CH = "Missing required Companies House number"
    MSG_INVALID_CH = "Companies House number must be 6-8 alphanumeric characters"
    MSG_MISSING_AUTH = "Missing required authorization date"
    MSG_INVALID_STANDARD = "Invalid accounting standard"
    MSG_FUTURE_AUTH = "Authorization date cannot be in the future"
    MSG_MISSING_AUDIT = "Missing required audit information"
    MSG_INVALID_OPINION = "Invalid audit opinion type"
    MSG_MISSING_ELEMENT = "Missing required FRC element"


# ==============================================================================
# MARKET DETECTION CONSTANTS
# ==============================================================================

# Detection priority (order matters)
DETECTION_PRIORITY = [MARKET_US_SEC, MARKET_EU_ESEF, MARKET_UK_FRC]

# Minimum confidence threshold for auto-detection (0.0-1.0)
MIN_DETECTION_CONFIDENCE = 0.25  # Lowered from 0.6 to allow detection with partial signals

# Detection signals and weights
NAMESPACE_MATCH_WEIGHT = 0.4
REQUIRED_ELEMENT_WEIGHT = 0.3
TAXONOMY_URL_WEIGHT = 0.2
IDENTIFIER_FORMAT_WEIGHT = 0.1

# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    # Market IDs
    'MARKET_US_SEC',
    'MARKET_EU_ESEF',
    'MARKET_UK_FRC',
    'MARKET_UNKNOWN',
    'ALL_MARKETS',
    
    # Market constant classes
    'US_SEC',
    'EU_ESEF',
    'UK_FRC',
    
    # Detection
    'DETECTION_PRIORITY',
    'MIN_DETECTION_CONFIDENCE',
    'NAMESPACE_MATCH_WEIGHT',
    'REQUIRED_ELEMENT_WEIGHT',
    'TAXONOMY_URL_WEIGHT',
    'IDENTIFIER_FORMAT_WEIGHT',
]