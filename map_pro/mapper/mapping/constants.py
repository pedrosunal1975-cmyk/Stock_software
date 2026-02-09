# Path: mapping/constants.py
"""
Mapping Constants - Market Agnostic Configuration

CRITICAL DATA SOURCE HIERARCHY:
===============================
1. PRIMARY:   XBRL Filing (roleType definitions, presentation networks, taxonomy)
2. SECONDARY: Standard Taxonomy (if filing explicitly declares to use it)
3. FALLBACK:  Heuristics below (ONLY for enhancement, NOT primary classification)

DESIGN PHILOSOPHY:
=================
- READ AS-IS: Accept what company declares in their XBRL filing
- MARKET AGNOSTIC: No assumptions about US GAAP, IFRS, or any specific taxonomy
- TAXONOMY AGNOSTIC: Works with any valid XBRL taxonomy
- FALLBACK ONLY: Patterns below used ONLY when taxonomy data unavailable

 CRITICAL WARNING:
The statement classification patterns below should NEVER be used as the
PRIMARY classification method. They exist ONLY as FALLBACK when:
1. Taxonomy roleType definitions are missing/unclear
2. Structural analysis is inconclusive
3. System needs human-friendly categorization

When patterns are used, system MUST log a warning that taxonomy data was unavailable.

NO BUSINESS LOGIC HERE - only constant definitions for configuration.
"""


# ============================================================================
# METADATA KEY VARIATIONS (Discovery Patterns - Keep)
# ============================================================================
# Different companies use different metadata key names
# These patterns help DISCOVER various naming conventions
# Add new variations as discovered in filings

# Period End Date Variations
PERIOD_END_METADATA_KEYS: list[str] = [
    'period_end_date',          # SEC standard
    'period_end',               # Common variation
    'end_date',                 # Simple form
    'fiscal_period_end',        # Fiscal year terminology
    'reporting_period_end',     # Reporting terminology
    'document_period_end_date', # Full form
    'fiscal_year_end',          # Annual reports
    'report_end_date',          # Report terminology
    'balance_sheet_date',       # Balance sheet specific
    'statement_date',           # Financial statement date
]

# XBRL concept names for period end
PERIOD_END_XBRL_CONCEPTS: list[str] = [
    'DocumentPeriodEndDate',
    'PeriodEndDate',
    'ReportingPeriodEndDate',
    'FiscalPeriodEndDate',
    'BalanceSheetDate',
    'StatementDate',
    'CurrentReportingPeriodEndDate',
]

# Filing Date Variations
FILING_DATE_METADATA_KEYS: list[str] = [
    'filing_date',
    'document_date',
    'submission_date',
    'report_date',
    'publication_date',
]

FILING_DATE_XBRL_CONCEPTS: list[str] = [
    'DocumentDate',
    'FilingDate',
    'DocumentCreationDate',
    'ReportDate',
]

# Entity Identifier Variations
ENTITY_IDENTIFIER_METADATA_KEYS: list[str] = [
    'entity_identifier',
    'cik',
    'central_index_key',
    'company_id',
    'entity_id',
    'registration_number',
]

ENTITY_IDENTIFIER_XBRL_CONCEPTS: list[str] = [
    'EntityCentralIndexKey',
    'CentralIndexKey',
    'EntityIdentifier',
    'CompanyIdentifier',
]

# Entity Name Variations
ENTITY_NAME_METADATA_KEYS: list[str] = [
    'entity_name',
    'company_name',
    'registrant_name',
    'issuer_name',
    'entity_registrant_name',
]

ENTITY_NAME_XBRL_CONCEPTS: list[str] = [
    'EntityRegistrantName',
    'RegistrantName',
    'EntityName',
    'CompanyName',
]

# ============================================================================
# OUTPUT CONFIGURATION (Operational - Keep)
# ============================================================================

# Format subdirectories created under each period folder
OUTPUT_FORMAT_DIRECTORIES: list[str] = [
    'json',
    'csv',
    'excel',
]

# Directory patterns to ignore when searching
IGNORE_DIRECTORY_PATTERNS: list[str] = [
    '.',      # Hidden directories
    '__',     # Python cache
    '.git',   # Version control
    '.venv',  # Virtual environments
]

# Standard subdirectory name for filings
FILINGS_SUBDIRECTORY: str = 'filings'

# ============================================================================
# DATE HANDLING (Universal - Keep)
# ============================================================================

# Date format separators
DATE_SEPARATORS: list[str] = [
    '-',  # ISO format: 2025-10-13
    '/',  # Alternative: 2025/10/13
    'T',  # ISO datetime separator: 2025-10-13T00:00:00
]

# Valid year range for period dates
YEAR_MIN: int = 1900
YEAR_MAX: int = 2100

# ============================================================================
# FILENAME HANDLING (Operational - Keep)
# ============================================================================

