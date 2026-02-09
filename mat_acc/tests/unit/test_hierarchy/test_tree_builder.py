# Path: mat_acc/tests/unit/test_hierarchy/test_tree_builder.py
"""
Tests for hierarchy tree builder module.
"""

import pytest
import sys
from decimal import Decimal
from pathlib import Path

# Add mat_acc to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from process.hierarchy.constants import NodeType, StatementType
from process.hierarchy.tree_builder import HierarchyBuilder


class TestHierarchyBuilderInit:
    """Test HierarchyBuilder initialization."""

    def test_create_builder(self):
        """Can create a HierarchyBuilder instance."""
        builder = HierarchyBuilder()
        assert builder is not None

    def test_initial_build_count_is_zero(self):
        """Initial build count should be zero."""
        builder = HierarchyBuilder()
        assert builder.build_count == 0

    def test_initial_last_error_is_none(self):
        """Initial last_error should be None."""
        builder = HierarchyBuilder()
        assert builder.last_error is None


class TestBuildFromMappedStatement:
    """Test building hierarchy from mapped statement data."""

    @pytest.fixture
    def sample_mapped_data(self):
        """Sample mapped statement data."""
        return {
            'statements': {
                'balance_sheet': {
                    'title': 'Consolidated Balance Sheet',
                    'line_items': [
                        {
                            'concept': 'us-gaap:AssetsAbstract',
                            'label': 'Assets',
                            'depth': 0,
                            'is_abstract': True,
                        },
                        {
                            'concept': 'us-gaap:AssetsCurrent',
                            'label': 'Current Assets',
                            'depth': 1,
                            'is_abstract': True,
                        },
                        {
                            'concept': 'us-gaap:Cash',
                            'label': 'Cash',
                            'depth': 2,
                            'value': '50000',
                            'unit': 'USD',
                        },
                        {
                            'concept': 'us-gaap:AccountsReceivable',
                            'label': 'Accounts Receivable',
                            'depth': 2,
                            'value': '30000',
                            'unit': 'USD',
                        },
                        {
                            'concept': 'us-gaap:AssetsCurrentTotal',
                            'label': 'Total Current Assets',
                            'depth': 1,
                            'value': '80000',
                            'unit': 'USD',
                        },
                    ],
                },
            },
        }

    def test_build_from_mapped_statement(self, sample_mapped_data):
        """Can build hierarchy from mapped statement."""
        builder = HierarchyBuilder()
        root = builder.build_from_mapped_statement(sample_mapped_data)

        assert root is not None
        assert root.label == 'Consolidated Balance Sheet'

    def test_build_increments_count(self, sample_mapped_data):
        """Building increments build count."""
        builder = HierarchyBuilder()
        builder.build_from_mapped_statement(sample_mapped_data)

        assert builder.build_count == 1

    def test_build_creates_children(self, sample_mapped_data):
        """Build creates child nodes."""
        builder = HierarchyBuilder()
        root = builder.build_from_mapped_statement(sample_mapped_data)

        assert root.child_count > 0

    def test_build_with_specific_statement(self, sample_mapped_data):
        """Can build specific statement by key."""
        builder = HierarchyBuilder()
        root = builder.build_from_mapped_statement(
            sample_mapped_data,
            statement_key='balance_sheet'
        )

        assert root is not None
        assert 'balance_sheet' in root.metadata.get('statement_key', '')

    def test_build_missing_statement_returns_none(self, sample_mapped_data):
        """Building non-existent statement returns None."""
        builder = HierarchyBuilder()
        root = builder.build_from_mapped_statement(
            sample_mapped_data,
            statement_key='nonexistent'
        )

        assert root is None
        assert builder.last_error is not None

    def test_build_empty_data_returns_none(self):
        """Building from empty data returns None."""
        builder = HierarchyBuilder()
        root = builder.build_from_mapped_statement({})

        assert root is None

    def test_values_are_extracted(self, sample_mapped_data):
        """Numeric values are extracted correctly."""
        builder = HierarchyBuilder()
        root = builder.build_from_mapped_statement(sample_mapped_data)

        # Find node with value
        cash_node = root.find_by_concept('us-gaap:Cash')
        assert cash_node is not None
        assert cash_node.value == Decimal('50000')


