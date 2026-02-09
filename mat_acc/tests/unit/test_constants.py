# Path: mat_acc/tests/unit/test_constants.py
"""
Unit Tests for Constants Module

Tests the system-wide constants and utility functions.
"""

import sys
from pathlib import Path

import pytest

# Add mat_acc to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from constants import (
    StatementType,
    CalculationLevel,
    ConfidenceLevel,
    QualityRating,
    Severity,
    ProcessingStatus,
    VerificationStatus,
    OutputFormat,
    LogCategory,
    CALCULATION_LEVEL_NAMES,
    CONFIDENCE_HIGH_MIN,
    CONFIDENCE_MEDIUM_MIN,
    CONFIDENCE_LOW_MIN,
    QUALITY_EXCELLENT_MIN,
    QUALITY_GOOD_MIN,
    QUALITY_FAIR_MIN,
    QUALITY_POOR_MIN,
    get_quality_rating,
    STATUS_OK,
    STATUS_FAIL,
    STATUS_WARN,
    VerificationKeys,
    MappedStatementKeys,
)


class TestStatementTypeEnum:
    """Test StatementType enum."""

    def test_balance_sheet_value(self):
        """Balance sheet should have correct value."""
        assert StatementType.BALANCE_SHEET.value == 'BalanceSheet'

    def test_income_statement_value(self):
        """Income statement should have correct value."""
        assert StatementType.INCOME_STATEMENT.value == 'IncomeStatement'

    def test_cash_flow_value(self):
        """Cash flow should have correct value."""
        assert StatementType.CASH_FLOW.value == 'CashFlow'

    def test_all_statement_types_exist(self):
        """All expected statement types should exist."""
        expected = ['BALANCE_SHEET', 'INCOME_STATEMENT', 'CASH_FLOW',
                    'STOCKHOLDERS_EQUITY', 'COMPREHENSIVE_INCOME']
        for name in expected:
            assert hasattr(StatementType, name)


class TestCalculationLevelEnum:
    """Test CalculationLevel enum."""

    def test_level_values(self):
        """Levels should have correct integer values."""
        assert CalculationLevel.LEVEL_1_BASIC == 1
        assert CalculationLevel.LEVEL_2_STANDARD == 2
        assert CalculationLevel.LEVEL_3_DETAILED == 3
        assert CalculationLevel.LEVEL_4_INDUSTRY == 4

    def test_level_ordering(self):
        """Levels should be orderable."""
        assert CalculationLevel.LEVEL_1_BASIC < CalculationLevel.LEVEL_2_STANDARD
        assert CalculationLevel.LEVEL_2_STANDARD < CalculationLevel.LEVEL_3_DETAILED

    def test_level_names_dict(self):
        """CALCULATION_LEVEL_NAMES should have all levels."""
        assert 1 in CALCULATION_LEVEL_NAMES
        assert 2 in CALCULATION_LEVEL_NAMES
        assert 3 in CALCULATION_LEVEL_NAMES
        assert 4 in CALCULATION_LEVEL_NAMES
        assert CALCULATION_LEVEL_NAMES[1] == 'Basic Aggregation'


class TestConfidenceLevelEnum:
    """Test ConfidenceLevel enum."""

    def test_confidence_values(self):
        """Confidence levels should have correct values."""
        assert ConfidenceLevel.HIGH.value == 'high'
        assert ConfidenceLevel.MEDIUM.value == 'medium'
        assert ConfidenceLevel.LOW.value == 'low'
        assert ConfidenceLevel.UNKNOWN.value == 'unknown'

    def test_confidence_thresholds(self):
        """Confidence thresholds should be properly ordered."""
        assert CONFIDENCE_HIGH_MIN > CONFIDENCE_MEDIUM_MIN
        assert CONFIDENCE_MEDIUM_MIN > CONFIDENCE_LOW_MIN
        assert CONFIDENCE_HIGH_MIN == 90.0
        assert CONFIDENCE_MEDIUM_MIN == 70.0


class TestQualityRatingEnum:
    """Test QualityRating enum."""

    def test_quality_values(self):
        """Quality ratings should have correct values."""
        assert QualityRating.EXCELLENT.value == 'excellent'
        assert QualityRating.GOOD.value == 'good'
        assert QualityRating.FAIR.value == 'fair'
        assert QualityRating.POOR.value == 'poor'
        assert QualityRating.FAILED.value == 'failed'

    def test_quality_thresholds(self):
        """Quality thresholds should be properly ordered."""
        assert QUALITY_EXCELLENT_MIN > QUALITY_GOOD_MIN
        assert QUALITY_GOOD_MIN > QUALITY_FAIR_MIN
        assert QUALITY_FAIR_MIN > QUALITY_POOR_MIN


