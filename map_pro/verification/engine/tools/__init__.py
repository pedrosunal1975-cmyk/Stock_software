# Path: verification/engine/checks_v2/tools/__init__.py
"""
Verification Tools Module

Specialized, reusable skill modules for XBRL verification.

Each tool provides focused functionality that can be used across all
processing stages. Tools are stateless and adaptable - processors
can pick up and drop them as needed.

Categories:
- naming: Concept name normalization and extraction
- period: Period extraction and comparison
- sign: Sign correction parsing and lookup
- context: Context classification, matching, and grouping
- fact: Fact finding, parsing, and duplicate handling
- dimension: Dimensional structure parsing
- hierarchy: Binding checking for calculation hierarchies
- calculation: Calculation weights and sum verification
- tolerance: Decimal tolerance and value comparison
"""

# Import all tools for easy access
from .naming import (
    Normalizer,
    LocalNameExtractor,
    normalize_name,
    extract_local_name,
)

from .period import (
    PeriodExtractor,
    PeriodComparator,
    PeriodInfo,
)

from .sign import (
    SignParser,
    SignLookup,
    SignInfo,
    SemanticSignInferrer,
)

from .context import (
    ContextClassifier,
    ContextMatcher,
    ContextGrouper,
    ContextGroup,
)

from .fact import (
    ValueParser,
    FactEntry,
    FactMatch,
    ChildContribution,
    DuplicateHandler,
    DuplicateInfo,
    FactFinder,
)

from .dimension import (
    DimensionParser,
    Dimension,
    DimensionMember,
    RoleDimensions,
    ContextDimensions,
)

from .hierarchy import (
    BindingChecker,
    BindingResult,
)

from .calculation import (
    WeightHandler,
    SumCalculator,
    SumResult,
)

from .tolerance import (
    DecimalTolerance,
    ToleranceResult,
    ToleranceChecker,
)


__all__ = [
    # Naming
    'Normalizer',
    'LocalNameExtractor',
    'normalize_name',
    'extract_local_name',
    # Period
    'PeriodExtractor',
    'PeriodComparator',
    'PeriodInfo',
    # Sign
    'SignParser',
    'SignLookup',
    'SignInfo',
    'SemanticSignInferrer',
    # Context
    'ContextClassifier',
    'ContextMatcher',
    'ContextGrouper',
    'ContextGroup',
    # Fact
    'ValueParser',
    'FactEntry',
    'FactMatch',
    'ChildContribution',
    'DuplicateHandler',
    'DuplicateInfo',
    'FactFinder',
    # Dimension
    'DimensionParser',
    'Dimension',
    'DimensionMember',
    'RoleDimensions',
    'ContextDimensions',
    # Hierarchy
    'BindingChecker',
    'BindingResult',
    # Calculation
    'WeightHandler',
    'SumCalculator',
    'SumResult',
    # Tolerance
    'DecimalTolerance',
    'ToleranceResult',
    'ToleranceChecker',
]
