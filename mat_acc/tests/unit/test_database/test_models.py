# Path: mat_acc/tests/unit/test_database/test_models.py
"""
Unit tests for database models.

Tests ProcessedFiling, StatementHierarchy, and HierarchyNode models.
"""

import pytest
from datetime import date
from unittest.mock import MagicMock

from database.models.base import (
    Base,
    initialize_engine,
    create_all_tables,
    session_scope,
    reset_engine,
)
from database.models.processed_filings import ProcessedFiling
from database.models.statement_hierarchies import StatementHierarchy
from database.models.hierarchy_nodes import HierarchyNode


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


class TestProcessedFiling:
    """Tests for ProcessedFiling model."""

    def test_create_filing(self, db_session):
        """Test creating a basic filing record."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        assert filing.filing_id is not None
        assert filing.market == 'sec'
        assert filing.company_name == 'Apple Inc'
        assert filing.form_type == '10-K'
        assert filing.filing_date == date(2024, 9, 30)

    def test_filing_key_property(self, db_session):
        """Test filing_key composite key generation."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        # filing_key replaces spaces and dashes with underscores for filesystem safety
        assert filing.filing_key == 'sec/Apple_Inc/10_K/2024-09-30'

    def test_filing_with_optional_fields(self, db_session):
        """Test filing with all optional fields."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Microsoft Corp',
            form_type='10-Q',
            filing_date=date(2024, 6, 30),
            source_path='/mnt/data/filings/msft',
            accession_number='0001193125-24-123456',
            cik='0000789019',
        )
        db_session.add(filing)
        db_session.flush()

        assert filing.source_path == '/mnt/data/filings/msft'
        assert filing.accession_number == '0001193125-24-123456'
        assert filing.cik == '0000789019'

    def test_filing_to_dict(self, db_session):
        """Test filing serialization to dictionary."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Tesla Inc',
            form_type='10-K',
            filing_date=date(2024, 12, 31),
        )
        db_session.add(filing)
        db_session.flush()

        d = filing.to_dict()

        assert d['market'] == 'sec'
        assert d['company_name'] == 'Tesla Inc'
        assert d['form_type'] == '10-K'
        assert d['filing_date'] == '2024-12-31'
        assert 'filing_id' in d

    def test_filing_repr(self, db_session):
        """Test filing string representation."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

        repr_str = repr(filing)

        assert 'ProcessedFiling' in repr_str
        assert 'Apple Inc' in repr_str
        assert '10-K' in repr_str


class TestStatementHierarchy:
    """Tests for StatementHierarchy model."""

    def test_create_hierarchy(self, db_session):
        """Test creating a statement hierarchy."""
        # First create a filing
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        # Create hierarchy
        hierarchy = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='Balance Sheet',
            statement_type='BALANCE_SHEET',
            statement_code='BS',
            role_uri='http://apple.com/role/BalanceSheet',
            node_count=50,
            max_depth=5,
        )
        db_session.add(hierarchy)
        db_session.flush()

        assert hierarchy.hierarchy_id is not None
        assert hierarchy.filing_id == filing.filing_id
        assert hierarchy.statement_name == 'Balance Sheet'
        assert hierarchy.statement_type == 'BALANCE_SHEET'
        assert hierarchy.statement_code == 'BS'

    def test_hierarchy_statistics(self, db_session):
        """Test hierarchy statistics fields."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        hierarchy = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='Income Statement',
            statement_type='INCOME_STATEMENT',
            statement_code='IS',
            node_count=75,
            max_depth=6,
            root_count=3,
            line_item_count=45,
            abstract_count=20,
            total_count=10,
        )
        db_session.add(hierarchy)
        db_session.flush()

        assert hierarchy.node_count == 75
        assert hierarchy.max_depth == 6
        assert hierarchy.root_count == 3
        assert hierarchy.line_item_count == 45
        assert hierarchy.abstract_count == 20
        assert hierarchy.total_count == 10

    def test_hierarchy_to_dict(self, db_session):
        """Test hierarchy serialization."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        hierarchy = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='Cash Flow',
            statement_type='CASH_FLOW',
            statement_code='CF',
            node_count=40,
            max_depth=4,
        )
        db_session.add(hierarchy)
        db_session.flush()

        d = hierarchy.to_dict()

        assert d['statement_name'] == 'Cash Flow'
        assert d['statement_type'] == 'CASH_FLOW'
        assert d['statement_code'] == 'CF'
        assert d['node_count'] == 40


class TestHierarchyNode:
    """Tests for HierarchyNode model."""

    def test_create_node(self, db_session):
        """Test creating a hierarchy node."""
        # Setup filing and hierarchy
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        hierarchy = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='Balance Sheet',
            statement_type='BALANCE_SHEET',
            statement_code='BS',
            node_count=1,
            max_depth=1,
        )
        db_session.add(hierarchy)
        db_session.flush()

        # Create node
        node = HierarchyNode(
            hierarchy_id=hierarchy.hierarchy_id,
            mat_acc_id='BS-001-001-c1',
            mat_acc_position='001-001',
            level=1,
            sibling=1,
            concept='us-gaap:Assets',
            label='Assets',
            node_type='line_item',
        )
        db_session.add(node)
        db_session.flush()

        assert node.node_id is not None
        assert node.mat_acc_id == 'BS-001-001-c1'
        assert node.mat_acc_position == '001-001'
        assert node.level == 1
        assert node.sibling == 1
        assert node.concept == 'us-gaap:Assets'
        assert node.label == 'Assets'
        assert node.node_type == 'line_item'

    def test_node_with_parent(self, db_session):
        """Test node with parent reference."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        hierarchy = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='Balance Sheet',
            statement_type='BALANCE_SHEET',
            statement_code='BS',
            node_count=2,
            max_depth=2,
        )
        db_session.add(hierarchy)
        db_session.flush()

        # Parent node
        parent_node = HierarchyNode(
            hierarchy_id=hierarchy.hierarchy_id,
            mat_acc_id='BS-001-000-c0',
            mat_acc_position='001-000',
            level=1,
            sibling=0,
            concept='us-gaap:AssetsAbstract',
            label='Assets [Abstract]',
            node_type='abstract',
        )
        db_session.add(parent_node)
        db_session.flush()

        # Child node
        child_node = HierarchyNode(
            hierarchy_id=hierarchy.hierarchy_id,
            mat_acc_id='BS-002-001-c1',
            mat_acc_position='002-001',
            level=2,
            sibling=1,
            parent_mat_acc_id='BS-001-000-c0',
            concept='us-gaap:CashAndCashEquivalentsAtCarryingValue',
            label='Cash and Cash Equivalents',
            node_type='line_item',
            value='12500000000',
        )
        db_session.add(child_node)
        db_session.flush()

        assert child_node.parent_mat_acc_id == 'BS-001-000-c0'
        assert child_node.value == '12500000000'

    def test_node_to_dict(self, db_session):
        """Test node serialization."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        hierarchy = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='Balance Sheet',
            statement_type='BALANCE_SHEET',
            statement_code='BS',
            node_count=1,
            max_depth=1,
        )
        db_session.add(hierarchy)
        db_session.flush()

        node = HierarchyNode(
            hierarchy_id=hierarchy.hierarchy_id,
            mat_acc_id='BS-001-001-c1',
            mat_acc_position='001-001',
            level=1,
            sibling=1,
            concept='us-gaap:Assets',
            label='Assets',
            node_type='line_item',
            value='100000000',
            unit='USD',
            context_ref='c1',
        )
        db_session.add(node)
        db_session.flush()

        d = node.to_dict()

        assert d['mat_acc_id'] == 'BS-001-001-c1'
        assert d['concept'] == 'us-gaap:Assets'
        assert d['label'] == 'Assets'
        assert d['value'] == '100000000'
        assert d['unit'] == 'USD'

    def test_node_from_hierarchy_node(self, db_session):
        """Test creating database node from process HierarchyNode."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        hierarchy = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='Balance Sheet',
            statement_type='BALANCE_SHEET',
            statement_code='BS',
            node_count=1,
            max_depth=1,
        )
        db_session.add(hierarchy)
        db_session.flush()

        # Create mock process HierarchyNode
        from process.hierarchy.node import HierarchyNode as ProcessNode
        from process.hierarchy.node import NodeType

        process_node = ProcessNode(
            concept='us-gaap:CashAndCashEquivalentsAtCarryingValue',
            label='Cash and Cash Equivalents',
            node_type=NodeType.LINE_ITEM,
            value='12500000000',
        )
        process_node.depth = 2
        process_node.sibling_index = 1
        process_node.unit = 'USD'  # Set as attribute
        process_node.metadata = {
            'mat_acc_id': 'BS-002-001-c1',
            'mat_acc_position': '002-001',
            'context_ref': 'c1',
            'decimals': '-6',
        }

        # Convert to database node
        db_node = HierarchyNode.from_hierarchy_node(
            hierarchy_id=hierarchy.hierarchy_id,
            node=process_node,
            parent_mat_acc_id='BS-001-000-c0',
        )

        assert db_node.mat_acc_id == 'BS-002-001-c1'
        assert db_node.mat_acc_position == '002-001'
        assert db_node.level == 2
        assert db_node.sibling == 1
        assert db_node.parent_mat_acc_id == 'BS-001-000-c0'
        assert db_node.concept == 'us-gaap:CashAndCashEquivalentsAtCarryingValue'
        assert db_node.label == 'Cash and Cash Equivalents'
        assert db_node.node_type == 'line_item'
        assert db_node.value == 12500000000.0  # Stored as float
        assert db_node.unit == 'USD'


