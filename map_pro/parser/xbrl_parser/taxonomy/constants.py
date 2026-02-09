# Path: xbrl_parser/taxonomy/constants.py
"""
Taxonomy Module Constants

Central repository for all taxonomy-related constants, namespace URIs, and patterns.

NO HARDCODED values should exist in other taxonomy module files - all constants
should be imported from this file or from foundation/url_addresses.py.
"""

# ==============================================================================
# XML SCHEMA NAMESPACE
# ==============================================================================

# W3C XML Schema namespace (used in all XSD files)
XSD_NS = "http://www.w3.org/2001/XMLSchema"

# XML Schema Instance namespace
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

# ==============================================================================
# XBRL LINKBASE NAMESPACES
# ==============================================================================

# XBRL Linkbase namespace (for all linkbase files)
LINK_NS = "http://www.xbrl.org/2003/linkbase"

# XLink namespace (for link relationships)
XLINK_NS = "http://www.w3.org/1999/xlink"

# XBRL Link Reference namespace
LINKREF_NS = "http://www.xbrl.org/2003/linkbaseRef"

# ==============================================================================
# XBRL CORE NAMESPACES
# ==============================================================================

# XBRL Instance namespace
XBRLI_NS = "http://www.xbrl.org/2003/instance"

# XBRL Types namespace
XBRLDT_NS = "http://xbrl.org/2005/xbrldt"

# XBRL Dimensions namespace
XBRLDI_NS = "http://xbrl.org/2006/xbrldi"

# ==============================================================================
# TAXONOMY FAMILY DETECTION PATTERNS
# ==============================================================================

# Patterns for detecting taxonomy families from namespace URIs
# Each taxonomy family has multiple patterns that can appear in namespace URIs
# These are checked in order until a match is found
TAXONOMY_DETECTION_PATTERNS = {
    'US_GAAP': ['us-gaap', 'fasb.org'],
    'IFRS': ['ifrs', 'iasb'],
    'UK_GAAP': ['frc.org.uk', 'uk-gaap'],
    'ESEF': ['esef', 'esma'],
    'DEI': ['dei'],
    # Add new taxonomies here as they are discovered
}

# ==============================================================================
# SCHEMA ELEMENT TYPES
# ==============================================================================

# XSD element types that define XBRL concepts
XSD_ELEMENT = "element"
XSD_COMPLEX_TYPE = "complexType"
XSD_SIMPLE_TYPE = "simpleType"
XSD_ATTRIBUTE = "attribute"
XSD_IMPORT = "import"
XSD_INCLUDE = "include"

# ==============================================================================
# LINKBASE TYPES
# ==============================================================================

# Linkbase file suffixes (for detection)
LINKBASE_SUFFIXES = {
    'presentation': ['_pre.xml', '-pre.xml', '_presentation.xml'],
    'calculation': ['_cal.xml', '-cal.xml', '_calculation.xml'],
    'definition': ['_def.xml', '-def.xml', '_definition.xml'],
    'label': ['_lab.xml', '-lab.xml', '_label.xml'],
    'reference': ['_ref.xml', '-ref.xml', '_reference.xml']
}

# Standard linkbase roles
STANDARD_ROLES = {
    'presentation': 'http://www.xbrl.org/2003/role/presentationLink',
    'calculation': 'http://www.xbrl.org/2003/role/calculationLink',
    'definition': 'http://www.xbrl.org/2003/role/definitionLink',
    'label': 'http://www.xbrl.org/2003/role/labelLink',
    'reference': 'http://www.xbrl.org/2003/role/referenceLink'
}

