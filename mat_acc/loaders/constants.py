# Path: mat_acc/loaders/constants.py
"""
Loaders Module Constants for mat_acc

Constants for data loading operations.
All patterns here are DETECTION AIDS, not business logic.
Adapted from map_pro/verification/loaders/constants.py
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
# VERIFICATION REPORTS DETECTION
# ==============================================================================

# Files that indicate a valid verification report directory
VERIFICATION_REPORT_FILE = 'verification_report.json'

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

# Statement category folders
MAPPED_STATEMENT_FOLDERS = ['core_statements', 'details', 'other']

# ==============================================================================
# PARSED OUTPUT DETECTION
# ==============================================================================

# Main parsed output file
PARSED_JSON_FILE = 'parsed.json'

# Additional parsed output files
PARSED_OUTPUT_FILES = ['facts.csv', 'summary.txt', 'workbook.xlsx']

# ==============================================================================
# XBRL FILING DETECTION
# ==============================================================================

# Linkbase file patterns
CALCULATION_LINKBASE_PATTERNS = [
    # Suffix patterns (US-GAAP style)
    '_cal.xml',
    '_calculation.xml',
    '-cal.xml',
    '-cal-',
    'cal.xml',
    # Prefix patterns (IFRS style)
    'cal_',
    'cal-',
]

PRESENTATION_LINKBASE_PATTERNS = [
    # Suffix patterns (US-GAAP style)
    '_pre.xml',
    '_presentation.xml',
    '-pre.xml',
    '-pre-',
    'pre.xml',
    # Prefix patterns (IFRS style)
    'pre_',
    'pre-',
]

DEFINITION_LINKBASE_PATTERNS = [
    # Suffix patterns (US-GAAP style)
    '_def.xml',
    '_definition.xml',
    '-def.xml',
    '-def-',
    'def.xml',
    # Prefix patterns (IFRS style)
    'def_',
    'def-',
]

LABEL_LINKBASE_PATTERNS = [
    # Suffix patterns (US-GAAP style)
    '_lab.xml',
    '_label.xml',
    '-lab.xml',
    '-lab-',
    'lab.xml',
    # Prefix patterns (IFRS style)
    'lab_',
    'lab-',
    # Language-specific patterns
    '-lab-en',
    '-lab-de',
    '-lab-fr',
]

REFERENCE_LINKBASE_PATTERNS = [
    # Suffix patterns (US-GAAP style)
    '_ref.xml',
    '_reference.xml',
    '-ref.xml',
    '-ref-',
    'ref.xml',
    # Prefix patterns (IFRS style)
    'ref_',
    'ref-',
]

# ==============================================================================
# IFRS-SPECIFIC LINKBASE PATTERNS
# ==============================================================================
# IFRS taxonomies use additional specialized linkbase types beyond standard XBRL

# Dimension linkbase patterns (IFRS separates dimensions from definition linkbase)
DIMENSION_LINKBASE_PATTERNS = [
    # Prefix patterns (IFRS style)
    'dim_',
    'dim-',
    # Suffix patterns
    '_dim.xml',
    '-dim.xml',
    '-dim-',
]

# Documentation linkbase patterns (human-readable documentation)
DOCUMENTATION_LINKBASE_PATTERNS = [
    # Prefix patterns (IFRS style)
    'doc_',
    'doc-',
    # Suffix patterns
    '_doc.xml',
    '-doc.xml',
    '-doc-',
]

# Generic label arc patterns (IFRS uses for dimensional labels)
GENERIC_LABEL_ARC_PATTERNS = [
    # Prefix patterns (IFRS style)
    'gla_',
    'gla-',
    # Suffix patterns
    '_gla.xml',
    '-gla.xml',
    '-gla-',
]

# Generic reference patterns (IFRS uses for dimensional references)
GENERIC_REFERENCE_PATTERNS = [
    # Prefix patterns (IFRS style)
    'gre_',
    'gre-',
    # Suffix patterns
    '_gre.xml',
    '-gre.xml',
    '-gre-',
]

# Implementation notes patterns (guidance files)
IMPLEMENTATION_PATTERNS = [
    # Prefix patterns (IFRS style)
    'in_',
    'in-',
    # Suffix patterns
    '_in.xml',
    '-in.xml',
    '-in-',
]

# Deprecated element patterns (files marking deprecated concepts)
DEPRECATED_ELEMENT_PATTERNS = [
    # Prefix patterns (IFRS style)
    'depr-',
    'depr_',
    # Suffix patterns
    '_depr.xml',
    '-depr.xml',
]

# Role type definition patterns (XSD files defining roles)
ROLE_TYPE_PATTERNS = [
    # Prefix patterns (IFRS style)
    'rol_',
    'rol-',
    # Suffix patterns
    '_rol.xsd',
    '-rol.xsd',
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
# FORM NAME VARIATIONS
# ==============================================================================

FORM_NAME_VARIATIONS = {
    '10-k': ['10-k', '10_k', '10k', 'form10k', 'form10-k', 'form 10-k', 'annual'],
    '10-q': ['10-q', '10_q', '10q', 'form10q', 'form10-q', 'form 10-q', 'quarterly'],
    '8-k': ['8-k', '8_k', '8k', 'form8k', 'form8-k', 'form 8-k', 'current'],
    '20-f': ['20-f', '20_f', '20f', 'form20f', 'form20-f', 'form 20-f'],
    '40-f': ['40-f', '40_f', '40f', 'form40f', 'form40-f', 'form 40-f'],
    '6-k': ['6-k', '6_k', '6k', 'form6k', 'form6-k', 'form 6-k'],
    'afr': ['afr', 'annual-financial-report', 'annual_financial_report'],
    'hyr': ['hyr', 'half-year-report', 'half_year_report', 'interim'],
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

    Args:
        form: Form name in any format (10-K, 10_K, 10K, etc.)

    Returns:
        Normalized form name (e.g., '10-k')
    """
    normalized = form.lower().replace('_', '-').replace(' ', '-')
    if normalized.startswith('form'):
        normalized = normalized[4:].lstrip('-').lstrip('_').lstrip(' ')
    return normalized


