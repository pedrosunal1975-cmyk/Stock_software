# Path: mat_acc/tests/unit/test_hierarchy/test_constants.py
"""
Tests for hierarchy constants module.
"""

import pytest
import sys
from pathlib import Path

# Add mat_acc to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from process.hierarchy.constants import (
    NodeType,
    StatementType,
    LinkbaseRole,
    OutputFormat,
    MAX_HIERARCHY_DEPTH,
    DEFAULT_INDENT_SIZE,
    BALANCE_SHEET_KEYWORDS,
    INCOME_STATEMENT_KEYWORDS,
    CASH_FLOW_KEYWORDS,
    EQUITY_KEYWORDS,
    TOTAL_PATTERNS,
    ABSTRACT_SUFFIX,
    MIN_NODES_FOR_VALID_HIERARCHY,
)


class TestNodeTypeEnum:
    """Test NodeType enumeration."""

    def test_root_type_exists(self):
        """NodeType should have ROOT."""
        assert NodeType.ROOT.value == "root"

    def test_abstract_type_exists(self):
        """NodeType should have ABSTRACT."""
        assert NodeType.ABSTRACT.value == "abstract"

    def test_line_item_type_exists(self):
        """NodeType should have LINE_ITEM."""
        assert NodeType.LINE_ITEM.value == "line_item"

    def test_total_type_exists(self):
        """NodeType should have TOTAL."""
        assert NodeType.TOTAL.value == "total"

    def test_all_node_types_defined(self):
        """All expected node types should be defined."""
        expected = {'root', 'abstract', 'line_item', 'total', 'dimension_member'}
        actual = {t.value for t in NodeType}
        assert actual == expected


class TestStatementTypeEnum:
    """Test StatementType enumeration."""

    def test_balance_sheet_type(self):
        """StatementType should have BALANCE_SHEET."""
        assert StatementType.BALANCE_SHEET.value == "balance_sheet"

    def test_income_statement_type(self):
        """StatementType should have INCOME_STATEMENT."""
        assert StatementType.INCOME_STATEMENT.value == "income_statement"

    def test_cash_flow_type(self):
        """StatementType should have CASH_FLOW."""
        assert StatementType.CASH_FLOW.value == "cash_flow"

    def test_unknown_type(self):
        """StatementType should have UNKNOWN."""
        assert StatementType.UNKNOWN.value == "unknown"


class TestLinkbaseRoleEnum:
    """Test LinkbaseRole enumeration."""

    def test_presentation_role(self):
        """LinkbaseRole should have PRESENTATION."""
        assert LinkbaseRole.PRESENTATION.value == "presentation"

    def test_calculation_role(self):
        """LinkbaseRole should have CALCULATION."""
        assert LinkbaseRole.CALCULATION.value == "calculation"


class TestOutputFormatEnum:
    """Test OutputFormat enumeration."""

    def test_dict_format(self):
        """OutputFormat should have DICT."""
        assert OutputFormat.DICT.value == "dict"

    def test_json_format(self):
        """OutputFormat should have JSON."""
        assert OutputFormat.JSON.value == "json"

    def test_text_format(self):
        """OutputFormat should have TEXT."""
        assert OutputFormat.TEXT.value == "text"


class TestDepthLimits:
    """Test depth limit constants."""

    def test_max_hierarchy_depth_value(self):
        """MAX_HIERARCHY_DEPTH should be reasonable."""
        assert MAX_HIERARCHY_DEPTH == 15
        assert MAX_HIERARCHY_DEPTH > 5

    def test_default_indent_size(self):
        """DEFAULT_INDENT_SIZE should be positive."""
        assert DEFAULT_INDENT_SIZE == 2
        assert DEFAULT_INDENT_SIZE > 0


class TestKeywordTuples:
    """Test keyword detection tuples."""

    def test_balance_sheet_keywords_not_empty(self):
        """BALANCE_SHEET_KEYWORDS should have values."""
        assert len(BALANCE_SHEET_KEYWORDS) > 0
        assert 'balance' in BALANCE_SHEET_KEYWORDS

    def test_income_statement_keywords_not_empty(self):
        """INCOME_STATEMENT_KEYWORDS should have values."""
        assert len(INCOME_STATEMENT_KEYWORDS) > 0
        assert 'income' in INCOME_STATEMENT_KEYWORDS

    def test_cash_flow_keywords_not_empty(self):
        """CASH_FLOW_KEYWORDS should have values."""
        assert len(CASH_FLOW_KEYWORDS) > 0
        assert 'cash' in CASH_FLOW_KEYWORDS

    def test_equity_keywords_not_empty(self):
        """EQUITY_KEYWORDS should have values."""
        assert len(EQUITY_KEYWORDS) > 0
        assert 'equity' in EQUITY_KEYWORDS

    def test_total_patterns_not_empty(self):
        """TOTAL_PATTERNS should have values."""
        assert len(TOTAL_PATTERNS) > 0
        assert 'total' in TOTAL_PATTERNS


class TestSuffixConstants:
    """Test suffix constants."""

    def test_abstract_suffix(self):
        """ABSTRACT_SUFFIX should be defined."""
        assert ABSTRACT_SUFFIX == "Abstract"

    def test_suffixes_are_strings(self):
        """All suffixes should be strings."""
        assert isinstance(ABSTRACT_SUFFIX, str)


class TestValidationThresholds:
    """Test validation threshold constants."""

    def test_min_nodes_for_valid_hierarchy(self):
        """MIN_NODES_FOR_VALID_HIERARCHY should be positive."""
        assert MIN_NODES_FOR_VALID_HIERARCHY >= 2
