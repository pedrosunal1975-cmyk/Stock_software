# Path: mat_acc/constants.py
"""
System-Wide Constants for mat_acc (Mathematical Accountancy)

Central repository for all constant values used across the system.
NO HARDCODED VALUES in module code - all constants defined here.

Constants are organized by category:
- Statement Types
- Calculation Levels
- Confidence Levels
- Quality Ratings
- Severity Levels
- Status Codes
- File Extensions
- JSON Keys
"""

from enum import Enum, IntEnum
from typing import Final


# ==============================================================================
# STATEMENT TYPES
# ==============================================================================

class StatementType(str, Enum):
    """
    Financial statement types supported by mat_acc.

    These map to standard XBRL presentation roles.
    """
    BALANCE_SHEET = 'BalanceSheet'
    INCOME_STATEMENT = 'IncomeStatement'
    CASH_FLOW = 'CashFlow'
    STOCKHOLDERS_EQUITY = 'StockholdersEquity'
    COMPREHENSIVE_INCOME = 'ComprehensiveIncome'

    # Aliases
    STATEMENT_OF_FINANCIAL_POSITION = 'BalanceSheet'
    STATEMENT_OF_OPERATIONS = 'IncomeStatement'
    STATEMENT_OF_CASH_FLOWS = 'CashFlow'


# ==============================================================================
# CALCULATION LEVELS
# ==============================================================================

class CalculationLevel(IntEnum):
    """
    Ratio calculation hierarchy levels.

    Level 1: Basic aggregations (sums, differences)
    Level 2: Standard financial ratios
    Level 3: Detailed analysis ratios
    Level 4: Industry-specific ratios
    """
    LEVEL_1_BASIC = 1
    LEVEL_2_STANDARD = 2
    LEVEL_3_DETAILED = 3
    LEVEL_4_INDUSTRY = 4


# Level descriptions for display
CALCULATION_LEVEL_NAMES: Final[dict[int, str]] = {
    1: 'Basic Aggregation',
    2: 'Standard Ratios',
    3: 'Detailed Analysis',
    4: 'Industry-Specific',
}


# ==============================================================================
# CONFIDENCE LEVELS
# ==============================================================================

class ConfidenceLevel(str, Enum):
    """
    Confidence levels for calculated values.

    Based on data quality and calculation reliability.
    """
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'
    UNKNOWN = 'unknown'


# Confidence thresholds (scores 0-100)
CONFIDENCE_HIGH_MIN: Final[float] = 90.0
CONFIDENCE_MEDIUM_MIN: Final[float] = 70.0
CONFIDENCE_LOW_MIN: Final[float] = 0.0


# ==============================================================================
# QUALITY RATINGS
# ==============================================================================

class QualityRating(str, Enum):
    """
    Data quality ratings for filings and calculations.
    """
    EXCELLENT = 'excellent'
    GOOD = 'good'
    FAIR = 'fair'
    POOR = 'poor'
    FAILED = 'failed'


# Quality score thresholds (scores 0-100)
QUALITY_EXCELLENT_MIN: Final[int] = 90
QUALITY_GOOD_MIN: Final[int] = 75
QUALITY_FAIR_MIN: Final[int] = 50
QUALITY_POOR_MIN: Final[int] = 25
QUALITY_FAILED_MIN: Final[int] = 0


def get_quality_rating(score: float) -> QualityRating:
    """
    Get quality rating from numeric score.

    Args:
        score: Quality score (0-100)

    Returns:
        QualityRating enum value
    """
    if score >= QUALITY_EXCELLENT_MIN:
        return QualityRating.EXCELLENT
    elif score >= QUALITY_GOOD_MIN:
        return QualityRating.GOOD
    elif score >= QUALITY_FAIR_MIN:
        return QualityRating.FAIR
    elif score >= QUALITY_POOR_MIN:
        return QualityRating.POOR
    else:
        return QualityRating.FAILED


# ==============================================================================
# SEVERITY LEVELS
# ==============================================================================

class Severity(str, Enum):
    """
    Severity levels for issues and warnings.
    """
    CRITICAL = 'critical'
    WARNING = 'warning'
    INFO = 'info'


# ==============================================================================
# STATUS CODES
# ==============================================================================

class ProcessingStatus(str, Enum):
    """
    Processing status for filings and jobs.
    """
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
    SKIPPED = 'skipped'


class VerificationStatus(str, Enum):
    """
    Verification status for filings.
    """
    VERIFIED = 'verified'
    PARTIALLY_VERIFIED = 'partially_verified'
    FAILED = 'failed'
    NOT_VERIFIED = 'not_verified'


# ==============================================================================
# FILE EXTENSIONS AND NAMES
# ==============================================================================

# Standard file names
VERIFICATION_REPORT_FILE: Final[str] = 'verification_report.json'
MAPPED_STATEMENT_FILE: Final[str] = 'mapped_statement.json'
PARSED_FILING_FILE: Final[str] = 'parsed.json'

# Output file extensions
class OutputFormat(str, Enum):
    """Supported output formats."""
    JSON = 'json'
    CSV = 'csv'
    EXCEL = 'xlsx'
    HTML = 'html'
    PDF = 'pdf'


# ==============================================================================
# JSON KEYS - Verification Reports
# ==============================================================================