def get_form_variations(form: str) -> list[str]:
    """
    Get all variations of a form name for searching.

    Args:
        form: Form name in any format

    Returns:
        List of form name variations to search for
    """
    normalized = normalize_form_name(form)
    variations = [form, form.lower(), form.upper()]
    variations.append(normalized)
    variations.append(normalized.replace('-', '_'))
    variations.append(normalized.replace('-', ''))

    if normalized in FORM_NAME_VARIATIONS:
        variations.extend(FORM_NAME_VARIATIONS[normalized])

    form_lower = form.lower()
    for canonical, var_list in FORM_NAME_VARIATIONS.items():
        if form_lower in var_list or canonical == form_lower:
            variations.extend(var_list)
            break

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

    Removes all special characters to enable matching across different
    naming conventions:
    - ELI_LILLY_AND_COMPANY vs ELI_LILLY_&_Co
    - PROCTER_GAMBLE_CO vs PROCTER_&_GAMBLE_Co

    Args:
        name: Name to normalize

    Returns:
        Normalized name for comparison (lowercase, alphanumeric only)
    """
    # Remove all non-alphanumeric characters for robust matching
    # This handles: _ - & ' " . , ( ) / \ and any other special chars
    normalized = name.lower()
    # Replace common word variants
    normalized = normalized.replace('&', 'and')
    normalized = normalized.replace('company', 'co')
    normalized = normalized.replace('corporation', 'corp')
    normalized = normalized.replace('incorporated', 'inc')
    # Remove all remaining non-alphanumeric
    normalized = ''.join(c for c in normalized if c.isalnum())
    return normalized


def normalize_name_strict(name: str) -> str:
    """
    Normalize name with stricter matching - removes conjunctions.

    Used as a fallback when normal matching fails due to
    inconsistent & vs AND vs nothing in company names.

    Examples:
        - PROCTER_GAMBLE_CO -> proctergambleco
        - PROCTER_&_GAMBLE_Co -> proctergambleco (removes 'and')
        - ELI_LILLY_AND_COMPANY -> elilillyco

    Args:
        name: Name to normalize

    Returns:
        Normalized name without conjunctions
    """
    normalized = normalize_name(name)
    # Remove common conjunctions that may or may not be present
    normalized = normalized.replace('and', '')
    normalized = normalized.replace('the', '')
    normalized = normalized.replace('of', '')
    return normalized


def names_match_flexible(name1: str, name2: str) -> bool:
    """
    Check if two names match using flexible matching strategies.

    Tries multiple normalization approaches:
    1. Standard normalization with substring matching
    2. Strict normalization (without conjunctions) with substring matching

    This handles cases like:
    - PROCTER_GAMBLE_CO vs PROCTER_&_GAMBLE_Co
    - ELI_LILLY_AND_COMPANY vs ELI_LILLY_&_Co

    Args:
        name1: First name
        name2: Second name

    Returns:
        True if names match by any strategy
    """
    # Strategy 1: Standard normalization
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    if norm1 in norm2 or norm2 in norm1:
        return True

    # Strategy 2: Strict normalization (remove conjunctions)
    strict1 = normalize_name_strict(name1)
    strict2 = normalize_name_strict(name2)

    if strict1 in strict2 or strict2 in strict1:
        return True

    return False


def parse_concept(concept: str) -> tuple[str, str]:
    """
    Parse XBRL concept into namespace prefix and local name.

    Handles all separator variations:
    - Colon separator: us-gaap:Assets -> ('us-gaap', 'Assets')
    - Underscore separator: ifrs-full_Equity -> ('ifrs-full', 'Equity')
    - No separator: Assets -> ('', 'Assets')

    Args:
        concept: Concept string (e.g., 'us-gaap:Assets' or 'ifrs-full_Equity')

    Returns:
        Tuple of (prefix, local_name)
    """
    if not concept:
        return '', ''

    # Handle colon separator first (standard QName format)
    if ':' in concept:
        parts = concept.split(':', 1)
        return parts[0], parts[1]

    # Handle underscore separator (used in some systems)
    if '_' in concept:
        idx = concept.find('_')
        prefix = concept[:idx]
        local_name = concept[idx + 1:]
        return prefix, local_name

    # No separator - treat whole thing as local name
    return '', concept


def extract_concept_local_name(concept: str) -> str:
    """
    Extract the local name from an XBRL concept.

    Convenience function that returns just the local name part.

    Args:
        concept: Concept string (e.g., 'us-gaap:Assets' or 'ifrs-full_Equity')

    Returns:
        Local name without namespace prefix
    """
    _, local_name = parse_concept(concept)
    return local_name


def normalize_concept_for_matching(concept: str) -> str:
    """
    Normalize concept for matching across different formats.

    Extracts local name and normalizes it for comparison.

    Args:
        concept: Concept string in any format

    Returns:
        Normalized local name for matching
    """
    local_name = extract_concept_local_name(concept)
    return local_name.lower()


# ==============================================================================
# DATE MATCHING UTILITIES
# ==============================================================================

DATE_FORMAT_PATTERNS = [
    '%Y-%m-%d',
    '%Y_%m_%d',
    '%Y%m%d',
    '%m-%d-%Y',
    '%m_%d_%Y',
    '%d-%m-%Y',
    '%Y',
]

DATE_SEPARATOR_CHARS = ['-', '_', '/']


def normalize_date_string(date_str: str) -> str:
    """
    Normalize date string for comparison.

    Args:
        date_str: Date string in any format

    Returns:
        Normalized date string (digits only)
    """
    if not date_str:
        return ''
    normalized = date_str
    for sep in DATE_SEPARATOR_CHARS:
        normalized = normalized.replace(sep, '')
    return ''.join(c for c in normalized if c.isdigit())


def extract_year_from_date(date_str: str) -> str:
    """
    Extract year from date string.

    Args:
        date_str: Date string

    Returns:
        4-digit year or empty string if not found
    """
    if not date_str:
        return ''
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
        return True

    if match_level == 'contains':
        norm1 = normalize_date_string(date1)
        norm2 = normalize_date_string(date2)
        return norm1 in norm2 or norm2 in norm1

    if match_level == 'year':
        year1 = extract_year_from_date(date1)
        year2 = extract_year_from_date(date2)
        if year1 and year2:
            return year1 == year2
        return True

    if match_level == 'exact':
        return normalize_date_string(date1) == normalize_date_string(date2)

    return True


DEFAULT_DATE_MATCH_LEVEL = 'any'

# ==============================================================================
# OPERATIONAL CONFIGURATION
# ==============================================================================

MAX_DIRECTORY_DEPTH = 25

MAX_FILE_SIZES = {
    'json': 500,
    'xml': 200,
    'xsd': 50,
    'csv': 100,
    'xlsx': 100,
}

LOG_LEVELS = {
    'discovery': 'INFO',
    'reading': 'DEBUG',
    'validation': 'INFO',
    'errors': 'ERROR',
}


__all__ = [
    'FILE_TYPE_PATTERNS',
    'VERIFICATION_REPORT_FILE',
    'MAPPED_STATEMENT_MARKERS',
    'MAPPED_OUTPUT_SUBDIRS',
    'MAPPED_STATEMENT_FOLDERS',
    'PARSED_JSON_FILE',
    'PARSED_OUTPUT_FILES',
    'CALCULATION_LINKBASE_PATTERNS',
    'PRESENTATION_LINKBASE_PATTERNS',
    'DEFINITION_LINKBASE_PATTERNS',
    'LABEL_LINKBASE_PATTERNS',
    'REFERENCE_LINKBASE_PATTERNS',
    # IFRS-specific linkbase patterns
    'DIMENSION_LINKBASE_PATTERNS',
    'DOCUMENTATION_LINKBASE_PATTERNS',
    'GENERIC_LABEL_ARC_PATTERNS',
    'GENERIC_REFERENCE_PATTERNS',
    'IMPLEMENTATION_PATTERNS',
    'DEPRECATED_ELEMENT_PATTERNS',
    'ROLE_TYPE_PATTERNS',
    'SCHEMA_FILE_PATTERNS',
    'INSTANCE_FILE_PATTERNS',
    'XLINK_NAMESPACE',
    'XBRL_LINKBASE_NAMESPACE',
    'XBRL_INSTANCE_NAMESPACE',
    'XLINK_ATTRS',
    'LINKBASE_ELEMENTS',
    'ARC_ATTRIBUTES',
    'FORM_NAME_VARIATIONS',
    'NAME_EQUIVALENT_CHARS',
    'normalize_form_name',
    'get_form_variations',
    'normalize_name',
    'normalize_name_strict',
    'names_match_flexible',
    'parse_concept',
    'extract_concept_local_name',
    'normalize_concept_for_matching',
    'DATE_FORMAT_PATTERNS',
    'DATE_SEPARATOR_CHARS',
    'DEFAULT_DATE_MATCH_LEVEL',
    'normalize_date_string',
    'extract_year_from_date',
    'dates_match_flexible',
    'MAX_DIRECTORY_DEPTH',
    'MAX_FILE_SIZES',
    'LOG_LEVELS',
]
