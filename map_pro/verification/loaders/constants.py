# Path: verification/loaders/constants.py
"""
Loaders Module Constants for Verification

Constants for data loading operations.
All patterns here are DETECTION AIDS, not business logic.
"""

# ==============================================================================
# FILE DETECTION PATTERNS
# ==============================================================================

# File type detection by extension
FILE_TYPE_PATTERNS = {
    'json': ['.json'],
    'csv': ['.csv'],
    'xlsx': ['.xlsx', '.xlsm'],
    'txt': ['.txt'],
    'xml': ['.xml'],
    'xbrl': ['.xbrl'],
    'htm': ['.htm', '.html', '.xhtml'],
    'xsd': ['.xsd'],
}

# ==============================================================================
# MAPPED STATEMENTS DETECTION
# ==============================================================================

# Files that indicate a valid mapped statement directory
MAPPED_STATEMENT_MARKERS = [
    'MAIN_FINANCIAL_STATEMENTS.json',
    'statements.json',
]

# Subdirectories within mapped statement output
MAPPED_OUTPUT_SUBDIRS = ['json', 'csv', 'excel']

# ==============================================================================
# PARSED OUTPUT DETECTION
# ==============================================================================

# Main parsed output file
PARSED_JSON_FILE = 'parsed.json'

# ==============================================================================
# XBRL FILING DETECTION
# ==============================================================================

# Linkbase file patterns
# Note: US-GAAP taxonomy uses patterns like 'us-gaap-dis-xxx-cal-2024.xml'
CALCULATION_LINKBASE_PATTERNS = [
    '_cal.xml',         # Company XBRL: aci-20250222_cal.xml
    '_calculation.xml', # Alternative naming
    '-cal.xml',         # Some taxonomies
    '-cal-',            # US-GAAP taxonomy: us-gaap-dis-xxx-cal-2024.xml
    'cal.xml',          # Bare name
]
PRESENTATION_LINKBASE_PATTERNS = [
    '_pre.xml',
    '_presentation.xml',
    '-pre.xml',
    '-pre-',            # US-GAAP taxonomy pattern
    'pre.xml',
]
DEFINITION_LINKBASE_PATTERNS = [
    '_def.xml',
    '_definition.xml',
    '-def.xml',
    '-def-',            # US-GAAP taxonomy pattern
    'def.xml',
]
LABEL_LINKBASE_PATTERNS = [
    '_lab.xml',
    '_label.xml',
    '-lab.xml',
    '-lab-',            # US-GAAP taxonomy pattern
    'lab.xml',
]

# Schema file patterns
SCHEMA_FILE_PATTERNS = ['.xsd']

# Instance document patterns
INSTANCE_FILE_PATTERNS = ['.xml', '.xbrl', '.xhtml', '.htm', '.html']

# ==============================================================================
# XBRL SPECIFICATION CONSTANTS
# ==============================================================================

# XML Namespace URIs (XBRL 2.1 Specification)
XLINK_NAMESPACE = 'http://www.w3.org/1999/xlink'
XBRL_LINKBASE_NAMESPACE = 'http://www.xbrl.org/2003/linkbase'
XBRL_INSTANCE_NAMESPACE = 'http://www.xbrl.org/2003/instance'

# XLink attribute names
XLINK_ATTRS = {
    'from': f'{{{XLINK_NAMESPACE}}}from',
    'to': f'{{{XLINK_NAMESPACE}}}to',
    'label': f'{{{XLINK_NAMESPACE}}}label',
    'href': f'{{{XLINK_NAMESPACE}}}href',
    'role': f'{{{XLINK_NAMESPACE}}}role',
    'arcrole': f'{{{XLINK_NAMESPACE}}}arcrole',
}

# Linkbase element names
LINKBASE_ELEMENTS = {
    'calculation_link': 'calculationLink',
    'calculation_arc': 'calculationArc',
    'presentation_link': 'presentationLink',
    'presentation_arc': 'presentationArc',
    'definition_link': 'definitionLink',
    'definition_arc': 'definitionArc',
    'locator': 'loc',
}

# Arc attributes
ARC_ATTRIBUTES = ['order', 'priority', 'use', 'weight', 'preferredLabel']

# ==============================================================================
# TAXONOMY LIBRARY PATTERNS
# ==============================================================================

