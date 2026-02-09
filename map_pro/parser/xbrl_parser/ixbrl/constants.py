# Path: xbrl_parser/ixbrl/constants.py
"""
iXBRL Constants

Central repository for iXBRL-specific constants.
Market-agnostic, standards-based namespaces and patterns.

All constants are based on XBRL and iXBRL specifications:
- XBRL 2.1 Specification
- Inline XBRL 1.0 (2011) and 1.1 (2013) Specifications
- ISO 4217 Currency Codes
- ISO 17442 Legal Entity Identifier (LEI)
"""

# ==============================================================================
# XBRL NAMESPACES - STANDARD
# ==============================================================================

# XBRL Instance namespace (http://www.xbrl.org/2003/instance)
XBRLI_NS = 'http://www.xbrl.org/2003/instance'

# XBRL Linkbase namespace
LINK_NS = 'http://www.xbrl.org/2003/linkbase'

# XLink namespace
XLINK_NS = 'http://www.w3.org/1999/xlink'

# XML namespace
XML_NS = 'http://www.w3.org/XML/1998/namespace'

# XSI namespace (XML Schema Instance)
XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'

# ==============================================================================
# iXBRL NAMESPACES
# ==============================================================================

# Inline XBRL 1.0 (2011 specification)
# Used in older iXBRL filings
IX_NS_2011 = 'http://www.xbrl.org/2008/inlineXBRL'

# Inline XBRL 1.1 (2013 specification)
# Most common in current filings
IX_NS_2013 = 'http://www.xbrl.org/2013/inlineXBRL'

# Default to 2013 version (most widely adopted)
IX_NS = IX_NS_2013

# ==============================================================================
# ISO 4217 CURRENCY CODES
# ==============================================================================

# ISO 4217 namespace for currency codes
ISO4217_NS = 'http://www.xbrl.org/2003/iso4217'

# ==============================================================================
# ENTITY IDENTIFIER SCHEMES (Market-Agnostic)
# ==============================================================================

# These are standard schemes defined by regulatory bodies and international organizations
# NO HARDCODED values - these are official URI patterns from specifications

# US SEC Central Index Key (CIK) scheme
# Used by US SEC for entity identification
SEC_CIK_SCHEME = 'http://www.sec.gov/CIK'

# Legal Entity Identifier (LEI) scheme - ISO 17442
# Global standard for entity identification
LEI_SCHEME = 'http://standards.iso.org/iso/17442'

# UK Companies House scheme
# Used by UK Financial Reporting Council (FRC)
UK_COMPANIES_HOUSE_SCHEME = 'http://www.companieshouse.gov.uk/'

# EU LEI scheme (alternative form)
# Used by European Securities and Markets Authority (ESMA)
EU_LEI_SCHEME = 'http://standard.iso.org/iso/17442'

# ==============================================================================
# XBRL DATE/TIME FORMATS
# ==============================================================================

# ISO 8601 date format (YYYY-MM-DD)
# Standard format for XBRL dates
XBRL_DATE_FORMAT = '%Y-%m-%d'

# ISO 8601 datetime format
# Standard format for XBRL datetimes
XBRL_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

# ==============================================================================
# iXBRL ELEMENT NAMES
# ==============================================================================

# iXBRL fact elements (from Inline XBRL spec)
IX_NON_FRACTION = 'nonFraction'
IX_NON_NUMERIC = 'nonNumeric'
IX_FRACTION = 'fraction'

# iXBRL structural elements
IX_HIDDEN = 'hidden'                # Hidden facts section
IX_HEADER = 'header'                # Document header section
IX_RESOURCES = 'resources'          # Resources section (contexts, units)
IX_REFERENCES = 'references'        # Schema references section
IX_CONTINUATION = 'continuation'    # Continuation for split content
IX_FOOTNOTE = 'footnote'            # Footnote element

# ==============================================================================
# XBRL STRUCTURAL ELEMENTS
# ==============================================================================

XBRL_CONTEXT = 'context'            # Context element
XBRL_UNIT = 'unit'                  # Unit element
XBRL_SCHEMA_REF = 'schemaRef'       # Schema reference element

# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    # Standard XBRL namespaces
    'XBRLI_NS',
    'LINK_NS',
    'XLINK_NS',
    'XML_NS',
    'XSI_NS',
    
    # iXBRL namespaces
    'IX_NS',
    'IX_NS_2011',
    'IX_NS_2013',
    
    # ISO standards
    'ISO4217_NS',
    
    # Entity identifier schemes
    'SEC_CIK_SCHEME',
    'LEI_SCHEME',
    'UK_COMPANIES_HOUSE_SCHEME',
    'EU_LEI_SCHEME',
    
    # Date/time formats
    'XBRL_DATE_FORMAT',
    'XBRL_DATETIME_FORMAT',
    
    # iXBRL element names
    'IX_NON_FRACTION',
    'IX_NON_NUMERIC',
    'IX_FRACTION',
    'IX_HIDDEN',
    'IX_HEADER',
    'IX_RESOURCES',
    'IX_REFERENCES',
    'IX_CONTINUATION',
    'IX_FOOTNOTE',
    
    # XBRL structural elements
    'XBRL_CONTEXT',
    'XBRL_UNIT',
    'XBRL_SCHEMA_REF',
]