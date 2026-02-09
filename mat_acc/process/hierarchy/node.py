# Path: mat_acc/process/hierarchy/node.py
"""
Hierarchy Node - Individual node in a financial statement hierarchy.

Each node represents a line item, grouping, or total in the statement
structure, maintaining relationships to parent/children for navigation.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from process.hierarchy.constants import (
    NodeType,
    MAX_HIERARCHY_DEPTH,
    DEFAULT_INDENT_SIZE,
    ABSTRACT_SUFFIX,
    TOTAL_PATTERNS,
)


@dataclass
class HierarchyNode:
    """
    A single node in the financial statement hierarchy tree.

    Represents a line item, abstract grouping, or total in the
    hierarchical structure of a financial statement.

    Attributes:
        concept: XBRL concept name (e.g., "us-gaap:Assets")
        label: Human-readable label (e.g., "Total Assets")
        node_type: Type of node (ROOT, ABSTRACT, LINE_ITEM, TOTAL)
        order: Presentation order from linkbase
        depth: Depth in the hierarchy (0 = root)
        value: Numeric value if this is a line item
        decimals: Decimal precision of the value
        unit: Unit of measurement (e.g., "USD", "shares")
        parent: Reference to parent node
        children: List of child nodes
        metadata: Additional metadata dictionary

    Example:
        node = HierarchyNode(
            concept="us-gaap:Assets",
            label="Total Assets",
            node_type=NodeType.TOTAL,
            value=Decimal("1234567890")
        )
    """
    # Core identification
    concept: str
    label: str
    node_type: NodeType = NodeType.LINE_ITEM

    # Position in hierarchy
    order: float = 0.0
    depth: int = 0

    # Value data (for line items)
    value: Optional[Decimal] = None
    decimals: Optional[int] = None
    unit: Optional[str] = None

    # Relationships (not in __init__ by default)
    parent: Optional[HierarchyNode] = field(default=None, repr=False)
    children: list[HierarchyNode] = field(default_factory=list, repr=False)

    # Additional data
    metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    # ===========================================================================
    # TREE NAVIGATION
    # ===========================================================================
    def add_child(self, child: HierarchyNode) -> None:
        """
        Add a child node to this node.

        Args:
            child: Node to add as child

        Raises:
            ValueError: If adding would create a cycle
        """
        if child is self:
            raise ValueError("Cannot add node as its own child")
        if self._would_create_cycle(child):
            raise ValueError("Adding this child would create a cycle")

        child.parent = self
        child.depth = self.depth + 1
        self.children.append(child)

    def remove_child(self, child: HierarchyNode) -> bool:
        """
        Remove a child node.

        Args:
            child: Node to remove

        Returns:
            True if child was removed, False if not found
        """
        if child in self.children:
            self.children.remove(child)
            child.parent = None
            return True
        return False

    def _would_create_cycle(self, potential_child: HierarchyNode) -> bool:
        """Check if adding a child would create a cycle."""
        current = self
        while current is not None:
            if current is potential_child:
                return True
            current = current.parent
        return False

    # ===========================================================================
    # RELATIONSHIP QUERIES
    # ===========================================================================
    @property
    def is_root(self) -> bool:
        """Check if this is the root node."""
        return self.parent is None

    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf node (no children)."""
        return len(self.children) == 0

    @property
    def is_abstract(self) -> bool:
        """Check if this is an abstract (grouping) node."""
        return (
            self.node_type == NodeType.ABSTRACT
            or self.concept.endswith(ABSTRACT_SUFFIX)
            or self.value is None
        )

    @property
    def is_total(self) -> bool:
        """Check if this appears to be a total/subtotal."""
        if self.node_type == NodeType.TOTAL:
            return True
        label_lower = self.label.lower()
        return any(pattern in label_lower for pattern in TOTAL_PATTERNS)

    @property
    def has_value(self) -> bool:
        """Check if this node has a numeric value."""
        return self.value is not None

    @property
    def siblings(self) -> list[HierarchyNode]:
        """Get sibling nodes (same parent, excluding self)."""
        if self.parent is None:
            return []
        return [child for child in self.parent.children if child is not self]

    @property
    def ancestors(self) -> list[HierarchyNode]:
        """Get all ancestor nodes from parent to root."""
        result = []
        current = self.parent
        while current is not None:
            result.append(current)
            current = current.parent
        return result

    @property
    def descendants(self) -> list[HierarchyNode]:
        """Get all descendant nodes (children, grandchildren, etc.)."""
        result = []
        for child in self.children:
            result.append(child)
            result.extend(child.descendants)
        return result

    @property
    def root(self) -> HierarchyNode:
        """Get the root node of this tree."""
        current = self
        while current.parent is not None:
            current = current.parent
        return current

    @property
    def path(self) -> list[HierarchyNode]:
        """Get path from root to this node."""
        return list(reversed(self.ancestors)) + [self]

    @property
    def path_labels(self) -> list[str]:
        """Get labels for path from root to this node."""
        return [node.label for node in self.path]

    # ===========================================================================
    # TREE ITERATION
    # ===========================================================================
    def iter_preorder(self) -> Iterator[HierarchyNode]:
        """
        Iterate nodes in pre-order (parent before children).

        Yields:
            Nodes in pre-order traversal
        """
        yield self
        for child in self.children:
            yield from child.iter_preorder()

    def iter_postorder(self) -> Iterator[HierarchyNode]:
        """
        Iterate nodes in post-order (children before parent).

        Yields:
            Nodes in post-order traversal
        """
        for child in self.children:
            yield from child.iter_postorder()
        yield self

    def iter_level_order(self) -> Iterator[HierarchyNode]:
        """
        Iterate nodes in level-order (breadth-first).

        Yields:
            Nodes level by level
        """
        queue = [self]
        while queue:
            node = queue.pop(0)
            yield node
            queue.extend(node.children)

    def iter_leaves(self) -> Iterator[HierarchyNode]:
        """
        Iterate only leaf nodes.

        Yields:
            Leaf nodes only
        """
        if self.is_leaf:
            yield self
        else:
            for child in self.children:
                yield from child.iter_leaves()

    def iter_with_values(self) -> Iterator[HierarchyNode]:
        """
        Iterate only nodes that have values.

        Yields:
            Nodes with non-None values
        """
        for node in self.iter_preorder():
            if node.has_value:
                yield node

    # ===========================================================================
    # SEARCH AND FILTER
    # ===========================================================================
    def find_by_concept(self, concept: str) -> Optional[HierarchyNode]:
        """
        Find a descendant node by concept name.

        Args:
            concept: Concept name to search for

        Returns:
            Found node or None
        """
        for node in self.iter_preorder():
            if node.concept == concept:
                return node
        return None

    def find_by_label(self, label: str, case_sensitive: bool = False) -> Optional[HierarchyNode]:
        """
        Find a descendant node by label.

        Args:
            label: Label to search for
            case_sensitive: Whether to match case

        Returns:
            Found node or None
        """
        search_label = label if case_sensitive else label.lower()
        for node in self.iter_preorder():
            node_label = node.label if case_sensitive else node.label.lower()
            if node_label == search_label:
                return node
        return None

    def find_all_by_type(self, node_type: NodeType) -> list[HierarchyNode]:
        """
        Find all descendant nodes of a specific type.

        Args:
            node_type: Type to filter by

        Returns:
            List of matching nodes
        """
        return [node for node in self.iter_preorder() if node.node_type == node_type]

    def find_totals(self) -> list[HierarchyNode]:
        """
        Find all total/subtotal nodes.

        Returns:
            List of total nodes
        """
        return [node for node in self.iter_preorder() if node.is_total]

    # ===========================================================================
    # STATISTICS
    # ===========================================================================
    @property
    def child_count(self) -> int:
        """Number of direct children."""
        return len(self.children)

    @property
    def descendant_count(self) -> int:
        """Total number of descendants."""
        return len(self.descendants)

    @property
    def leaf_count(self) -> int:
        """Number of leaf nodes in subtree."""
        return sum(1 for _ in self.iter_leaves())

    @property
    def max_depth(self) -> int:
        """Maximum depth of any node in subtree."""
        if self.is_leaf:
            return self.depth
        return max(child.max_depth for child in self.children)

    @property
    def subtree_value_sum(self) -> Decimal:
        """Sum of all values in subtree."""
        total = Decimal('0')
        for node in self.iter_with_values():
            if node.value is not None:
                total += node.value
        return total

    # ===========================================================================
    # CONVERSION AND REPRESENTATION
    # ===========================================================================
    def to_dict(self, include_children: bool = True) -> dict[str, Any]:
        """
        Convert node to dictionary.

        Args:
            include_children: Whether to include children recursively

        Returns:
            Dictionary representation
        """
        result = {
            'concept': self.concept,
            'label': self.label,
            'node_type': self.node_type.value,
            'order': self.order,
            'depth': self.depth,
        }

        if self.value is not None:
            result['value'] = str(self.value)
        if self.decimals is not None:
            result['decimals'] = self.decimals
        if self.unit is not None:
            result['unit'] = self.unit
        if self.metadata:
            result['metadata'] = self.metadata

        if include_children and self.children:
            result['children'] = [
                child.to_dict(include_children=True)
                for child in self.children
            ]

        return result

    def to_text(self, indent_size: int = DEFAULT_INDENT_SIZE) -> str:
        """
        Convert subtree to indented text representation.

        Args:
            indent_size: Spaces per indentation level

        Returns:
            Multi-line text representation
        """
        lines = []
        for node in self.iter_preorder():
            indent = ' ' * (node.depth * indent_size)
            value_str = f" = {node.value}" if node.has_value else ""
            lines.append(f"{indent}{node.label}{value_str}")
        return '\n'.join(lines)

    def __str__(self) -> str:
        """String representation."""
        value_str = f" = {self.value}" if self.has_value else ""
        children_str = f" ({self.child_count} children)" if self.children else ""
        return f"{self.label}{value_str}{children_str}"

    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"HierarchyNode(concept='{self.concept}', "
            f"label='{self.label}', "
            f"type={self.node_type.value}, "
            f"depth={self.depth})"
        )


