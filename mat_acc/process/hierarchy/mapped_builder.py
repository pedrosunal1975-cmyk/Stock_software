# Path: mat_acc/process/hierarchy/mapped_builder.py
"""
Mapped Statement Hierarchy Builder - Builds hierarchies from mapper output.

This module builds hierarchies from the map_pro mapper's JSON output files.
Supports both the modern hierarchy format and legacy line_items format.

Structure Awareness:
The mapper outputs individual statement JSONs in:
  - json/core_statements/  (main financial statements)
  - json/details/          (detailed disclosures)
  - json/other/            (other statements)
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from process.hierarchy.constants import (
    NodeType,
    MAX_HIERARCHY_DEPTH,
    StatementType,
)
from process.hierarchy.node import HierarchyNode, create_root_node
from process.hierarchy.builder_utils import (
    extract_value,
    determine_node_type,
    detect_node_type_from_concept,
    sort_children_recursive,
    generate_mat_acc_ids_for_tree,
    create_node_with_metadata,
    concept_to_label,
)

# Logger setup
try:
    from core.logger import get_process_logger
    logger = get_process_logger('hierarchy.mapped_builder')
except ImportError:
    logger = logging.getLogger(__name__)


class MappedHierarchyBuilder:
    """
    Builds hierarchies from mapped statement JSON files.

    Supports:
    - Modern hierarchy format (statement_type + hierarchy field)
    - Legacy format (statements dict with line_items)

    Example:
        builder = MappedHierarchyBuilder()

        # Build from a single statement file
        hierarchy = builder.build_from_file(Path('statement.json'))

        # Build all statements from a filing folder
        hierarchies = builder.build_from_folder(Path('/mapped/filing/'))
    """

    def __init__(self):
        """Initialize the mapped hierarchy builder."""
        self._build_count = 0
        self._last_error: Optional[str] = None
        self._discovered_types: set[str] = set()

    # =========================================================================
    # PUBLIC BUILD METHODS
    # =========================================================================

    def build_from_file(
        self,
        json_path: Path
    ) -> Optional[HierarchyNode]:
        """
        Build hierarchy from a single statement JSON file.

        Args:
            json_path: Path to the statement JSON file

        Returns:
            Root node of the hierarchy, or None if build failed
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return self._build_from_data(data, json_path.stem)

        except json.JSONDecodeError as e:
            self._last_error = f"JSON decode error in {json_path}: {e}"
            logger.error(self._last_error)
            return None
        except Exception as e:
            self._last_error = f"Error reading {json_path}: {e}"
            logger.error(self._last_error)
            return None

    def build_from_data(
        self,
        data: dict[str, Any],
        statement_name: str = "statement"
    ) -> Optional[HierarchyNode]:
        """
        Build hierarchy from statement data dictionary.

        Args:
            data: Statement data with hierarchy field
            statement_name: Name for the statement

        Returns:
            Root node of the hierarchy, or None if build failed
        """
        return self._build_from_data(data, statement_name)

    def build_from_folder(
        self,
        filing_folder: Path,
        include_details: bool = True,
        include_other: bool = True
    ) -> dict[str, HierarchyNode]:
        """
        Build hierarchies from all statement files in a mapped filing folder.

        Searches json/core_statements/, json/details/, json/other/ folders.

        Args:
            filing_folder: Path to the mapped filing folder
            include_details: Whether to include statements from details/
            include_other: Whether to include statements from other/

        Returns:
            Dictionary mapping statement names to their root nodes
        """
        result = {}

        # Find the json folder
        json_folder = filing_folder / 'json'
        if not json_folder.exists():
            json_folder = filing_folder
            if not json_folder.exists():
                self._last_error = f"JSON folder not found in {filing_folder}"
                logger.warning(self._last_error)
                return result

        # Define folders to search
        folders_to_search = ['core_statements']
        if include_details:
            folders_to_search.append('details')
        if include_other:
            folders_to_search.append('other')

        # Search each folder for statement files
        for folder_name in folders_to_search:
            folder_path = json_folder / folder_name
            if not folder_path.exists() or not folder_path.is_dir():
                continue

            for json_file in folder_path.glob('*.json'):
                hierarchy = self.build_from_file(json_file)
                if hierarchy:
                    key = json_file.stem
                    result[key] = hierarchy
                    logger.info(f"Built hierarchy for '{key}' from {folder_name}/")

        logger.info(f"Built {len(result)} hierarchies from {filing_folder}")
        return result

    def build_from_filing_entry(
        self,
        filing_entry: Any,
        include_details: bool = True,
        include_other: bool = True
    ) -> dict[str, HierarchyNode]:
        """
        Build hierarchies from a MappedFilingEntry.

        Args:
            filing_entry: MappedFilingEntry from MappedDataLoader
            include_details: Whether to include details/
            include_other: Whether to include other/

        Returns:
            Dictionary mapping statement names to their root nodes
        """
        if hasattr(filing_entry, 'json_folder') and filing_entry.json_folder:
            return self.build_from_folder(
                filing_entry.json_folder.parent,
                include_details=include_details,
                include_other=include_other
            )
        elif hasattr(filing_entry, 'filing_folder'):
            return self.build_from_folder(
                filing_entry.filing_folder,
                include_details=include_details,
                include_other=include_other
            )
        else:
            self._last_error = "Invalid filing entry - no folder path"
            logger.error(self._last_error)
            return {}

    # =========================================================================
    # INTERNAL BUILD METHODS
    # =========================================================================

    def _build_from_data(
        self,
        data: dict[str, Any],
        statement_name: str
    ) -> Optional[HierarchyNode]:
        """Build hierarchy from statement data dictionary."""
        try:
            # Extract statement type DYNAMICALLY from the data
            statement_type = data.get('statement_type', 'UNKNOWN')
            self._discovered_types.add(statement_type)

            # Get role information
            role_uri = data.get('role_uri', '')
            role_definition = data.get('role_definition', statement_name)

            # Create root node
            root_label = role_definition or statement_name
            root = create_root_node(
                label=root_label,
                concept=f"root:{statement_name}"
            )
            root.metadata['statement_type'] = statement_type
            root.metadata['role_uri'] = role_uri
            root.metadata['statement_name'] = statement_name

            # Get hierarchy data
            hierarchy_data = data.get('hierarchy', {})
            if not hierarchy_data:
                logger.warning(f"No hierarchy data in {statement_name}")
                return root

            # Build from hierarchy structure
            self._build_from_hierarchy_data(root, hierarchy_data)

            # Generate mat_acc_id for each node
            generate_mat_acc_ids_for_tree(root, statement_type)

            self._build_count += 1
            logger.info(
                f"Built hierarchy for '{statement_name}' "
                f"(type: {statement_type}): {root.descendant_count + 1} nodes"
            )

            return root

        except Exception as e:
            self._last_error = f"Build failed for {statement_name}: {e}"
            logger.error(self._last_error)
            return None

    def _build_from_hierarchy_data(
        self,
        root: HierarchyNode,
        hierarchy_data: dict[str, Any]
    ) -> None:
        """
        Build hierarchy from hierarchy field structure.

        Supports TWO formats:
        1. Mapper format: roots, children (dict), parents (dict), order (dict)
        2. Legacy format: roots, nodes (dict), arcs (list)
        """
        roots = hierarchy_data.get('roots', [])

        # Detect format by checking for 'children' KEY (mapper format)
        # vs 'arcs' KEY (legacy format)
        # Note: Use 'in' check, not truthiness, since empty dicts/lists are valid
        if 'children' in hierarchy_data:
            # MAPPER FORMAT: children dict, order dict
            children_map = hierarchy_data.get('children', {})
            order_map = hierarchy_data.get('order', {})
            self._build_from_children_format(root, roots, children_map, order_map)
        else:
            # LEGACY FORMAT: nodes dict, arcs list
            nodes_data = hierarchy_data.get('nodes', {})
            arcs = hierarchy_data.get('arcs', [])
            self._build_from_arcs_format(root, roots, nodes_data, arcs)

    def _build_from_children_format(
        self,
        root: HierarchyNode,
        roots: list[str],
        children_map: dict[str, list[str]],
        order_map: dict[str, float]
    ) -> None:
        """
        Build hierarchy from mapper's children dict format.

        Args:
            root: Root node to attach children to
            roots: List of root concept names
            children_map: Dict mapping parent concept -> [child concepts]
            order_map: Dict mapping concept -> order value
        """
        # Collect all concepts from children map
        all_concepts = set(roots)
        for parent, children in children_map.items():
            all_concepts.add(parent)
            all_concepts.update(children)

        if not all_concepts:
            logger.warning("Empty hierarchy - no concepts found")
            return

        # Create nodes for all concepts
        nodes: dict[str, HierarchyNode] = {}
        for concept in all_concepts:
            order = float(order_map.get(concept, 0))
            node = self._create_node_from_concept(concept, order)
            if node:
                nodes[concept] = node

        # Establish parent-child relationships from children map
        for parent_concept, child_concepts in children_map.items():
            if parent_concept not in nodes:
                continue

            parent_node = nodes[parent_concept]

            for child_concept in child_concepts:
                if child_concept not in nodes:
                    continue

                child_node = nodes[child_concept]
                if child_node not in parent_node.children:
                    parent_node.add_child(child_node)

        # Attach root concepts to the statement root
        for root_concept in roots:
            if root_concept in nodes:
                root_node = nodes[root_concept]
                if root_node.parent is None:
                    root.add_child(root_node)

        # Attach any orphan nodes (concepts with no parent in children_map)
        for concept, node in nodes.items():
            if node.parent is None and concept not in roots:
                root.add_child(node)

        # Sort children by order
        sort_children_recursive(root)

        logger.debug(
            f"Built hierarchy from children format: {len(nodes)} nodes, "
            f"{len(roots)} roots"
        )

    def _build_from_arcs_format(
        self,
        root: HierarchyNode,
        roots: list[str],
        nodes_data: dict[str, Any],
        arcs: list[dict[str, Any]]
    ) -> None:
        """
        Build hierarchy from legacy arcs list format.

        Args:
            root: Root node to attach children to
            roots: List of root concept names
            nodes_data: Dict mapping concept -> node data
            arcs: List of arc objects with from/to/order
        """
        if not roots and not nodes_data:
            logger.warning("Empty hierarchy data - no roots or nodes")
            return

        # Create all nodes first
        nodes: dict[str, HierarchyNode] = {}

        for concept, node_data in nodes_data.items():
            node = self._create_node(concept, node_data)
            if node:
                nodes[concept] = node

        # Establish parent-child relationships from arcs
        for arc in arcs:
            parent_concept = arc.get('from', arc.get('parent', ''))
            child_concept = arc.get('to', arc.get('child', ''))
            order = arc.get('order', 0)

            if parent_concept in nodes and child_concept in nodes:
                parent_node = nodes[parent_concept]
                child_node = nodes[child_concept]

                if order:
                    child_node.order = float(order)

                if child_node not in parent_node.children:
                    parent_node.add_child(child_node)

        # Attach root concepts to the statement root
        for root_concept in roots:
            if root_concept in nodes:
                root_node = nodes[root_concept]
                if root_node.parent is None:
                    root.add_child(root_node)

        # Attach any orphan nodes
        for concept, node in nodes.items():
            if node.parent is None and concept not in roots:
                root.add_child(node)

        # Sort children by order
        sort_children_recursive(root)

    def _create_node_from_concept(
        self,
        concept: str,
        order: float = 0
    ) -> Optional[HierarchyNode]:
        """
        Create a hierarchy node from just a concept name.

        Used when hierarchy data has children dict but no nodes dict.

        Args:
            concept: Concept name (e.g., 'us-gaap:Assets')
            order: Sort order

        Returns:
            HierarchyNode instance
        """
        if not concept:
            return None

        # Generate label from concept name
        label = concept_to_label(concept)

        # Detect node type from concept name
        node_type = detect_node_type_from_concept(concept)

        node = HierarchyNode(
            concept=concept,
            label=label,
            node_type=node_type,
            order=order,
        )

        return node

    def _create_node(
        self,
        concept: str,
        node_data: dict[str, Any]
    ) -> Optional[HierarchyNode]:
        """Create a hierarchy node from hierarchy node data."""
        if not concept:
            return None

        # Extract label
        label = node_data.get('label', node_data.get('preferred_label', ''))
        if not label:
            label = concept.split(':')[-1].split('_')[-1]

        return create_node_with_metadata(concept, label, node_data)

    # =========================================================================
    # LEGACY BUILD METHODS (for backward compatibility)
    # =========================================================================

    def build_from_mapped_statement(
        self,
        mapped_data: dict[str, Any],
        statement_key: Optional[str] = None
    ) -> Optional[HierarchyNode]:
        """
        Build hierarchy from a mapped statement dictionary.

        LEGACY METHOD - kept for backward compatibility.

        Args:
            mapped_data: Mapped statement data
            statement_key: Optional specific statement to build

        Returns:
            Root node of the hierarchy, or None if build failed
        """
        # Try new format first
        if 'hierarchy' in mapped_data:
            return self.build_from_data(mapped_data, statement_key or 'statement')

        # Fall back to legacy format
        return self._build_legacy_format(mapped_data, statement_key)

    def build_all_statements(
        self,
        mapped_data: dict[str, Any]
    ) -> dict[str, HierarchyNode]:
        """
        Build hierarchies for all statements in mapped data.

        LEGACY METHOD - kept for backward compatibility.

        Args:
            mapped_data: Mapped statement data

        Returns:
            Dictionary mapping statement keys to their root nodes
        """
        if 'hierarchy' in mapped_data:
            hierarchy = self.build_from_data(mapped_data, 'statement')
            return {'statement': hierarchy} if hierarchy else {}

        return self._build_all_legacy_format(mapped_data)

    def _build_legacy_format(
        self,
        mapped_data: dict[str, Any],
        statement_key: Optional[str] = None
    ) -> Optional[HierarchyNode]:
        """Build from legacy format (statements dict with line_items)."""
        statements = self._normalize_statements_legacy(mapped_data)

        if not statements:
            self._last_error = "No statements found in mapped data"
            logger.warning(self._last_error)
            return None

        if statement_key:
            statement_data = statements.get(statement_key)
            if not statement_data:
                for key, data in statements.items():
                    if statement_key.lower() in key.lower():
                        statement_data = data
                        statement_key = key
                        break

            if not statement_data:
                self._last_error = f"Statement '{statement_key}' not found"
                logger.warning(self._last_error)
                return None
        else:
            statement_key = next(iter(statements.keys()))
            statement_data = statements[statement_key]

        root = self._build_statement_hierarchy_legacy(statement_key, statement_data)

        if root:
            self._build_count += 1

        return root

    def _build_all_legacy_format(
        self,
        mapped_data: dict[str, Any]
    ) -> dict[str, HierarchyNode]:
        """Build all statements from legacy format."""
        result = {}
        statements = self._normalize_statements_legacy(mapped_data)

        for statement_key, statement_data in statements.items():
            hierarchy = self._build_statement_hierarchy_legacy(statement_key, statement_data)
            if hierarchy:
                result[statement_key] = hierarchy

        return result

    def _normalize_statements_legacy(
        self,
        mapped_data: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Normalize statements to dict format (legacy)."""
        raw_statements = mapped_data.get('statements', [])
        if not raw_statements:
            raw_statements = mapped_data.get('financial_statements', [])

        if not raw_statements:
            return {}

        if isinstance(raw_statements, dict):
            return raw_statements

        if isinstance(raw_statements, list):
            result = {}
            for i, stmt in enumerate(raw_statements):
                if not isinstance(stmt, dict):
                    continue

                name = (
                    stmt.get('statement_name') or
                    stmt.get('statement_type') or
                    stmt.get('name') or
                    stmt.get('title') or
                    f"statement_{i}"
                )

                key = name.lower().replace(' ', '_').replace('-', '_')
                result[key] = stmt

            return result

        return {}

    def _build_statement_hierarchy_legacy(
        self,
        statement_key: str,
        statement_data: dict[str, Any]
    ) -> Optional[HierarchyNode]:
        """Build hierarchy from legacy format statement."""
        statement_type = self._detect_statement_type_from_key(statement_key)

        root_label = statement_data.get('title', statement_key.replace('_', ' ').title())
        root = create_root_node(label=root_label, concept=f"root:{statement_key}")
        root.metadata['statement_type'] = statement_type
        root.metadata['statement_key'] = statement_key

        line_items = statement_data.get('line_items', [])
        if not line_items:
            line_items = statement_data.get('items', [])
        if not line_items:
            line_items = statement_data.get('rows', [])

        if not line_items:
            logger.warning(f"No line items found in statement '{statement_key}'")
            return root

        self._build_from_line_items_legacy(root, line_items)

        return root

    def _build_from_line_items_legacy(
        self,
        root: HierarchyNode,
        line_items: list[dict[str, Any]]
    ) -> None:
        """Build hierarchy from line items (legacy format)."""
        parent_stack: list[HierarchyNode] = [root]
        last_depth = 0

        for item in line_items:
            node = self._create_node_legacy(item)
            if node is None:
                continue

            item_depth = item.get('depth', item.get('level', 1))
            if item_depth < 0:
                item_depth = 0
            if item_depth > MAX_HIERARCHY_DEPTH:
                item_depth = MAX_HIERARCHY_DEPTH

            if item_depth > last_depth:
                if parent_stack and parent_stack[-1].children:
                    parent_stack.append(parent_stack[-1].children[-1])
            elif item_depth < last_depth:
                while len(parent_stack) > item_depth + 1:
                    parent_stack.pop()

            while len(parent_stack) <= item_depth:
                parent_stack.append(parent_stack[-1])

            current_parent = parent_stack[min(item_depth, len(parent_stack) - 1)]
            current_parent.add_child(node)

            last_depth = item_depth

    def _create_node_legacy(
        self,
        item: dict[str, Any]
    ) -> Optional[HierarchyNode]:
        """Create node from legacy line item format."""
        concept = item.get('concept', item.get('name', ''))
        if not concept:
            return None

        label = item.get('label', item.get('preferred_label', concept))
        node_type = determine_node_type(concept, label, item)
        value = extract_value(item)
        order = float(item.get('order', item.get('sort_order', 0)))

        node = HierarchyNode(
            concept=concept,
            label=label,
            node_type=node_type,
            value=value,
            order=order,
            unit=item.get('unit', item.get('unit_ref')),
            decimals=item.get('decimals'),
        )

        if 'context_ref' in item:
            node.metadata['context_ref'] = item['context_ref']
        if 'period' in item:
            node.metadata['period'] = item['period']
        if 'balance_type' in item:
            node.metadata['balance_type'] = item['balance_type']

        return node

    def _detect_statement_type_from_key(self, statement_key: str) -> str:
        """Detect statement type from key (legacy helper)."""
        key_lower = statement_key.lower()

        if any(kw in key_lower for kw in ('balance', 'financial_position', 'assets')):
            return 'BALANCE_SHEET'
        if any(kw in key_lower for kw in ('income', 'operations', 'profit', 'loss')):
            return 'INCOME_STATEMENT'
        if any(kw in key_lower for kw in ('cash', 'cashflow')):
            return 'CASH_FLOW'
        if any(kw in key_lower for kw in ('equity', 'stockholders', 'shareholders')):
            return 'EQUITY'

        return 'UNKNOWN'

    # Keep for test compatibility
    def _detect_statement_type(self, statement_key: str) -> StatementType:
        """Detect statement type - kept for test compatibility."""
        type_str = self._detect_statement_type_from_key(statement_key)
        try:
            return StatementType(type_str.lower())
        except ValueError:
            return StatementType.UNKNOWN

    def _determine_node_type(
        self,
        item: dict[str, Any],
        concept: str,
        label: str
    ) -> NodeType:
        """Determine node type - kept for test compatibility."""
        return determine_node_type(concept, label, item)

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error

    @property
    def build_count(self) -> int:
        """Get number of successful builds."""
        return self._build_count

    @property
    def discovered_types(self) -> set[str]:
        """Get all dynamically discovered statement types."""
        return self._discovered_types.copy()

    def reset_stats(self) -> None:
        """Reset build statistics."""
        self._build_count = 0
        self._last_error = None
        self._discovered_types.clear()


__all__ = ['MappedHierarchyBuilder']
