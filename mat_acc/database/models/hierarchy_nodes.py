# Path: mat_acc/database/models/hierarchy_nodes.py
"""
Hierarchy Node Model

Stores individual nodes in a statement hierarchy with mat_acc_id.
Each node represents a concept in the financial statement structure.

Architecture:
- mat_acc_id uniquely identifies position in hierarchy
- Stores concept, label, value, and structural information
- Links to parent/children via mat_acc_id references
"""

import uuid as uuid_module
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, Integer, Float, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship

from database.models.base import Base


class HierarchyNode(Base):
    """
    Hierarchy node record.

    Stores a single node in a statement hierarchy with its mat_acc_id.
    The mat_acc_id uniquely encodes the node's position in the hierarchy.

    mat_acc_id Format:
        {STATEMENT_CODE}-{LEVEL:03d}-{SIBLING:03d}-{CONTEXT_REF}
        Example: BS-002-001-c4

    Components:
        - STATEMENT_CODE: Dynamic 2-letter code (BS, IS, CF, etc.)
        - LEVEL: Hierarchy depth (000 = root)
        - SIBLING: Position among siblings (001-based)
        - CONTEXT_REF: Optional context reference (c4, c12, etc.)

    Example:
        node = HierarchyNode(
            hierarchy_id=hierarchy.hierarchy_id,
            mat_acc_id='BS-002-001-c4',
            mat_acc_position='BS-002-001',
            concept='us-gaap:AssetsCurrent',
            label='Current Assets',
            node_type='line_item',
            level=2,
            sibling=1,
            context_ref='c4',
            value=1500000.00
        )
    """
    __tablename__ = 'hierarchy_nodes'

    # Primary key
    node_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid_module.uuid4()),
        comment="Unique node identifier"
    )

    # Foreign key to hierarchy
    hierarchy_id = Column(
        String(36),
        ForeignKey('statement_hierarchies.hierarchy_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Reference to parent hierarchy"
    )

    # mat_acc_id - THE CORE IDENTIFIER
    mat_acc_id = Column(
        String(50),
        nullable=False,
        index=True,
        unique=False,  # Unique within filing, but not globally
        comment="mat_acc unique identifier (e.g., BS-002-001-c4)"
    )
    mat_acc_position = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Position without context (e.g., BS-002-001)"
    )

    # Position in hierarchy
    level = Column(
        Integer,
        nullable=False,
        index=True,
        comment="Hierarchy depth (0 = root)"
    )
    sibling = Column(
        Integer,
        nullable=False,
        comment="Sibling position (1-based)"
    )
    parent_mat_acc_id = Column(
        String(50),
        index=True,
        comment="mat_acc_id of parent node (for traversal)"
    )

    # Concept information
    concept = Column(
        String(255),
        nullable=False,
        index=True,
        comment="XBRL concept name (e.g., us-gaap:Assets)"
    )
    label = Column(
        Text,
        nullable=False,
        comment="Human-readable label from company filing"
    )
    standard_label = Column(
        Text,
        nullable=True,
        comment="Standard taxonomy label (from US-GAAP, IFRS, etc.) or generated"
    )
    label_source = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Source of standard_label: taxonomy name (us-gaap, ifrs-full) or 'generated'"
    )
    taxonomy_namespace = Column(
        String(255),
        nullable=True,
        comment="Taxonomy namespace that provided the standard label"
    )

    node_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Node type: root, abstract, line_item, total, dimension_member"
    )

    # Value information
    has_value = Column(
        Boolean,
        default=False,
        comment="Whether node has a numeric value"
    )
    value = Column(
        Float,
        comment="Numeric value (if any)"
    )
    unit = Column(
        String(50),
        comment="Unit of measurement (e.g., USD, shares)"
    )
    decimals = Column(
        Integer,
        comment="Decimal precision"
    )

    # Context information
    context_ref = Column(
        String(50),
        index=True,
        comment="Context reference (e.g., c4, c12)"
    )

    # Ordering
    order = Column(
        Float,
        default=0.0,
        comment="Sort order from presentation linkbase"
    )

    # Timestamp
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )

    # Indexes for common queries
    __table_args__ = (
        Index('idx_node_hierarchy_level', 'hierarchy_id', 'level'),
        Index('idx_node_mat_acc', 'mat_acc_id'),
        Index('idx_node_concept', 'concept'),
        Index('idx_node_parent', 'parent_mat_acc_id'),
    )

    # Relationships
    hierarchy = relationship(
        "StatementHierarchy",
        back_populates="nodes"
    )

    @property
    def is_root(self) -> bool:
        """Check if this is a root node."""
        return self.level == 0

    @property
    def is_abstract(self) -> bool:
        """Check if this is an abstract node."""
        return self.node_type == 'abstract'

    @property
    def is_line_item(self) -> bool:
        """Check if this is a line item."""
        return self.node_type == 'line_item'

    @property
    def is_total(self) -> bool:
        """Check if this is a total/subtotal."""
        return self.node_type == 'total'

    @classmethod
    def from_hierarchy_node(
        cls,
        hierarchy_id: str,
        node: 'process.hierarchy.HierarchyNode',
        parent_mat_acc_id: Optional[str] = None
    ) -> 'HierarchyNode':
        """
        Create database node from process.hierarchy.HierarchyNode.

        Args:
            hierarchy_id: ID of parent StatementHierarchy
            node: HierarchyNode from process.hierarchy module
            parent_mat_acc_id: mat_acc_id of parent (for non-root nodes)

        Returns:
            HierarchyNode database model instance
        """
        mat_acc_id = node.metadata.get('mat_acc_id', '')
        mat_acc_position = node.metadata.get('mat_acc_position', '')

        # Parse level and sibling from mat_acc_position (format: CODE-LEVEL-SIBLING)
        # e.g., 'BS-002-001' -> level=2, sibling=1
        parts = mat_acc_position.split('-') if mat_acc_position else []
        level = int(parts[1]) if len(parts) >= 2 else node.depth
        sibling = int(parts[2]) if len(parts) >= 3 else 1

        return cls(
            hierarchy_id=hierarchy_id,
            mat_acc_id=mat_acc_id,
            mat_acc_position=mat_acc_position,
            level=level,
            sibling=sibling,
            parent_mat_acc_id=parent_mat_acc_id,
            concept=node.concept,
            label=node.label,
            node_type=node.node_type.value,
            has_value=node.has_value,
            value=float(node.value) if node.value is not None else None,
            unit=node.unit,
            decimals=node.decimals,
            context_ref=node.metadata.get('context_ref'),
            order=node.order,
        )

    def __repr__(self) -> str:
        return (
            f"<HierarchyNode("
            f"mat_acc_id='{self.mat_acc_id}', "
            f"label='{self.label[:30]}...', "
            f"type='{self.node_type}'"
            f")>"
        )

    def to_dict(self) -> dict:
        """
        Convert node to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'node_id': self.node_id,
            'hierarchy_id': self.hierarchy_id,
            'mat_acc_id': self.mat_acc_id,
            'mat_acc_position': self.mat_acc_position,
            'level': self.level,
            'sibling': self.sibling,
            'parent_mat_acc_id': self.parent_mat_acc_id,
            'concept': self.concept,
            'label': self.label,
            'standard_label': self.standard_label,
            'label_source': self.label_source,
            'taxonomy_namespace': self.taxonomy_namespace,
            'node_type': self.node_type,
            'has_value': self.has_value,
            'value': self.value,
            'unit': self.unit,
            'decimals': self.decimals,
            'context_ref': self.context_ref,
            'order': self.order,
        }


__all__ = ['HierarchyNode']
