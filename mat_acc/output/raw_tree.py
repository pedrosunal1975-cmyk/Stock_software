# Path: mat_acc/output/raw_tree.py
"""
Raw Tree Generator for mat_acc

Generates human-readable tree visualizations of statement hierarchies
stored in the database. Creates both ASCII text and JSON formats.

The ASCII tree format displays hierarchies like the 'tree' command:

    BS-000-000 [ROOT] StatementOfFinancialPosition
    +-- BS-001-001 [Abstract] Assets
    |   +-- BS-001-002-c4 CurrentAssets .................. 12,456,000
    |   |   +-- BS-001-003-c4 Cash ....................... 2,345,000
    |   |   `-- BS-001-004-c4 Inventories ................ 4,567,000
    |   `-- BS-001-005-c4 NonCurrentAssets ............... 34,567,000
    `-- BS-002-001 [Abstract] Liabilities
        `-- ...

Usage:
    generator = RawTreeGenerator()
    generator.generate_for_filing(filing_id)
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from config_loader import ConfigLoader
from database.models.base import initialize_engine, session_scope
from database.models.processed_filings import ProcessedFiling
from database.models.statement_hierarchies import StatementHierarchy
from database.models.hierarchy_nodes import HierarchyNode


logger = logging.getLogger('output.raw_tree')


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class TreeNode:
    """A node in the tree for rendering."""
    mat_acc_id: str
    label: str
    concept: str
    node_type: str
    value: Optional[float] = None
    context_ref: Optional[str] = None
    level: int = 0
    children: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            'mat_acc_id': self.mat_acc_id,
            'label': self.label,
            'concept': self.concept,
            'node_type': self.node_type,
            'level': self.level,
        }
        if self.value is not None:
            result['value'] = self.value
        if self.context_ref:
            result['context_ref'] = self.context_ref
        if self.children:
            result['children'] = [c.to_dict() for c in self.children]
        return result


@dataclass
class StatementTree:
    """A complete statement tree."""
    statement_name: str
    statement_type: str
    statement_code: str
    role_uri: str
    node_count: int
    root: Optional[TreeNode] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'statement_name': self.statement_name,
            'statement_type': self.statement_type,
            'statement_code': self.statement_code,
            'role_uri': self.role_uri,
            'node_count': self.node_count,
            'tree': self.root.to_dict() if self.root else None,
        }


@dataclass
class FilingTrees:
    """All trees for a filing."""
    filing_id: str
    market: str
    company_name: str
    form_type: str
    filing_date: str
    generated_at: str
    statements: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'filing_id': self.filing_id,
            'market': self.market,
            'company_name': self.company_name,
            'form_type': self.form_type,
            'filing_date': self.filing_date,
            'generated_at': self.generated_at,
            'statement_count': len(self.statements),
            'statements': [s.to_dict() for s in self.statements],
        }


# ==============================================================================
# TEXT FORMATTER
# ==============================================================================

class RawTreeFormatter:
    """
    Formats tree data as ASCII art.

    Uses box-drawing characters for clear hierarchy visualization:
    +-- for branch
    |   for continuation
    `-- for last child
    """

    # Tree drawing characters
    BRANCH = '+-- '
    LAST_BRANCH = '`-- '
    PIPE = '|   '
    SPACE = '    '

    # Value alignment column
    VALUE_COLUMN = 60

    def __init__(self, use_unicode: bool = False):
        """
        Initialize formatter.

        Args:
            use_unicode: Use Unicode box-drawing chars instead of ASCII
        """
        if use_unicode:
            self.BRANCH = '\u251c\u2500\u2500 '  # ├──
            self.LAST_BRANCH = '\u2514\u2500\u2500 '  # └──
            self.PIPE = '\u2502   '  # │
            self.SPACE = '    '

    def format_filing(self, filing_trees: FilingTrees) -> str:
        """
        Format all statement trees for a filing.

        Args:
            filing_trees: FilingTrees object with all statements

        Returns:
            Formatted string for the entire filing
        """
        lines = []

        # Header
        lines.append('=' * 80)
        lines.append(f'{filing_trees.company_name}')
        lines.append(f'{filing_trees.form_type} - {filing_trees.filing_date}')
        lines.append(f'Market: {filing_trees.market.upper()}')
        lines.append(f'Generated: {filing_trees.generated_at}')
        lines.append('=' * 80)
        lines.append('')

        # Summary
        lines.append(f'Statements: {len(filing_trees.statements)}')
        total_nodes = sum(s.node_count for s in filing_trees.statements)
        lines.append(f'Total nodes: {total_nodes}')
        lines.append('')

        # Each statement
        for statement in filing_trees.statements:
            lines.extend(self.format_statement(statement))
            lines.append('')

        return '\n'.join(lines)

    def format_statement(self, statement: StatementTree) -> list[str]:
        """
        Format a single statement tree.

        Args:
            statement: StatementTree object

        Returns:
            List of formatted lines
        """
        lines = []

        # Statement header
        lines.append('-' * 80)
        lines.append(f'{statement.statement_name} ({statement.statement_code})')
        lines.append(f'Type: {statement.statement_type}')
        lines.append(f'Nodes: {statement.node_count}')
        lines.append('-' * 80)
        lines.append('')

        # Tree
        if statement.root:
            lines.extend(self._format_node(statement.root, '', True))

        return lines

    def _format_node(
        self,
        node: TreeNode,
        prefix: str,
        is_last: bool
    ) -> list[str]:
        """
        Recursively format a node and its children.

        Args:
            node: TreeNode to format
            prefix: Current line prefix for indentation
            is_last: Whether this is the last child of its parent

        Returns:
            List of formatted lines
        """
        lines = []

        # Build the node line
        connector = self.LAST_BRANCH if is_last else self.BRANCH

        # Node type indicator
        type_indicator = self._get_type_indicator(node.node_type)

        # Build the display line
        node_text = f'{node.mat_acc_id} {type_indicator} {node.label or node.concept}'

        # Add value if present
        if node.value is not None:
            # Calculate dots for alignment
            current_len = len(prefix) + len(connector) + len(node_text)
            dots_needed = max(2, self.VALUE_COLUMN - current_len)
            dots = '.' * dots_needed
            value_str = self._format_value(node.value)
            node_text = f'{node_text} {dots} {value_str}'

        lines.append(f'{prefix}{connector}{node_text}')

        # Process children
        child_prefix = prefix + (self.SPACE if is_last else self.PIPE)
        for i, child in enumerate(node.children):
            is_child_last = (i == len(node.children) - 1)
            lines.extend(self._format_node(child, child_prefix, is_child_last))

        return lines

    def _get_type_indicator(self, node_type: str) -> str:
        """Get a visual indicator for node type."""
        indicators = {
            'root': '[ROOT]',
            'abstract': '[Abstract]',
            'line_item': '',
            'total': '[Total]',
            'subtotal': '[Subtotal]',
        }
        return indicators.get(node_type, '')

    def _format_value(self, value: float) -> str:
        """Format a numeric value with thousand separators."""
        if value is None:
            return ''

        # Handle negative values
        if value < 0:
            return f'({abs(value):,.0f})'

        return f'{value:,.0f}'


