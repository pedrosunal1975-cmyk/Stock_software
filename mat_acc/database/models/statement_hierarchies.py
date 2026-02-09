# Path: mat_acc/database/models/statement_hierarchies.py
"""
Statement Hierarchy Model

Stores statement hierarchy metadata and links to hierarchy nodes.
Each hierarchy represents one financial statement from a filing.

Architecture:
- Statement type dynamically detected
- Statement code dynamically generated
- Links to individual nodes via relationship
"""

import uuid as uuid_module
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship

from database.models.base import Base


class StatementHierarchy(Base):
    """
    Statement hierarchy record.

    Stores metadata for a single financial statement hierarchy.
    Links to hierarchy nodes that contain the actual structure.

    Example:
        hierarchy = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='consolidatedbalancesheets',
            statement_type='BALANCE_SHEET',
            statement_code='BS',
            role_uri='http://apple.com/role/BalanceSheet',
            node_count=39,
            max_depth=4
        )
    """
    __tablename__ = 'statement_hierarchies'

    # Primary key
    hierarchy_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid_module.uuid4()),
        comment="Unique hierarchy identifier"
    )

    # Foreign key to filing
    filing_id = Column(
        String(36),
        ForeignKey('processed_filings.filing_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Reference to source filing"
    )

    # Statement identification
    statement_name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Statement name (e.g., 'consolidatedbalancesheets')"
    )
    statement_type = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Statement type (e.g., 'BALANCE_SHEET', 'INCOME_STATEMENT')"
    )
    statement_code = Column(
        String(10),
        nullable=False,
        index=True,
        comment="Dynamic 2-letter code (e.g., 'BS', 'IS')"
    )

    # Role information
    role_uri = Column(
        Text,
        comment="XBRL role URI for this statement"
    )
    role_definition = Column(
        Text,
        comment="Role definition/description"
    )

    # Structure statistics
    node_count = Column(
        Integer,
        default=0,
        comment="Total number of nodes in hierarchy"
    )
    max_depth = Column(
        Integer,
        default=0,
        comment="Maximum hierarchy depth"
    )
    root_count = Column(
        Integer,
        default=0,
        comment="Number of root nodes"
    )
    line_item_count = Column(
        Integer,
        default=0,
        comment="Number of line item nodes"
    )
    abstract_count = Column(
        Integer,
        default=0,
        comment="Number of abstract nodes"
    )
    total_count = Column(
        Integer,
        default=0,
        comment="Number of total/subtotal nodes"
    )

    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )

    # Indexes
    __table_args__ = (
        Index('idx_hierarchy_filing_type', 'filing_id', 'statement_type'),
        Index('idx_hierarchy_code', 'statement_code'),
    )

    # Relationships
    filing = relationship(
        "ProcessedFiling",
        back_populates="hierarchies"
    )
    nodes = relationship(
        "HierarchyNode",
        back_populates="hierarchy",
        cascade="all, delete-orphan",
        order_by="HierarchyNode.level, HierarchyNode.sibling"
    )

    @property
    def root_nodes(self):
        """
        Get root nodes (level 0) of this hierarchy.

        Returns:
            List of root HierarchyNode objects
        """
        return [n for n in self.nodes if n.level == 0]

    def get_node_by_mat_acc_id(self, mat_acc_id: str) -> Optional['HierarchyNode']:
        """
        Find a node by its mat_acc_id.

        Args:
            mat_acc_id: The mat_acc_id to search for

        Returns:
            HierarchyNode or None
        """
        for node in self.nodes:
            if node.mat_acc_id == mat_acc_id:
                return node
        return None

    def get_nodes_at_level(self, level: int):
        """
        Get all nodes at a specific depth level.

        Args:
            level: The depth level (0 = root)

        Returns:
            List of HierarchyNode objects at that level
        """
        return [n for n in self.nodes if n.level == level]

    def __repr__(self) -> str:
        return (
            f"<StatementHierarchy("
            f"id={self.hierarchy_id[:8]}..., "
            f"name='{self.statement_name}', "
            f"type='{self.statement_type}', "
            f"code='{self.statement_code}', "
            f"nodes={self.node_count}"
            f")>"
        )

    def to_dict(self) -> dict:
        """
        Convert hierarchy to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'hierarchy_id': self.hierarchy_id,
            'filing_id': self.filing_id,
            'statement_name': self.statement_name,
            'statement_type': self.statement_type,
            'statement_code': self.statement_code,
            'role_uri': self.role_uri,
            'role_definition': self.role_definition,
            'node_count': self.node_count,
            'max_depth': self.max_depth,
            'root_count': self.root_count,
            'line_item_count': self.line_item_count,
            'abstract_count': self.abstract_count,
            'total_count': self.total_count,
            'created_at': str(self.created_at) if self.created_at else None,
        }

    def to_dict_with_nodes(self) -> dict:
        """
        Convert hierarchy to dictionary including all nodes.

        Returns:
            Dictionary with hierarchy and nodes
        """
        result = self.to_dict()
        result['nodes'] = [n.to_dict() for n in self.nodes]
        return result


__all__ = ['StatementHierarchy']