class TestBuildAllStatements:
    """Test building all statements at once."""

    @pytest.fixture
    def multi_statement_data(self):
        """Data with multiple statements."""
        return {
            'statements': {
                'balance_sheet': {
                    'title': 'Balance Sheet',
                    'line_items': [
                        {'concept': 'assets', 'label': 'Assets', 'depth': 0},
                    ],
                },
                'income_statement': {
                    'title': 'Income Statement',
                    'line_items': [
                        {'concept': 'revenue', 'label': 'Revenue', 'depth': 0},
                    ],
                },
            },
        }

    def test_build_all_statements(self, multi_statement_data):
        """Can build all statements at once."""
        builder = HierarchyBuilder()
        hierarchies = builder.build_all_statements(multi_statement_data)

        assert 'balance_sheet' in hierarchies
        assert 'income_statement' in hierarchies

    def test_each_statement_has_root(self, multi_statement_data):
        """Each statement gets its own root node."""
        builder = HierarchyBuilder()
        hierarchies = builder.build_all_statements(multi_statement_data)

        for key, root in hierarchies.items():
            assert root is not None
            assert root.is_root


class TestStatementTypeDetection:
    """Test statement type detection."""

    def test_detect_balance_sheet(self):
        """Detects balance sheet from key."""
        builder = HierarchyBuilder()
        result = builder._detect_statement_type('balance_sheet')
        assert result == StatementType.BALANCE_SHEET

    def test_detect_income_statement(self):
        """Detects income statement from key."""
        builder = HierarchyBuilder()
        result = builder._detect_statement_type('income_statement')
        assert result == StatementType.INCOME_STATEMENT

    def test_detect_cash_flow(self):
        """Detects cash flow from key."""
        builder = HierarchyBuilder()
        result = builder._detect_statement_type('cash_flow_statement')
        assert result == StatementType.CASH_FLOW

    def test_detect_equity(self):
        """Detects equity statement from key."""
        builder = HierarchyBuilder()
        result = builder._detect_statement_type('stockholders_equity')
        assert result == StatementType.EQUITY

    def test_detect_unknown(self):
        """Returns unknown for unrecognized key."""
        builder = HierarchyBuilder()
        result = builder._detect_statement_type('other_disclosures')
        assert result == StatementType.UNKNOWN


class TestNodeTypeDetection:
    """Test node type determination."""

    def test_detect_abstract_from_suffix(self):
        """Detects abstract from concept suffix."""
        builder = HierarchyBuilder()
        node_type = builder._determine_node_type(
            {},
            'us-gaap:AssetsAbstract',
            'Assets'
        )
        assert node_type == NodeType.ABSTRACT

    def test_detect_abstract_from_flag(self):
        """Detects abstract from is_abstract flag."""
        builder = HierarchyBuilder()
        node_type = builder._determine_node_type(
            {'is_abstract': True},
            'us-gaap:Assets',
            'Assets'
        )
        assert node_type == NodeType.ABSTRACT

    def test_detect_total_from_label(self):
        """Detects total from label."""
        builder = HierarchyBuilder()
        node_type = builder._determine_node_type(
            {'value': 100},
            'us-gaap:Assets',
            'Total Assets'
        )
        assert node_type == NodeType.TOTAL

    def test_detect_line_item(self):
        """Detects line item for valued nodes."""
        builder = HierarchyBuilder()
        node_type = builder._determine_node_type(
            {'value': 100},
            'us-gaap:Cash',
            'Cash'
        )
        assert node_type == NodeType.LINE_ITEM


class TestValueExtraction:
    """Test value extraction from line items."""

    def test_extract_decimal_value(self):
        """Extracts decimal value."""
        builder = HierarchyBuilder()
        value = builder._extract_value({'value': '1234.56'})
        assert value == Decimal('1234.56')

    def test_extract_integer_value(self):
        """Extracts integer value."""
        builder = HierarchyBuilder()
        value = builder._extract_value({'value': 1000})
        assert value == Decimal('1000')

    def test_extract_from_fact_value(self):
        """Extracts from fact_value key."""
        builder = HierarchyBuilder()
        value = builder._extract_value({'fact_value': '500'})
        assert value == Decimal('500')

    def test_extract_from_amount(self):
        """Extracts from amount key."""
        builder = HierarchyBuilder()
        value = builder._extract_value({'amount': '750'})
        assert value == Decimal('750')

    def test_extract_removes_commas(self):
        """Removes commas from value string."""
        builder = HierarchyBuilder()
        value = builder._extract_value({'value': '1,234,567'})
        assert value == Decimal('1234567')

    def test_extract_returns_none_for_missing(self):
        """Returns None when no value."""
        builder = HierarchyBuilder()
        value = builder._extract_value({})
        assert value is None

    def test_extract_returns_none_for_na(self):
        """Returns None for N/A values."""
        builder = HierarchyBuilder()
        value = builder._extract_value({'value': 'N/A'})
        assert value is None


