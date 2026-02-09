# Path: verification/engine/checks_v2/tools/dimension/__init__.py
"""
Dimension Tools for XBRL Verification

Provides dimensional structure parsing and analysis.

Modules:
- dimension_info: Data structures for dimensional information
- dimension_parser: Parse definition linkbase and instance contexts

XBRL DIMENSIONAL CONCEPTS:
1. Hypercube (Table): Container for dimensional structure
2. Dimension (Axis): A dimensional qualifier (e.g., ClassOfStockAxis)
3. Domain: The set of allowed values for a dimension
4. Member: A specific value in a domain (e.g., CommonClassAMember)
5. Default Member: The member that applies when no explicit qualifier is given

Usage:
    from verification.engine.checks_v2.tools.dimension import (
        DimensionParser,
        Dimension,
        RoleDimensions,
        ContextDimensions,
    )

    # Parse definition linkbase
    parser = DimensionParser()
    parser.parse_definition_linkbase('path/to/_def.xml')

    # Check if context is default
    is_default = parser.is_default_context('c-4')
"""

from .dimension_info import (
    DimensionMember,
    Dimension,
    RoleDimensions,
    ContextDimensions,
)
from .dimension_parser import DimensionParser


__all__ = [
    'DimensionMember',
    'Dimension',
    'RoleDimensions',
    'ContextDimensions',
    'DimensionParser',
]
