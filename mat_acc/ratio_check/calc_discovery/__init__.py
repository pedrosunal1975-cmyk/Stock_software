# Path: mat_acc/ratio_check/calc_discovery/__init__.py
"""
Calculation Discovery

Extracts and maps company-declared formulas from the XBRL
calculation linkbase. Uses the company's own math to generate
dynamic fallback formulas and composite matches.

Integration point: after matching, before value population.
"""

from .formula_extractor import (
    FormulaChild,
    DeclaredFormula,
    extract_formulas,
)
from .formula_mapper import enhance_matches


__all__ = [
    'FormulaChild',
    'DeclaredFormula',
    'extract_formulas',
    'enhance_matches',
]