class TestResetStats:
    """Test statistics reset."""

    def test_reset_clears_build_count(self):
        """reset_stats clears build count."""
        builder = HierarchyBuilder()
        builder._build_count = 5
        builder.reset_stats()
        assert builder.build_count == 0

    def test_reset_clears_last_error(self):
        """reset_stats clears last error."""
        builder = HierarchyBuilder()
        builder._last_error = "Some error"
        builder.reset_stats()
        assert builder.last_error is None


class TestAlternativeDataStructures:
    """Test building from alternative data structures."""

    def test_build_from_financial_statements_key(self):
        """Can build from 'financial_statements' key."""
        data = {
            'financial_statements': {
                'balance_sheet': {
                    'title': 'Balance Sheet',
                    'line_items': [
                        {'concept': 'assets', 'label': 'Assets', 'depth': 0},
                    ],
                },
            },
        }
        builder = HierarchyBuilder()
        root = builder.build_from_mapped_statement(data)

        assert root is not None

    def test_build_from_items_key(self):
        """Can build from 'items' key."""
        data = {
            'statements': {
                'balance_sheet': {
                    'title': 'Balance Sheet',
                    'items': [
                        {'concept': 'assets', 'label': 'Assets', 'depth': 0},
                    ],
                },
            },
        }
        builder = HierarchyBuilder()
        root = builder.build_from_mapped_statement(data)

        assert root is not None
        assert root.child_count > 0

    def test_build_from_rows_key(self):
        """Can build from 'rows' key."""
        data = {
            'statements': {
                'balance_sheet': {
                    'title': 'Balance Sheet',
                    'rows': [
                        {'concept': 'assets', 'label': 'Assets', 'depth': 0},
                    ],
                },
            },
        }
        builder = HierarchyBuilder()
        root = builder.build_from_mapped_statement(data)

        assert root is not None

    def test_build_from_statements_list(self):
        """Can build from statements as a list."""
        data = {
            'statements': [
                {
                    'statement_name': 'Balance Sheet',
                    'line_items': [
                        {'concept': 'assets', 'label': 'Assets', 'depth': 0},
                        {'concept': 'cash', 'label': 'Cash', 'depth': 1, 'value': 1000},
                    ],
                },
                {
                    'statement_name': 'Income Statement',
                    'line_items': [
                        {'concept': 'revenue', 'label': 'Revenue', 'depth': 0, 'value': 5000},
                    ],
                },
            ],
        }
        builder = HierarchyBuilder()
        hierarchies = builder.build_all_statements(data)

        assert len(hierarchies) == 2
        assert 'balance_sheet' in hierarchies
        assert 'income_statement' in hierarchies

    def test_build_from_statements_list_with_title(self):
        """Can build from statements list using title as key."""
        data = {
            'statements': [
                {
                    'title': 'Consolidated Balance Sheet',
                    'line_items': [
                        {'concept': 'assets', 'label': 'Assets', 'depth': 0},
                    ],
                },
            ],
        }
        builder = HierarchyBuilder()
        hierarchies = builder.build_all_statements(data)

        assert len(hierarchies) == 1
        # Key should be normalized from title
        key = list(hierarchies.keys())[0]
        assert 'balance' in key.lower() or 'consolidated' in key.lower()


