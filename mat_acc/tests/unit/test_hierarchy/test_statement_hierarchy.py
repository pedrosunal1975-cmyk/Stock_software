# Path: mat_acc/tests/unit/test_hierarchy/test_statement_hierarchy.py
"""
Tests for statement hierarchy module.
"""

import pytest
import json
import sys
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

# Add mat_acc to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from process.hierarchy.constants import NodeType, StatementType
from process.hierarchy.node import HierarchyNode, create_root_node
from process.hierarchy.statement_hierarchy import (
    StatementHierarchy,
    create_statement_hierarchy,
)


@pytest.fixture
def sample_hierarchy():
    """Create a sample hierarchy for testing."""
    root = create_root_node(label="Balance Sheet", concept="root:balance_sheet")

    # Add some child nodes
    assets = HierarchyNode(concept="us-gaap:Assets", label="Assets", node_type=NodeType.ABSTRACT)
    root.add_child(assets)

    current_assets = HierarchyNode(
        concept="us-gaap:CurrentAssets",
        label="Current Assets",
        node_type=NodeType.ABSTRACT
    )
    assets.add_child(current_assets)

    cash = HierarchyNode(
        concept="us-gaap:Cash",
        label="Cash",
        node_type=NodeType.LINE_ITEM,
        value=Decimal("50000"),
        unit="USD"
    )
    current_assets.add_child(cash)

    receivables = HierarchyNode(
        concept="us-gaap:AccountsReceivable",
        label="Accounts Receivable",
        node_type=NodeType.LINE_ITEM,
        value=Decimal("30000"),
        unit="USD"
    )
    current_assets.add_child(receivables)

    total_current = HierarchyNode(
        concept="us-gaap:CurrentAssetsTotal",
        label="Total Current Assets",
        node_type=NodeType.TOTAL,
        value=Decimal("80000"),
        unit="USD"
    )
    current_assets.add_child(total_current)

    return StatementHierarchy(
        root=root,
        statement_type=StatementType.BALANCE_SHEET,
        company="Test Company",
        period_end="2024-12-31",
        currency="USD"
    )


class TestStatementHierarchyCreation:
    """Test StatementHierarchy creation."""

    def test_create_statement_hierarchy(self, sample_hierarchy):
        """Can create a StatementHierarchy."""
        assert sample_hierarchy is not None
        assert sample_hierarchy.root is not None

    def test_hierarchy_has_attributes(self, sample_hierarchy):
        """StatementHierarchy has expected attributes."""
        assert sample_hierarchy.statement_type == StatementType.BALANCE_SHEET
        assert sample_hierarchy.company == "Test Company"
        assert sample_hierarchy.period_end == "2024-12-31"
        assert sample_hierarchy.currency == "USD"

    def test_factory_function(self):
        """create_statement_hierarchy factory works."""
        root = create_root_node(label="Income Statement")
        hierarchy = create_statement_hierarchy(
            root=root,
            statement_type=StatementType.INCOME_STATEMENT,
            company="Factory Co",
            period_end="2024-06-30",
            extra_info="test"
        )

        assert hierarchy.company == "Factory Co"
        assert hierarchy.metadata.get('extra_info') == "test"


class TestStatementHierarchyValidation:
    """Test validation methods."""

    def test_validate_returns_tuple(self, sample_hierarchy):
        """validate returns (bool, list) tuple."""
        is_valid, messages = sample_hierarchy.validate()

        assert isinstance(is_valid, bool)
        assert isinstance(messages, list)

    def test_valid_hierarchy_passes(self, sample_hierarchy):
        """Valid hierarchy passes validation."""
        is_valid, messages = sample_hierarchy.validate()
        assert is_valid is True

    def test_is_valid_property(self, sample_hierarchy):
        """is_valid property returns boolean."""
        assert sample_hierarchy.is_valid is True

    def test_too_few_nodes_fails(self):
        """Hierarchy with too few nodes fails."""
        root = create_root_node(label="Empty")
        hierarchy = StatementHierarchy(root=root)

        is_valid, messages = hierarchy.validate()

        assert is_valid is False


class TestStatementHierarchyStatistics:
    """Test statistics methods."""

    def test_node_count(self, sample_hierarchy):
        """node_count returns total nodes."""
        # root + assets + current_assets + cash + receivables + total_current = 6
        assert sample_hierarchy.node_count == 6

    def test_line_item_count(self, sample_hierarchy):
        """line_item_count returns valued nodes."""
        # cash + receivables = 2 (total_current is TOTAL type)
        assert sample_hierarchy.line_item_count == 2

    def test_abstract_count(self, sample_hierarchy):
        """abstract_count returns abstract nodes."""
        # assets + current_assets = 2
        assert sample_hierarchy.abstract_count == 2

    def test_total_count(self, sample_hierarchy):
        """total_count returns total/subtotal nodes."""
        # total_current = 1
        assert sample_hierarchy.total_count == 1

    def test_max_depth(self, sample_hierarchy):
        """max_depth returns deepest level."""
        # root(0) -> assets(1) -> current_assets(2) -> cash(3)
        assert sample_hierarchy.max_depth == 3

    def test_get_statistics(self, sample_hierarchy):
        """get_statistics returns complete stats dict."""
        stats = sample_hierarchy.get_statistics()

        assert 'node_count' in stats
        assert 'line_item_count' in stats
        assert 'statement_type' in stats
        assert stats['company'] == "Test Company"


