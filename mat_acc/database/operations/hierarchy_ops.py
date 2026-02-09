# Path: mat_acc/database/operations/hierarchy_ops.py
"""
Hierarchy Operations

CRUD operations for StatementHierarchy and HierarchyNode records.
Provides methods for storing, querying, and managing hierarchies.

Supports fact merging: when a FactMerger is provided, nodes are expanded
into fact instances with context_ref, enabling unique mat_acc_id per fact.
"""

import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from sqlalchemy.orm import Session

from database.models.statement_hierarchies import StatementHierarchy
from database.models.hierarchy_nodes import HierarchyNode as DBHierarchyNode
from database.models.processed_filings import ProcessedFiling

if TYPE_CHECKING:
    from process.hierarchy.fact_merger import FactMerger


logger = logging.getLogger(__name__)


class HierarchyOperations:
    """
    Operations for StatementHierarchy and HierarchyNode records.

    Provides static methods for storing and querying hierarchies.
    Key method is store_hierarchy() which converts HierarchyBuilder
    output to database records.

    Example:
        from process.hierarchy import HierarchyBuilder
        from database import session_scope, HierarchyOperations

        builder = HierarchyBuilder()
        hierarchies = builder.build_from_filing_folder(filing_path)

        with session_scope() as session:
            for name, root in hierarchies.items():
                HierarchyOperations.store_hierarchy(
                    session,
                    filing_id=filing.filing_id,
                    name=name,
                    root=root
                )
    """

    @staticmethod
    def store_hierarchy(
        session: Session,
        filing_id: str,
        name: str,
        root: 'process.hierarchy.HierarchyNode',
        fact_merger: Optional['FactMerger'] = None
    ) -> StatementHierarchy:
        """
        Store a hierarchy from HierarchyBuilder output.

        Converts a process.hierarchy.HierarchyNode tree to database records.
        When fact_merger is provided, nodes are expanded into fact instances
        with context_ref for unique identification in ratio calculations.

        Args:
            session: Database session
            filing_id: ID of parent ProcessedFiling
            name: Statement name
            root: Root HierarchyNode from process.hierarchy
            fact_merger: Optional FactMerger for expanding nodes with facts

        Returns:
            Created StatementHierarchy instance
        """
        # Get statement metadata from root
        statement_type = root.metadata.get('statement_type', 'UNKNOWN')
        role_uri = root.metadata.get('role_uri', '')
        role_definition = root.metadata.get('role_definition', '')

        # Get statement code from first child's mat_acc_id (root has special code)
        statement_code = ''
        for node in root.iter_preorder():
            mat_acc_id = node.metadata.get('mat_acc_id', '')
            if mat_acc_id and '-' in mat_acc_id:
                statement_code = mat_acc_id.split('-')[0]
                break

        if not statement_code:
            # Fallback: generate from statement type
            from process.hierarchy.mat_acc_id import get_statement_code
            statement_code = get_statement_code(statement_type)

        # Calculate statistics
        node_count = root.descendant_count + 1
        max_depth = root.max_depth
        root_count = len([c for c in root.children if c.depth == 1])

        line_item_count = 0
        abstract_count = 0
        total_count = 0

        for node in root.iter_preorder():
            if node.node_type.value == 'line_item':
                line_item_count += 1
            elif node.node_type.value == 'abstract':
                abstract_count += 1
            elif node.node_type.value == 'total':
                total_count += 1

        # Create hierarchy record
        hierarchy = StatementHierarchy(
            filing_id=filing_id,
            statement_name=name,
            statement_type=statement_type,
            statement_code=statement_code,
            role_uri=role_uri,
            role_definition=role_definition,
            node_count=node_count,
            max_depth=max_depth,
            root_count=root_count,
            line_item_count=line_item_count,
            abstract_count=abstract_count,
            total_count=total_count,
        )
        session.add(hierarchy)
        session.flush()  # Get the ID

        # Store all nodes (with fact expansion if merger provided)
        actual_node_count = HierarchyOperations._store_nodes_recursive(
            session,
            hierarchy.hierarchy_id,
            root,
            parent_mat_acc_id=None,
            fact_merger=fact_merger
        )

        # Update node count if fact expansion changed it
        if actual_node_count != node_count:
            hierarchy.node_count = actual_node_count

        logger.debug(
            f"Stored hierarchy '{name}' ({statement_type}): "
            f"{actual_node_count} nodes, depth={max_depth}"
        )

        return hierarchy

    @staticmethod
    def _store_nodes_recursive(
        session: Session,
        hierarchy_id: str,
        node: 'process.hierarchy.HierarchyNode',
        parent_mat_acc_id: Optional[str],
        fact_merger: Optional['FactMerger'] = None
    ) -> int:
        """
        Recursively store nodes from a HierarchyNode tree.

        When fact_merger is provided, expands each concept node into
        multiple fact instances (one per context_ref found in parsed.json).

        Args:
            session: Database session
            hierarchy_id: ID of parent StatementHierarchy
            node: Current HierarchyNode to store
            parent_mat_acc_id: mat_acc_id of parent node (structural position)
            fact_merger: Optional FactMerger for fact expansion

        Returns:
            Number of nodes stored (including expanded fact instances)
        """
        from process.hierarchy.mat_acc_id import normalize_context_ref

        nodes_stored = 0
        mat_acc_position = node.metadata.get('mat_acc_position', '')

        # Check if we should expand this node with facts
        facts_to_store = []
        if fact_merger and node.concept:
            facts = fact_merger.get_facts_for_concept(node.concept)
            if facts:
                facts_to_store = facts

        if facts_to_store:
            # Store one node per fact (with context_ref)
            for fact in facts_to_store:
                # Create mat_acc_id with context_ref
                ctx = normalize_context_ref(fact.context_ref)
                mat_acc_id_with_ctx = f"{mat_acc_position}-{ctx}"

                # Create database node with fact data
                db_node = DBHierarchyNode(
                    hierarchy_id=hierarchy_id,
                    mat_acc_id=mat_acc_id_with_ctx,
                    mat_acc_position=mat_acc_position,
                    level=node.depth,
                    sibling=node.metadata.get('sibling', 1),
                    parent_mat_acc_id=parent_mat_acc_id,
                    concept=node.concept,
                    label=node.label,
                    node_type=node.node_type.value,
                    has_value=fact.has_numeric_value,
                    value=fact.numeric_value,
                    unit=fact.unit,
                    decimals=fact.decimals,
                    context_ref=fact.context_ref,
                    order=node.order,
                )
                session.add(db_node)
                nodes_stored += 1
        else:
            # No facts - store structural node without context_ref
            db_node = DBHierarchyNode.from_hierarchy_node(
                hierarchy_id=hierarchy_id,
                node=node,
                parent_mat_acc_id=parent_mat_acc_id
            )
            session.add(db_node)
            nodes_stored += 1

        # Get this node's mat_acc_position for children (structural parent)
        # Children use structural position as parent, not fact-specific mat_acc_id
        current_mat_acc_position = mat_acc_position

        # Recurse to children
        for child in node.children:
            nodes_stored += HierarchyOperations._store_nodes_recursive(
                session,
                hierarchy_id,
                child,
                parent_mat_acc_id=current_mat_acc_position,
                fact_merger=fact_merger
            )

        return nodes_stored

    @staticmethod
    def store_all_hierarchies(
        session: Session,
        filing_id: str,
        hierarchies: Dict[str, 'process.hierarchy.HierarchyNode'],
        fact_merger: Optional['FactMerger'] = None
    ) -> List[StatementHierarchy]:
        """
        Store all hierarchies for a filing.

        When fact_merger is provided, nodes are expanded into fact instances
        with context_ref from parsed.json, enabling unique mat_acc_id per fact.

        Args:
            session: Database session
            filing_id: ID of parent ProcessedFiling
            hierarchies: Dict mapping statement names to root nodes
            fact_merger: Optional FactMerger for fact expansion

        Returns:
            List of created StatementHierarchy instances
        """
        results = []
        total_nodes = 0

        for name, root in hierarchies.items():
            hierarchy = HierarchyOperations.store_hierarchy(
                session, filing_id, name, root, fact_merger=fact_merger
            )
            results.append(hierarchy)
            total_nodes += hierarchy.node_count

        # Update filing stats
        filing = session.query(ProcessedFiling).filter_by(
            filing_id=filing_id
        ).first()
        if filing:
            filing.statement_count = len(results)
            filing.total_node_count = total_nodes

        logger.info(
            f"Stored {len(results)} hierarchies with {total_nodes} total nodes"
        )

        return results

    @staticmethod
    def find_hierarchy_by_id(
        session: Session,
        hierarchy_id: str
    ) -> Optional[StatementHierarchy]:
        """
        Find hierarchy by ID.

        Args:
            session: Database session
            hierarchy_id: Hierarchy UUID

        Returns:
            StatementHierarchy or None
        """
        return session.query(StatementHierarchy).filter_by(
            hierarchy_id=hierarchy_id
        ).first()

    @staticmethod
    def find_hierarchies_by_filing(
        session: Session,
        filing_id: str
    ) -> List[StatementHierarchy]:
        """
        Find all hierarchies for a filing.

        Args:
            session: Database session
            filing_id: Filing UUID

        Returns:
            List of StatementHierarchy records
        """
        return session.query(StatementHierarchy).filter_by(
            filing_id=filing_id
        ).order_by(StatementHierarchy.statement_name).all()

    @staticmethod
    def find_hierarchies_by_type(
        session: Session,
        statement_type: str,
        limit: int = 100
    ) -> List[StatementHierarchy]:
        """
        Find hierarchies by statement type.

        Args:
            session: Database session
            statement_type: Statement type (BALANCE_SHEET, etc.)
            limit: Maximum results

        Returns:
            List of StatementHierarchy records
        """
        return session.query(StatementHierarchy).filter_by(
            statement_type=statement_type
        ).limit(limit).all()

    @staticmethod
    def find_hierarchies_by_code(
        session: Session,
        statement_code: str,
        limit: int = 100
    ) -> List[StatementHierarchy]:
        """
        Find hierarchies by statement code.

        Args:
            session: Database session
            statement_code: Statement code (BS, IS, etc.)
            limit: Maximum results

        Returns:
            List of StatementHierarchy records
        """
        return session.query(StatementHierarchy).filter_by(
            statement_code=statement_code
        ).limit(limit).all()

    @staticmethod
    def find_node_by_mat_acc_id(
        session: Session,
        hierarchy_id: str,
        mat_acc_id: str
    ) -> Optional[DBHierarchyNode]:
        """
        Find a node by its mat_acc_id within a hierarchy.

        Args:
            session: Database session
            hierarchy_id: Hierarchy UUID
            mat_acc_id: mat_acc_id to find

        Returns:
            HierarchyNode or None
        """
        return session.query(DBHierarchyNode).filter_by(
            hierarchy_id=hierarchy_id,
            mat_acc_id=mat_acc_id
        ).first()

    @staticmethod
    def find_nodes_by_concept(
        session: Session,
        concept: str,
        limit: int = 100
    ) -> List[DBHierarchyNode]:
        """
        Find nodes by XBRL concept name.

        Args:
            session: Database session
            concept: Concept name (e.g., us-gaap:Assets)
            limit: Maximum results

        Returns:
            List of HierarchyNode records
        """
        return session.query(DBHierarchyNode).filter_by(
            concept=concept
        ).limit(limit).all()

    @staticmethod
    def find_nodes_at_level(
        session: Session,
        hierarchy_id: str,
        level: int
    ) -> List[DBHierarchyNode]:
        """
        Find all nodes at a specific level in a hierarchy.

        Args:
            session: Database session
            hierarchy_id: Hierarchy UUID
            level: Depth level (0 = root)

        Returns:
            List of HierarchyNode records at that level
        """
        return session.query(DBHierarchyNode).filter_by(
            hierarchy_id=hierarchy_id,
            level=level
        ).order_by(DBHierarchyNode.sibling).all()

    @staticmethod
    def find_children(
        session: Session,
        hierarchy_id: str,
        parent_mat_acc_id: str
    ) -> List[DBHierarchyNode]:
        """
        Find children of a node.

        Args:
            session: Database session
            hierarchy_id: Hierarchy UUID
            parent_mat_acc_id: Parent's mat_acc_id

        Returns:
            List of child HierarchyNode records
        """
        return session.query(DBHierarchyNode).filter_by(
            hierarchy_id=hierarchy_id,
            parent_mat_acc_id=parent_mat_acc_id
        ).order_by(DBHierarchyNode.sibling).all()

    @staticmethod
    def get_hierarchy_with_nodes(
        session: Session,
        hierarchy_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get hierarchy with all its nodes as dictionary.

        Args:
            session: Database session
            hierarchy_id: Hierarchy UUID

        Returns:
            Dictionary with hierarchy and nodes, or None
        """
        hierarchy = HierarchyOperations.find_hierarchy_by_id(
            session, hierarchy_id
        )
        if not hierarchy:
            return None

        return hierarchy.to_dict_with_nodes()

    @staticmethod
    def delete_hierarchy(
        session: Session,
        hierarchy: StatementHierarchy
    ) -> None:
        """
        Delete a hierarchy and all its nodes.

        Args:
            session: Database session
            hierarchy: Hierarchy to delete
        """
        name = hierarchy.statement_name
        session.delete(hierarchy)
        logger.info(f"Deleted hierarchy: {name}")

    @staticmethod
    def count_hierarchies(session: Session) -> int:
        """
        Count total hierarchies.

        Args:
            session: Database session

        Returns:
            Total count
        """
        return session.query(StatementHierarchy).count()

    @staticmethod
    def count_nodes(session: Session) -> int:
        """
        Count total nodes across all hierarchies.

        Args:
            session: Database session

        Returns:
            Total count
        """
        return session.query(DBHierarchyNode).count()


__all__ = ['HierarchyOperations']
