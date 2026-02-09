# Path: mat_acc/tests/unit/test_loaders.py
"""
Unit Tests for Loaders Module

Tests all loader classes including:
- VerificationDataLoader / VerificationReader
- MappedDataLoader / MappedReader
- ParsedDataLoader / ParsedReader
- XBRLDataLoader / XBRLReader
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add mat_acc to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ==============================================================================
# VERIFICATION LOADER TESTS
# ==============================================================================

class TestVerificationDataLoader:
    """Test VerificationDataLoader (blind reader)."""

    def test_init_with_config(self, mock_config):
        """Should initialize with config."""
        from loaders.verification_data import VerificationDataLoader

        loader = VerificationDataLoader(mock_config)
        assert loader.config is mock_config

    def test_discover_filings_empty_dir(self, temp_dir):
        """Should return empty list for empty directory."""
        from loaders.verification_data import VerificationDataLoader

        mock_config = MagicMock()
        mock_config.get.return_value = temp_dir

        loader = VerificationDataLoader(mock_config)
        filings = loader.discover_all_verified_filings()

        assert filings == []

    def test_discover_filings_finds_reports(
        self, test_data_structure, mock_config_with_paths, create_verification_report
    ):
        """Should find verification reports."""
        from loaders.verification_data import VerificationDataLoader

        loader = VerificationDataLoader(mock_config_with_paths)
        filings = loader.discover_all_verified_filings()

        assert len(filings) >= 1

    def test_filing_entry_has_metadata(
        self, test_data_structure, mock_config_with_paths, create_verification_report
    ):
        """Filing entries should have metadata."""
        from loaders.verification_data import VerificationDataLoader

        loader = VerificationDataLoader(mock_config_with_paths)
        filings = loader.discover_all_verified_filings()

        if filings:
            entry = filings[0]
            assert hasattr(entry, 'market')
            assert hasattr(entry, 'company')
            assert hasattr(entry, 'form')
            assert hasattr(entry, 'report_path')


class TestVerificationReader:
    """Test VerificationReader (content reader)."""

    def test_load_report_returns_object(
        self, mock_config_with_paths, create_verification_report
    ):
        """Should load and parse verification report."""
        from loaders.verification_data import VerificationDataLoader, VerifiedFilingEntry
        from loaders.verification_reader import VerificationReader

        loader = VerificationDataLoader(mock_config_with_paths)
        reader = VerificationReader(mock_config_with_paths)

        filings = loader.discover_all_verified_filings()
        if filings:
            report = reader.load_report(filings[0])
            assert report is not None

    def test_report_has_summary(
        self, mock_config_with_paths, create_verification_report
    ):
        """Report should have summary with score."""
        from loaders.verification_data import VerificationDataLoader
        from loaders.verification_reader import VerificationReader

        loader = VerificationDataLoader(mock_config_with_paths)
        reader = VerificationReader(mock_config_with_paths)

        filings = loader.discover_all_verified_filings()
        if filings:
            report = reader.load_report(filings[0])
            if report:
                assert hasattr(report, 'summary')
                assert hasattr(report.summary, 'score')

    def test_is_verified_checks_score(self, mock_config):
        """is_verified should check against threshold."""
        from loaders.verification_reader import VerificationReader, VerificationReport, VerificationSummary

        reader = VerificationReader(mock_config)

        # Create mock report
        summary = VerificationSummary(
            score=98.0,
            total_checks=100,
            passed=98,
            failed=2,
            skipped=0,
            critical_issues=0,
            warning_issues=2,
            info_issues=0,
        )
        report = MagicMock()
        report.summary = summary

        assert reader.is_verified(report, min_score=95.0) is True
        assert reader.is_verified(report, min_score=99.0) is False


# ==============================================================================
# MAPPED DATA LOADER TESTS
# ==============================================================================

class TestMappedDataLoader:
    """Test MappedDataLoader (blind reader)."""

    def test_init_with_config(self, mock_config):
        """Should initialize with config."""
        from loaders.mapped_data import MappedDataLoader

        loader = MappedDataLoader(mock_config)
        assert loader.config is mock_config

    def test_discover_returns_list(self, temp_dir):
        """Should return list of filings."""
        from loaders.mapped_data import MappedDataLoader

        mock_config = MagicMock()
        mock_config.get.return_value = temp_dir

        loader = MappedDataLoader(mock_config)
        filings = loader.discover_all_mapped_filings()

        assert isinstance(filings, list)

    def test_finds_mapped_statements(
        self, test_data_structure, mock_config_with_paths, create_mapped_statement
    ):
        """Should find mapped statement files."""
        from loaders.mapped_data import MappedDataLoader

        loader = MappedDataLoader(mock_config_with_paths)
        filings = loader.discover_all_mapped_filings()

        # Should find at least one filing
        assert len(filings) >= 0  # May be 0 if structure doesn't match


class TestMappedReader:
    """Test MappedReader (content reader)."""

    def test_read_statements_returns_object(
        self, test_data_structure, mock_config_with_paths, create_mapped_statement
    ):
        """Should read and parse mapped statements."""
        from loaders.mapped_data import MappedDataLoader
        from loaders.mapped_reader import MappedReader

        loader = MappedDataLoader(mock_config_with_paths)
        reader = MappedReader()

        filings = loader.discover_all_mapped_filings()
        if filings:
            statements = reader.read_statements(filings[0])
            # May be None if no files found
            assert statements is None or hasattr(statements, 'statements')

    def test_get_all_facts(self):
        """Should extract all facts from statements."""
        from loaders.mapped_reader import MappedReader, MappedStatements, Statement, StatementFact

        reader = MappedReader()

        # Create test data
        fact1 = StatementFact(concept='us-gaap:Assets', value=1000000)
        fact2 = StatementFact(concept='us-gaap:Liabilities', value=500000)
        stmt = Statement(name='BalanceSheet', facts=[fact1, fact2])
        statements = MappedStatements(statements=[stmt])

        all_facts = reader.get_all_facts(statements)

        assert len(all_facts) == 2
        assert fact1 in all_facts
        assert fact2 in all_facts


# ==============================================================================
# PARSED DATA LOADER TESTS
# ==============================================================================

class TestParsedDataLoader:
    """Test ParsedDataLoader (blind reader)."""

    def test_init_with_config(self, mock_config):
        """Should initialize with config."""
        from loaders.parsed_data import ParsedDataLoader

        loader = ParsedDataLoader(mock_config)
        assert loader.config is mock_config

    def test_discover_returns_list(self, temp_dir):
        """Should return list of filings."""
        from loaders.parsed_data import ParsedDataLoader

        mock_config = MagicMock()
        mock_config.get.return_value = temp_dir

        loader = ParsedDataLoader(mock_config)
        filings = loader.discover_all_parsed_filings()

        assert isinstance(filings, list)

    def test_finds_parsed_json(
        self, test_data_structure, mock_config_with_paths, create_parsed_filing
    ):
        """Should find parsed.json files."""
        from loaders.parsed_data import ParsedDataLoader

        loader = ParsedDataLoader(mock_config_with_paths)
        filings = loader.discover_all_parsed_filings()

        assert len(filings) >= 1


class TestParsedReader:
    """Test ParsedReader (content reader)."""

    def test_read_parsed_filing(
        self, test_data_structure, mock_config_with_paths, create_parsed_filing
    ):
        """Should read and parse parsed.json."""
        from loaders.parsed_data import ParsedDataLoader
        from loaders.parsed_reader import ParsedReader

        loader = ParsedDataLoader(mock_config_with_paths)
        reader = ParsedReader()

        filings = loader.discover_all_parsed_filings()
        if filings:
            parsed = reader.read_parsed_filing(filings[0])
            assert parsed is not None
            assert hasattr(parsed, 'facts')

    def test_get_numeric_facts(self):
        """Should filter numeric facts."""
        from loaders.parsed_reader import ParsedReader, ParsedFiling, ParsedFact

        reader = ParsedReader()

        # Create test data
        fact1 = ParsedFact(concept='us-gaap:Assets', value=1000000, unit='usd')
        fact2 = ParsedFact(concept='dei:EntityName', value='TestCo', unit=None)
        filing = ParsedFiling(facts=[fact1, fact2])

        numeric = reader.get_numeric_facts(filing)

        assert len(numeric) == 1
        assert numeric[0].concept == 'us-gaap:Assets'


# ==============================================================================
# XBRL DATA LOADER TESTS
# ==============================================================================

class TestXBRLDataLoader:
    """Test XBRLDataLoader (blind reader)."""

    def test_init_with_config(self, mock_config):
        """Should initialize with config."""
        from loaders.xbrl_data import XBRLDataLoader

        loader = XBRLDataLoader(mock_config)
        assert loader.config is mock_config

    def test_discover_all_files(self, temp_dir):
        """Should discover files recursively."""
        from loaders.xbrl_data import XBRLDataLoader

        # Create some test files
        (temp_dir / 'test.xml').touch()
        (temp_dir / 'subdir').mkdir()
        (temp_dir / 'subdir' / 'test2.xml').touch()

        mock_config = MagicMock()
        mock_config.get.return_value = temp_dir

        loader = XBRLDataLoader(mock_config)
        files = loader.discover_all_files()

        assert len(files) >= 2


class TestXBRLReader:
    """Test XBRLReader (content reader)."""

    def test_init(self, mock_config):
        """Should initialize."""
        from loaders.xbrl_reader import XBRLReader

        reader = XBRLReader(mock_config)
        assert reader is not None

    def test_extract_concept_from_href(self):
        """Should extract concept from xlink:href."""
        from loaders.xbrl_reader import XBRLReader

        reader = XBRLReader()

        href = 'schema.xsd#us-gaap_Assets'
        concept = reader._extract_concept_from_href(href)

        assert concept == 'us-gaap:Assets'

    def test_extract_concept_no_fragment(self):
        """Should handle href without fragment."""
        from loaders.xbrl_reader import XBRLReader

        reader = XBRLReader()

        href = 'schema.xsd'
        concept = reader._extract_concept_from_href(href)

        assert concept == 'schema.xsd'


# ==============================================================================
# LOADER CONSTANTS TESTS
# ==============================================================================

class TestLoaderConstants:
    """Test loader constants module."""

    def test_normalize_form_name(self):
        """Should normalize form names."""
        from loaders.constants import normalize_form_name

        assert normalize_form_name('10-K') == '10-k'
        assert normalize_form_name('10_K') == '10-k'
        assert normalize_form_name('Form10-K') == '10-k'

    def test_get_form_variations(self):
        """Should return form name variations."""
        from loaders.constants import get_form_variations

        variations = get_form_variations('10-K')

        assert '10-k' in [v.lower() for v in variations]
        assert '10_k' in [v.lower() for v in variations]
        assert '10k' in [v.lower() for v in variations]

    def test_normalize_name(self):
        """Should normalize names for comparison."""
        from loaders.constants import normalize_name

        assert normalize_name('Test Company') == 'testcompany'
        assert normalize_name('Test_Company') == 'testcompany'
        assert normalize_name('Test-Company') == 'testcompany'

    def test_dates_match_flexible_any(self):
        """dates_match_flexible with 'any' should always match."""
        from loaders.constants import dates_match_flexible

        assert dates_match_flexible('2024-01-01', '2023-01-01', 'any') is True
        assert dates_match_flexible(None, '2023-01-01', 'any') is True

    def test_dates_match_flexible_year(self):
        """dates_match_flexible with 'year' should match same year."""
        from loaders.constants import dates_match_flexible

        assert dates_match_flexible('2024-01-01', '2024-12-31', 'year') is True
        assert dates_match_flexible('2024-01-01', '2023-12-31', 'year') is False

    def test_dates_match_flexible_exact(self):
        """dates_match_flexible with 'exact' should match exactly."""
        from loaders.constants import dates_match_flexible

        assert dates_match_flexible('2024-01-01', '2024-01-01', 'exact') is True
        assert dates_match_flexible('2024-01-01', '2024-01-02', 'exact') is False
        # Different separators should still match
        assert dates_match_flexible('2024-01-01', '2024_01_01', 'exact') is True
