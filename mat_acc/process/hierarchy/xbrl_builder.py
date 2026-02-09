# Path: mat_acc/process/hierarchy/xbrl_builder.py
"""
XBRL Hierarchy Builder - Builds hierarchies from XBRL presentation linkbase.

This module extracts statement hierarchies directly from XBRL filing's
presentation linkbase files. The presentation linkbase is the authoritative
source for statement structure.

Market Agnostic: Works with any XBRL filing (SEC, ESEF, FCA, etc.)
"""

import logging
from pathlib import Path
from typing import Optional

from process.hierarchy.constants import NodeType
from process.hierarchy.node import HierarchyNode, create_root_node
from process.hierarchy.builder_utils import (
    detect_node_type_from_concept,
    sort_children_recursive,
    concept_to_label,
    generate_mat_acc_ids_for_tree,
)

# Logger setup
try:
    from core.logger import get_process_logger
    logger = get_process_logger('hierarchy.xbrl_builder')
except ImportError:
    logger = logging.getLogger(__name__)


class XbrlHierarchyBuilder:
    """
    Builds hierarchies from XBRL presentation linkbase files.

    This is the PRIMARY method for building fact hierarchies.
    The presentation linkbase (_pre.xml) is the authoritative source
    for statement structure.

    Example:
        builder = XbrlHierarchyBuilder()
        hierarchies = builder.build_from_filing(Path('/path/to/filing/'))

        for name, root in hierarchies.items():
            print(f"{name}: {root.descendant_count} nodes")
    """

    def __init__(self):
        """Initialize the XBRL hierarchy builder."""
        self._build_count = 0
        self._last_error: Optional[str] = None
        self._discovered_types: set[str] = set()
        self._linkbase_parser = None

    def build_from_filing(
        self,
        filing_dir: Path
    ) -> dict[str, HierarchyNode]:
        """
        Build hierarchies from XBRL filing's presentation linkbase.

        Args:
            filing_dir: Path to the XBRL filing directory

        Returns:
            Dictionary mapping statement names to their root nodes
        """
        from process.hierarchy.linkbase_parser import LinkbaseParser

        if self._linkbase_parser is None:
            self._linkbase_parser = LinkbaseParser()

        # Find linkbase files
        linkbase_files = self._linkbase_parser.find_linkbase_files(filing_dir)

        if not linkbase_files.get('presentation'):
            self._last_error = f"No presentation linkbase found in {filing_dir}"
            logger.warning(self._last_error)
            return {}

        return self.build_from_linkbase(linkbase_files['presentation'])

    def build_from_linkbase(
        self,
        linkbase_path: Path
    ) -> dict[str, HierarchyNode]:
        """
        Build hierarchies from a presentation linkbase file.

        Args:
            linkbase_path: Path to the presentation linkbase file (*_pre.xml)

        Returns:
            Dictionary mapping statement names to their root nodes
        """
        from process.hierarchy.linkbase_parser import LinkbaseParser

        if self._linkbase_parser is None:
            self._linkbase_parser = LinkbaseParser()

        roles = self._linkbase_parser.parse_presentation_linkbase(linkbase_path)

        if not roles:
            self._last_error = f"No roles found in {linkbase_path}"
            logger.warning(self._last_error)
            return {}

        result = {}

        for role in roles:
            hierarchy = self._build_from_role(role)
            if hierarchy:
                key = self._role_to_key(role)
                result[key] = hierarchy
                self._discovered_types.add(role.statement_type)

        logger.info(
            f"Built {len(result)} hierarchies from XBRL linkbase. "
            f"Types: {self._discovered_types}"
        )

        return result

    def _build_from_role(self, role) -> Optional[HierarchyNode]:
        """
        Build hierarchy from a StatementRole.

        Args:
            role: StatementRole from LinkbaseParser

        Returns:
            Root node of the hierarchy
        """
        # Create root node for the statement
        root_label = role.role_definition or self._extract_role_name(role.role_uri)
        root = create_root_node(
            label=root_label,
            concept=f"role:{role.role_uri}"
        )
        root.metadata['statement_type'] = role.statement_type
        root.metadata['role_uri'] = role.role_uri

        # Build node lookup from locators
        nodes: dict[str, HierarchyNode] = {}

        for label, locator in role.locators.items():
            node = HierarchyNode(
                concept=locator.concept_name,
                label=concept_to_label(locator.concept_name),
                node_type=detect_node_type_from_concept(locator.concept_name),
            )
            nodes[label] = node

        # Build parent-child relationships from arcs
        for arc in role.arcs:
            if arc.from_label in nodes and arc.to_label in nodes:
                parent_node = nodes[arc.from_label]
                child_node = nodes[arc.to_label]

                child_node.order = arc.order
                if arc.preferred_label:
                    child_node.metadata['preferred_label'] = arc.preferred_label

                if child_node not in parent_node.children:
                    parent_node.add_child(child_node)

        # Find and attach root concepts (parents that aren't children)
        child_labels = {arc.to_label for arc in role.arcs}
        for label, node in nodes.items():
            if label not in child_labels and node.parent is None:
                root.add_child(node)

        # Sort children by order
        sort_children_recursive(root)

        # Generate mat_acc_id for each node
        generate_mat_acc_ids_for_tree(root, role.statement_type)

        self._build_count += 1

        return root

    def _role_to_key(self, role) -> str:
        """Convert role to a dictionary key."""
        uri = role.role_uri
        if '#' in uri:
            name = uri.split('#')[-1]
        elif '/' in uri:
            name = uri.split('/')[-1]
        else:
            name = uri

        # Clean up the name
        name = name.replace('Statement', '').replace('Disclosure', '')
        name = ''.join(c if c.isalnum() else '_' for c in name)
        name = name.strip('_').lower()

        return name or 'unknown'

    def _extract_role_name(self, role_uri: str) -> str:
        """Extract human-readable name from role URI."""
        if '#' in role_uri:
            name = role_uri.split('#')[-1]
        elif '/' in role_uri:
            name = role_uri.split('/')[-1]
        else:
            name = role_uri

        # Convert CamelCase to spaces
        result = []
        for char in name:
            if char.isupper() and result:
                result.append(' ')
            result.append(char)

        return ''.join(result)

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


__all__ = ['XbrlHierarchyBuilder']