class TestGetQualityRating:
    """Test get_quality_rating function."""

    def test_excellent_rating(self):
        """Score 90+ should be excellent."""
        assert get_quality_rating(95.0) == QualityRating.EXCELLENT
        assert get_quality_rating(90.0) == QualityRating.EXCELLENT
        assert get_quality_rating(100.0) == QualityRating.EXCELLENT

    def test_good_rating(self):
        """Score 75-89 should be good."""
        assert get_quality_rating(85.0) == QualityRating.GOOD
        assert get_quality_rating(75.0) == QualityRating.GOOD

    def test_fair_rating(self):
        """Score 50-74 should be fair."""
        assert get_quality_rating(60.0) == QualityRating.FAIR
        assert get_quality_rating(50.0) == QualityRating.FAIR

    def test_poor_rating(self):
        """Score 25-49 should be poor."""
        assert get_quality_rating(40.0) == QualityRating.POOR
        assert get_quality_rating(25.0) == QualityRating.POOR

    def test_failed_rating(self):
        """Score below 25 should be failed."""
        assert get_quality_rating(20.0) == QualityRating.FAILED
        assert get_quality_rating(0.0) == QualityRating.FAILED


class TestSeverityEnum:
    """Test Severity enum."""

    def test_severity_values(self):
        """Severity levels should have correct values."""
        assert Severity.CRITICAL.value == 'critical'
        assert Severity.WARNING.value == 'warning'
        assert Severity.INFO.value == 'info'


class TestStatusEnums:
    """Test status enums."""

    def test_processing_status_values(self):
        """ProcessingStatus should have all expected values."""
        expected = ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'SKIPPED']
        for name in expected:
            assert hasattr(ProcessingStatus, name)

    def test_verification_status_values(self):
        """VerificationStatus should have all expected values."""
        expected = ['VERIFIED', 'PARTIALLY_VERIFIED', 'FAILED', 'NOT_VERIFIED']
        for name in expected:
            assert hasattr(VerificationStatus, name)


class TestOutputFormatEnum:
    """Test OutputFormat enum."""

    def test_output_format_values(self):
        """OutputFormat should have all expected formats."""
        assert OutputFormat.JSON.value == 'json'
        assert OutputFormat.CSV.value == 'csv'
        assert OutputFormat.EXCEL.value == 'xlsx'
        assert OutputFormat.HTML.value == 'html'
        assert OutputFormat.PDF.value == 'pdf'


class TestStatusIndicators:
    """Test ASCII status indicators."""

    def test_status_indicators_are_ascii(self):
        """Status indicators should be ASCII only."""
        indicators = [STATUS_OK, STATUS_FAIL, STATUS_WARN]

        for indicator in indicators:
            assert all(ord(c) < 128 for c in indicator), f"Non-ASCII in {indicator}"

    def test_status_indicator_values(self):
        """Status indicators should have expected values."""
        assert STATUS_OK == '[OK]'
        assert STATUS_FAIL == '[FAIL]'
        assert STATUS_WARN == '[WARN]'


class TestVerificationKeys:
    """Test VerificationKeys constants."""

    def test_top_level_keys(self):
        """Should have all top-level keys."""
        assert VerificationKeys.FILING_ID == 'filing_id'
        assert VerificationKeys.MARKET == 'market'
        assert VerificationKeys.COMPANY == 'company'
        assert VerificationKeys.FORM == 'form'
        assert VerificationKeys.DATE == 'date'

    def test_summary_keys(self):
        """Should have all summary keys."""
        assert VerificationKeys.SUMMARY == 'summary'
        assert VerificationKeys.SCORE == 'score'
        assert VerificationKeys.TOTAL_CHECKS == 'total_checks'
        assert VerificationKeys.PASSED == 'passed'
        assert VerificationKeys.FAILED == 'failed'

    def test_check_keys(self):
        """Should have all check keys."""
        assert VerificationKeys.CHECKS == 'checks'
        assert VerificationKeys.CHECK_NAME == 'check_name'
        assert VerificationKeys.SEVERITY == 'severity'


class TestMappedStatementKeys:
    """Test MappedStatementKeys constants."""

    def test_metadata_keys(self):
        """Should have all metadata keys."""
        assert MappedStatementKeys.METADATA == 'metadata'
        assert MappedStatementKeys.FILING_ID == 'filing_id'
        assert MappedStatementKeys.COMPANY == 'company'

    def test_statement_keys(self):
        """Should have all statement keys."""
        assert MappedStatementKeys.STATEMENTS == 'statements'
        assert MappedStatementKeys.STATEMENT_TYPE == 'statement_type'
        assert MappedStatementKeys.LINE_ITEMS == 'line_items'

    def test_line_item_keys(self):
        """Should have all line item keys."""
        assert MappedStatementKeys.CONCEPT_NAME == 'concept_name'
        assert MappedStatementKeys.LABEL == 'label'
        assert MappedStatementKeys.VALUES == 'values'
