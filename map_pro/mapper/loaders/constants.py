# Path: loaders/constants.py
"""
Loaders Module Constants

CRITICAL DATA SOURCE HIERARCHY:
===============================
1. PRIMARY:   Read from XBRL filing (namespace declarations, schema references)
2. SECONDARY: Read from standard taxonomy (if filing declares to use it)
3. FALLBACK:  Patterns below (ONLY for enhancement/detection, NOT classification)

DESIGN PRINCIPLE:
================
Constants define DETECTION AIDS, not BUSINESS LOGIC.
Loaders discover what EXISTS in filing, they don't ASSUME what should exist.

All patterns below are FALLBACK HEURISTICS - used only when filing data unavailable.
Primary source is ALWAYS the filing itself.
"""

# ==============================================================================
# FILE DETECTION PATTERNS (Universal - Keep)
# ==============================================================================

# File type detection by extension (universal across all systems)
FILE_TYPE_PATTERNS = {
    'json': ['.json'],
    'csv': ['.csv'],
    'xlsx': ['.xlsx', '.xlsm'],
    'txt': ['.txt'],
    'xml': ['.xml'],
    'xbrl': ['.xbrl'],
    'htm': ['.htm', '.html'],
    'xsd': ['.xsd'],
}

# ==============================================================================
# XBRL SPECIFICATION CONSTANTS (From XBRL 2.1 Spec - Keep)
# ==============================================================================

# XML Namespace URIs (XBRL 2.1 Specification)
XLINK_NAMESPACE = 'http://www.w3.org/1999/xlink'
XBRL_NAMESPACE = 'http://www.xbrl.org/2003/linkbase'

# XLink attribute names (XBRL Specification)
XLINK_ATTRS = {
    'from': f'{{{XLINK_NAMESPACE}}}from',
    'to': f'{{{XLINK_NAMESPACE}}}to',
    'label': f'{{{XLINK_NAMESPACE}}}label',
    'href': f'{{{XLINK_NAMESPACE}}}href',
    'role': f'{{{XLINK_NAMESPACE}}}role',
    'arcrole': f'{{{XLINK_NAMESPACE}}}arcrole',
}

# Linkbase element names (XBRL Specification)
LINKBASE_ELEMENT_NAMES = {
    'presentation_link': 'presentationLink',
    'presentation_arc': 'presentationArc',
    'calculation_link': 'calculationLink',
    'calculation_arc': 'calculationArc',
    'definition_link': 'definitionLink',
    'definition_arc': 'definitionArc',
    'label_link': 'labelLink',
    'reference_link': 'referenceLink',
    'locator': 'loc',
}

# Arc attribute names (XBRL Specification)
ARC_ATTRIBUTES = [
    'order',
    'priority',
    'use',
    'weight',
    'preferredLabel',
]

# ==============================================================================
# STANDARD XBRL NAMESPACE PATTERNS (Universal - Keep)
# ==============================================================================

# Core XBRL namespaces that appear in most filings
# These are from XBRL specifications, not market-specific
STANDARD_XBRL_URI_PATTERNS = [
    'xbrl.org/2003',          # XBRL 2.1
    'xbrl.org/2005',          # XBRL Dimensions
    'xbrl.org/2006',          # XBRL Dimensions extensions
    'w3.org/2001/XMLSchema',  # XML Schema
]

# ==============================================================================
# TAXONOMY IDENTIFICATION FALLBACK (Use with caution - Read from filing first!)
# ==============================================================================

#  FALLBACK ONLY - DO NOT USE AS PRIMARY IDENTIFICATION
# PRIMARY: Read namespace declarations from filing's schema references
# SECONDARY: Read taxonomy info from schemaRef elements
# FALLBACK: Use patterns below ONLY if above methods unavailable

# These patterns assist in RECOGNIZING taxonomies when namespace URIs
# don't follow predictable formats. They should NEVER replace reading
# actual schema references from the filing.

