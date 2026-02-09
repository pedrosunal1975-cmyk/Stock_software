# Path: xbrl_parser/instance/constants.py
"""
Instance Module Constants

Central repository for all instance-related constants and namespace URIs.

NO HARDCODED values should exist in other instance module files - all constants
should be imported from this file.
"""

# ==============================================================================
# XBRL INSTANCE NAMESPACES
# ==============================================================================

# XBRL Instance namespace (main namespace for instance documents)
XBRLI_NS = "http://www.xbrl.org/2003/instance"

# XBRL Dimensions Instance namespace
XBRLDI_NS = "http://xbrl.org/2006/xbrldi"

# ==============================================================================
# XBRL LINKBASE NAMESPACES
# ==============================================================================

# XBRL Linkbase namespace (for footnotes and other links)
LINK_NS = "http://www.xbrl.org/2003/linkbase"

# XLink namespace (for link relationships)
XLINK_NS = "http://www.w3.org/1999/xlink"

# ==============================================================================
# XML STANDARD NAMESPACES
# ==============================================================================

# XML Schema Instance namespace
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

# XML Schema namespace
XSD_NS = "http://www.w3.org/2001/XMLSchema"

# XML namespace (for xml:lang and other XML attributes)
XML_NS = "http://www.w3.org/XML/1998/namespace"

# ==============================================================================
# ISO CURRENCY NAMESPACE
# ==============================================================================

# ISO 4217 currency codes namespace
ISO4217_NS = "http://www.xbrl.org/2003/iso4217"

# ==============================================================================
# XBRL ELEMENT NAMES
# ==============================================================================

# Context elements
ELEM_CONTEXT = "context"
ELEM_ENTITY = "entity"
ELEM_IDENTIFIER = "identifier"
ELEM_SEGMENT = "segment"
ELEM_SCENARIO = "scenario"
ELEM_PERIOD = "period"
ELEM_INSTANT = "instant"
ELEM_START_DATE = "startDate"
ELEM_END_DATE = "endDate"
ELEM_FOREVER = "forever"

# Unit elements
ELEM_UNIT = "unit"
ELEM_MEASURE = "measure"
ELEM_DIVIDE = "divide"
ELEM_UNIT_NUMERATOR = "unitNumerator"
ELEM_UNIT_DENOMINATOR = "unitDenominator"

# Dimension elements
ELEM_EXPLICIT_MEMBER = "explicitMember"
ELEM_TYPED_MEMBER = "typedMember"

# Footnote elements
ELEM_FOOTNOTE_LINK = "footnoteLink"
ELEM_FOOTNOTE = "footnote"
ELEM_FOOTNOTE_ARC = "footnoteArc"
ELEM_LOC = "loc"

# ==============================================================================
# XBRL ATTRIBUTES
# ==============================================================================

# Common attributes
ATTR_ID = "id"
ATTR_CONTEXT_REF = "contextRef"
ATTR_UNIT_REF = "unitRef"
ATTR_DECIMALS = "decimals"
ATTR_PRECISION = "precision"

# XLink attributes
ATTR_XLINK_TYPE = "type"
ATTR_XLINK_HREF = "href"
ATTR_XLINK_ROLE = "role"
ATTR_XLINK_ARCROLE = "arcrole"
ATTR_XLINK_LABEL = "label"
ATTR_XLINK_FROM = "from"
ATTR_XLINK_TO = "to"
ATTR_XLINK_ORDER = "order"

# Entity attributes
ATTR_SCHEME = "scheme"

# Dimension attributes
ATTR_DIMENSION = "dimension"

# XML attributes
ATTR_LANG = "lang"  # Used as {XML_NS}lang

# XSI attributes
ATTR_NIL = "nil"  # Used as {XSI_NS}nil

# ==============================================================================
# FACT TYPE DETECTION PATTERNS
# ==============================================================================

# Namespace patterns that indicate standard fact types
SKIP_NAMESPACES = [
    LINK_NS,
    XSD_NS
]

# ==============================================================================
# PERIOD TYPES
# ==============================================================================

# XBRL period types
PERIOD_TYPE_INSTANT = "instant"
PERIOD_TYPE_DURATION = "duration"
PERIOD_TYPE_FOREVER = "forever"

# ==============================================================================
# PARSING LIMITS
# ==============================================================================

# Maximum number of contexts to parse
MAX_CONTEXTS = 10000

# Maximum number of units to parse
MAX_UNITS = 1000

# Maximum number of facts to parse
MAX_FACTS = 1000000

# Maximum dimension depth
MAX_DIMENSION_DEPTH = 10

# ==============================================================================
# FOOTNOTE CONSTANTS
# ==============================================================================

# Standard footnote arcrole
FOOTNOTE_ARCROLE = "http://www.xbrl.org/2003/arcrole/fact-footnote"

# Standard footnote role
FOOTNOTE_ROLE = "http://www.xbrl.org/2003/role/footnote"

# ==============================================================================
# DATE FORMATS
# ==============================================================================

# ISO date formats for XBRL dates
DATE_FORMAT_ISO = "%Y-%m-%d"
DATETIME_FORMAT_ISO = "%Y-%m-%dT%H:%M:%S"


__all__ = [
    # Namespaces
    'XBRLI_NS',
    'XBRLDI_NS',
    'LINK_NS',
    'XLINK_NS',
    'XSI_NS',
    'XSD_NS',
    'XML_NS',
    'ISO4217_NS',
    
    # Elements
    'ELEM_CONTEXT',
    'ELEM_ENTITY',
    'ELEM_IDENTIFIER',
    'ELEM_SEGMENT',
    'ELEM_SCENARIO',
    'ELEM_PERIOD',
    'ELEM_INSTANT',
    'ELEM_START_DATE',
    'ELEM_END_DATE',
    'ELEM_FOREVER',
    'ELEM_UNIT',
    'ELEM_MEASURE',
    'ELEM_DIVIDE',
    'ELEM_UNIT_NUMERATOR',
    'ELEM_UNIT_DENOMINATOR',
    'ELEM_EXPLICIT_MEMBER',
    'ELEM_TYPED_MEMBER',
    'ELEM_FOOTNOTE_LINK',
    'ELEM_FOOTNOTE',
    'ELEM_FOOTNOTE_ARC',
    'ELEM_LOC',
    
    # Attributes
    'ATTR_ID',
    'ATTR_CONTEXT_REF',
    'ATTR_UNIT_REF',
    'ATTR_DECIMALS',
    'ATTR_PRECISION',
    'ATTR_XLINK_TYPE',
    'ATTR_XLINK_HREF',
    'ATTR_XLINK_ROLE',
    'ATTR_XLINK_ARCROLE',
    'ATTR_XLINK_LABEL',
    'ATTR_XLINK_FROM',
    'ATTR_XLINK_TO',
    'ATTR_XLINK_ORDER',
    'ATTR_SCHEME',
    'ATTR_DIMENSION',
    'ATTR_LANG',
    'ATTR_NIL',
    
    # Patterns
    'SKIP_NAMESPACES',
    
    # Period types
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_DURATION',
    'PERIOD_TYPE_FOREVER',
    
    # Limits
    'MAX_CONTEXTS',
    'MAX_UNITS',
    'MAX_FACTS',
    'MAX_DIMENSION_DEPTH',
    
    # Footnotes
    'FOOTNOTE_ARCROLE',
    'FOOTNOTE_ROLE',
    
    # Date formats
    'DATE_FORMAT_ISO',
    'DATETIME_FORMAT_ISO',
]