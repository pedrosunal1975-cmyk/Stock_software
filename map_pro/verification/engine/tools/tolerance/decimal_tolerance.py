# Path: verification/engine/checks_v2/tools/tolerance/decimal_tolerance.py
"""
Decimal Tolerance for XBRL Verification

Implements XBRL rounding rules per the specification and DQC Global Rule Logic.

KEY RULES:
1. Compare numbers at the LOWEST decimal precision between the values
2. Use XBRL "round half to nearest even" (banker's rounding)
3. Example: 532,000,000 (decimals=-6) equals 532,300,000 (decimals=-5) when rounded

DECIMALS ATTRIBUTE:
- Positive decimals: digits after decimal point (e.g., 2 = 0.01 precision)
- Negative decimals: rounding to powers of 10 (e.g., -6 = millions, -3 = thousands)
- INF: exact value, no rounding

This module is AGNOSTIC and can be used by any verification component.
"""

import logging
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
from dataclasses import dataclass
from typing import Optional

from ...constants.tolerances import (
    DECIMAL_COMPARISON_EPSILON_BASE,
    DECIMAL_EPSILON_MULTIPLIER,
)
from ...constants.xbrl import DECIMALS_INF


@dataclass
class ToleranceResult:
    """
    Result of a tolerance comparison.

    Provides full details of the comparison for diagnostic purposes.

    Attributes:
        values_equal: Whether values are equal within tolerance
        value1_rounded: First value after rounding
        value2_rounded: Second value after rounding
        comparison_decimals: The decimals used for comparison (lowest)
        difference: Absolute difference after rounding
        message: Human-readable explanation
        strategy_used: Which comparison strategy was applied
    """
    values_equal: bool
    value1_rounded: float
    value2_rounded: float
    comparison_decimals: Optional[int]
    difference: float
    message: str
    strategy_used: str = 'decimal'