class TestModelRelationships:
    """Tests for model relationships."""

    def test_filing_to_hierarchies_relationship(self, db_session):
        """Test that filing can access its hierarchies."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        # Add multiple hierarchies
        hierarchy1 = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='Balance Sheet',
            statement_type='BALANCE_SHEET',
            statement_code='BS',
            node_count=50,
            max_depth=5,
        )
        hierarchy2 = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='Income Statement',
            statement_type='INCOME_STATEMENT',
            statement_code='IS',
            node_count=75,
            max_depth=6,
        )
        db_session.add_all([hierarchy1, hierarchy2])
        db_session.flush()

        # Query filing and check relationship
        queried = db_session.query(ProcessedFiling).filter_by(
            filing_id=filing.filing_id
        ).first()

        assert len(queried.hierarchies) == 2
        statement_names = {h.statement_name for h in queried.hierarchies}
        assert statement_names == {'Balance Sheet', 'Income Statement'}

    def test_hierarchy_to_nodes_relationship(self, db_session):
        """Test that hierarchy can access its nodes."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        hierarchy = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='Balance Sheet',
            statement_type='BALANCE_SHEET',
            statement_code='BS',
            node_count=3,
            max_depth=2,
        )
        db_session.add(hierarchy)
        db_session.flush()

        # Add nodes
        nodes = [
            HierarchyNode(
                hierarchy_id=hierarchy.hierarchy_id,
                mat_acc_id='BS-001-000-c0',
                mat_acc_position='001-000',
                level=1,
                sibling=0,
                concept='us-gaap:AssetsAbstract',
                label='Assets [Abstract]',
                node_type='abstract',
            ),
            HierarchyNode(
                hierarchy_id=hierarchy.hierarchy_id,
                mat_acc_id='BS-002-001-c1',
                mat_acc_position='002-001',
                level=2,
                sibling=1,
                concept='us-gaap:Cash',
                label='Cash',
                node_type='line_item',
            ),
            HierarchyNode(
                hierarchy_id=hierarchy.hierarchy_id,
                mat_acc_id='BS-002-002-c1',
                mat_acc_position='002-002',
                level=2,
                sibling=2,
                concept='us-gaap:Receivables',
                label='Receivables',
                node_type='line_item',
            ),
        ]
        db_session.add_all(nodes)
        db_session.flush()

        # Query hierarchy and check relationship
        queried = db_session.query(StatementHierarchy).filter_by(
            hierarchy_id=hierarchy.hierarchy_id
        ).first()

        assert len(queried.nodes) == 3
        mat_acc_ids = {n.mat_acc_id for n in queried.nodes}
        assert 'BS-001-000-c0' in mat_acc_ids
        assert 'BS-002-001-c1' in mat_acc_ids

    def test_cascade_delete(self, db_session):
        """Test that deleting filing cascades to hierarchies and nodes."""
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )
        db_session.add(filing)
        db_session.flush()

        hierarchy = StatementHierarchy(
            filing_id=filing.filing_id,
            statement_name='Balance Sheet',
            statement_type='BALANCE_SHEET',
            statement_code='BS',
            node_count=1,
            max_depth=1,
        )
        db_session.add(hierarchy)
        db_session.flush()

        node = HierarchyNode(
            hierarchy_id=hierarchy.hierarchy_id,
            mat_acc_id='BS-001-001-c1',
            mat_acc_position='001-001',
            level=1,
            sibling=1,
            concept='us-gaap:Assets',
            label='Assets',
            node_type='line_item',
        )
        db_session.add(node)
        db_session.flush()

        # Store IDs
        hierarchy_id = hierarchy.hierarchy_id
        node_id = node.node_id

        # Delete filing
        db_session.delete(filing)
        db_session.flush()

        # Verify cascade
        assert db_session.query(StatementHierarchy).filter_by(
            hierarchy_id=hierarchy_id
        ).first() is None
        assert db_session.query(HierarchyNode).filter_by(
            node_id=node_id
        ).first() is None
