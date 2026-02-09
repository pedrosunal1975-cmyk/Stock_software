# Path: verification/engine/checks_v2/tools/tolerance/__init__.py
"""
Tolerance Tools for XBRL Verification

Provides decimal tolerance and value comparison across all processing stages.

Key Components:
- DecimalTolerance: XBRL-compliant decimal rounding and comparison
- ToleranceChecker: Multi-strategy value tolerance checking
- ToleranceResult: Structured result from tolerance comparisons

XBRL Decimal Rules (per specification and DQC Global Rule Logic):
1. Compare numbers at the LOWEST decimal precision between values
2. Use "round half to nearest even" (banker's rounding)
3. Negative decimals indicate rounding to powers of 10 (e.g., -6 = millions)
"""

from .decimal_tolerance import DecimalTolerance, ToleranceResult
from .tolerance_checker import ToleranceChecker

__all__ = [
    'DecimalTolerance',
    'ToleranceResult',
    'ToleranceChecker',
]