# ==============================================================================
# FACTORY FUNCTIONS
# ==============================================================================
def create_root_node(label: str, concept: str = "root") -> HierarchyNode:
    """
    Create a root node for a hierarchy.

    Args:
        label: Label for the root (e.g., "Balance Sheet")
        concept: Concept name (default "root")

    Returns:
        New root node
    """
    return HierarchyNode(
        concept=concept,
        label=label,
        node_type=NodeType.ROOT,
        depth=0,
    )


def create_abstract_node(
    concept: str,
    label: str,
    order: float = 0.0
) -> HierarchyNode:
    """
    Create an abstract (grouping) node.

    Args:
        concept: XBRL concept name
        label: Human-readable label
        order: Presentation order

    Returns:
        New abstract node
    """
    return HierarchyNode(
        concept=concept,
        label=label,
        node_type=NodeType.ABSTRACT,
        order=order,
    )


def create_line_item_node(
    concept: str,
    label: str,
    value: Optional[Decimal] = None,
    order: float = 0.0,
    unit: Optional[str] = None,
    decimals: Optional[int] = None,
) -> HierarchyNode:
    """
    Create a line item node with value.

    Args:
        concept: XBRL concept name
        label: Human-readable label
        value: Numeric value
        order: Presentation order
        unit: Unit of measurement
        decimals: Decimal precision

    Returns:
        New line item node
    """
    return HierarchyNode(
        concept=concept,
        label=label,
        node_type=NodeType.LINE_ITEM,
        value=value,
        order=order,
        unit=unit,
        decimals=decimals,
    )


__all__ = [
    'HierarchyNode',
    'create_root_node',
    'create_abstract_node',
    'create_line_item_node',
]