# Characters to replace in filenames
FILENAME_SPACE_REPLACEMENT: str = '_'
FILENAME_DASH_REPLACEMENT: str = '_'

# Maximum length for folder/file names
MAX_ENTITY_NAME_LENGTH: int = 50
MAX_FILENAME_LENGTH: int = 100

# Default fallback names
DEFAULT_ENTITY_NAME: str = 'unknown'
DEFAULT_STATEMENT_NAME: str = 'statement'

# ============================================================================
# OPERATIONAL LIMITS (Keep)
# ============================================================================

# Maximum number of facts to search when looking for metadata
MAX_FACTS_TO_SEARCH: int = 200

# Delimiter used in parsed folder names
PARSED_FOLDER_DELIMITER: str = '__'

# Debug logging separator
DEBUG_SEPARATOR: str = '=' * 60

# Filing type character replacements
FILING_TYPE_REPLACEMENTS = {
    '-': '_',  # 10-K  10_K
}

# ============================================================================
# NETWORK CLASSIFICATION - STRUCTURAL HEURISTICS
# ============================================================================

#  IMPORTANT: These are HEURISTICS, not requirements!
# Companies can have any structure - these are guidelines only
# Used AFTER reading from taxonomy, NEVER instead of taxonomy

# Core statements typically have substantive fact counts
# BUT: Small companies may have fewer, complex companies more
# This is a HEURISTIC for "likely core vs detail" distinction
CORE_STATEMENT_MIN_FACTS = 15  # Lowered from 100 - too restrictive

# Core statements typically have shallow hierarchies (broad aggregation)
# Details have deep hierarchies (narrow focus)
# This is a HEURISTIC, not a rule
CORE_STATEMENT_MAX_DEPTH = 6

# Core statements typically have one abstract root concept
# This is a HEURISTIC based on common practice
CORE_STATEMENT_MIN_ROOTS = 1

# Confidence thresholds for classification
CONFIDENCE_HIGH_THRESHOLD = 0.8    # 80%+ confidence
CONFIDENCE_MEDIUM_THRESHOLD = 0.5  # 50-80% confidence

# ============================================================================
# EXCLUSION HEURISTICS (Fallback patterns - Use with caution)
# ============================================================================

#  USAGE RULES:
# PRIMARY:   Read roleType definition from taxonomy schema
# SECONDARY: Analyze roleType usedOn attribute
# FALLBACK:  Use patterns below ONLY if taxonomy unavailable + LOG WARNING

# These keywords commonly indicate supporting schedules (not primary statements)
# UNIVERSAL across markets - these patterns work in SEC, FRC, ESMA filings
# BUT: Always read from taxonomy first!

DETAIL_INDICATORS = [
    'Details',      # Most common suffix for detail schedules
    'Schedule',     # Tabular supporting information
    'Schedules',    # Plural form
    'Narrative',    # Textual disclosures
]

TABLE_INDICATORS = [
    'Tables',       # Grouped tabular data
    'Tabular',      # Tabular presentation
]

POLICY_INDICATORS = [
    'Policies',                         # Generic policies
    'AccountingPolicies',               # Full form
    'SignificantAccountingPolicies',    # SEC common form
]

PARENTHETICAL_INDICATOR = 'Parenthetical'  # Supplementary to main statement

DOCUMENT_INDICATORS = [
    'DocumentAndEntityInformation',
    'CoverPage',
    'Document',
    'Cover',
]

# ============================================================================
# STATEMENT TYPE FALLBACK PATTERNS ( FALLBACK ONLY - NOT PRIMARY!)
# ============================================================================

#  CRITICAL WARNING 
# 
# These patterns should NEVER be the PRIMARY method for statement classification!
#
# CORRECT USAGE FLOW:
# 1. Read roleType definition from filing's taxonomy schema
# 2. Parse roleType/definition text for statement type indicators
# 3. Analyze presentation network structure
# 4. ONLY IF ABOVE FAIL: Use patterns below + LOG WARNING
#
# When patterns are used, system MUST:
# - Log warning: "Used fallback pattern for role {uri} - taxonomy unavailable"
# - Include in output metadata: classification_source = "fallback_pattern"
# - Report lower confidence score
#
# These patterns exist for:
# - Filings with incomplete taxonomy definitions
# - Human-friendly categorization when taxonomy unclear
# - Diagnostics and quality monitoring
#
# They DO NOT exist for:
# - Primary classification logic
# - Bypassing taxonomy reading
# - Assuming statement structure

# Balance Sheet / Statement of Financial Position patterns
# These are BROAD to catch both core statements AND detail schedules
BALANCE_SHEET_FALLBACK_PATTERNS = [
    # Core statement indicators
    'FinancialPosition',
    'BalanceSheet',
    'BalanceSheets',
    'StatementOfFinancialPosition',
    # Component indicators (detail schedules)
    'Property',
    'Equipment',
    'Asset',
    'Liability',
    'Inventory',
    'Investment',
    'Debt',
    'Payable',
    'Receivable',
    'Goodwill',
    'Intangible',
]

