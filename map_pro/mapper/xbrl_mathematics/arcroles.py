# Path: xbrl_mathematics/arcroles.py
"""
XBRL Arcrole URI Constants

This module contains standard arcrole URIs defined in XBRL specifications.
These URIs are used to identify relationship types in linkbases.

SOURCE AUTHORITY:
----------------
XBRL 2.1 Specification Section 5.2 "Linkbases"
XBRL Dimensions 1.0 Specification

Published by: XBRL International (now IFRS Foundation)

CRITICAL NOTE:
-------------
This module contains ONLY the arcrole URI CONSTANTS from specifications.
The actual relationships (parent-child, calculation, etc.) come from
linkbase files (_pre.xml, _cal.xml, _def.xml) - NOT here.

SCOPE:
------
UNIVERSAL - applies to all XBRL 2.1 and XBRL Dimensions filings globally
"""



# =============================================================================
# XBRL 2.1 SPECIFICATION ARCROLES
# =============================================================================

# Section 5.2.3 - Presentation Linkbase
ARCROLE_PARENT_CHILD = 'http://www.xbrl.org/2003/arcrole/parent-child'

# Section 5.2.5 - Calculation Linkbase  
ARCROLE_SUMMATION_ITEM = 'http://www.xbrl.org/2003/arcrole/summation-item'

# Section 5.2.6 - Definition Linkbase
ARCROLE_GENERAL_SPECIAL = 'http://www.xbrl.org/2003/arcrole/general-special'
ARCROLE_ESSENCE_ALIAS = 'http://www.xbrl.org/2003/arcrole/essence-alias'
ARCROLE_SIMILAR_TUPLES = 'http://www.xbrl.org/2003/arcrole/similar-tuples'
ARCROLE_REQUIRES_ELEMENT = 'http://www.xbrl.org/2003/arcrole/requires-element'

# =============================================================================
# XBRL DIMENSIONS 1.0 SPECIFICATION ARCROLES
# =============================================================================

# Hypercube-Dimension Relationships
ARCROLE_HYPERCUBE_DIMENSION = 'http://xbrl.org/int/dim/arcrole/hypercube-dimension'

# Dimension-Domain Relationships
ARCROLE_DIMENSION_DOMAIN = 'http://xbrl.org/int/dim/arcrole/dimension-domain'

# Domain-Member Relationships
ARCROLE_DOMAIN_MEMBER = 'http://xbrl.org/int/dim/arcrole/domain-member'

# Primary Item-Hypercube Relationships
ARCROLE_ALL = 'http://xbrl.org/int/dim/arcrole/all'
ARCROLE_NOTALL = 'http://xbrl.org/int/dim/arcrole/notAll'

# Dimension-Default Relationships
ARCROLE_DIMENSION_DEFAULT = 'http://xbrl.org/int/dim/arcrole/dimension-default'


# =============================================================================
# ARCROLE DICTIONARIES (for convenience)
# =============================================================================

# XBRL 2.1 Arcroles
PRESENTATION_ARCROLES: dict[str, str] = {
    'parent-child': ARCROLE_PARENT_CHILD,
}

CALCULATION_ARCROLES: dict[str, str] = {
    'summation-item': ARCROLE_SUMMATION_ITEM,
}

DEFINITION_ARCROLES: dict[str, str] = {
    'general-special': ARCROLE_GENERAL_SPECIAL,
    'essence-alias': ARCROLE_ESSENCE_ALIAS,
    'similar-tuples': ARCROLE_SIMILAR_TUPLES,
    'requires-element': ARCROLE_REQUIRES_ELEMENT,
}

# XBRL Dimensions 1.0 Arcroles
DIMENSION_ARCROLES: dict[str, str] = {
    'hypercube-dimension': ARCROLE_HYPERCUBE_DIMENSION,
    'dimension-domain': ARCROLE_DIMENSION_DOMAIN,
    'domain-member': ARCROLE_DOMAIN_MEMBER,
    'all': ARCROLE_ALL,
    'notAll': ARCROLE_NOTALL,
    'dimension-default': ARCROLE_DIMENSION_DEFAULT,
}

# All arcroles combined
ALL_ARCROLES: dict[str, str] = {
    **PRESENTATION_ARCROLES,
    **CALCULATION_ARCROLES,
    **DEFINITION_ARCROLES,
    **DIMENSION_ARCROLES,
}


# =============================================================================
# REVERSE LOOKUP (URI -> Name)
# =============================================================================

ARCROLE_NAMES: dict[str, str] = {
    v: k for k, v in ALL_ARCROLES.items()
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_arcrole_uri(arcrole_name: str) -> str:
    """
    Get full arcrole URI from short name.
    
    Args:
        arcrole_name: Short name (e.g., 'parent-child', 'summation-item')
        
    Returns:
        Full arcrole URI
        
    Raises:
        KeyError: If arcrole name not found
        
    Examples:
        >>> get_arcrole_uri('parent-child')
        'http://www.xbrl.org/2003/arcrole/parent-child'
        
        >>> get_arcrole_uri('hypercube-dimension')
        'http://xbrl.org/int/dim/arcrole/hypercube-dimension'
    """
    return ALL_ARCROLES[arcrole_name]


def get_arcrole_name(arcrole_uri: str) -> str:
    """
    Get short name from arcrole URI.
    
    Args:
        arcrole_uri: Full arcrole URI
        
    Returns:
        Short name
        
    Raises:
        KeyError: If arcrole URI not found
        
    Examples:
        >>> get_arcrole_name('http://www.xbrl.org/2003/arcrole/parent-child')
        'parent-child'
        
        >>> get_arcrole_name('http://xbrl.org/int/dim/arcrole/hypercube-dimension')
        'hypercube-dimension'
    """
    return ARCROLE_NAMES[arcrole_uri]


def is_standard_arcrole(arcrole_uri: str) -> bool:
    """
    Check if arcrole URI is from XBRL specification.
    
    Args:
        arcrole_uri: Arcrole URI to check
        
    Returns:
        True if standard arcrole from XBRL spec
        
    Examples:
        >>> is_standard_arcrole('http://www.xbrl.org/2003/arcrole/parent-child')
        True
        
        >>> is_standard_arcrole('http://company.com/arcrole/custom')
        False
    """
    return arcrole_uri in ARCROLE_NAMES


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Individual arcrole URIs
    'ARCROLE_PARENT_CHILD',
    'ARCROLE_SUMMATION_ITEM',
    'ARCROLE_GENERAL_SPECIAL',
    'ARCROLE_ESSENCE_ALIAS',
    'ARCROLE_SIMILAR_TUPLES',
    'ARCROLE_REQUIRES_ELEMENT',
    'ARCROLE_HYPERCUBE_DIMENSION',
    'ARCROLE_DIMENSION_DOMAIN',
    'ARCROLE_DOMAIN_MEMBER',
    'ARCROLE_ALL',
    'ARCROLE_NOTALL',
    'ARCROLE_DIMENSION_DEFAULT',
    
    # Dictionaries
    'PRESENTATION_ARCROLES',
    'CALCULATION_ARCROLES',
    'DEFINITION_ARCROLES',
    'DIMENSION_ARCROLES',
    'ALL_ARCROLES',
    'ARCROLE_NAMES',
    
    # Helper functions
    'get_arcrole_uri',
    'get_arcrole_name',
    'is_standard_arcrole',
]