class TestNewHierarchyFormat:
    """Test building from new hierarchy format (roots, nodes, arcs)."""

    @pytest.fixture
    def hierarchy_format_data(self):
        """Sample data in the new hierarchy format."""
        return {
            'role_uri': 'http://example.com/role/BalanceSheet',
            'role_definition': 'Consolidated Balance Sheet',
            'statement_type': 'BALANCE_SHEET',
            'hierarchy': {
                'roots': ['us-gaap_AssetsAbstract'],
                'nodes': {
                    'us-gaap_AssetsAbstract': {
                        'label': 'Assets',
                        'is_abstract': True,
                    },
                    'us-gaap_AssetsCurrent': {
                        'label': 'Current Assets',
                        'is_abstract': True,
                    },
                    'us-gaap_Cash': {
                        'label': 'Cash',
                        'value': 50000,
                    },
                    'us-gaap_AccountsReceivable': {
                        'label': 'Accounts Receivable',
                        'value': 30000,
                    },
                },
                'arcs': [
                    {'from': 'us-gaap_AssetsAbstract', 'to': 'us-gaap_AssetsCurrent', 'order': 1},
                    {'from': 'us-gaap_AssetsCurrent', 'to': 'us-gaap_Cash', 'order': 1},
                    {'from': 'us-gaap_AssetsCurrent', 'to': 'us-gaap_AccountsReceivable', 'order': 2},
                ],
            },
        }

    def test_build_from_statement_data(self, hierarchy_format_data):
        """Can build hierarchy from new format with hierarchy field."""
        builder = HierarchyBuilder()
        root = builder.build_from_statement_data(hierarchy_format_data, 'balance_sheet')

        assert root is not None
        assert root.descendant_count > 0

    def test_statement_type_extracted(self, hierarchy_format_data):
        """Statement type is extracted from data."""
        builder = HierarchyBuilder()
        root = builder.build_from_statement_data(hierarchy_format_data, 'balance_sheet')

        assert root.metadata.get('statement_type') == 'BALANCE_SHEET'

    def test_hierarchy_structure_preserved(self, hierarchy_format_data):
        """Hierarchy structure from arcs is preserved."""
        builder = HierarchyBuilder()
        root = builder.build_from_statement_data(hierarchy_format_data, 'balance_sheet')

        # Find the Cash node
        cash_node = root.find_by_concept('us-gaap_Cash')
        assert cash_node is not None

        # Cash should be under Current Assets
        assert 'Current Assets' in cash_node.parent.label

    def test_values_extracted_from_nodes(self, hierarchy_format_data):
        """Values are extracted from nodes."""
        builder = HierarchyBuilder()
        root = builder.build_from_statement_data(hierarchy_format_data, 'balance_sheet')

        cash_node = root.find_by_concept('us-gaap_Cash')
        assert cash_node is not None
        assert cash_node.value == Decimal('50000')

    def test_discovered_types_tracked(self, hierarchy_format_data):
        """Discovered statement types are tracked."""
        builder = HierarchyBuilder()
        builder.build_from_statement_data(hierarchy_format_data, 'balance_sheet')

        assert 'BALANCE_SHEET' in builder.discovered_types

    def test_build_from_mapped_statement_detects_hierarchy_format(self, hierarchy_format_data):
        """build_from_mapped_statement detects new hierarchy format."""
        builder = HierarchyBuilder()
        root = builder.build_from_mapped_statement(hierarchy_format_data)

        assert root is not None
        assert root.metadata.get('statement_type') == 'BALANCE_SHEET'

    def test_empty_hierarchy_still_creates_root(self):
        """Empty hierarchy data still creates root node."""
        data = {
            'statement_type': 'UNKNOWN',
            'hierarchy': {},
        }
        builder = HierarchyBuilder()
        root = builder.build_from_statement_data(data, 'empty')

        assert root is not None
        assert root.child_count == 0

    def test_orphan_nodes_attached_to_root(self):
        """Nodes without parent arcs are attached to root."""
        data = {
            'statement_type': 'TEST',
            'hierarchy': {
                'roots': [],
                'nodes': {
                    'orphan1': {'label': 'Orphan One'},
                    'orphan2': {'label': 'Orphan Two'},
                },
                'arcs': [],
            },
        }
        builder = HierarchyBuilder()
        root = builder.build_from_statement_data(data, 'test')

        assert root.child_count == 2


