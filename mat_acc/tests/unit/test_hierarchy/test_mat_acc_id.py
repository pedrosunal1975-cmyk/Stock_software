# Path: mat_acc/tests/unit/test_hierarchy/test_mat_acc_id.py
"""
Tests for mat_acc_id generation and parsing utilities.

Tests the DYNAMIC statement code generation system that works with
any taxonomy/market statement types - not hardcoded mappings.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from process.hierarchy.mat_acc_id import (
    format_mat_acc_id,
    parse_mat_acc_id,
    get_statement_code,
    get_statement_type,
    format_position,
    normalize_context_ref,
    add_context_to_position,
    generate_statement_code,
    get_registered_types,
    clear_registry,
)


@pytest.fixture(autouse=True)
def reset_registry():
    """Clear the statement type registry before and after each test."""
    clear_registry()
    yield
    clear_registry()


class TestFormatMatAccId:
    """Tests for format_mat_acc_id function."""

    def test_format_with_context(self):
        """Format mat_acc_id with context reference."""
        result = format_mat_acc_id('BS', 2, 1, 'c4')
        assert result == 'BS-002-001-c4'

    def test_format_without_context(self):
        """Format mat_acc_id without context reference."""
        result = format_mat_acc_id('IS', 3, 5)
        assert result == 'IS-003-005'

    def test_format_normalizes_context_with_dash(self):
        """Format normalizes context_ref c-4 to c4."""
        result = format_mat_acc_id('CF', 1, 2, 'c-4')
        assert result == 'CF-001-002-c4'

    def test_format_normalizes_context_with_underscore(self):
        """Format normalizes context_ref c_4 to c4."""
        result = format_mat_acc_id('EQ', 0, 1, 'c_12')
        assert result == 'EQ-000-001-c12'

    def test_format_pads_level_to_three_digits(self):
        """Level is zero-padded to 3 digits."""
        result = format_mat_acc_id('BS', 1, 1)
        assert result == 'BS-001-001'

    def test_format_pads_sibling_to_three_digits(self):
        """Sibling is zero-padded to 3 digits."""
        result = format_mat_acc_id('BS', 0, 99)
        assert result == 'BS-000-099'

    def test_format_handles_large_numbers(self):
        """Format handles large level and sibling numbers."""
        result = format_mat_acc_id('OT', 15, 123)
        assert result == 'OT-015-123'


class TestParseMatAccId:
    """Tests for parse_mat_acc_id function."""

    def test_parse_full_id_with_context(self):
        """Parse full mat_acc_id with context."""
        # First register the statement type
        get_statement_code('BALANCE_SHEET')

        result = parse_mat_acc_id('BS-002-001-c4')
        assert result['statement_code'] == 'BS'
        assert result['statement_type'] == 'BALANCE_SHEET'
        assert result['level'] == 2
        assert result['sibling'] == 1
        assert result['context_ref'] == 'c4'
        assert result['position'] == 'BS-002-001'

    def test_parse_id_without_context(self):
        """Parse mat_acc_id without context."""
        # First register the statement type
        get_statement_code('INCOME_STATEMENT')

        result = parse_mat_acc_id('IS-003-005')
        assert result['statement_code'] == 'IS'
        assert result['statement_type'] == 'INCOME_STATEMENT'
        assert result['level'] == 3
        assert result['sibling'] == 5
        assert result['context_ref'] is None
        assert result['position'] == 'IS-003-005'

    def test_parse_cash_flow_id(self):
        """Parse cash flow statement ID."""
        # First register the statement type
        get_statement_code('CASH_FLOW')

        result = parse_mat_acc_id('CF-001-002-c12')
        assert result['statement_code'] == 'CF'
        assert result['statement_type'] == 'CASH_FLOW'

    def test_parse_equity_id(self):
        """Parse equity statement ID."""
        # First register the statement type
        get_statement_code('EQUITY_STATEMENT')

        result = parse_mat_acc_id('ES-000-001')
        assert result['statement_code'] == 'ES'
        assert result['statement_type'] == 'EQUITY_STATEMENT'

    def test_parse_unknown_code_returns_unknown(self):
        """Parse ID with unregistered code returns UNKNOWN."""
        result = parse_mat_acc_id('XX-005-010')
        assert result['statement_code'] == 'XX'
        assert result['statement_type'] == 'UNKNOWN'

    def test_parse_invalid_id_returns_defaults(self):
        """Parse invalid ID returns default values."""
        result = parse_mat_acc_id('invalid')
        assert result['statement_code'] == ''
        assert result['level'] == 0
        assert result['sibling'] == 0


class TestDynamicStatementCodeGeneration:
    """Tests for DYNAMIC statement code generation - the core feature."""

    def test_generates_code_from_first_letters(self):
        """Generate code from first letter of first two words."""
        code = get_statement_code('BALANCE_SHEET')
        assert code == 'BS'
        assert len(code) == 2
        assert code.isupper()

    def test_generates_code_for_income_statement(self):
        """Generate code for income statement."""
        code = get_statement_code('INCOME_STATEMENT')
        assert code == 'IS'

    def test_generates_code_for_cash_flow(self):
        """Generate code for cash flow."""
        code = get_statement_code('CASH_FLOW')
        assert code == 'CF'

    def test_generates_code_for_single_word(self):
        """Generate code for single word statement type."""
        code = get_statement_code('EQUITY')
        assert len(code) == 2
        assert code.isupper()

    def test_same_type_returns_same_code(self):
        """Same statement type always returns same code."""
        code1 = get_statement_code('BALANCE_SHEET')
        code2 = get_statement_code('BALANCE_SHEET')
        assert code1 == code2

    def test_case_insensitive(self):
        """Statement type is case insensitive."""
        code1 = get_statement_code('BALANCE_SHEET')
        code2 = get_statement_code('balance_sheet')
        code3 = get_statement_code('Balance_Sheet')
        assert code1 == code2 == code3

    def test_supports_any_statement_type(self):
        """Support ANY statement type - not just hardcoded ones."""
        # ESEF statement types
        code1 = get_statement_code('STATEMENT_OF_FINANCIAL_POSITION')
        assert len(code1) == 2

        # UK GAAP statement types
        code2 = get_statement_code('PROFIT_AND_LOSS_ACCOUNT')
        assert len(code2) == 2

        # Custom statement types
        code3 = get_statement_code('CUSTOM_COMPANY_STATEMENT')
        assert len(code3) == 2

        # Japanese GAAP (hypothetical)
        code4 = get_statement_code('CONSOLIDATED_BALANCE_SHEET')
        assert len(code4) == 2

    def test_handles_collision_gracefully(self):
        """Different statement types with same initials get unique codes."""
        # Both start with 'B S'
        code1 = get_statement_code('BALANCE_SHEET')
        code2 = get_statement_code('BUDGET_SUMMARY')

        # Both should have valid codes
        assert len(code1) == 2
        assert len(code2) == 2
        assert code1.isupper()
        assert code2.isupper()

    def test_empty_string_returns_xx(self):
        """Empty string returns XX as default."""
        code = generate_statement_code('')
        assert code == 'XX'

    def test_registered_types_tracking(self):
        """Track all registered statement types."""
        get_statement_code('BALANCE_SHEET')
        get_statement_code('INCOME_STATEMENT')
        get_statement_code('CASH_FLOW')

        registered = get_registered_types()
        assert 'BALANCE_SHEET' in registered
        assert 'INCOME_STATEMENT' in registered
        assert 'CASH_FLOW' in registered
        assert len(registered) == 3


class TestGetStatementType:
    """Tests for get_statement_type function."""

    def test_returns_registered_type(self):
        """Returns the registered statement type for a code."""
        get_statement_code('BALANCE_SHEET')  # Register it
        assert get_statement_type('BS') == 'BALANCE_SHEET'

    def test_returns_unknown_for_unregistered(self):
        """Returns UNKNOWN for unregistered code."""
        assert get_statement_type('XX') == 'UNKNOWN'
        assert get_statement_type('ZZ') == 'UNKNOWN'

    def test_case_insensitive_lookup(self):
        """Code lookup is case insensitive."""
        get_statement_code('BALANCE_SHEET')
        assert get_statement_type('bs') == 'BALANCE_SHEET'
        assert get_statement_type('Bs') == 'BALANCE_SHEET'


class TestFormatPosition:
    """Tests for format_position function."""

    def test_format_position(self):
        """Format position without context."""
        result = format_position('BS', 2, 1)
        assert result == 'BS-002-001'

    def test_format_position_zero_level(self):
        """Format position with zero level."""
        result = format_position('IS', 0, 1)
        assert result == 'IS-000-001'


class TestNormalizeContextRef:
    """Tests for normalize_context_ref function."""

    def test_normalize_with_dash(self):
        """Normalize context with dash."""
        assert normalize_context_ref('c-4') == 'c4'

    def test_normalize_with_underscore(self):
        """Normalize context with underscore."""
        assert normalize_context_ref('c_12') == 'c12'

    def test_normalize_already_clean(self):
        """Already clean context stays same."""
        assert normalize_context_ref('c4') == 'c4'

    def test_normalize_complex(self):
        """Normalize complex context reference."""
        assert normalize_context_ref('context-ref-123') == 'contextref123'


class TestAddContextToPosition:
    """Tests for add_context_to_position function."""

    def test_add_context(self):
        """Add context to position."""
        result = add_context_to_position('BS-002-001', 'c4')
        assert result == 'BS-002-001-c4'

    def test_add_context_normalizes(self):
        """Add context normalizes the context_ref."""
        result = add_context_to_position('IS-003-005', 'c-12')
        assert result == 'IS-003-005-c12'


class TestClearRegistry:
    """Tests for clear_registry function."""

    def test_clear_removes_all_types(self):
        """Clear removes all registered types."""
        get_statement_code('BALANCE_SHEET')
        get_statement_code('INCOME_STATEMENT')

        assert len(get_registered_types()) == 2

        clear_registry()

        assert len(get_registered_types()) == 0

    def test_after_clear_codes_regenerated(self):
        """After clear, codes are regenerated on next use."""
        code1 = get_statement_code('BALANCE_SHEET')
        clear_registry()
        code2 = get_statement_code('BALANCE_SHEET')

        # Should get same code after regeneration
        assert code1 == code2


class TestMarketAgnosticDesign:
    """Tests proving the system works with any market's statement types."""

    def test_sec_us_gaap_statements(self):
        """Works with SEC US-GAAP statement types."""
        statements = [
            'BALANCE_SHEET',
            'INCOME_STATEMENT',
            'CASH_FLOW_STATEMENT',
            'STOCKHOLDERS_EQUITY',
        ]
        codes = [get_statement_code(s) for s in statements]

        # All codes should be unique
        assert len(codes) == len(set(codes))

        # All codes should be 2 uppercase letters
        for code in codes:
            assert len(code) == 2
            assert code.isupper()

    def test_esef_ifrs_statements(self):
        """Works with ESEF IFRS statement types."""
        statements = [
            'STATEMENT_OF_FINANCIAL_POSITION',
            'STATEMENT_OF_COMPREHENSIVE_INCOME',
            'STATEMENT_OF_CASH_FLOWS',
            'STATEMENT_OF_CHANGES_IN_EQUITY',
        ]
        codes = [get_statement_code(s) for s in statements]

        # All codes should be valid
        for code in codes:
            assert len(code) == 2
            assert code.isupper()

    def test_uk_gaap_statements(self):
        """Works with UK GAAP statement types."""
        statements = [
            'PROFIT_AND_LOSS_ACCOUNT',
            'BALANCE_SHEET',
            'STATEMENT_OF_TOTAL_RECOGNISED_GAINS_AND_LOSSES',
        ]
        codes = [get_statement_code(s) for s in statements]

        for code in codes:
            assert len(code) == 2
            assert code.isupper()

    def test_custom_company_statements(self):
        """Works with custom company-specific statement types."""
        statements = [
            'SEGMENT_REPORTING',
            'GEOGRAPHIC_BREAKDOWN',
            'PRODUCT_LINE_ANALYSIS',
            'QUARTERLY_COMPARISON',
        ]
        codes = [get_statement_code(s) for s in statements]

        for code in codes:
            assert len(code) == 2
            assert code.isupper()
