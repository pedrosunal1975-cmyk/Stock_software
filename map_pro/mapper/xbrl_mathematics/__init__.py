"""
XBRL Mathematical Formulas and Processing Rules

This package contains Python implementations of formulas and rules defined in
the XBRL 2.1 Specification that CANNOT be extracted programmatically from
XBRL filings or taxonomy files.

CRITICAL DESIGN PRINCIPLE:
-------------------------
This library contains ONLY formulas/rules that exist in specification prose.
If something can be extracted from:
- Company XBRL files (instance documents)
- Taxonomy schemas (.xsd)
- Linkbase files (_cal.xml, _pre.xml, _def.xml, _lab.xml)
- Declared namespaces
Then it does NOT belong here - it should be extracted from those sources instead.

AUTHORITY:
----------
XBRL 2.1 Specification (W3C Recommendation)
Published by: XBRL International (now IFRS Foundation)
Date: December 31, 2003 (corrected February 20, 2013)
URL: http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/
     XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html

SCOPE:
------
UNIVERSAL (Market-Agnostic) - applies to ALL XBRL 2.1 filings globally

WHAT BELONGS HERE:
-----------------
âœ… Decimals scaling formula (Section 4.6.5)
âœ… Precision scaling formula (Section 4.6.4)
âœ… Context matching rules (Section 4.7)
âœ… Period type validation (Section 4.9)
âœ… QName resolution algorithm (Section 5.1)
âœ… Calculation validation formula (Section 5.2.5)
âœ… Duplicate fact detection (Section 4.10)

WHAT DOES NOT BELONG HERE:
--------------------------
âŒ Calculation relationships (extract from _cal.xml)
âŒ Presentation hierarchy (extract from _pre.xml)
âŒ Dimension definitions (extract from _def.xml)
âŒ Concept definitions (extract from .xsd)
âŒ Unit structures (extract from instance)
âŒ Context structures (extract from instance)
"""

# Version info
__version__ = '1.0.0'
__spec_version__ = 'XBRL 2.1 (2003-12-31, corrected 2013-02-20)'
__spec_authority__ = 'XBRL International / IFRS Foundation'

# Import formulas
from .decimals import (
    scale_value_with_decimals,
    scale_value_with_precision,
    infer_decimals_from_precision,
    parse_decimals_attribute,
    parse_precision_attribute,
)

from .context import (
    contexts_match,
    periods_match,
    entities_match,
    segments_match,
)

from .period import (
    validate_period_type,
    PERIOD_TYPE_INSTANT,
    PERIOD_TYPE_DURATION,
    PERIOD_TYPE_FOREVER,
    VALID_PERIOD_TYPES,
    PeriodType,
)

from .qname import (
    resolve_qname,
    split_qname,
)

from .validation import (
    detect_duplicate_fact,
    validate_calculation_arc,
)

from .arcroles import (
    # XBRL 2.1 arcroles
    ARCROLE_PARENT_CHILD,
    ARCROLE_SUMMATION_ITEM,
    PRESENTATION_ARCROLES,
    CALCULATION_ARCROLES,
    DEFINITION_ARCROLES,
    # XBRL Dimensions arcroles
    ARCROLE_HYPERCUBE_DIMENSION,
    ARCROLE_DIMENSION_DOMAIN,
    ARCROLE_DOMAIN_MEMBER,
    ARCROLE_ALL,
    ARCROLE_NOTALL,
    DIMENSION_ARCROLES,
    ALL_ARCROLES,
)

# Public API
__all__ = [
    # Decimals and precision (Section 4.6)
    'scale_value_with_decimals',
    'scale_value_with_precision',
    'infer_decimals_from_precision',
    'parse_decimals_attribute',
    'parse_precision_attribute',
    
    # Context matching (Section 4.7)
    'contexts_match',
    'periods_match',
    'entities_match',
    'segments_match',
    
    # Period validation and constants (Section 4.7.2, 4.9)
    'validate_period_type',
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_DURATION',
    'PERIOD_TYPE_FOREVER',
    'VALID_PERIOD_TYPES',
    'PeriodType',
    
    # QName resolution (Section 5.1)
    'resolve_qname',
    'split_qname',
    
    # Validation (Sections 4.10, 5.2.5)
    'detect_duplicate_fact',
    'validate_calculation_arc',
    
    # Arcrole URIs (Section 5.2 and XBRL Dimensions)
    'ARCROLE_PARENT_CHILD',
    'ARCROLE_SUMMATION_ITEM',
    'PRESENTATION_ARCROLES',
    'CALCULATION_ARCROLES',
    'DEFINITION_ARCROLES',
    'ARCROLE_HYPERCUBE_DIMENSION',
    'ARCROLE_DIMENSION_DOMAIN',
    'ARCROLE_DOMAIN_MEMBER',
    'ARCROLE_ALL',
    'ARCROLE_NOTALL',
    'DIMENSION_ARCROLES',
    'ALL_ARCROLES',
]