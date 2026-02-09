# Path: mat_acc/tests/integration/test_database_integration.py
"""
Integration tests for database with hierarchy builder.

Tests that verify:
1. PostgreSQL database connection works
2. Hierarchies are built and stored correctly
3. Data can be queried back from the database

These tests use real test data from fixtures.
"""

import os
import pytest
from datetime import date
from pathlib import Path

from database.models.base import reset_engine, get_connection_info
from database.integration.hierarchy_storage import HierarchyStorage


# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent.parent / 'fixtures' / 'mapped_statements'


@pytest.fixture(autouse=True)
def reset_db_state():
    """Reset database state before and after each test."""
    reset_engine()
    yield
    reset_engine()


@pytest.fixture
def test_filing_folder():
    """
    Get path to test filing folder with mapped statements.

    Uses the same fixtures as the hierarchy tests.
    """
    # Look for test mapped statement files
    if FIXTURES_DIR.exists():
        # Use the fixture folder if available
        return FIXTURES_DIR
    return None


class TestSQLiteForTesting:
    """Test SQLite in-memory database for unit testing."""

    def test_sqlite_in_memory_with_use_sqlite_flag(self):
        """Test that use_sqlite=True creates in-memory SQLite."""
        storage = HierarchyStorage(use_sqlite=True)
        storage.initialize()

        info = get_connection_info()
        assert info['type'] == 'sqlite'
        assert info['status'] == 'connected'

    def test_sqlite_in_memory_with_memory_url(self):
        """Test that ':memory:' URL creates SQLite."""
        storage = HierarchyStorage(db_url=':memory:')
        storage.initialize()

        info = get_connection_info()
        assert info['type'] == 'sqlite'


class TestPostgreSQLConnection:
    """Test PostgreSQL database connection."""

    def test_postgresql_connection(self):
        """Test that default connection uses PostgreSQL."""
        storage = HierarchyStorage()
        storage.initialize()

        info = get_connection_info()
        assert info['status'] == 'connected'
        assert info['type'] == 'postgresql'
        assert 'postgresql://' in info['url']

    def test_can_list_filings_from_postgresql(self):
        """Test that we can query PostgreSQL."""
        storage = HierarchyStorage()
        storage.initialize()

        # Should be able to list filings (even if empty)
        filings = storage.list_processed_filings()
        assert isinstance(filings, list)


class TestHierarchyStorageIntegration:
    """Test hierarchy storage with real data."""

    def test_process_filing_folder_creates_records(self, test_filing_folder):
        """Test that processing a filing folder creates database records."""
        if test_filing_folder is None:
            pytest.skip("Test fixtures not available")

        # Use SQLite for this test to avoid polluting PostgreSQL
        storage = HierarchyStorage(use_sqlite=True)

        result = storage.process_filing_folder(
            folder_path=test_filing_folder,
            market='sec',
            company_name='Test Company',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

        assert result['filing_id'] is not None
        assert result['statement_count'] > 0 or len(result['errors']) == 0

    def test_can_query_stored_hierarchies(self, test_filing_folder):
        """Test that stored hierarchies can be queried back."""
        if test_filing_folder is None:
            pytest.skip("Test fixtures not available")

        storage = HierarchyStorage(use_sqlite=True)

        # Process filing
        result = storage.process_filing_folder(
            folder_path=test_filing_folder,
            market='sec',
            company_name='Test Company',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

        if result['statement_count'] == 0:
            pytest.skip("No statements found in test folder")

        # Query back
        filing_id = result['filing_id']
        summary = storage.get_filing_summary(filing_id)

        assert summary is not None
        assert summary['filing']['company_name'] == 'Test Company'
        assert len(summary['hierarchies']) == result['statement_count']

    def test_list_processed_filings(self, test_filing_folder):
        """Test listing processed filings."""
        if test_filing_folder is None:
            pytest.skip("Test fixtures not available")

        storage = HierarchyStorage(use_sqlite=True)

        # Process filing
        storage.process_filing_folder(
            folder_path=test_filing_folder,
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
        )

        # List filings
        filings = storage.list_processed_filings(market='sec')

        assert len(filings) >= 1
        assert any(f['company_name'] == 'Apple Inc' for f in filings)


class TestRealFilingProcessing:
    """
    Test with real filing data.

    These tests use actual mapped statements from the verification directory.
    """

    @pytest.fixture
    def real_filing_path(self):
        """Get path to a real mapped filing if available."""
        # Check verification reports directory
        verification_dir = Path('/mnt/map_pro/verification/reports')
        if not verification_dir.exists():
            return None

        # Find first available filing folder
        for market_dir in verification_dir.iterdir():
            if market_dir.is_dir():
                for company_dir in market_dir.iterdir():
                    if company_dir.is_dir():
                        for form_dir in company_dir.iterdir():
                            if form_dir.is_dir():
                                for date_dir in form_dir.iterdir():
                                    if date_dir.is_dir():
                                        # Check for statement files
                                        json_files = list(date_dir.glob('*.json'))
                                        if json_files:
                                            return date_dir
        return None

    def test_process_real_filing_to_postgresql(self, real_filing_path):
        """Test processing an actual filing to PostgreSQL."""
        if real_filing_path is None:
            pytest.skip("No real filings available for testing")

        # Parse filing info from path
        # Expected: /mnt/map_pro/verification/reports/{market}/{company}/{form}/{date}
        parts = real_filing_path.parts
        try:
            date_str = parts[-1]
            form_type = parts[-2]
            company_name = parts[-3]
            market = parts[-4]
            filing_date = date.fromisoformat(date_str)
        except (IndexError, ValueError):
            pytest.skip("Could not parse filing info from path")

        # Use PostgreSQL (default)
        storage = HierarchyStorage()
        result = storage.process_filing_folder(
            folder_path=real_filing_path,
            market=market,
            company_name=company_name,
            form_type=form_type,
            filing_date=filing_date,
        )

        # Verify results
        if result['errors']:
            print(f"Errors: {result['errors']}")

        assert result['filing_id'] is not None
        print(f"Processed: {result['statement_count']} statements, "
              f"{result['total_nodes']} nodes to PostgreSQL")
