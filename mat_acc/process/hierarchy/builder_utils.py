# Path: mat_acc/process/hierarchy/builder_utils.py
"""
Shared Utility Functions for Hierarchy Builders.

Contains common operations used by multiple builder implementations:
- Value extraction from node data
- Node type detection
- Tree sorting
- Node creation helpers
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from process.hierarchy.constants import (
    NodeType,
    ABSTRACT_SUFFIX,
    TOTAL_PATTERNS,
)
from process.hierarchy.node import HierarchyNode
from process.hierarchy.mat_acc_id import (
    get_statement_code,
    format_mat_acc_id,
    normalize_context_ref,
)


def extract_value(data: dict[str, Any]) -> Optional[Decimal]:
    """
    Extract numeric value from node data.

    Tries multiple common keys used in different data formats.

    Args:
        data: Node data dictionary

    Returns:
        Decimal value or None if not found/invalid

    Example:
        >>> extract_value({'value': '1000.50'})
        Decimal('1000.50')
        >>> extract_value({'fact_value': 1000})
        Decimal('1000')
    """
    # Try various value keys in order of preference
    raw_value = data.get('value')
    if raw_value is None:
        raw_value = data.get('fact_value')
    if raw_value is None:
        raw_value = data.get('amount')
    if raw_value is None:
        raw_value = data.get('numeric_value')

    if raw_value is None:
        return None

    # Convert to Decimal
    try:
        if isinstance(raw_value, Decimal):
            return raw_value
        elif isinstance(raw_value, (int, float)):
            return Decimal(str(raw_value))
        elif isinstance(raw_value, str):
            # Remove commas and whitespace
            clean_value = raw_value.replace(',', '').strip()
            if not clean_value or clean_value in ('', '-', 'N/A', 'n/a'):
                return None
            return Decimal(clean_value)
    except (InvalidOperation, ValueError):
        return None

    return None


def determine_node_type(
    concept: str,
    label: str,
    node_data: dict[str, Any]
) -> NodeType:
    """
    Determine node type from concept, label, and data.

    Uses multiple heuristics:
    1. Explicit abstract flag
    2. Abstract suffix in concept name
    3. Total patterns in label
    4. Absence of value suggests abstract

    Args:
        concept: Concept name
        label: Node label
        node_data: Node data dictionary

    Returns:
        Appropriate NodeType
    """
    # Check explicit abstract flag
    if node_data.get('is_abstract', node_data.get('abstract', False)):
        return NodeType.ABSTRACT

    # Check concept name for Abstract suffix
    if concept.endswith(ABSTRACT_SUFFIX):
        return NodeType.ABSTRACT

    # Check for total patterns in label
    label_lower = label.lower()
    if any(pattern in label_lower for pattern in TOTAL_PATTERNS):
        return NodeType.TOTAL

    # Check if it has a value - if no value, likely abstract
    has_value = any(
        node_data.get(key) is not None
        for key in ['value', 'fact_value', 'amount', 'numeric_value']
    )
    if not has_value and node_data.get('is_abstract') is not False:
        # No value and not explicitly non-abstract
        return NodeType.ABSTRACT

    return NodeType.LINE_ITEM


def detect_node_type_from_concept(concept_name: str) -> NodeType:
    """
    Detect node type from concept name alone.

    Simpler detection when only concept name is available.

    Args:
        concept_name: XBRL concept name

    Returns:
        Detected NodeType
    """
    name_lower = concept_name.lower()

    if name_lower.endswith('abstract'):
        return NodeType.ABSTRACT
    if any(pattern in name_lower for pattern in TOTAL_PATTERNS):
        return NodeType.TOTAL

    return NodeType.LINE_ITEM


def sort_children_recursive(node: HierarchyNode) -> None:
    """
    Sort children by order, recursively through entire tree.

    Args:
        node: Node whose children to sort
    """
    if node.children:
        node.children.sort(key=lambda n: (n.order, n.label))
        for child in node.children:
            sort_children_recursive(child)


def concept_to_label(concept_name: str) -> str:
    """
    Convert concept name to human-readable label.

    Handles namespaced concepts and CamelCase conversion.

    Args:
        concept_name: Concept name (e.g., 'us-gaap:AssetsCurrent')

    Returns:
        Human-readable label (e.g., 'Assets Current')
    """
    # Remove namespace prefix
    if ':' in concept_name:
        concept_name = concept_name.split(':')[-1]
    if '_' in concept_name:
        parts = concept_name.split('_')
        concept_name = parts[-1] if len(parts) > 1 else concept_name

    # Convert CamelCase to spaces
    result = []
    for char in concept_name:
        if char.isupper() and result:
            result.append(' ')
        result.append(char)

    return ''.join(result)


def generate_mat_acc_ids_for_tree(
    root: HierarchyNode,
    statement_type: str,
    default_context_ref: Optional[str] = None
) -> None:
    """
    Generate mat_acc_id for each node in a hierarchy tree.

    Format: {STATEMENT_CODE}-{LEVEL:03d}-{SIBLING:03d}-{CONTEXT_REF}
    Example: BS-002-001-c4

    Args:
        root: Root node of the hierarchy
        statement_type: Statement type (BALANCE_SHEET, etc.)
        default_context_ref: Default context ref to use if not in node
    """
    code = get_statement_code(statement_type)

    # Track sibling position at each level
    sibling_counters: dict[int, int] = {}

    for node in root.iter_preorder():
        level = node.depth

        # Initialize/reset sibling counter for this level
        if level not in sibling_counters:
            sibling_counters[level] = 0
        sibling_counters[level] += 1

        # Reset deeper level counters when we go up
        for l in list(sibling_counters.keys()):
            if l > level:
                del sibling_counters[l]

        sibling = sibling_counters[level]

        # Generate structural position (without context)
        mat_acc_position = f"{code}-{level:03d}-{sibling:03d}"
        node.metadata['mat_acc_position'] = mat_acc_position

        # Get context_ref from node metadata, or use default
        context_ref = node.metadata.get('context_ref', default_context_ref)

        # Generate full mat_acc_id with context_ref
        if context_ref:
            ctx = normalize_context_ref(context_ref)
            mat_acc_id = f"{mat_acc_position}-{ctx}"
        else:
            mat_acc_id = mat_acc_position

        node.metadata['mat_acc_id'] = mat_acc_id


def create_node_with_metadata(
    concept: str,
    label: str,
    node_data: dict[str, Any]
) -> HierarchyNode:
    """
    Create a HierarchyNode with extracted metadata.

    Args:
        concept: Concept name
        label: Node label
        node_data: Node data dictionary

    Returns:
        Configured HierarchyNode
    """
    # Determine node type
    node_type = determine_node_type(concept, label, node_data)

    # Extract value
    value = extract_value(node_data)

    # Extract order
    order = float(node_data.get('order', 0))

    # Create the node
    node = HierarchyNode(
        concept=concept,
        label=label,
        node_type=node_type,
        value=value,
        order=order,
        unit=node_data.get('unit', node_data.get('unit_ref')),
        decimals=node_data.get('decimals'),
    )

    # Add common metadata
    if 'balance' in node_data:
        node.metadata['balance'] = node_data['balance']
    if 'period_type' in node_data:
        node.metadata['period_type'] = node_data['period_type']
    if 'is_monetary' in node_data:
        node.metadata['is_monetary'] = node_data['is_monetary']

    # Store context_ref for mat_acc_id generation
    context_ref = node_data.get('context_ref', node_data.get('contextRef'))
    if context_ref:
        node.metadata['context_ref'] = context_ref

    return node


__all__ = [
    'extract_value',
    'determine_node_type',
    'detect_node_type_from_concept',
    'sort_children_recursive',
    'concept_to_label',
    'generate_mat_acc_ids_for_tree',
    'create_node_with_metadata',
]