class VerificationKeys:
    """
    Standard JSON keys for verification reports.

    Used for consistent parsing across the system.
    """
    # Top level
    FILING_ID: Final[str] = 'filing_id'
    MARKET: Final[str] = 'market'
    COMPANY: Final[str] = 'company'
    FORM: Final[str] = 'form'
    DATE: Final[str] = 'date'
    VERIFIED_AT: Final[str] = 'verified_at'
    PROCESSING_TIME_MS: Final[str] = 'processing_time_ms'

    # Summary
    SUMMARY: Final[str] = 'summary'
    SCORE: Final[str] = 'score'
    TOTAL_CHECKS: Final[str] = 'total_checks'
    PASSED: Final[str] = 'passed'
    FAILED: Final[str] = 'failed'
    SKIPPED: Final[str] = 'skipped'
    CRITICAL_ISSUES: Final[str] = 'critical_issues'
    WARNING_ISSUES: Final[str] = 'warning_issues'
    INFO_ISSUES: Final[str] = 'info_issues'

    # Checks
    CHECKS: Final[str] = 'checks'
    CHECK_NAME: Final[str] = 'check_name'
    CHECK_TYPE: Final[str] = 'check_type'
    SEVERITY: Final[str] = 'severity'
    MESSAGE: Final[str] = 'message'
    CONCEPT: Final[str] = 'concept'
    CONTEXT_ID: Final[str] = 'context_id'
    EXPECTED_VALUE: Final[str] = 'expected_value'
    ACTUAL_VALUE: Final[str] = 'actual_value'
    DIFFERENCE: Final[str] = 'difference'
    DETAILS: Final[str] = 'details'


# ==============================================================================
# JSON KEYS - Mapped Statements
# ==============================================================================

class MappedStatementKeys:
    """
    Standard JSON keys for mapped statement files.
    """
    # Metadata
    METADATA: Final[str] = 'metadata'
    FILING_ID: Final[str] = 'filing_id'
    COMPANY: Final[str] = 'company'
    CIK: Final[str] = 'cik'
    FORM_TYPE: Final[str] = 'form_type'
    FISCAL_YEAR_END: Final[str] = 'fiscal_year_end'
    FILING_DATE: Final[str] = 'filing_date'

    # Statements
    STATEMENTS: Final[str] = 'statements'
    STATEMENT_TYPE: Final[str] = 'statement_type'
    ROLE_URI: Final[str] = 'role_uri'
    DEFINITION: Final[str] = 'definition'
    LINE_ITEMS: Final[str] = 'line_items'

    # Line Items
    CONCEPT_NAME: Final[str] = 'concept_name'
    LABEL: Final[str] = 'label'
    LEVEL: Final[str] = 'level'
    ORDER: Final[str] = 'order'
    IS_ABSTRACT: Final[str] = 'is_abstract'
    BALANCE_TYPE: Final[str] = 'balance_type'
    PERIOD_TYPE: Final[str] = 'period_type'
    VALUES: Final[str] = 'values'


# ==============================================================================
# DISPLAY FORMATTING
# ==============================================================================

# Menu formatting
MENU_WIDTH: Final[int] = 60
MENU_SEPARATOR: Final[str] = '-' * MENU_WIDTH
MENU_HEADER: Final[str] = '=' * MENU_WIDTH

# Number formatting
DECIMAL_PLACES: Final[int] = 2
PERCENTAGE_PLACES: Final[int] = 1

# Status indicators (ASCII only - no emojis)
STATUS_OK: Final[str] = '[OK]'
STATUS_FAIL: Final[str] = '[FAIL]'
STATUS_WARN: Final[str] = '[WARN]'
STATUS_INFO: Final[str] = '[INFO]'
STATUS_SKIP: Final[str] = '[SKIP]'
STATUS_PROGRESS: Final[str] = '[...]'


# ==============================================================================
# LOGGING CATEGORIES
# ==============================================================================

class LogCategory(str, Enum):
    """
    IPO logging categories for mat_acc.
    """
    INPUT = 'input'
    PROCESS = 'process'
    OUTPUT = 'output'


# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    # Enums
    'StatementType',
    'CalculationLevel',
    'ConfidenceLevel',
    'QualityRating',
    'Severity',
    'ProcessingStatus',
    'VerificationStatus',
    'OutputFormat',
    'LogCategory',

    # Constants
    'CALCULATION_LEVEL_NAMES',
    'CONFIDENCE_HIGH_MIN',
    'CONFIDENCE_MEDIUM_MIN',
    'CONFIDENCE_LOW_MIN',
    'QUALITY_EXCELLENT_MIN',
    'QUALITY_GOOD_MIN',
    'QUALITY_FAIR_MIN',
    'QUALITY_POOR_MIN',
    'QUALITY_FAILED_MIN',

    # File names
    'VERIFICATION_REPORT_FILE',
    'MAPPED_STATEMENT_FILE',
    'PARSED_FILING_FILE',

    # Key classes
    'VerificationKeys',
    'MappedStatementKeys',

    # Display
    'MENU_WIDTH',
    'MENU_SEPARATOR',
    'MENU_HEADER',
    'DECIMAL_PLACES',
    'PERCENTAGE_PLACES',
    'STATUS_OK',
    'STATUS_FAIL',
    'STATUS_WARN',
    'STATUS_INFO',
    'STATUS_SKIP',
    'STATUS_PROGRESS',

    # Functions
    'get_quality_rating',
]