# Common standard taxonomy patterns
STANDARD_TAXONOMY_PATTERNS = {
    'us_gaap': ['us-gaap', 'fasb.org/us-gaap'],
    'ifrs': ['ifrs', 'iasb'],
    'uk_gaap': ['uk-gaap', 'frc.org.uk'],
    'esef': ['esef', 'esma'],
    'dei': ['dei', 'xbrl.sec.gov/dei'],
    'srt': ['srt', 'fasb.org/srt'],
}

# ==============================================================================
# FORM NAME VARIATIONS
# ==============================================================================

# Common SEC form names and their variations
# Used to handle different naming conventions across systems
# Key: normalized form name, Value: list of variations to search for
FORM_NAME_VARIATIONS = {
    '10-k': ['10-k', '10_k', '10k', 'form10k', 'form10-k', 'form 10-k', 'annual'],
    '10-q': ['10-q', '10_q', '10q', 'form10q', 'form10-q', 'form 10-q', 'quarterly'],
    '8-k': ['8-k', '8_k', '8k', 'form8k', 'form8-k', 'form 8-k', 'current'],
    '20-f': ['20-f', '20_f', '20f', 'form20f', 'form20-f', 'form 20-f'],
    '40-f': ['40-f', '40_f', '40f', 'form40f', 'form40-f', 'form 40-f'],
    '6-k': ['6-k', '6_k', '6k', 'form6k', 'form6-k', 'form 6-k'],
    # ESEF/European forms
    'afr': ['afr', 'annual-financial-report', 'annual_financial_report'],
    'hyr': ['hyr', 'half-year-report', 'half_year_report', 'interim'],
    # Generic
    'annual': ['annual', 'annual-report', 'annual_report', 'ar'],
}

# Characters that are interchangeable in form/directory names
NAME_EQUIVALENT_CHARS = [
    ('-', '_'),
    (' ', '_'),
    (' ', '-'),
]


def normalize_form_name(form: str) -> str:
    """
    Normalize form name to canonical format.

    Converts various formats to lowercase with hyphen separator.

    Args:
        form: Form name in any format (10-K, 10_K, 10K, etc.)

    Returns:
        Normalized form name (e.g., '10-k')
    """
    # Lowercase and replace underscores with hyphens
    normalized = form.lower().replace('_', '-').replace(' ', '-')

    # Remove 'form' prefix if present
    if normalized.startswith('form'):
        normalized = normalized[4:].lstrip('-').lstrip('_').lstrip(' ')

    return normalized


def get_form_variations(form: str) -> list[str]:
    """
    Get all variations of a form name for searching.

    Returns both the input form and all known variations.

    Args:
        form: Form name in any format

    Returns:
        List of form name variations to search for
    """
    normalized = normalize_form_name(form)

    # Start with direct variations
    variations = [form, form.lower(), form.upper()]

    # Add normalized version and its transformations
    variations.append(normalized)
    variations.append(normalized.replace('-', '_'))
    variations.append(normalized.replace('-', ''))

    # Add known variations if available
    if normalized in FORM_NAME_VARIATIONS:
        variations.extend(FORM_NAME_VARIATIONS[normalized])

    # Also check if input (lowercased) matches any known form
    form_lower = form.lower()
    for canonical, var_list in FORM_NAME_VARIATIONS.items():
        if form_lower in var_list or canonical == form_lower:
            variations.extend(var_list)
            break

    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for v in variations:
        v_lower = v.lower()
        if v_lower not in seen:
            seen.add(v_lower)
            unique_variations.append(v)

    return unique_variations


def normalize_name(name: str) -> str:
    """
    Normalize any name (company, form, etc.) for comparison.

    Removes spaces, underscores, hyphens and lowercases.

    Args:
        name: Name to normalize

    Returns:
        Normalized name for comparison
    """
    return name.lower().replace('_', '').replace('-', '').replace(' ', '')

# ==============================================================================
# DATE MATCHING UTILITIES
# ==============================================================================

# Date format patterns commonly found in filing directories
# These are detection patterns, not strict formats
DATE_FORMAT_PATTERNS = [
    '%Y-%m-%d',      # 2025-04-21
    '%Y_%m_%d',      # 2025_04_21
    '%Y%m%d',        # 20250421
    '%m-%d-%Y',      # 04-21-2025
    '%m_%d_%Y',      # 04_21_2025
    '%d-%m-%Y',      # 21-04-2025
    '%Y',            # 2025 (year only)
]

# Characters that are interchangeable in date strings
DATE_SEPARATOR_CHARS = ['-', '_', '/']