class TestMapperChildrenFormat:
    """Test building from mapper's children dict format."""

    def test_build_from_children_format(self):
        """Build hierarchy from mapper's children dict format."""
        # This is the format the mapper produces
        data = {
            'statement_type': 'BALANCE_SHEET',
            'hierarchy': {
                'roots': ['us-gaap:AssetsAbstract'],
                'children': {
                    'us-gaap:AssetsAbstract': [
                        'us-gaap:AssetsCurrent',
                        'us-gaap:AssetsNoncurrent',
                    ],
                    'us-gaap:AssetsCurrent': [
                        'us-gaap:CashAndCashEquivalentsAtCarryingValue',
                        'us-gaap:AccountsReceivableNetCurrent',
                    ],
                },
                'parents': {
                    'us-gaap:AssetsCurrent': 'us-gaap:AssetsAbstract',
                    'us-gaap:AssetsNoncurrent': 'us-gaap:AssetsAbstract',
                    'us-gaap:CashAndCashEquivalentsAtCarryingValue': 'us-gaap:AssetsCurrent',
                    'us-gaap:AccountsReceivableNetCurrent': 'us-gaap:AssetsCurrent',
                },
                'order': {
                    'us-gaap:AssetsCurrent': 1.0,
                    'us-gaap:AssetsNoncurrent': 2.0,
                    'us-gaap:CashAndCashEquivalentsAtCarryingValue': 1.0,
                    'us-gaap:AccountsReceivableNetCurrent': 2.0,
                },
            },
        }

        builder = HierarchyBuilder()
        root = builder.build_from_statement_data(data, 'balance_sheet')

        assert root is not None
        # Root should have the statement root as parent of actual hierarchy
        assert root.child_count >= 1  # At least the hierarchy root

        # Count all descendants
        total_nodes = root.descendant_count + 1
        # Should have: statement root + AssetsAbstract + AssetsCurrent + AssetsNoncurrent +
        # CashAndCashEquivalentsAtCarryingValue + AccountsReceivableNetCurrent = 6
        assert total_nodes >= 5

    def test_children_format_preserves_order(self):
        """Children format preserves order from order dict."""
        data = {
            'statement_type': 'INCOME_STATEMENT',
            'hierarchy': {
                'roots': ['parent'],
                'children': {
                    'parent': ['child_b', 'child_a', 'child_c'],
                },
                'parents': {},
                'order': {
                    'child_a': 1.0,
                    'child_b': 2.0,
                    'child_c': 3.0,
                },
            },
        }

        builder = HierarchyBuilder()
        root = builder.build_from_statement_data(data, 'test')

        # Find the parent node (should be first child of root)
        parent_node = root.children[0]

        # Children should be sorted by order
        child_orders = [c.order for c in parent_node.children]
        assert child_orders == sorted(child_orders)

    def test_children_format_empty_hierarchy(self):
        """Empty children format still creates root."""
        data = {
            'statement_type': 'OTHER',
            'hierarchy': {
                'roots': [],
                'children': {},
                'parents': {},
                'order': {},
            },
        }

        builder = HierarchyBuilder()
        root = builder.build_from_statement_data(data, 'empty')

        assert root is not None
        assert root.child_count == 0

    def test_children_format_creates_labels_from_concepts(self):
        """Children format generates labels from concept names."""
        data = {
            'statement_type': 'BALANCE_SHEET',
            'hierarchy': {
                'roots': ['us-gaap:AssetsAbstract'],
                'children': {},
                'parents': {},
                'order': {},
            },
        }

        builder = HierarchyBuilder()
        root = builder.build_from_statement_data(data, 'test')

        # The root should have AssetsAbstract as child
        assert root.child_count == 1
        child = root.children[0]

        # Label should be generated from concept (CamelCase to spaces)
        assert 'Assets' in child.label or 'Abstract' in child.label


class TestBuildFromStatementFile:
    """Test building from statement JSON file."""

    def test_build_from_json_file(self, tmp_path):
        """Can build hierarchy from JSON file."""
        import json

        # Create test file
        test_data = {
            'statement_type': 'INCOME_STATEMENT',
            'hierarchy': {
                'roots': ['revenue'],
                'nodes': {
                    'revenue': {'label': 'Revenue', 'value': 100000},
                },
                'arcs': [],
            },
        }
        test_file = tmp_path / 'test_statement.json'
        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        builder = HierarchyBuilder()
        root = builder.build_from_statement_file(test_file)

        assert root is not None
        assert root.metadata.get('statement_type') == 'INCOME_STATEMENT'

    def test_build_from_nonexistent_file(self):
        """Building from non-existent file returns None."""
        builder = HierarchyBuilder()
        root = builder.build_from_statement_file(Path('/nonexistent/file.json'))

        assert root is None
        assert builder.last_error is not None

    def test_build_from_invalid_json(self, tmp_path):
        """Building from invalid JSON returns None."""
        test_file = tmp_path / 'invalid.json'
        with open(test_file, 'w') as f:
            f.write('not valid json {{{')

        builder = HierarchyBuilder()
        root = builder.build_from_statement_file(test_file)

        assert root is None
        assert 'JSON decode error' in builder.last_error