class DecimalTolerance:
    """
    XBRL decimal tolerance checker.

    Compares numeric values respecting their decimal precision attributes.
    Uses banker's rounding (round half to nearest even) per XBRL spec.

    Usage:
        tolerance = DecimalTolerance()

        # Compare two values at their respective precisions
        result = tolerance.compare(
            value1=532000000, decimals1=-6,  # 532 million (rounded to millions)
            value2=532300000, decimals2=-5   # 532.3 million (rounded to 100k)
        )
        # result.values_equal = True (both round to 532M at decimals=-6)

        # Check if value is within tolerance
        result = tolerance.is_within_tolerance(
            expected=1000000,
            actual=999999,
            expected_decimals=-3,
            actual_decimals=-3
        )
    """

    def __init__(self):
        """Initialize decimal tolerance checker."""
        self.logger = logging.getLogger('tools.tolerance.decimal_tolerance')

    def round_to_decimals(self, value: float, decimals: Optional[int]) -> float:
        """
        Round a value to the specified decimals precision.

        Uses XBRL "round half to nearest even" (banker's rounding).

        Args:
            value: The numeric value to round
            decimals: The decimals precision:
                - None or INF: return exact value
                - Positive: digits after decimal point
                - Negative: round to power of 10 (e.g., -3 = thousands)

        Returns:
            Rounded value
        """
        if decimals is None:
            return value

        # Handle string decimals (e.g., "INF" for infinite precision)
        if isinstance(decimals, str):
            if decimals.upper() == DECIMALS_INF:
                return value  # Infinite precision, no rounding needed
            try:
                decimals = int(decimals)
            except ValueError:
                return value  # Unknown string value, return as-is

        try:
            # Convert to Decimal for precise rounding
            d = Decimal(str(value))

            if decimals >= 0:
                # Positive decimals: round to N decimal places
                # e.g., decimals=2 means round to 0.01
                quantize_str = '0.' + '0' * decimals if decimals > 0 else '1'
                quantize_value = Decimal(quantize_str)
                rounded = d.quantize(quantize_value, rounding=ROUND_HALF_EVEN)
            else:
                # Negative decimals: round to power of 10
                # e.g., decimals=-6 means round to nearest 1,000,000
                # We need to divide, round, then multiply back
                divisor = Decimal(10) ** (-decimals)
                scaled = d / divisor
                rounded_scaled = scaled.quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)
                rounded = rounded_scaled * divisor

            return float(rounded)

        except (InvalidOperation, ValueError) as e:
            self.logger.warning(f"Rounding error for {value} at decimals={decimals}: {e}")
            return value

    def normalize_decimals(self, decimals) -> Optional[int]:
        """
        Normalize decimals value to int or None.

        XBRL decimals can be:
        - int: normal precision value
        - str "INF": infinite precision (treat as None for comparison)
        - str number: needs conversion to int
        - None: unspecified precision

        Args:
            decimals: Raw decimals value

        Returns:
            Normalized int value or None
        """
        if decimals is None:
            return None
        if isinstance(decimals, str):
            if decimals.upper() == DECIMALS_INF:
                return None  # Infinite precision, use other value for comparison
            try:
                return int(decimals)
            except ValueError:
                return None
        return int(decimals)

    def get_comparison_decimals(
        self,
        decimals1: Optional[int],
        decimals2: Optional[int]
    ) -> Optional[int]:
        """
        Determine the decimals to use for comparison.

        Per DQC rules: compare at the LOWEST decimal precision.

        Args:
            decimals1: Decimals for first value
            decimals2: Decimals for second value

        Returns:
            The lowest decimals value (least precise), or None if both are None
        """
        # Normalize decimals values (handle "INF", string numbers, etc.)
        d1 = self.normalize_decimals(decimals1)
        d2 = self.normalize_decimals(decimals2)

        if d1 is None and d2 is None:
            return None

        if d1 is None:
            return d2
        if d2 is None:
            return d1

        # Return the lower (less precise) decimals
        # e.g., -6 (millions) is less precise than -3 (thousands)
        return min(d1, d2)

    def compare(
        self,
        value1: float,
        value2: float,
        decimals1: Optional[int] = None,
        decimals2: Optional[int] = None
    ) -> ToleranceResult:
        """
        Compare two values respecting their decimal precisions.

        Both values are rounded to the LOWEST precision before comparison.

        Args:
            value1: First value
            value2: Second value
            decimals1: Decimals precision for value1
            decimals2: Decimals precision for value2

        Returns:
            ToleranceResult with comparison details
        """
        comparison_decimals = self.get_comparison_decimals(decimals1, decimals2)

        # Round both values to comparison precision
        rounded1 = self.round_to_decimals(value1, comparison_decimals)
        rounded2 = self.round_to_decimals(value2, comparison_decimals)

        difference = abs(rounded1 - rounded2)

        # Values are equal if rounded values match
        # Use small epsilon for floating point comparison
        if comparison_decimals is None:
            epsilon = DECIMAL_COMPARISON_EPSILON_BASE
        else:
            epsilon = (10 ** (-comparison_decimals if comparison_decimals >= 0 else 0)
                       * DECIMAL_EPSILON_MULTIPLIER)

        values_equal = difference <= epsilon

        if values_equal:
            message = (
                f"Values equal at decimals={comparison_decimals}: "
                f"{rounded1:,.0f} == {rounded2:,.0f}"
            )
        else:
            message = (
                f"Values differ at decimals={comparison_decimals}: "
                f"{rounded1:,.0f} != {rounded2:,.0f} (diff={difference:,.0f})"
            )

        return ToleranceResult(
            values_equal=values_equal,
            value1_rounded=rounded1,
            value2_rounded=rounded2,
            comparison_decimals=comparison_decimals,
            difference=difference,
            message=message,
            strategy_used='decimal',
        )

    def is_within_tolerance(
        self,
        expected: float,
        actual: float,
        expected_decimals: Optional[int] = None,
        actual_decimals: Optional[int] = None
    ) -> ToleranceResult:
        """
        Check if actual value is within tolerance of expected value.

        Convenience wrapper around compare() with clearer semantics.

        Args:
            expected: The expected/target value
            actual: The actual/computed value
            expected_decimals: Decimals precision for expected value
            actual_decimals: Decimals precision for actual value

        Returns:
            ToleranceResult with comparison details
        """
        return self.compare(
            value1=expected,
            value2=actual,
            decimals1=expected_decimals,
            decimals2=actual_decimals,
        )


__all__ = ['DecimalTolerance', 'ToleranceResult']
