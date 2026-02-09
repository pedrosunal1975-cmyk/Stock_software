# Path: verification/engine/checks_v2/tools/calculation/__init__.py
"""
Calculation Tools for XBRL Verification

Provides weight handling and sum calculation for verification.

Modules:
- weight_handler: Handle XBRL calculation weights
- sum_calculator: Calculate weighted sums and compare to totals

XBRL CALCULATION WEIGHTS:
- Weight of 1.0 means ADD to sum
- Weight of -1.0 means SUBTRACT from sum

Usage:
    from verification.engine.checks_v2.tools.calculation import (
        WeightHandler,
        SumCalculator,
        SumResult,
    )

    # Handle weights
    handler = WeightHandler()
    contribution = handler.apply_weight(1000000, -1.0)

    # Calculate sums
    calculator = SumCalculator()
    result = calculator.calculate_and_compare(
        children=children,
        parent_value=1000000
    )
"""

from .weight_handler import WeightHandler
from .sum_calculator import SumCalculator, SumResult


__all__ = [
    'WeightHandler',
    'SumCalculator',
    'SumResult',
]
