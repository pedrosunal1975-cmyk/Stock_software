# Path: verification/engine/checks_v2/tools/fact/value_parser.py
"""
Value Parser for XBRL Verification

Handles parsing of raw values from financial statements.

Techniques consolidated from:
- checks/core/value_parsing.py

DESIGN: Stateless tool for parsing raw values to numeric form.
Handles common financial statement conventions.
"""

import logging
from typing import Optional

from ...constants.patterns import NIL_VALUES, EM_DASH, EN_DASH


class ValueParser:
    """
    Handles parsing of raw values from financial statements.

    Converts various string representations into numeric values,
    handling common financial statement conventions.

    This is a STATELESS tool - can be reused across all processing stages.

    Strategies:
    - 'standard': Default parsing with common conventions
    - 'strict': No nil-to-zero conversion, stricter parsing

    Usage:
        parser = ValueParser()

        # Parse various formats
        parser.parse_value('1,234,567')  # -> 1234567.0
        parser.parse_value('(500)')      # -> -500.0
        parser.parse_value('-')          # -> 0.0 (nil)
        parser.parse_value('$1,000')     # -> 1000.0
    """

    def __init__(self, strategy: str = 'standard'):
        """
        Initialize the value parser.

        Args:
            strategy: Parsing strategy ('standard' or 'strict')
        """
        self.logger = logging.getLogger('tools.fact.value_parser')
        self._strategy = strategy
        self._nil_values = NIL_VALUES

    def set_strategy(self, strategy: str) -> None:
        """
        Set the parsing strategy.

        Args:
            strategy: 'standard' or 'strict'
        """
        if strategy not in ('standard', 'strict'):
            raise ValueError(f"Unknown strategy: {strategy}")
        self._strategy = strategy

    def parse_value(self, raw_value) -> Optional[float]:
        """
        Parse a raw value to float.

        Handles financial statement conventions:
        - Em-dash, en-dash, hyphen mean zero/nil
        - Removes commas and dollar signs
        - Parentheses indicate negative values
        - Returns None if unparseable

        Args:
            raw_value: Raw value from statement

        Returns:
            Float value or None
        """
        if raw_value is None:
            return None

        raw_str = str(raw_value).strip()

        # Check for nil/zero representations
        if self._is_nil_string(raw_str):
            if self._strategy == 'strict':
                return None
            return 0.0

        try:
            # Clean common financial formatting:
            # - Remove commas (thousands separators)
            # - Remove dollar signs
            # - Convert parentheses to negative sign
            cleaned = (
                raw_str
                .replace(',', '')
                .replace('$', '')
                .replace('(', '-')
                .replace(')', '')
            )
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def _is_nil_string(self, raw_str: str) -> bool:
        """Check if string represents nil/zero."""
        return raw_str in self._nil_values or raw_str in {EM_DASH, EN_DASH}

    def is_nil_value(self, raw_value) -> bool:
        """
        Check if a value represents nil/zero.

        Args:
            raw_value: Raw value to check

        Returns:
            True if value is nil/zero representation
        """
        if raw_value is None:
            return True
        raw_str = str(raw_value).strip()
        return self._is_nil_string(raw_str)

    def is_numeric(self, raw_value) -> bool:
        """
        Check if a value can be parsed to a number.

        Args:
            raw_value: Raw value to check

        Returns:
            True if value is parseable to float
        """
        return self.parse_value(raw_value) is not None

    def parse_decimals(self, decimals_value) -> Optional[int]:
        """
        Parse decimals attribute to integer.

        Handles string decimals (common in mapped statements).
        Special handling for 'INF' which means infinite precision.

        Args:
            decimals_value: Raw decimals value

        Returns:
            Integer decimals or None for INF/invalid
        """
        if decimals_value is None:
            return None
        if isinstance(decimals_value, str):
            if decimals_value.upper() == 'INF':
                return None
            try:
                return int(decimals_value)
            except ValueError:
                return None
        try:
            return int(decimals_value)
        except (ValueError, TypeError):
            return None


__all__ = ['ValueParser']