# Income Statement / Statement of Operations patterns
INCOME_STATEMENT_FALLBACK_PATTERNS = [
    # Core statement indicators
    'Income',
    'Operations',
    'Comprehensive',
    'EarningsStatement',
    'ProfitAndLoss',
    'StatementOfIncome',
    'StatementOfOperations',
    # Component indicators (detail schedules)
    'Revenue',
    'Sales',
    'Expense',
    'Cost',
    'Earning',
]

# Cash Flow Statement patterns
CASH_FLOW_FALLBACK_PATTERNS = [
    'CashFlow',
    'CashFlows',
    'StatementOfCashFlow',
]

# Equity / Changes in Equity patterns
EQUITY_FALLBACK_PATTERNS = [
    'Equity',
    'Stockholders',
    'Shareholders',
    'ChangesInEquity',
    'StatementOfStockholdersEquity',
    'StatementOfShareholdersEquity',
]

# ============================================================================
# CLASSIFICATION ENUMERATIONS (Keep - These are categorical types)
# ============================================================================

class NetworkCategory:
    """Network category classifications."""
    CORE_STATEMENT = 'CORE_STATEMENT'
    DETAIL = 'DETAIL'
    TABLE = 'TABLE'
    POLICY = 'POLICY'
    PARENTHETICAL = 'PARENTHETICAL'
    DOCUMENT = 'DOCUMENT'
    UNKNOWN = 'UNKNOWN'


class StatementType:
    """Statement type classifications."""
    BALANCE_SHEET = 'BALANCE_SHEET'
    INCOME_STATEMENT = 'INCOME_STATEMENT'
    CASH_FLOW = 'CASH_FLOW'
    EQUITY = 'EQUITY'
    COMPREHENSIVE_INCOME = 'COMPREHENSIVE_INCOME'
    NOTES = 'NOTES'
    OTHER = 'OTHER'
    UNKNOWN = 'UNKNOWN'


class ConfidenceLevel:
    """Classification confidence levels."""
    HIGH = 'HIGH'        # From taxonomy definition (primary source)
    MEDIUM = 'MEDIUM'    # From structural analysis (secondary)
    LOW = 'LOW'          # From fallback patterns (tertiary)


# ============================================================================
# EXPORT ALL
# ============================================================================

__all__ = [
    # Metadata Discovery
    'PERIOD_END_METADATA_KEYS',
    'PERIOD_END_XBRL_CONCEPTS',
    'FILING_DATE_METADATA_KEYS',
    'FILING_DATE_XBRL_CONCEPTS',
    'ENTITY_IDENTIFIER_METADATA_KEYS',
    'ENTITY_IDENTIFIER_XBRL_CONCEPTS',
    'ENTITY_NAME_METADATA_KEYS',
    'ENTITY_NAME_XBRL_CONCEPTS',
    
    # Output Configuration
    'OUTPUT_FORMAT_DIRECTORIES',
    'IGNORE_DIRECTORY_PATTERNS',
    'FILINGS_SUBDIRECTORY',
    
    # Date Handling
    'DATE_SEPARATORS',
    'YEAR_MIN',
    'YEAR_MAX',
    
    # Filename Handling
    'FILENAME_SPACE_REPLACEMENT',
    'FILENAME_DASH_REPLACEMENT',
    'MAX_ENTITY_NAME_LENGTH',
    'MAX_FILENAME_LENGTH',
    'DEFAULT_ENTITY_NAME',
    'DEFAULT_STATEMENT_NAME',
    
    # Operational
    'MAX_FACTS_TO_SEARCH',
    'PARSED_FOLDER_DELIMITER',
    'DEBUG_SEPARATOR',
    'FILING_TYPE_REPLACEMENTS',
    
    # Structural Heuristics
    'CORE_STATEMENT_MIN_FACTS',
    'CORE_STATEMENT_MAX_DEPTH',
    'CORE_STATEMENT_MIN_ROOTS',
    'CONFIDENCE_HIGH_THRESHOLD',
    'CONFIDENCE_MEDIUM_THRESHOLD',
    
    # Exclusion Heuristics (fallback)
    'DETAIL_INDICATORS',
    'TABLE_INDICATORS',
    'POLICY_INDICATORS',
    'PARENTHETICAL_INDICATOR',
    'DOCUMENT_INDICATORS',
    
    # Statement Type Fallback Patterns ( use with extreme caution)
    'BALANCE_SHEET_FALLBACK_PATTERNS',
    'INCOME_STATEMENT_FALLBACK_PATTERNS',
    'CASH_FLOW_FALLBACK_PATTERNS',
    'EQUITY_FALLBACK_PATTERNS',
    
    # Enumerations
    'NetworkCategory',
    'StatementType',
    'ConfidenceLevel',
]