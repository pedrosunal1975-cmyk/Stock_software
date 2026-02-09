# Path: mat_acc/process/hierarchy/__init__.py
"""
Hierarchy Builder Package for mat_acc

Builds navigable tree structures from financial statement presentations.
Uses presentation linkbase data to establish parent-child relationships.

Components:
- HierarchyNode: Individual node in the hierarchy tree
- HierarchyBuilder: Main orchestrator for building hierarchies
- XbrlHierarchyBuilder: Builds from XBRL presentation linkbase
- MappedHierarchyBuilder: Builds from mapped statement JSON files
- StatementHierarchy: Complete statement hierarchy with navigation
- LinkbaseParser: Parses XBRL presentation/calculation linkbase files

mat_acc_id Utilities:
- format_mat_acc_id: Generate mat_acc_id from components
- parse_mat_acc_id: Parse mat_acc_id into components
- get_statement_code: Get statement code from type

Example:
    from process.hierarchy import HierarchyBuilder, LinkbaseParser

    # Parse linkbase files directly (source of truth for hierarchy)
    parser = LinkbaseParser()
    linkbase_files = parser.find_linkbase_files(Path('/path/to/xbrl/filing'))
    roles = parser.parse_presentation_linkbase(linkbase_files['presentation'])

    # Or use HierarchyBuilder for integrated workflow
    builder = HierarchyBuilder()
    hierarchies = builder.build_from_xbrl_filing(Path('/path/to/xbrl/filing'))
"""

from process.hierarchy.constants import NodeType, StatementType
from process.hierarchy.node import HierarchyNode, create_root_node
from process.hierarchy.tree_builder import HierarchyBuilder
from process.hierarchy.xbrl_builder import XbrlHierarchyBuilder
from process.hierarchy.mapped_builder import MappedHierarchyBuilder
from process.hierarchy.statement_hierarchy import StatementHierarchy
from process.hierarchy.linkbase_parser import (
    LinkbaseParser,
    LinkbaseLocator,
    LinkbaseArc,
    StatementRole,
)
from process.hierarchy.mat_acc_id import (
    generate_statement_code,
    get_statement_code,
    get_statement_type,
    format_mat_acc_id,
    format_position,
    parse_mat_acc_id,
    normalize_context_ref,
    add_context_to_position,
    get_registered_types,
    clear_registry,
)

__all__ = [
    # Node types
    'HierarchyNode',
    'create_root_node',
    'NodeType',
    'StatementType',
    # Builders
    'HierarchyBuilder',
    'XbrlHierarchyBuilder',
    'MappedHierarchyBuilder',
    'StatementHierarchy',
    # Linkbase parsing
    'LinkbaseParser',
    'LinkbaseLocator',
    'LinkbaseArc',
    'StatementRole',
    # mat_acc_id utilities (DYNAMIC code generation)
    'generate_statement_code',
    'get_statement_code',
    'get_statement_type',
    'format_mat_acc_id',
    'format_position',
    'parse_mat_acc_id',
    'normalize_context_ref',
    'add_context_to_position',
    'get_registered_types',
    'clear_registry',
]
