# Path: mat_acc/tests/unit/test_database/test_operations.py
"""
Unit tests for database operations.

Tests FilingOperations and HierarchyOperations classes.
"""

import pytest
from datetime import date

from database.models.base import (
    initialize_engine,
    create_all_tables,
    session_scope,
    reset_engine,
)
from database.models.processed_filings import ProcessedFiling
from database.models.statement_hierarchies import StatementHierarchy
from database.models.hierarchy_nodes import HierarchyNode
from database.operations.filing_ops import FilingOperations
from database.operations.hierarchy_ops import HierarchyOperations


@pytest.fixture(autouse=True)
def reset_db():
    """Reset database before and after each test."""
    reset_engine()
    yield
    reset_engine()


@pytest.fixture
def db_session():
    """Create in-memory database session for testing."""
    initialize_engine(':memory:')
    create_all_tables()
    with session_scope() as session:
        yield session


class TestFilingOperations:
    """Tests for FilingOperations class."""

    def test_create_filing(self, db_session):
        """Test creating a filing through operations."""
        filing = FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

        assert filing.filing_id is not None
        assert filing.market == 'sec'
        assert filing.company_name == 'Apple Inc'

    def test_create_filing_with_optional_fields(self, db_session):
        """Test creating filing with all fields."""
        filing = FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Microsoft Corp',
            form_type='10-Q',
            filing_date=date(2024, 6, 30),
            source_path='/mnt/data/filings/msft',
            accession_number='0001193125-24-123456',
            cik='0000789019',
        )

        assert filing.source_path == '/mnt/data/filings/msft'
        assert filing.accession_number == '0001193125-24-123456'
        assert filing.cik == '0000789019'

    def test_find_by_id(self, db_session):
        """Test finding filing by ID."""
        created = FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Tesla Inc',
            form_type='10-K',
            filing_date=date(2024, 12, 31),
        )

        found = FilingOperations.find_by_id(db_session, created.filing_id)

        assert found is not None
        assert found.company_name == 'Tesla Inc'

    def test_find_by_id_not_found(self, db_session):
        """Test finding non-existent filing."""
        found = FilingOperations.find_by_id(db_session, 'nonexistent-uuid')

        assert found is None

    def test_find_by_key(self, db_session):
        """Test finding filing by unique key combination."""
        FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

        found = FilingOperations.find_by_key(
            db_session,
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

        assert found is not None
        assert found.company_name == 'Apple Inc'

    def test_find_by_key_not_found(self, db_session):
        """Test finding non-existent filing by key."""
        found = FilingOperations.find_by_key(
            db_session,
            market='sec',
            company_name='NonExistent Corp',
            form_type='10-K',
            filing_date=date(2024, 1, 1),
        )

        assert found is None

    def test_get_or_create_creates_new(self, db_session):
        """Test get_or_create when filing doesn't exist."""
        filing, created = FilingOperations.get_or_create(
            db_session,
            market='sec',
            company_name='New Company',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

        assert created is True
        assert filing.company_name == 'New Company'

    def test_get_or_create_returns_existing(self, db_session):
        """Test get_or_create when filing exists."""
        # Create first
        FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Existing Company',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

        # Get or create
        filing, created = FilingOperations.get_or_create(
            db_session,
            market='sec',
            company_name='Existing Company',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

        assert created is False
        assert filing.company_name == 'Existing Company'

    def test_find_by_company(self, db_session):
        """Test finding filings by company."""
        # Create multiple filings
        FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Apple Inc',
            form_type='10-Q',
            filing_date=date(2024, 6, 30),
        )
        FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Microsoft Corp',
            form_type='10-K',
            filing_date=date(2024, 6, 30),
        )

        filings = FilingOperations.find_by_company(db_session, 'Apple Inc')

        assert len(filings) == 2
        assert all(f.company_name == 'Apple Inc' for f in filings)

    def test_find_by_market(self, db_session):
        """Test finding filings by market."""
        FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        FilingOperations.create_filing(
            db_session,
            market='frc',
            company_name='British Company',
            form_type='Annual Report',
            filing_date=date(2024, 3, 31),
        )

        sec_filings = FilingOperations.find_by_market(db_session, 'sec')
        frc_filings = FilingOperations.find_by_market(db_session, 'frc')

        assert len(sec_filings) == 1
        assert len(frc_filings) == 1
        assert sec_filings[0].company_name == 'Apple Inc'

    def test_find_by_form_type(self, db_session):
        """Test finding filings by form type."""
        FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Microsoft Corp',
            form_type='10-K',
            filing_date=date(2024, 6, 30),
        )
        FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Apple Inc',
            form_type='10-Q',
            filing_date=date(2024, 6, 30),
        )

        tenk_filings = FilingOperations.find_by_form_type(db_session, '10-K')

        assert len(tenk_filings) == 2

    def test_update_stats(self, db_session):
        """Test updating filing statistics."""
        filing = FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

        FilingOperations.update_stats(
            db_session,
            filing,
            statement_count=4,
            total_node_count=150,
        )

        assert filing.statement_count == 4
        assert filing.total_node_count == 150

    def test_delete_filing(self, db_session):
        """Test deleting a filing."""
        filing = FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='To Delete',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        filing_id = filing.filing_id

        FilingOperations.delete_filing(db_session, filing)

        assert FilingOperations.find_by_id(db_session, filing_id) is None

    def test_count(self, db_session):
        """Test counting filings."""
        assert FilingOperations.count(db_session) == 0

        FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Microsoft Corp',
            form_type='10-K',
            filing_date=date(2024, 6, 30),
        )

        assert FilingOperations.count(db_session) == 2