# ==============================================================================
# TREE GENERATOR
# ==============================================================================

class RawTreeGenerator:
    """
    Generates raw tree outputs from the mat_acc database.

    Creates directory structure: /{market}/{company}/{form}/{period}/
    Generates:
    - raw_tree.txt: Human-readable ASCII tree
    - raw_tree.json: Machine-readable JSON

    Example:
        generator = RawTreeGenerator()
        generator.generate_for_filing(filing_id)
        # Or all filings:
        generator.generate_all()
    """

    def __init__(self, output_base: Optional[Path] = None):
        """
        Initialize the generator.

        Args:
            output_base: Base directory for outputs.
                         Defaults to config's output_dir.
        """
        self.config = ConfigLoader()

        if output_base:
            self.output_base = Path(output_base)
        else:
            self.output_base = Path(self.config.get('output_dir'))

        self.formatter = RawTreeFormatter(use_unicode=False)

        # Ensure database is initialized
        initialize_engine()

        logger.info(f'RawTreeGenerator initialized, output: {self.output_base}')

    def generate_all(self) -> list[dict]:
        """
        Generate raw trees for all filings in the database.

        Returns:
            List of result dictionaries with file paths
        """
        results = []

        with session_scope() as session:
            filings = session.query(ProcessedFiling).all()

            for filing in filings:
                try:
                    result = self._generate_for_filing_record(session, filing)
                    results.append(result)
                except Exception as e:
                    logger.error(f'Error generating tree for {filing.filing_id}: {e}')
                    results.append({
                        'filing_id': filing.filing_id,
                        'success': False,
                        'error': str(e),
                    })

        return results

    def generate_for_filing(self, filing_id: str) -> dict:
        """
        Generate raw tree for a specific filing.

        Args:
            filing_id: UUID of the filing

        Returns:
            Result dictionary with file paths
        """
        with session_scope() as session:
            filing = session.query(ProcessedFiling).filter_by(
                filing_id=filing_id
            ).first()

            if not filing:
                raise ValueError(f'Filing not found: {filing_id}')

            return self._generate_for_filing_record(session, filing)

    def _generate_for_filing_record(
        self,
        session,
        filing: ProcessedFiling
    ) -> dict:
        """Generate outputs for a filing record."""
        # Build output path
        output_dir = self._get_output_path(filing)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build tree data
        filing_trees = self._build_filing_trees(session, filing)

        # Generate text output
        txt_path = output_dir / 'raw_tree.txt'
        txt_content = self.formatter.format_filing(filing_trees)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(txt_content)

        # Generate JSON output
        json_path = output_dir / 'raw_tree.json'
        json_content = json.dumps(filing_trees.to_dict(), indent=2)
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(json_content)

        logger.info(
            f'Generated raw trees for {filing.company_name}/{filing.form_type}: '
            f'{output_dir}'
        )

        return {
            'filing_id': filing.filing_id,
            'success': True,
            'output_dir': str(output_dir),
            'txt_path': str(txt_path),
            'json_path': str(json_path),
            'statement_count': len(filing_trees.statements),
        }

    def _get_output_path(self, filing: ProcessedFiling) -> Path:
        """
        Build output path following map_pro pattern.

        Pattern: /{market}/{company}/{form}/{period}/
        """
        # Sanitize names for filesystem
        company = self._sanitize_filename(filing.company_name)
        form = self._sanitize_filename(filing.form_type)
        period = filing.filing_date.isoformat()

        return self.output_base / filing.market / company / form / period

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as filename."""
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        # Remove or replace problematic characters
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            name = name.replace(char, '_')
        return name

    def _build_filing_trees(
        self,
        session,
        filing: ProcessedFiling
    ) -> FilingTrees:
        """Build FilingTrees from database records."""
        filing_trees = FilingTrees(
            filing_id=str(filing.filing_id),
            market=filing.market,
            company_name=filing.company_name,
            form_type=filing.form_type,
            filing_date=filing.filing_date.isoformat(),
            generated_at=datetime.now().isoformat(),
        )

        # Get all hierarchies for this filing
        hierarchies = session.query(StatementHierarchy).filter_by(
            filing_id=filing.filing_id
        ).order_by(StatementHierarchy.statement_name).all()

        for hierarchy in hierarchies:
            statement_tree = self._build_statement_tree(session, hierarchy)
            filing_trees.statements.append(statement_tree)

        return filing_trees

    def _build_statement_tree(
        self,
        session,
        hierarchy: StatementHierarchy
    ) -> StatementTree:
        """Build StatementTree from a hierarchy record."""
        statement = StatementTree(
            statement_name=hierarchy.statement_name,
            statement_type=hierarchy.statement_type,
            statement_code=hierarchy.statement_code,
            role_uri=hierarchy.role_uri or '',
            node_count=hierarchy.node_count,
        )

        # Get all nodes for this hierarchy
        nodes = session.query(HierarchyNode).filter_by(
            hierarchy_id=hierarchy.hierarchy_id
        ).order_by(HierarchyNode.level, HierarchyNode.sibling).all()

        # Build tree structure
        statement.root = self._build_node_tree(nodes)

        return statement

    def _build_node_tree(self, nodes: list[HierarchyNode]) -> Optional[TreeNode]:
        """
        Build a TreeNode tree from flat list of database nodes.

        Uses mat_acc_position to determine parent-child relationships.
        """
        if not nodes:
            return None

        # Index nodes by mat_acc_position (structural position without context)
        # Group nodes by their structural position
        nodes_by_position = {}
        for node in nodes:
            position = node.mat_acc_position or node.mat_acc_id
            if position not in nodes_by_position:
                nodes_by_position[position] = []
            nodes_by_position[position].append(node)

        # Create TreeNodes - use first node of each position for structure
        tree_nodes = {}
        for position, node_list in nodes_by_position.items():
            # For nodes with context_ref, use the one with value if available
            primary_node = node_list[0]
            for n in node_list:
                if n.value is not None:
                    primary_node = n
                    break

            tree_node = TreeNode(
                mat_acc_id=primary_node.mat_acc_id,
                label=primary_node.label or '',
                concept=primary_node.concept or '',
                node_type=primary_node.node_type or 'line_item',
                value=primary_node.value,
                context_ref=primary_node.context_ref,
                level=primary_node.level,
            )
            tree_nodes[position] = tree_node

        # Build parent-child relationships
        root = None
        for position, tree_node in tree_nodes.items():
            # Find parent
            parent_position = None
            for node in nodes_by_position[position]:
                if node.parent_mat_acc_id:
                    parent_position = node.parent_mat_acc_id
                    break

            if parent_position and parent_position in tree_nodes:
                tree_nodes[parent_position].children.append(tree_node)
            elif tree_node.level == 0:
                root = tree_node

        # Sort children by mat_acc_id
        def sort_children(node):
            node.children.sort(key=lambda x: x.mat_acc_id)
            for child in node.children:
                sort_children(child)

        if root:
            sort_children(root)

        return root


__all__ = ['RawTreeGenerator', 'RawTreeFormatter']
