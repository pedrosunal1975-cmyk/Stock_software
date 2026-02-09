# Path: verification/engine/checks_v2/constants/xbrl.py
"""
XBRL Specification Constants

Constants from XBRL 2.1 specification and related standards.
These are fixed by the XBRL specification, not configurable.

Categories:
1. XML Namespaces - Standard XBRL namespace URIs
2. XLink Attributes - Standard XLink attribute names
3. Linkbase Elements - Element names in linkbase documents
4. Arcroles - Standard arcrole URIs
5. Dimension Constants - XBRL Dimensions 1.0 constants
"""

# ==============================================================================
# XML NAMESPACE URIs (XBRL 2.1 Specification)
# ==============================================================================

# XLink namespace - used for linkbase arcs and locators
XLINK_NAMESPACE = 'http://www.w3.org/1999/xlink'

# XBRL Linkbase namespace - for linkbase document elements
XBRL_LINKBASE_NAMESPACE = 'http://www.xbrl.org/2003/linkbase'

# XBRL Instance namespace - for instance document elements
XBRL_INSTANCE_NAMESPACE = 'http://www.xbrl.org/2003/instance'

# XBRL Dimensions namespace - for dimensional elements
XBRL_DIMENSIONS_NAMESPACE = 'http://xbrl.org/2005/xbrldt'

# XBRL Dimensional Instance namespace - for explicit members
XBRL_DIMENSIONAL_INSTANCE_NAMESPACE = 'http://xbrl.org/2006/xbrldi'


# ==============================================================================
# XLINK ATTRIBUTE NAMES
# ==============================================================================
# Pre-formatted attribute names with Clark notation for XML parsing.
# Usage: element.get(XLINK_ATTRS['from'])

XLINK_ATTRS = {
    'from': f'{{{XLINK_NAMESPACE}}}from',
    'to': f'{{{XLINK_NAMESPACE}}}to',
    'label': f'{{{XLINK_NAMESPACE}}}label',
    'href': f'{{{XLINK_NAMESPACE}}}href',
    'role': f'{{{XLINK_NAMESPACE}}}role',
    'arcrole': f'{{{XLINK_NAMESPACE}}}arcrole',
    'type': f'{{{XLINK_NAMESPACE}}}type',
    'title': f'{{{XLINK_NAMESPACE}}}title',
    'show': f'{{{XLINK_NAMESPACE}}}show',
    'actuate': f'{{{XLINK_NAMESPACE}}}actuate',
}


# ==============================================================================
# LINKBASE ELEMENT NAMES
# ==============================================================================
# Standard element local names in linkbase documents.
# Used when iterating over linkbase content.

LINKBASE_ELEMENTS = {
    # Calculation linkbase
    'calculation_link': 'calculationLink',
    'calculation_arc': 'calculationArc',
    # Presentation linkbase
    'presentation_link': 'presentationLink',
    'presentation_arc': 'presentationArc',
    # Definition linkbase
    'definition_link': 'definitionLink',
    'definition_arc': 'definitionArc',
    # Label linkbase
    'label_link': 'labelLink',
    'label_arc': 'labelArc',
    'label': 'label',
    # Common elements
    'locator': 'loc',
    'linkbase': 'linkbase',
}


# ==============================================================================
# ARC ATTRIBUTES
# ==============================================================================
# Standard attribute names on linkbase arcs

ARC_ATTRIBUTES = [
    'order',           # Ordering of arc
    'priority',        # Arc priority for override
    'use',             # 'optional' or 'prohibited'
    'weight',          # Calculation weight (-1.0 or 1.0)
    'preferredLabel',  # Preferred label role
]


# ==============================================================================
# ARCROLE URIs
# ==============================================================================
# Standard arcrole URIs from XBRL specification.
# These identify the semantic meaning of arc relationships.

# Base arcrole URI
ARCROLE_BASE = 'http://www.xbrl.org/2003/arcrole'

# Calculation relationships
ARCROLE_CALCULATION = f'{ARCROLE_BASE}/summation-item'
ARCROLE_SUMMATION_ITEM = ARCROLE_CALCULATION  # Alias

# Presentation relationships
ARCROLE_PARENT_CHILD = f'{ARCROLE_BASE}/parent-child'

# Definition relationships
ARCROLE_GENERAL_SPECIAL = f'{ARCROLE_BASE}/general-special'
ARCROLE_ESSENCE_ALIAS = f'{ARCROLE_BASE}/essence-alias'
ARCROLE_SIMILAR_TUPLES = f'{ARCROLE_BASE}/similar-tuples'
ARCROLE_REQUIRES_ELEMENT = f'{ARCROLE_BASE}/requires-element'