# Standard arcroles
STANDARD_ARCROLES = {
    'parent-child': 'http://www.xbrl.org/2003/arcrole/parent-child',
    'summation-item': 'http://www.xbrl.org/2003/arcrole/summation-item',
    'general-special': 'http://www.xbrl.org/2003/arcrole/general-special',
    'essence-alias': 'http://www.xbrl.org/2003/arcrole/essence-alias',
    'similar-tuples': 'http://www.xbrl.org/2003/arcrole/similar-tuples',
    'requires-element': 'http://www.xbrl.org/2003/arcrole/requires-element',
    'dimension-default': 'http://xbrl.org/int/dim/arcrole/dimension-default',
    'dimension-domain': 'http://xbrl.org/int/dim/arcrole/dimension-domain',
    'domain-member': 'http://xbrl.org/int/dim/arcrole/domain-member',
    'hypercube-dimension': 'http://xbrl.org/int/dim/arcrole/hypercube-dimension',
    'all': 'http://xbrl.org/int/dim/arcrole/all',
    'notAll': 'http://xbrl.org/int/dim/arcrole/notAll'
}

# ==============================================================================
# XBRL TYPES
# ==============================================================================

# Standard XBRL types (for concept type detection)
XBRL_ITEM_TYPES = [
    'monetaryItemType',
    'sharesItemType',
    'pureItemType',
    'integerItemType',
    'decimalItemType',
    'floatItemType',
    'doubleItemType',
    'dateItemType',
    'dateTimeItemType',
    'stringItemType',
    'booleanItemType',
    'anyURIItemType'
]

# Text block type (for large text content)
TEXT_BLOCK_TYPES = [
    'textBlockItemType',
    'escapedItemType',
    'normalizedStringItemType'
]

# ==============================================================================
# PERIOD TYPES
# ==============================================================================

# XBRL period types
PERIOD_TYPE_INSTANT = "instant"
PERIOD_TYPE_DURATION = "duration"

# ==============================================================================
# BALANCE TYPES
# ==============================================================================

# XBRL balance types
BALANCE_TYPE_DEBIT = "debit"
BALANCE_TYPE_CREDIT = "credit"

# ==============================================================================
# SCHEMA LOADING LIMITS
# ==============================================================================

# Maximum recursion depth for schema imports
MAX_IMPORT_DEPTH = 50

# Maximum number of schemas to load
MAX_SCHEMA_COUNT = 1000

# Maximum file size for schema files (MB)
MAX_SCHEMA_SIZE_MB = 50

# ==============================================================================
# CACHING
# ==============================================================================

# Default cache size for taxonomy cache (MB)
DEFAULT_CACHE_SIZE_MB = 1024

# Cache entry TTL (days)
CACHE_ENTRY_TTL_DAYS = 30

# ==============================================================================
# VALIDATION
# ==============================================================================

# Required schema attributes
REQUIRED_SCHEMA_ATTRS = ['targetNamespace']

# Required element attributes
REQUIRED_ELEMENT_ATTRS = ['name']


__all__ = [
    # XML Schema
    'XSD_NS',
    'XSI_NS',
    
    # XBRL Linkbase
    'LINK_NS',
    'XLINK_NS',
    'LINKREF_NS',
    
    # XBRL Core
    'XBRLI_NS',
    'XBRLDT_NS',
    'XBRLDI_NS',
    
    # Taxonomy detection
    'TAXONOMY_DETECTION_PATTERNS',
    
    # Schema elements
    'XSD_ELEMENT',
    'XSD_COMPLEX_TYPE',
    'XSD_SIMPLE_TYPE',
    'XSD_ATTRIBUTE',
    'XSD_IMPORT',
    'XSD_INCLUDE',
    
    # Linkbase types and roles
    'LINKBASE_SUFFIXES',
    'STANDARD_ROLES',
    'STANDARD_ARCROLES',
    
    # XBRL types
    'XBRL_ITEM_TYPES',
    'TEXT_BLOCK_TYPES',
    
    # Period and balance types
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_DURATION',
    'BALANCE_TYPE_DEBIT',
    'BALANCE_TYPE_CREDIT',
    
    # Limits
    'MAX_IMPORT_DEPTH',
    'MAX_SCHEMA_COUNT',
    'MAX_SCHEMA_SIZE_MB',
    
    # Caching
    'DEFAULT_CACHE_SIZE_MB',
    'CACHE_ENTRY_TTL_DAYS',
    
    # Validation
    'REQUIRED_SCHEMA_ATTRS',
    'REQUIRED_ELEMENT_ATTRS',
]