class TestStatementHierarchyIteration:
    """Test iteration methods."""

    def test_iter_line_items(self, sample_hierarchy):
        """iter_line_items yields valued line items."""
        items = list(sample_hierarchy.iter_line_items())

        # cash and receivables have values and are LINE_ITEM type
        assert len(items) == 2
        concepts = [n.concept for n in items]
        assert "us-gaap:Cash" in concepts
        assert "us-gaap:AccountsReceivable" in concepts

    def test_iter_abstracts(self, sample_hierarchy):
        """iter_abstracts yields abstract nodes."""
        abstracts = list(sample_hierarchy.iter_abstracts())

        assert len(abstracts) == 2
        concepts = [n.concept for n in abstracts]
        assert "us-gaap:Assets" in concepts

    def test_iter_totals(self, sample_hierarchy):
        """iter_totals yields total nodes."""
        totals = list(sample_hierarchy.iter_totals())

        assert len(totals) == 1
        assert totals[0].label == "Total Current Assets"

    def test_iter_at_depth(self, sample_hierarchy):
        """iter_at_depth yields nodes at specific depth."""
        depth_1_nodes = list(sample_hierarchy.iter_at_depth(1))

        # Only "Assets" is at depth 1
        assert len(depth_1_nodes) == 1
        assert depth_1_nodes[0].label == "Assets"

    def test_dunder_iter(self, sample_hierarchy):
        """Can iterate hierarchy directly."""
        nodes = list(sample_hierarchy)
        assert len(nodes) == 6


class TestStatementHierarchySearch:
    """Test search methods."""

    def test_find_by_concept(self, sample_hierarchy):
        """find_by_concept finds node."""
        node = sample_hierarchy.find_by_concept("us-gaap:Cash")

        assert node is not None
        assert node.label == "Cash"

    def test_find_by_concept_not_found(self, sample_hierarchy):
        """find_by_concept returns None when not found."""
        node = sample_hierarchy.find_by_concept("nonexistent")
        assert node is None

    def test_find_by_label(self, sample_hierarchy):
        """find_by_label finds node."""
        node = sample_hierarchy.find_by_label("Cash")

        assert node is not None
        assert node.concept == "us-gaap:Cash"

    def test_find_by_label_contains(self, sample_hierarchy):
        """find_by_label_contains finds multiple nodes."""
        nodes = sample_hierarchy.find_by_label_contains("Assets")

        # Assets, Current Assets, Total Current Assets = 3
        assert len(nodes) == 3

    def test_get_top_level_items(self, sample_hierarchy):
        """get_top_level_items returns direct children of root."""
        items = sample_hierarchy.get_top_level_items()

        # Only "Assets" is direct child of root
        assert len(items) == 1
        assert items[0].label == "Assets"

    def test_contains_operator(self, sample_hierarchy):
        """'in' operator checks for concept."""
        assert "us-gaap:Cash" in sample_hierarchy
        assert "nonexistent" not in sample_hierarchy


class TestStatementHierarchyExport:
    """Test export methods."""

    def test_to_dict(self, sample_hierarchy):
        """to_dict converts to dictionary."""
        d = sample_hierarchy.to_dict()

        assert 'metadata' in d
        assert 'statistics' in d
        assert 'hierarchy' in d
        assert d['metadata']['company'] == "Test Company"

    def test_to_json(self, sample_hierarchy):
        """to_json converts to JSON string."""
        json_str = sample_hierarchy.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed['metadata']['company'] == "Test Company"

    def test_to_json_file(self, sample_hierarchy):
        """to_json_file writes to file."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_hierarchy.json"
            sample_hierarchy.to_json_file(path)

            assert path.exists()

            with open(path) as f:
                data = json.load(f)
            assert data['metadata']['company'] == "Test Company"

    def test_to_text(self, sample_hierarchy):
        """to_text converts to indented text."""
        text = sample_hierarchy.to_text()

        assert "Balance Sheet" in text
        assert "Test Company" in text
        assert "Cash" in text
        assert "50,000" in text or "50000" in text

    def test_to_flat_list(self, sample_hierarchy):
        """to_flat_list converts to list of dicts."""
        items = sample_hierarchy.to_flat_list()

        assert len(items) == 6
        assert all('concept' in item for item in items)
        assert all('label' in item for item in items)
        assert all('depth' in item for item in items)


class TestStatementHierarchySpecialMethods:
    """Test special/dunder methods."""

    def test_str(self, sample_hierarchy):
        """__str__ returns readable string."""
        s = str(sample_hierarchy)

        assert "balance_sheet" in s
        assert "Test Company" in s

    def test_repr(self, sample_hierarchy):
        """__repr__ returns debug string."""
        r = repr(sample_hierarchy)

        assert "StatementHierarchy" in r

    def test_len(self, sample_hierarchy):
        """len() returns node count."""
        assert len(sample_hierarchy) == 6