class TestBuildFromFilingFolder:
    """Test building from filing folder structure."""

    @pytest.fixture
    def filing_folder(self, tmp_path):
        """Create a mock filing folder structure."""
        import json

        # Create folder structure
        json_folder = tmp_path / 'json'
        json_folder.mkdir()
        (json_folder / 'core_statements').mkdir()
        (json_folder / 'details').mkdir()
        (json_folder / 'other').mkdir()

        # Create test statement files
        balance_sheet = {
            'statement_type': 'BALANCE_SHEET',
            'hierarchy': {
                'roots': ['assets'],
                'nodes': {'assets': {'label': 'Total Assets', 'value': 1000000}},
                'arcs': [],
            },
        }
        income_stmt = {
            'statement_type': 'INCOME_STATEMENT',
            'hierarchy': {
                'roots': ['revenue'],
                'nodes': {'revenue': {'label': 'Revenue', 'value': 500000}},
                'arcs': [],
            },
        }
        detail_stmt = {
            'statement_type': 'DETAIL',
            'hierarchy': {
                'roots': ['detail'],
                'nodes': {'detail': {'label': 'Detail Item'}},
                'arcs': [],
            },
        }

        with open(json_folder / 'core_statements' / 'balance_sheet.json', 'w') as f:
            json.dump(balance_sheet, f)
        with open(json_folder / 'core_statements' / 'income_statement.json', 'w') as f:
            json.dump(income_stmt, f)
        with open(json_folder / 'details' / 'revenue_detail.json', 'w') as f:
            json.dump(detail_stmt, f)

        return tmp_path

    def test_build_from_filing_folder(self, filing_folder):
        """Can build all hierarchies from filing folder."""
        builder = HierarchyBuilder()
        hierarchies = builder.build_from_filing_folder(filing_folder)

        assert len(hierarchies) >= 2  # At least core statements
        assert 'balance_sheet' in hierarchies
        assert 'income_statement' in hierarchies

    def test_discovered_types_from_folder(self, filing_folder):
        """All statement types are discovered from folder."""
        builder = HierarchyBuilder()
        builder.build_from_filing_folder(filing_folder)

        assert 'BALANCE_SHEET' in builder.discovered_types
        assert 'INCOME_STATEMENT' in builder.discovered_types

    def test_exclude_details(self, filing_folder):
        """Can exclude details folder."""
        builder = HierarchyBuilder()
        hierarchies = builder.build_from_filing_folder(
            filing_folder,
            include_details=False
        )

        # Should not include the detail statement
        assert 'revenue_detail' not in hierarchies

    def test_nonexistent_folder(self):
        """Non-existent folder returns empty dict."""
        builder = HierarchyBuilder()
        hierarchies = builder.build_from_filing_folder(Path('/nonexistent'))

        assert hierarchies == {}


class TestDiscoveredTypes:
    """Test discovered_types property."""

    def test_discovered_types_initially_empty(self):
        """discovered_types is initially empty."""
        builder = HierarchyBuilder()
        assert len(builder.discovered_types) == 0

    def test_discovered_types_accumulates(self):
        """discovered_types accumulates across builds."""
        builder = HierarchyBuilder()

        data1 = {
            'statement_type': 'TYPE_A',
            'hierarchy': {'roots': [], 'nodes': {}, 'arcs': []},
        }
        data2 = {
            'statement_type': 'TYPE_B',
            'hierarchy': {'roots': [], 'nodes': {}, 'arcs': []},
        }

        builder.build_from_statement_data(data1, 'stmt1')
        builder.build_from_statement_data(data2, 'stmt2')

        assert 'TYPE_A' in builder.discovered_types
        assert 'TYPE_B' in builder.discovered_types

    def test_reset_clears_discovered_types(self):
        """reset_stats clears discovered_types."""
        builder = HierarchyBuilder()
        # Build something to populate discovered_types
        data = {
            'statement_type': 'TEST_TYPE',
            'hierarchy': {'roots': [], 'nodes': {}, 'arcs': []},
        }
        builder.build_from_statement_data(data, 'test')
        assert 'TEST_TYPE' in builder.discovered_types

        builder.reset_stats()
        assert len(builder.discovered_types) == 0