def normalize_date_string(date_str: str) -> str:
    """
    Normalize date string for comparison.

    Removes separators and converts to digits-only format.
    This allows matching dates regardless of separator used.

    Args:
        date_str: Date string in any format

    Returns:
        Normalized date string (digits only)
    """
    if not date_str:
        return ''

    # Remove all common separators
    normalized = date_str
    for sep in DATE_SEPARATOR_CHARS:
        normalized = normalized.replace(sep, '')

    # Keep only digits
    return ''.join(c for c in normalized if c.isdigit())


def extract_year_from_date(date_str: str) -> str:
    """
    Extract year from date string.

    Works with various date formats.

    Args:
        date_str: Date string

    Returns:
        4-digit year or empty string if not found
    """
    if not date_str:
        return ''

    # Try to find a 4-digit year pattern
    import re
    year_match = re.search(r'(19|20)\d{2}', date_str)
    if year_match:
        return year_match.group(0)

    return ''


def dates_match_flexible(date1: str, date2: str, match_level: str = 'year') -> bool:
    """
    Check if two dates match with flexible matching levels.

    Matching levels:
    - 'exact': Normalized dates must match exactly
    - 'year': Only years need to match
    - 'contains': One date contains the other (substring)
    - 'any': Always returns True (no date matching)

    Args:
        date1: First date string
        date2: Second date string
        match_level: How strict the matching should be

    Returns:
        True if dates match at the specified level
    """
    if match_level == 'any':
        return True

    if not date1 or not date2:
        return True  # If either date is missing, consider it a match

    if match_level == 'contains':
        # Substring matching
        norm1 = normalize_date_string(date1)
        norm2 = normalize_date_string(date2)
        return norm1 in norm2 or norm2 in norm1

    if match_level == 'year':
        # Only match year
        year1 = extract_year_from_date(date1)
        year2 = extract_year_from_date(date2)
        if year1 and year2:
            return year1 == year2
        return True  # If can't extract year, consider it a match

    if match_level == 'exact':
        # Normalized exact match
        return normalize_date_string(date1) == normalize_date_string(date2)

    # Default: be permissive
    return True


# Default date match level for filing lookups
# Options: 'any', 'year', 'contains', 'exact'
DEFAULT_DATE_MATCH_LEVEL = 'any'


# ==============================================================================
# OPERATIONAL CONFIGURATION
# ==============================================================================

# Maximum directory depth to search
MAX_DIRECTORY_DEPTH = 25

# File size limits (MB)
MAX_FILE_SIZES = {
    'json': 500,
    'xml': 200,
    'xsd': 50,
    'csv': 100,
    'xlsx': 100,
}

# Logging levels for loader operations
LOG_LEVELS = {
    'discovery': 'INFO',
    'reading': 'DEBUG',
    'validation': 'INFO',
    'errors': 'ERROR',
}


__all__ = [
    # File patterns
    'FILE_TYPE_PATTERNS',

    # Mapped statements
    'MAPPED_STATEMENT_MARKERS',
    'MAPPED_OUTPUT_SUBDIRS',

    # Parsed output
    'PARSED_JSON_FILE',

    # XBRL patterns
    'CALCULATION_LINKBASE_PATTERNS',
    'PRESENTATION_LINKBASE_PATTERNS',
    'DEFINITION_LINKBASE_PATTERNS',
    'LABEL_LINKBASE_PATTERNS',
    'SCHEMA_FILE_PATTERNS',
    'INSTANCE_FILE_PATTERNS',

    # XBRL namespaces
    'XLINK_NAMESPACE',
    'XBRL_LINKBASE_NAMESPACE',
    'XBRL_INSTANCE_NAMESPACE',
    'XLINK_ATTRS',
    'LINKBASE_ELEMENTS',
    'ARC_ATTRIBUTES',

    # Taxonomy patterns
    'STANDARD_TAXONOMY_PATTERNS',

    # Form name variations
    'FORM_NAME_VARIATIONS',
    'NAME_EQUIVALENT_CHARS',
    'normalize_form_name',
    'get_form_variations',
    'normalize_name',

    # Date matching utilities
    'DATE_FORMAT_PATTERNS',
    'DATE_SEPARATOR_CHARS',
    'DEFAULT_DATE_MATCH_LEVEL',
    'normalize_date_string',
    'extract_year_from_date',
    'dates_match_flexible',

    # Configuration
    'MAX_DIRECTORY_DEPTH',
    'MAX_FILE_SIZES',
    'LOG_LEVELS',
]