TAXONOMY_RECOGNITION_PATTERNS = {
    # Pattern name -> URI substrings that MAY indicate this taxonomy
    # Use for logging/diagnostics only, not business logic
    'us_gaap': ['us-gaap', 'fasb.org/us-gaap'],
    'ifrs': ['ifrs', 'iasb'],
    'uk_gaap': ['uk-gaap', 'frc.org.uk'],
    'esef': ['esef', 'esma'],
    'dei': ['dei', 'xbrl.sec.gov/dei'],
    'srt': ['srt', 'fasb.org/srt'],
}

# USAGE NOTE:
#  WRONG: Check pattern first to identify taxonomy
#  RIGHT: Read schemaRef from filing, use pattern only for friendly naming

# ==============================================================================
# DATA STRUCTURE DETECTION PATTERNS (Discovery Aids - Keep)
# ==============================================================================

# Common JSON/dict keys that might contain XBRL data elements
# These help DISCOVER structure, not define it
FACT_CONTAINER_PATTERNS = [
    'instance.facts',
    'facts',
    'data.facts',
    'filing.facts',
]

CONTEXT_CONTAINER_PATTERNS = [
    'instance.contexts',
    'contexts',
    'data.contexts',
    'filing.contexts',
]

UNIT_CONTAINER_PATTERNS = [
    'instance.units',
    'units',
    'data.units',
]

METADATA_CONTAINER_PATTERNS = [
    'metadata',
    'filing_metadata',
    'document_info',
]

NAMESPACE_CONTAINER_PATTERNS = [
    'instance.namespaces',
    'namespaces',
    'xmlns',
]

# ==============================================================================
# OPERATIONAL CONFIGURATION (Keep)
# ==============================================================================

# Maximum directory depth to search (prevent infinite loops)
MAX_DIRECTORY_DEPTH = 25

# File size limits (MB) for different file types
MAX_FILE_SIZES = {
    'json': 500,   # JSON files up to 500MB
    'xml': 200,    # XML files up to 200MB
    'xsd': 50,     # Schema files up to 50MB
    'csv': 100,    # CSV files up to 100MB
    'xlsx': 100,   # Excel files up to 100MB
}

# Log levels for different loader operations
LOG_LEVELS = {
    'discovery': 'INFO',
    'structure_analysis': 'DEBUG',
    'validation': 'INFO',
    'errors': 'ERROR',
}

# Cache settings for structure discovery
STRUCTURE_CACHE_ENABLED = False  # Disabled by default - always discover fresh
STRUCTURE_CACHE_TTL_SECONDS = 300  # 5 minutes if enabled

# Error handling limits
MAX_VALIDATION_ERRORS = 100
MAX_VALIDATION_WARNINGS = 1000

# ==============================================================================
# REMOVED: Market-Specific Assumptions
# ==============================================================================

# REMOVED: MARKET_DETECTION_PATTERNS
# Reason: Should read jurisdiction from filing metadata, not pattern match

# REMOVED: MIN_FACT_COUNT_THRESHOLDS per market
# Reason: Fact counts vary by company size, not market
# Each filing declares its own facts - no minimum required


__all__ = [
    # File detection
    'FILE_TYPE_PATTERNS',
    
    # XBRL Specification Constants
    'XLINK_NAMESPACE',
    'XBRL_NAMESPACE',
    'XLINK_ATTRS',
    'LINKBASE_ELEMENT_NAMES',
    'ARC_ATTRIBUTES',
    'STANDARD_XBRL_URI_PATTERNS',
    
    # Taxonomy recognition (fallback only)
    'TAXONOMY_RECOGNITION_PATTERNS',
    
    # Structure detection
    'FACT_CONTAINER_PATTERNS',
    'CONTEXT_CONTAINER_PATTERNS',
    'UNIT_CONTAINER_PATTERNS',
    'METADATA_CONTAINER_PATTERNS',
    'NAMESPACE_CONTAINER_PATTERNS',
    
    # Configuration
    'MAX_DIRECTORY_DEPTH',
    'MAX_FILE_SIZES',
    'LOG_LEVELS',
    'STRUCTURE_CACHE_ENABLED',
    'STRUCTURE_CACHE_TTL_SECONDS',
    'MAX_VALIDATION_ERRORS',
    'MAX_VALIDATION_WARNINGS',
]