# Path: components/__init__.py
"""
Components Module - Water Paradigm

Core utilities for XBRL extraction (no transformation).

Essential components:
- QNameUtils: QName parsing and manipulation
- Validators: Basic data validation
- RelationshipNavigator: Navigate taxonomy relationships
- DimensionHandler: Handle dimensional contexts
- PeriodNormalizer: Period formatting

Example:
    from ..components import QNameUtils
    
    # Parse QNames
    local_name = QNameUtils.get_local_name('us-gaap:Revenue')
    namespace = QNameUtils.get_namespace('us-gaap:Revenue')
"""

# Core utilities (KEEP)
from .qname_utils import QNameUtils, QName
from .validators import (
    Validators,
    ValidationError,
    validate_fact,
    validate_context,
)

# XBRL Specification Constants (from xbrl_mathematics/)
from . import constants

# Relationship and dimension utilities (KEEP - used by StatementBuilder)
from .relationship_navigator import (
    RelationshipNavigator,
    Relationship,
)
from .dimension_handler import (
    DimensionHandler,
    DimensionMember,
    DimensionAxis,
    Hypercube,
    DimensionalContext,
)

# Note: period_normalizer can be imported directly if needed

__all__ = [
    # QName utilities
    'QNameUtils',
    'QName',
    
    # Validation
    'Validators',
    'ValidationError',
    'validate_fact',
    'validate_context',
    
    # Constants (XBRL Specification constants)
    'constants',
    
    # Relationship Navigation
    'RelationshipNavigator',
    'Relationship',
    
    # Dimension Handling
    'DimensionHandler',
    'DimensionMember',
    'DimensionAxis',
    'Hypercube',
    'DimensionalContext',
]