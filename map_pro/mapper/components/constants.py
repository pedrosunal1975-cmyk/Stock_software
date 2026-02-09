# Path: components/constants.py
"""
Components Constants

This module re-exports XBRL specification constants from xbrl_mathematics/
for convenient access by components.

DESIGN PRINCIPLE:
----------------
ALL constants in this file are imported from xbrl_mathematics/
NO new hardcoded values should be added here - only re-exports.

SOURCE HIERARCHY:
1. Primary: XBRL filings (instance, linkbases, taxonomies)
2. Fallback: xbrl_mathematics/ (spec formulas not in filings)
3. This file: Re-exports from xbrl_mathematics/ for convenience

If you need a new constant:
1. Check if it's from XBRL specification
2. If yes, add to appropriate xbrl_mathematics/ file
3. Then re-export it here
4. If no (company/market specific), it doesn't belong in constants
"""

# Import from xbrl_mathematics
from ..xbrl_mathematics.period import (
    PERIOD_TYPE_INSTANT,
    PERIOD_TYPE_DURATION,
    PERIOD_TYPE_FOREVER,
    VALID_PERIOD_TYPES,
    PeriodType,
)

from ..xbrl_mathematics.arcroles import (
    # Individual arcrole URIs
    ARCROLE_PARENT_CHILD,
    ARCROLE_SUMMATION_ITEM,
    ARCROLE_HYPERCUBE_DIMENSION,
    ARCROLE_DIMENSION_DOMAIN,
    ARCROLE_DOMAIN_MEMBER,
    ARCROLE_ALL,
    ARCROLE_NOTALL,
    
    # Arcrole dictionaries
    PRESENTATION_ARCROLES,
    CALCULATION_ARCROLES,
    DEFINITION_ARCROLES,
    DIMENSION_ARCROLES,
    ALL_ARCROLES,
)


__all__ = [
    # Period types (from XBRL 2.1 Spec Section 4.7.2)
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_DURATION',
    'PERIOD_TYPE_FOREVER',
    'VALID_PERIOD_TYPES',
    'PeriodType',
    
    # Arcrole URIs (from XBRL 2.1 Spec Section 5.2)
    'ARCROLE_PARENT_CHILD',
    'ARCROLE_SUMMATION_ITEM',
    
    # Dimension arcrole URIs (from XBRL Dimensions 1.0 Spec)
    'ARCROLE_HYPERCUBE_DIMENSION',
    'ARCROLE_DIMENSION_DOMAIN',
    'ARCROLE_DOMAIN_MEMBER',
    'ARCROLE_ALL',
    'ARCROLE_NOTALL',
    
    # Arcrole dictionaries
    'PRESENTATION_ARCROLES',
    'CALCULATION_ARCROLES',
    'DEFINITION_ARCROLES',
    'DIMENSION_ARCROLES',
    'ALL_ARCROLES',
]