class TestHierarchyOperations:
    """Tests for HierarchyOperations class."""

    @pytest.fixture
    def filing(self, db_session):
        """Create a test filing."""
        return FilingOperations.create_filing(
            db_session,
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

    @pytest.fixture
    def mock_hierarchy_root(self):
        """Create a mock HierarchyNode from process.hierarchy."""
        from process.hierarchy.node import HierarchyNode as ProcessNode
        from process.hierarchy.node import NodeType

        # Create root node
        root = ProcessNode(
            concept='statement:root',
            label='Balance Sheet',
            node_type=NodeType.ABSTRACT,
        )
        root.depth = 0
        root.sibling_index = 0
        root.metadata = {
            'mat_acc_id': 'BS-000-000-root',
            'mat_acc_position': '000-000',
            'statement_type': 'BALANCE_SHEET',
            'role_uri': 'http://example.com/role/BalanceSheet',
            'role_definition': 'Balance Sheet',
        }

        # Add child node
        child1 = ProcessNode(
            concept='us-gaap:Assets',
            label='Assets',
            node_type=NodeType.LINE_ITEM,
            value='100000000',
        )
        child1.depth = 1
        child1.sibling_index = 1
        child1.metadata = {
            'mat_acc_id': 'BS-001-001-c1',
            'mat_acc_position': '001-001',
            'context_ref': 'c1',
            'unit': 'USD',
        }
        root.add_child(child1)

        # Add grandchild node
        grandchild = ProcessNode(
            concept='us-gaap:CashAndCashEquivalents',
            label='Cash and Cash Equivalents',
            node_type=NodeType.LINE_ITEM,
            value='12500000000',
        )
        grandchild.depth = 2
        grandchild.sibling_index = 1
        grandchild.metadata = {
            'mat_acc_id': 'BS-002-001-c1',
            'mat_acc_position': '002-001',
            'context_ref': 'c1',
            'unit': 'USD',
        }
        child1.add_child(grandchild)

        return root

    def test_store_hierarchy(self, db_session, filing, mock_hierarchy_root):
        """Test storing a complete hierarchy."""
        hierarchy = HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )

        assert hierarchy.hierarchy_id is not None
        assert hierarchy.statement_name == 'Balance Sheet'
        assert hierarchy.statement_type == 'BALANCE_SHEET'
        assert hierarchy.node_count == 3  # root + child + grandchild

    def test_store_all_hierarchies(self, db_session, filing, mock_hierarchy_root):
        """Test storing multiple hierarchies."""
        # Create a second mock hierarchy
        from process.hierarchy.node import HierarchyNode as ProcessNode
        from process.hierarchy.node import NodeType

        income_root = ProcessNode(
            concept='statement:root',
            label='Income Statement',
            node_type=NodeType.ABSTRACT,
        )
        income_root.depth = 0
        income_root.sibling_index = 0
        income_root.metadata = {
            'mat_acc_id': 'IS-000-000-root',
            'mat_acc_position': '000-000',
            'statement_type': 'INCOME_STATEMENT',
            'role_uri': 'http://example.com/role/IncomeStatement',
        }

        child = ProcessNode(
            concept='us-gaap:Revenue',
            label='Revenue',
            node_type=NodeType.LINE_ITEM,
            value='50000000000',
        )
        child.depth = 1
        child.sibling_index = 1
        child.metadata = {
            'mat_acc_id': 'IS-001-001-c1',
            'mat_acc_position': '001-001',
        }
        income_root.add_child(child)

        hierarchies = {
            'Balance Sheet': mock_hierarchy_root,
            'Income Statement': income_root,
        }

        results = HierarchyOperations.store_all_hierarchies(
            db_session,
            filing_id=filing.filing_id,
            hierarchies=hierarchies,
        )

        assert len(results) == 2
        assert filing.statement_count == 2
        assert filing.total_node_count == 5  # 3 + 2

    def test_find_hierarchy_by_id(self, db_session, filing, mock_hierarchy_root):
        """Test finding hierarchy by ID."""
        created = HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )

        found = HierarchyOperations.find_hierarchy_by_id(
            db_session, created.hierarchy_id
        )

        assert found is not None
        assert found.statement_name == 'Balance Sheet'

    def test_find_hierarchies_by_filing(self, db_session, filing, mock_hierarchy_root):
        """Test finding all hierarchies for a filing."""
        HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )

        hierarchies = HierarchyOperations.find_hierarchies_by_filing(
            db_session, filing.filing_id
        )

        assert len(hierarchies) == 1
        assert hierarchies[0].statement_name == 'Balance Sheet'

    def test_find_hierarchies_by_type(self, db_session, filing, mock_hierarchy_root):
        """Test finding hierarchies by statement type."""
        HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )

        hierarchies = HierarchyOperations.find_hierarchies_by_type(
            db_session, 'BALANCE_SHEET'
        )

        assert len(hierarchies) == 1
        assert hierarchies[0].statement_type == 'BALANCE_SHEET'

    def test_find_node_by_mat_acc_id(self, db_session, filing, mock_hierarchy_root):
        """Test finding node by mat_acc_id."""
        hierarchy = HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )

        node = HierarchyOperations.find_node_by_mat_acc_id(
            db_session,
            hierarchy_id=hierarchy.hierarchy_id,
            mat_acc_id='BS-001-001-c1',
        )

        assert node is not None
        assert node.concept == 'us-gaap:Assets'

    def test_find_nodes_by_concept(self, db_session, filing, mock_hierarchy_root):
        """Test finding nodes by XBRL concept."""
        HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )

        nodes = HierarchyOperations.find_nodes_by_concept(
            db_session, 'us-gaap:Assets'
        )

        assert len(nodes) == 1
        assert nodes[0].label == 'Assets'

    def test_find_nodes_at_level(self, db_session, filing, mock_hierarchy_root):
        """Test finding nodes at specific level."""
        hierarchy = HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )

        # Level 1 contains Assets node
        level_1_nodes = HierarchyOperations.find_nodes_at_level(
            db_session,
            hierarchy_id=hierarchy.hierarchy_id,
            level=1,
        )

        # Verify at least one node at level 1 including Assets
        assert len(level_1_nodes) >= 1
        concepts = {n.concept for n in level_1_nodes}
        assert 'us-gaap:Assets' in concepts

    def test_find_children(self, db_session, filing, mock_hierarchy_root):
        """Test finding children of a node."""
        hierarchy = HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )

        children = HierarchyOperations.find_children(
            db_session,
            hierarchy_id=hierarchy.hierarchy_id,
            parent_mat_acc_id='BS-001-001-c1',
        )

        assert len(children) == 1
        assert children[0].concept == 'us-gaap:CashAndCashEquivalents'

    def test_get_hierarchy_with_nodes(self, db_session, filing, mock_hierarchy_root):
        """Test getting hierarchy with all nodes as dict."""
        hierarchy = HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )

        result = HierarchyOperations.get_hierarchy_with_nodes(
            db_session, hierarchy.hierarchy_id
        )

        # Result has hierarchy data at root level with 'nodes' key
        assert result is not None
        assert 'hierarchy_id' in result
        assert 'statement_name' in result
        assert 'nodes' in result
        assert len(result['nodes']) == 3

    def test_delete_hierarchy(self, db_session, filing, mock_hierarchy_root):
        """Test deleting a hierarchy."""
        hierarchy = HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )
        hierarchy_id = hierarchy.hierarchy_id

        HierarchyOperations.delete_hierarchy(db_session, hierarchy)

        assert HierarchyOperations.find_hierarchy_by_id(
            db_session, hierarchy_id
        ) is None

    def test_count_hierarchies(self, db_session, filing, mock_hierarchy_root):
        """Test counting hierarchies."""
        assert HierarchyOperations.count_hierarchies(db_session) == 0

        HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )

        assert HierarchyOperations.count_hierarchies(db_session) == 1

    def test_count_nodes(self, db_session, filing, mock_hierarchy_root):
        """Test counting nodes."""
        assert HierarchyOperations.count_nodes(db_session) == 0

        HierarchyOperations.store_hierarchy(
            db_session,
            filing_id=filing.filing_id,
            name='Balance Sheet',
            root=mock_hierarchy_root,
        )

        assert HierarchyOperations.count_nodes(db_session) == 3