# Label relationships
ARCROLE_CONCEPT_LABEL = f'{ARCROLE_BASE}/concept-label'

# Dimensional arcroles (XBRL Dimensions 1.0)
ARCROLE_DIM_BASE = 'http://xbrl.org/int/dim/arcrole'
ARCROLE_ALL = f'{ARCROLE_DIM_BASE}/all'
ARCROLE_NOT_ALL = f'{ARCROLE_DIM_BASE}/notAll'
ARCROLE_HYPERCUBE_DIMENSION = f'{ARCROLE_DIM_BASE}/hypercube-dimension'
ARCROLE_DIMENSION_DOMAIN = f'{ARCROLE_DIM_BASE}/dimension-domain'
ARCROLE_DOMAIN_MEMBER = f'{ARCROLE_DIM_BASE}/domain-member'
ARCROLE_DIMENSION_DEFAULT = f'{ARCROLE_DIM_BASE}/dimension-default'


# ==============================================================================
# ROLE URIs
# ==============================================================================
# Standard role URIs for linkbase elements

ROLE_BASE = 'http://www.xbrl.org/2003/role'

# Standard label roles
ROLE_LABEL = f'{ROLE_BASE}/label'
ROLE_TERSE_LABEL = f'{ROLE_BASE}/terseLabel'
ROLE_VERBOSE_LABEL = f'{ROLE_BASE}/verboseLabel'
ROLE_POSITIVE_LABEL = f'{ROLE_BASE}/positiveLabel'
ROLE_NEGATIVE_LABEL = f'{ROLE_BASE}/negativeLabel'
ROLE_ZERO_LABEL = f'{ROLE_BASE}/zeroLabel'
ROLE_TOTAL_LABEL = f'{ROLE_BASE}/totalLabel'
ROLE_PERIOD_START_LABEL = f'{ROLE_BASE}/periodStartLabel'
ROLE_PERIOD_END_LABEL = f'{ROLE_BASE}/periodEndLabel'
ROLE_DOCUMENTATION = f'{ROLE_BASE}/documentation'


# ==============================================================================
# CALCULATION WEIGHTS
# ==============================================================================
# Standard calculation weights in XBRL calculation linkbase

WEIGHT_ADD = 1.0       # Child adds to parent
WEIGHT_SUBTRACT = -1.0  # Child subtracts from parent


# ==============================================================================
# DECIMAL PRECISION VALUES
# ==============================================================================
# Special precision values

DECIMALS_INF = 'INF'  # Infinite precision (exact value)


__all__ = [
    # Namespaces
    'XLINK_NAMESPACE',
    'XBRL_LINKBASE_NAMESPACE',
    'XBRL_INSTANCE_NAMESPACE',
    'XBRL_DIMENSIONS_NAMESPACE',
    'XBRL_DIMENSIONAL_INSTANCE_NAMESPACE',
    # Attributes
    'XLINK_ATTRS',
    'ARC_ATTRIBUTES',
    # Element names
    'LINKBASE_ELEMENTS',
    # Arcroles
    'ARCROLE_BASE',
    'ARCROLE_CALCULATION',
    'ARCROLE_SUMMATION_ITEM',
    'ARCROLE_PARENT_CHILD',
    'ARCROLE_GENERAL_SPECIAL',
    'ARCROLE_ESSENCE_ALIAS',
    'ARCROLE_SIMILAR_TUPLES',
    'ARCROLE_REQUIRES_ELEMENT',
    'ARCROLE_CONCEPT_LABEL',
    'ARCROLE_DIM_BASE',
    'ARCROLE_ALL',
    'ARCROLE_NOT_ALL',
    'ARCROLE_HYPERCUBE_DIMENSION',
    'ARCROLE_DIMENSION_DOMAIN',
    'ARCROLE_DOMAIN_MEMBER',
    'ARCROLE_DIMENSION_DEFAULT',
    # Roles
    'ROLE_BASE',
    'ROLE_LABEL',
    'ROLE_TERSE_LABEL',
    'ROLE_VERBOSE_LABEL',
    'ROLE_POSITIVE_LABEL',
    'ROLE_NEGATIVE_LABEL',
    'ROLE_ZERO_LABEL',
    'ROLE_TOTAL_LABEL',
    'ROLE_PERIOD_START_LABEL',
    'ROLE_PERIOD_END_LABEL',
    'ROLE_DOCUMENTATION',
    # Weights
    'WEIGHT_ADD',
    'WEIGHT_SUBTRACT',
    # Precision
    'DECIMALS_INF',
]
