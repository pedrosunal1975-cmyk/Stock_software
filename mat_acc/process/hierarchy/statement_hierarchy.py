# Path: mat_acc/process/hierarchy/statement_hierarchy.py
"""
Statement Hierarchy - High-level wrapper for financial statement hierarchies.

Provides a convenient interface for working with complete statement
hierarchies, including metadata, validation, and export capabilities.
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from process.hierarchy.constants import (
    NodeType,
    StatementType,
    OutputFormat,
    MIN_NODES_FOR_VALID_HIERARCHY,
    MAX_CHILDREN_WARNING,
)
from process.hierarchy.node import HierarchyNode

# Logger setup
try:
    from core.logger import get_process_logger
    logger = get_process_logger('hierarchy.statement')
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class StatementHierarchy:
    """
    Complete financial statement hierarchy with metadata and utilities.

    Wraps a HierarchyNode root with additional statement-level information
    and provides convenient methods for analysis and export.

    Attributes:
        root: Root node of the hierarchy tree
        statement_type: Type of financial statement
        company: Company name
        period_end: Reporting period end date
        filing_date: Date of the filing
        currency: Primary currency
        metadata: Additional metadata

    Example:
        hierarchy = StatementHierarchy(
            root=root_node,
            statement_type=StatementType.BALANCE_SHEET,
            company="Apple Inc",
            period_end="2024-09-30"
        )

        # Navigate the hierarchy
        for node in hierarchy.iter_line_items():
            print(f"{node.label}: {node.value}")

        # Export to JSON
        hierarchy.to_json_file(Path("balance_sheet.json"))
    """
    root: HierarchyNode
    statement_type: StatementType = StatementType.UNKNOWN
    company: str = ""
    period_end: str = ""
    filing_date: str = ""
    currency: str = "USD"
    metadata: dict[str, Any] = field(default_factory=dict)

    # ===========================================================================
    # VALIDATION
    # ===========================================================================
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the hierarchy structure.

        Returns:
            Tuple of (is_valid, list of warning/error messages)
        """
        messages = []
        is_valid = True

        # Check minimum nodes
        node_count = self.node_count
        if node_count < MIN_NODES_FOR_VALID_HIERARCHY:
            messages.append(f"Too few nodes: {node_count}")
            is_valid = False

        # Check for excessive children
        for node in self.root.iter_preorder():
            if node.child_count > MAX_CHILDREN_WARNING:
                messages.append(
                    f"Node '{node.label}' has {node.child_count} children "
                    f"(exceeds {MAX_CHILDREN_WARNING})"
                )

        # Check for orphaned totals (totals without children)
        for node in self.root.iter_preorder():
            if node.is_total and node.is_leaf:
                messages.append(f"Total '{node.label}' has no children")

        # Check depth consistency
        max_depth = self.max_depth
        if max_depth > 10:
            messages.append(f"Hierarchy is very deep: {max_depth} levels")

        # Check for missing labels
        for node in self.root.iter_preorder():
            if not node.label or node.label == node.concept:
                messages.append(f"Node '{node.concept}' has no proper label")

        if messages:
            logger.info(f"Validation messages: {messages}")

        return is_valid, messages

    @property
    def is_valid(self) -> bool:
        """Quick check if hierarchy is valid."""
        valid, _ = self.validate()
        return valid

    # ===========================================================================
    # STATISTICS
    # ===========================================================================
    @property
    def node_count(self) -> int:
        """Total number of nodes in hierarchy."""
        return self.root.descendant_count + 1

    @property
    def line_item_count(self) -> int:
        """Number of line item nodes (with values)."""
        return sum(1 for _ in self.iter_line_items())

    @property
    def abstract_count(self) -> int:
        """Number of abstract (grouping) nodes."""
        return len(self.root.find_all_by_type(NodeType.ABSTRACT))

    @property
    def total_count(self) -> int:
        """Number of total/subtotal nodes."""
        return len(self.root.find_totals())

    @property
    def max_depth(self) -> int:
        """Maximum depth of the hierarchy."""
        return self.root.max_depth

    @property
    def value_sum(self) -> Decimal:
        """Sum of all values in hierarchy."""
        return self.root.subtree_value_sum

    def get_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive statistics about the hierarchy.

        Returns:
            Dictionary of statistics
        """
        return {
            'node_count': self.node_count,
            'line_item_count': self.line_item_count,
            'abstract_count': self.abstract_count,
            'total_count': self.total_count,
            'max_depth': self.max_depth,
            'statement_type': self.statement_type.value,
            'company': self.company,
            'period_end': self.period_end,
            'currency': self.currency,
        }

    # ===========================================================================
    # ITERATION
    # ===========================================================================
    def iter_line_items(self) -> Iterator[HierarchyNode]:
        """
        Iterate over line item nodes only.

        Yields:
            Line item nodes (those with values)
        """
        for node in self.root.iter_preorder():
            if node.node_type == NodeType.LINE_ITEM and node.has_value:
                yield node

    def iter_abstracts(self) -> Iterator[HierarchyNode]:
        """
        Iterate over abstract (grouping) nodes.

        Yields:
            Abstract nodes
        """
        for node in self.root.iter_preorder():
            if node.node_type == NodeType.ABSTRACT:
                yield node

    def iter_totals(self) -> Iterator[HierarchyNode]:
        """
        Iterate over total/subtotal nodes.

        Yields:
            Total nodes
        """
        for node in self.root.iter_preorder():
            if node.is_total:
                yield node

    def iter_at_depth(self, depth: int) -> Iterator[HierarchyNode]:
        """
        Iterate over nodes at a specific depth.

        Args:
            depth: Depth level (0 = root)

        Yields:
            Nodes at the specified depth
        """
        for node in self.root.iter_preorder():
            if node.depth == depth:
                yield node

    # ===========================================================================
    # SEARCH
    # ===========================================================================
    def find_by_concept(self, concept: str) -> Optional[HierarchyNode]:
        """
        Find a node by concept name.

        Args:
            concept: XBRL concept name

        Returns:
            Found node or None
        """
        return self.root.find_by_concept(concept)

    def find_by_label(
        self,
        label: str,
        case_sensitive: bool = False
    ) -> Optional[HierarchyNode]:
        """
        Find a node by label.

        Args:
            label: Label text to search
            case_sensitive: Whether to match case

        Returns:
            Found node or None
        """
        return self.root.find_by_label(label, case_sensitive)

    def find_by_label_contains(self, text: str) -> list[HierarchyNode]:
        """
        Find all nodes whose labels contain the given text.

        Args:
            text: Text to search for

        Returns:
            List of matching nodes
        """
        text_lower = text.lower()
        return [
            node for node in self.root.iter_preorder()
            if text_lower in node.label.lower()
        ]

    def get_top_level_items(self) -> list[HierarchyNode]:
        """
        Get direct children of root (top-level sections).

        Returns:
            List of top-level nodes
        """
        return list(self.root.children)

    # ===========================================================================
    # EXPORT
    # ===========================================================================
    def to_dict(self) -> dict[str, Any]:
        """
        Convert hierarchy to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'metadata': {
                'statement_type': self.statement_type.value,
                'company': self.company,
                'period_end': self.period_end,
                'filing_date': self.filing_date,
                'currency': self.currency,
                'generated_at': datetime.now().isoformat(),
                **self.metadata,
            },
            'statistics': self.get_statistics(),
            'hierarchy': self.root.to_dict(include_children=True),
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Convert hierarchy to JSON string.

        Args:
            indent: JSON indentation

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_json_file(self, path: Path) -> None:
        """
        Write hierarchy to JSON file.

        Args:
            path: Output file path
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(self.to_json())
        logger.info(f"Wrote hierarchy to {path}")

    def to_text(self, include_values: bool = True) -> str:
        """
        Convert hierarchy to indented text.

        Args:
            include_values: Whether to include values

        Returns:
            Multi-line text representation
        """
        lines = [
            f"Statement: {self.statement_type.value}",
            f"Company: {self.company}",
            f"Period: {self.period_end}",
            "",
        ]

        for node in self.root.iter_preorder():
            indent = "  " * node.depth
            if include_values and node.has_value:
                lines.append(f"{indent}{node.label}: {node.value:,}")
            else:
                lines.append(f"{indent}{node.label}")

        return '\n'.join(lines)

    def to_flat_list(self) -> list[dict[str, Any]]:
        """
        Convert hierarchy to flat list of items.

        Useful for CSV export or DataFrame creation.

        Returns:
            List of dictionaries
        """
        items = []
        for node in self.root.iter_preorder():
            items.append({
                'concept': node.concept,
                'label': node.label,
                'depth': node.depth,
                'node_type': node.node_type.value,
                'value': str(node.value) if node.value else None,
                'unit': node.unit,
                'is_total': node.is_total,
                'path': ' > '.join(node.path_labels),
            })
        return items

    # ===========================================================================
    # SPECIAL METHODS
    # ===========================================================================
    def __str__(self) -> str:
        """String representation."""
        return (
            f"StatementHierarchy({self.statement_type.value}, "
            f"{self.company}, {self.period_end}, "
            f"{self.node_count} nodes)"
        )

    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"StatementHierarchy(statement_type={self.statement_type}, "
            f"company='{self.company}', "
            f"period_end='{self.period_end}', "
            f"nodes={self.node_count})"
        )

    def __len__(self) -> int:
        """Number of nodes."""
        return self.node_count

    def __iter__(self) -> Iterator[HierarchyNode]:
        """Iterate over all nodes."""
        return self.root.iter_preorder()

    def __contains__(self, concept: str) -> bool:
        """Check if concept exists in hierarchy."""
        return self.find_by_concept(concept) is not None


# ==============================================================================
# FACTORY FUNCTIONS
# ==============================================================================
def create_statement_hierarchy(
    root: HierarchyNode,
    statement_type: StatementType,
    company: str,
    period_end: str,
    **kwargs: Any
) -> StatementHierarchy:
    """
    Create a StatementHierarchy with common defaults.

    Args:
        root: Root node of hierarchy
        statement_type: Type of statement
        company: Company name
        period_end: Period end date
        **kwargs: Additional metadata

    Returns:
        New StatementHierarchy
    """
    return StatementHierarchy(
        root=root,
        statement_type=statement_type,
        company=company,
        period_end=period_end,
        metadata=kwargs,
    )


__all__ = [
    'StatementHierarchy',
    'create_statement_hierarchy',
]
