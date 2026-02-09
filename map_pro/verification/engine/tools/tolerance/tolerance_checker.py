# Path: verification/engine/checks_v2/tools/tolerance/tolerance_checker.py
"""
Multi-Strategy Tolerance Checker for XBRL Verification

Provides flexible value comparison with multiple tolerance strategies:

1. DECIMAL STRATEGY: Use XBRL decimal precision for rounding
2. ABSOLUTE STRATEGY: Use fixed absolute tolerance for small values
3. PERCENTAGE STRATEGY: Use percentage tolerance for large values
4. AUTO STRATEGY: Select best strategy based on value magnitude and decimals

This allows processors to pick the right tolerance check for each situation.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .decimal_tolerance import DecimalTolerance, ToleranceResult
from ...constants.tolerances import (
    DEFAULT_CALCULATION_TOLERANCE,
    DEFAULT_ROUNDING_TOLERANCE,
    LARGE_VALUE_THRESHOLD,
)


@dataclass
class ToleranceConfig:
    """
    Configuration for tolerance checking.

    Allows customization of tolerance thresholds for specific use cases.
    """
    percentage_tolerance: float = DEFAULT_CALCULATION_TOLERANCE  # 1%
    absolute_tolerance: float = DEFAULT_ROUNDING_TOLERANCE  # $1
    large_value_threshold: float = LARGE_VALUE_THRESHOLD  # $1000


class ToleranceChecker:
    """
    Multi-strategy tolerance checker.

    Provides flexible value comparison with the ability to select
    different strategies based on the context.

    Usage:
        checker = ToleranceChecker()

        # Auto-select best strategy
        result = checker.check(
            expected=1000000,
            actual=999999,
            expected_decimals=-3,
            actual_decimals=-3
        )

        # Force specific strategy
        result = checker.check_percentage(
            expected=1000000,
            actual=990000,
            tolerance=0.01
        )

        # Configure custom thresholds
        config = ToleranceConfig(percentage_tolerance=0.02)
        checker = ToleranceChecker(config)
    """

    def __init__(self, config: ToleranceConfig = None):
        """
        Initialize checker with optional configuration.

        Args:
            config: ToleranceConfig with custom thresholds, or None for defaults
        """
        self.logger = logging.getLogger('tools.tolerance.tolerance_checker')
        self.config = config or ToleranceConfig()
        self._decimal_tolerance = DecimalTolerance()

    def check(
        self,
        expected: float,
        actual: float,
        expected_decimals: Optional[int] = None,
        actual_decimals: Optional[int] = None,
        strategy: str = 'auto'
    ) -> ToleranceResult:
        """
        Check if actual value is within tolerance of expected value.

        Args:
            expected: Expected value (e.g., sum of children)
            actual: Actual value (e.g., parent total)
            expected_decimals: Decimals for expected value
            actual_decimals: Decimals for actual value
            strategy: Comparison strategy ('auto', 'decimal', 'absolute', 'percentage')

        Returns:
            ToleranceResult with comparison details
        """
        if strategy == 'decimal':
            return self.check_decimal(expected, actual, expected_decimals, actual_decimals)
        elif strategy == 'absolute':
            return self.check_absolute(expected, actual)
        elif strategy == 'percentage':
            return self.check_percentage(expected, actual)
        else:  # auto
            return self.check_auto(expected, actual, expected_decimals, actual_decimals)

    def check_auto(
        self,
        expected: float,
        actual: float,
        expected_decimals: Optional[int] = None,
        actual_decimals: Optional[int] = None
    ) -> ToleranceResult:
        """
        Auto-select best tolerance strategy.

        Strategy selection:
        1. If decimals available: use decimal-based comparison
        2. For small values (< threshold): use absolute tolerance
        3. For large values: use percentage tolerance

        Args:
            expected: Expected value
            actual: Actual value
            expected_decimals: Decimals for expected value
            actual_decimals: Decimals for actual value

        Returns:
            ToleranceResult with comparison details
        """
        # If decimals are available, use decimal-based comparison
        if expected_decimals is not None or actual_decimals is not None:
            return self._decimal_tolerance.compare(
                expected, actual, expected_decimals, actual_decimals
            )

        # No decimals available - use value-based tolerance
        return self._check_value_based(expected, actual)

    def check_decimal(
        self,
        expected: float,
        actual: float,
        expected_decimals: Optional[int] = None,
        actual_decimals: Optional[int] = None
    ) -> ToleranceResult:
        """
        Check using XBRL decimal tolerance.

        Args:
            expected: Expected value
            actual: Actual value
            expected_decimals: Decimals for expected value
            actual_decimals: Decimals for actual value

        Returns:
            ToleranceResult with comparison details
        """
        return self._decimal_tolerance.compare(
            expected, actual, expected_decimals, actual_decimals
        )

    def check_absolute(
        self,
        expected: float,
        actual: float,
        tolerance: float = None
    ) -> ToleranceResult:
        """
        Check using absolute tolerance.

        Args:
            expected: Expected value
            actual: Actual value
            tolerance: Absolute tolerance (default from config)

        Returns:
            ToleranceResult with comparison details
        """
        tol = tolerance if tolerance is not None else self.config.absolute_tolerance
        difference = abs(expected - actual)
        values_equal = difference <= tol

        message = (
            f"Absolute comparison: diff={difference:.2f}, "
            f"tolerance={tol:.2f}, "
            f"{'OK' if values_equal else 'MISMATCH'}"
        )

        return ToleranceResult(
            values_equal=values_equal,
            value1_rounded=expected,
            value2_rounded=actual,
            comparison_decimals=None,
            difference=difference,
            message=message,
            strategy_used='absolute',
        )

    def check_percentage(
        self,
        expected: float,
        actual: float,
        tolerance: float = None
    ) -> ToleranceResult:
        """
        Check using percentage tolerance.

        Args:
            expected: Expected value
            actual: Actual value
            tolerance: Percentage tolerance (default from config)

        Returns:
            ToleranceResult with comparison details
        """
        tol = tolerance if tolerance is not None else self.config.percentage_tolerance
        difference = abs(expected - actual)

        # Avoid division by zero
        base = max(abs(expected), abs(actual))
        if base == 0:
            pct_diff = 0.0 if difference == 0 else float('inf')
        else:
            pct_diff = difference / base

        values_equal = pct_diff <= tol

        message = (
            f"Percentage comparison: diff={difference:,.0f} ({pct_diff:.2%}), "
            f"tolerance={tol:.1%}, "
            f"{'OK' if values_equal else 'MISMATCH'}"
        )

        return ToleranceResult(
            values_equal=values_equal,
            value1_rounded=expected,
            value2_rounded=actual,
            comparison_decimals=None,
            difference=difference,
            message=message,
            strategy_used='percentage',
        )

    def _check_value_based(
        self,
        expected: float,
        actual: float
    ) -> ToleranceResult:
        """
        Check using value-magnitude-based strategy selection.

        Small values use absolute tolerance, large values use percentage.
        """
        # Handle both zero case
        if expected == 0 and actual == 0:
            return ToleranceResult(
                values_equal=True,
                value1_rounded=expected,
                value2_rounded=actual,
                comparison_decimals=None,
                difference=0.0,
                message="Both values are zero",
                strategy_used='zero',
            )

        # Small values: use absolute tolerance
        if (abs(expected) < self.config.large_value_threshold or
                abs(actual) < self.config.large_value_threshold):
            return self.check_absolute(expected, actual)

        # Large values: use percentage tolerance
        return self.check_percentage(expected, actual)

    def is_within_tolerance(
        self,
        expected: float,
        actual: float,
        expected_decimals: Optional[int] = None,
        actual_decimals: Optional[int] = None
    ) -> bool:
        """
        Simple boolean check if values are within tolerance.

        Convenience method for when only the boolean result is needed.

        Args:
            expected: Expected value
            actual: Actual value
            expected_decimals: Decimals for expected value
            actual_decimals: Decimals for actual value

        Returns:
            True if values are within tolerance
        """
        result = self.check(expected, actual, expected_decimals, actual_decimals)
        return result.values_equal


__all__ = ['ToleranceChecker', 'ToleranceConfig']
