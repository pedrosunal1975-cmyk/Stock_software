# Path: mat_acc/process/hierarchy/constants.py
"""
Constants for Hierarchy Builder

Defines node types, roles, and structure constants used
throughout the hierarchy building process.
"""

from enum import Enum
from typing import Final


# ==============================================================================
# NODE TYPE ENUMERATION
# ==============================================================================
class NodeType(Enum):
    """
    Types of nodes in the hierarchy tree.

    ROOT: Top-level statement node (e.g., "Balance Sheet")
    ABSTRACT: Grouping node with no value (e.g., "Current Assets")
    LINE_ITEM: Actual line item with value (e.g., "Cash and Equivalents")
    TOTAL: Calculated total node (e.g., "Total Current Assets")
    DIMENSION_MEMBER: Dimensional breakdown member
    """
    ROOT = "root"
    ABSTRACT = "abstract"
    LINE_ITEM = "line_item"
    TOTAL = "total"
    DIMENSION_MEMBER = "dimension_member"


class StatementType(Enum):
    """
    Standard financial statement types.
    """
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW = "cash_flow"
    EQUITY = "equity"
    COMPREHENSIVE_INCOME = "comprehensive_income"
    UNKNOWN = "unknown"


class LinkbaseRole(Enum):
    """
    XBRL linkbase roles used for hierarchy building.
    """
    PRESENTATION = "presentation"
    CALCULATION = "calculation"
    DEFINITION = "definition"
    LABEL = "label"


# ==============================================================================
# HIERARCHY DEPTH LIMITS
# ==============================================================================
MAX_HIERARCHY_DEPTH: Final[int] = 15
"""Maximum allowed depth for hierarchy trees (prevents infinite recursion)."""

DEFAULT_INDENT_SIZE: Final[int] = 2
"""Default indentation spaces for text representation."""


# ==============================================================================
# NODE RELATIONSHIP CONSTANTS
# ==============================================================================
PARENT_CHILD_ARC: Final[str] = "parent-child"
"""Standard arc role for parent-child relationships."""

SUMMATION_ARC: Final[str] = "summation-item"
"""Arc role for calculation summation relationships."""


# ==============================================================================
# STANDARD ROLE URIS (Common across taxonomies)
# ==============================================================================
# These are used to identify statement types from role URIs
BALANCE_SHEET_KEYWORDS: Final[tuple] = (
    'balance',
    'financial_position',
    'financialposition',
    'statement_of_financial',
    'assets',
)

INCOME_STATEMENT_KEYWORDS: Final[tuple] = (
    'income',
    'operations',
    'profit',
    'loss',
    'earnings',
    'comprehensive',
)

CASH_FLOW_KEYWORDS: Final[tuple] = (
    'cash',
    'cashflow',
    'cash_flow',
)

EQUITY_KEYWORDS: Final[tuple] = (
    'equity',
    'stockholders',
    'shareholders',
    'changes_in_equity',
)


# ==============================================================================
# TOTAL/SUBTOTAL DETECTION PATTERNS
# ==============================================================================
TOTAL_PATTERNS: Final[tuple] = (
    'total',
    'sum',
    'net',
    'aggregate',
)

SUBTOTAL_PATTERNS: Final[tuple] = (
    'subtotal',
    'sub_total',
    'sub-total',
)


# ==============================================================================
# ABSTRACT ELEMENT DETECTION
# ==============================================================================
ABSTRACT_SUFFIX: Final[str] = "Abstract"
"""Common suffix indicating an abstract (grouping) element."""

AXIS_SUFFIX: Final[str] = "Axis"
"""Suffix indicating a dimensional axis."""

MEMBER_SUFFIX: Final[str] = "Member"
"""Suffix indicating a dimension member."""

DOMAIN_SUFFIX: Final[str] = "Domain"
"""Suffix indicating a dimension domain."""


# ==============================================================================
# HIERARCHY OUTPUT FORMATS
# ==============================================================================
class OutputFormat(Enum):
    """Output formats for hierarchy export."""
    DICT = "dict"
    JSON = "json"
    TEXT = "text"
    TREE = "tree"


# ==============================================================================
# VALIDATION THRESHOLDS
# ==============================================================================
MIN_NODES_FOR_VALID_HIERARCHY: Final[int] = 2
"""Minimum nodes required for a valid hierarchy (root + at least one child)."""

MAX_CHILDREN_WARNING: Final[int] = 50
"""Warn if a node has more than this many direct children."""


# ==============================================================================
# MAT_ACC_ID STATEMENT TYPE CODE GENERATION
# ==============================================================================
# Statement codes are generated DYNAMICALLY from discovered statement types
# Format: {STATEMENT_CODE}-{LEVEL:03d}-{SIBLING:03d}-{CONTEXT_REF}
# Example: BS-002-001-c4
#
# The code generator creates unique 2-letter codes from any statement type
# No hardcoded list - supports any taxonomy/market's statement types

# Maximum length for statement codes
STATEMENT_CODE_LENGTH: Final[int] = 2
"""Number of characters in generated statement codes."""


# ==============================================================================
# EXPORTS
# ==============================================================================
__all__ = [
    # Enums
    'NodeType',
    'StatementType',
    'LinkbaseRole',
    'OutputFormat',
    # Hierarchy limits
    'MAX_HIERARCHY_DEPTH',
    'DEFAULT_INDENT_SIZE',
    # Arc types
    'PARENT_CHILD_ARC',
    'SUMMATION_ARC',
    # Statement type keywords
    'BALANCE_SHEET_KEYWORDS',
    'INCOME_STATEMENT_KEYWORDS',
    'CASH_FLOW_KEYWORDS',
    'EQUITY_KEYWORDS',
    # Detection patterns
    'TOTAL_PATTERNS',
    'SUBTOTAL_PATTERNS',
    # Element suffixes
    'ABSTRACT_SUFFIX',
    'AXIS_SUFFIX',
    'MEMBER_SUFFIX',
    'DOMAIN_SUFFIX',
    # Validation
    'MIN_NODES_FOR_VALID_HIERARCHY',
    'MAX_CHILDREN_WARNING',
    # mat_acc_id code generation
    'STATEMENT_CODE_LENGTH',
]
