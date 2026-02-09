# Path: verification/engine/checks_v2/tools/calculation/sum_calculator.py
"""
Sum Calculator for XBRL Verification

Calculates weighted sums from child contributions.

Techniques consolidated from:
- checks/verifiers/calculation_verifier.py

DESIGN: Stateless tool for calculating sums with weights.
Uses sign tools for corrections and tolerance tools for comparison.

SIGN CORRECTION STRATEGY:
1. iXBRL sign="-" corrections (from SignLookup) - explicit from document
2. Semantic sign inference (from SemanticSignInferrer) - fallback for deficit patterns

The semantic inference handles cases like RetainedEarningsAccumulatedDeficit where:
- Company has accumulated losses (deficit)
- Value is filed as positive (the absolute amount)
- Semantically it should be negative for equity calculations to work
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from .weight_handler import WeightHandler
from ..sign.sign_lookup import SignLookup
from ..sign.semantic_inferrer import SemanticSignInferrer
from ..tolerance.decimal_tolerance import DecimalTolerance


@dataclass
class SumResult:
    """
    Result of calculating a weighted sum.

    Attributes:
        expected_sum: Calculated sum from children
        actual_value: Parent/total value to compare
        difference: expected_sum - actual_value
        passed: Whether values match within tolerance
        min_decimals: Minimum decimal precision used
        children_contributions: List of (concept, value, weight, contribution)
        sign_corrections_applied: Number of sign corrections applied
        message: Human-readable result message
    """
    expected_sum: float
    actual_value: float
    difference: float
    passed: bool
    min_decimals: Optional[int] = None
    children_contributions: list = field(default_factory=list)
    sign_corrections_applied: int = 0
    message: str = ""


class SumCalculator:
    """
    Calculates weighted sums from child contributions.

    Provides:
    - Weighted sum calculation
    - Sign correction application (iXBRL and semantic)
    - Tolerance comparison

    This is a STATELESS tool that can use sign lookup and tolerance tools.

    Sign Correction Strategy:
    1. First check SignLookup for explicit iXBRL sign="-" corrections
    2. If no explicit correction, use SemanticSignInferrer for deficit patterns
    3. Semantic inference applies to concepts like AccumulatedDeficit with positive values

    Usage:
        calculator = SumCalculator()
        calculator.enable_semantic_inference()  # Enable semantic fallback

        # Calculate sum from children
        children = [
            {'concept': 'liabilities', 'value': 500000, 'weight': 1.0, 'decimals': -3},
            {'concept': 'equity', 'value': 500000, 'weight': 1.0, 'decimals': -3},
        ]
        parent_value = 1000000

        result = calculator.calculate_and_compare(
            children=children,
            parent_value=parent_value,
            parent_decimals=-3,
            apply_semantic_corrections=True
        )

        if result.passed:
            print("Calculation verified")
    """

    def __init__(
        self,
        sign_lookup: SignLookup = None,
        decimal_tolerance: DecimalTolerance = None,
        semantic_inferrer: SemanticSignInferrer = None
    ):
        """
        Initialize the sum calculator.

        Args:
            sign_lookup: Optional SignLookup for iXBRL sign corrections
            decimal_tolerance: Optional DecimalTolerance for comparisons
            semantic_inferrer: Optional SemanticSignInferrer for fallback
        """
        self.logger = logging.getLogger('tools.calculation.sum_calculator')
        self._weight_handler = WeightHandler()
        self._sign_lookup = sign_lookup
        self._decimal_tolerance = decimal_tolerance or DecimalTolerance()
        self._semantic_inferrer = semantic_inferrer

    def set_sign_lookup(self, sign_lookup: SignLookup) -> None:
        """Set the sign lookup for iXBRL corrections."""
        self._sign_lookup = sign_lookup

    def set_semantic_inferrer(self, inferrer: SemanticSignInferrer) -> None:
        """Set the semantic inferrer for fallback corrections."""
        self._semantic_inferrer = inferrer

    def enable_semantic_inference(self, deficit_only: bool = True) -> None:
        """
        Enable semantic sign inference with default inferrer.

        Args:
            deficit_only: If True (default), only use deficit patterns.
                         This is safer for calculation verification as it won't
                         incorrectly match concepts like NetIncomeLoss.
        """
        if not self._semantic_inferrer:
            self._semantic_inferrer = SemanticSignInferrer(deficit_only=deficit_only)

    def calculate_sum(
        self,
        children: list[dict],
        apply_sign_corrections: bool = True,
        apply_semantic_corrections: bool = False
    ) -> tuple[float, list[dict], int]:
        """
        Calculate weighted sum from children.

        Args:
            children: List of dicts with 'concept', 'value', 'weight', 'context_id'
            apply_sign_corrections: Whether to apply iXBRL sign corrections
            apply_semantic_corrections: Whether to apply semantic sign inference
                                        (for deficit patterns with positive values)

        Returns:
            Tuple of (sum, contributions_list, sign_corrections_count)
        """
        total = 0.0
        contributions = []
        corrections_applied = 0

        for child in children:
            concept = child.get('concept', '')
            original_concept = child.get('original_concept', concept)
            value = child.get('value', 0.0)
            weight = child.get('weight', 1.0)
            context_id = child.get('context_id', '')
            decimals = child.get('decimals')

            sign_corrected = False

            # First try iXBRL sign correction if enabled and lookup available
            if apply_sign_corrections and self._sign_lookup:
                correction = self._sign_lookup.get_correction(
                    original_concept, context_id
                )
                if correction == -1:
                    value = -abs(value)
                    corrections_applied += 1
                    sign_corrected = True

            # Fallback to semantic inference if:
            # - Semantic corrections enabled
            # - No iXBRL correction was applied
            # - Value is positive (semantic inference only negates positive values)
            # - Semantic inferrer is available
            if (apply_semantic_corrections and
                not sign_corrected and
                value > 0 and
                self._semantic_inferrer):
                # Check if concept name suggests negative value
                inferred_sign = self._semantic_inferrer.infer(original_concept)
                if inferred_sign == -1:
                    self.logger.info(
                        f"Semantic sign correction: '{original_concept}' "
                        f"value {value:,.0f} -> {-value:,.0f} (deficit pattern)"
                    )
                    value = -abs(value)
                    corrections_applied += 1
                    sign_corrected = True

            # Apply weight
            weighted = self._weight_handler.apply_weight(value, weight)
            total += weighted

            contributions.append({
                'concept': concept,
                'original_concept': original_concept,
                'value': child.get('value'),
                'weight': weight,
                'contribution': weighted,
                'decimals': decimals,
                'sign_corrected': sign_corrected,
            })

        return total, contributions, corrections_applied

    def calculate_and_compare(
        self,
        children: list[dict],
        parent_value: float,
        parent_decimals: Optional[int] = None,
        parent_concept: str = None,
        parent_context_id: str = None,
        apply_sign_corrections: bool = True,
        apply_semantic_corrections: bool = False
    ) -> SumResult:
        """
        Calculate sum and compare to parent value.

        Args:
            children: List of child dicts
            parent_value: Expected total value
            parent_decimals: Parent decimal precision
            parent_concept: Parent concept for sign correction
            parent_context_id: Parent context for sign correction
            apply_sign_corrections: Whether to apply iXBRL sign corrections
            apply_semantic_corrections: Whether to apply semantic sign inference
                                        (for deficit patterns with positive values)

        Returns:
            SumResult with comparison
        """
        # Calculate sum
        expected_sum, contributions, corrections = self.calculate_sum(
            children, apply_sign_corrections, apply_semantic_corrections
        )

        # Apply sign correction to parent if needed
        actual_value = parent_value
        if apply_sign_corrections and self._sign_lookup and parent_concept:
            correction = self._sign_lookup.get_correction(
                parent_concept, parent_context_id or ''
            )
            if correction == -1:
                actual_value = -abs(parent_value)
                corrections += 1

        # Get minimum decimals for comparison
        min_decimals = parent_decimals
        for child in children:
            child_decimals = child.get('decimals')
            if child_decimals is not None:
                if min_decimals is None:
                    min_decimals = child_decimals
                else:
                    min_decimals = min(min_decimals, child_decimals)

        # Compare using decimal tolerance
        tolerance_result = self._decimal_tolerance.is_within_tolerance(
            expected=expected_sum,
            actual=actual_value,
            expected_decimals=min_decimals,
            actual_decimals=parent_decimals,
        )

        passed = tolerance_result.values_equal
        difference = tolerance_result.difference

        # Build message
        if passed:
            message = f"expected {expected_sum:,.0f}, found {actual_value:,.0f} OK"
        else:
            message = f"expected {expected_sum:,.0f}, found {actual_value:,.0f}, diff {difference:,.0f}"

        if corrections > 0:
            message += f" ({corrections} sign corrections)"

        return SumResult(
            expected_sum=expected_sum,
            actual_value=actual_value,
            difference=difference,
            passed=passed,
            min_decimals=min_decimals,
            children_contributions=contributions,
            sign_corrections_applied=corrections,
            message=message,
        )

    def get_min_decimals(self, children: list[dict], parent_decimals: Optional[int]) -> Optional[int]:
        """
        Get minimum decimals from children and parent.

        Args:
            children: List of child dicts
            parent_decimals: Parent decimal precision

        Returns:
            Minimum decimals value
        """
        min_d = parent_decimals
        for child in children:
            d = child.get('decimals')
            if d is not None:
                if min_d is None:
                    min_d = d
                else:
                    min_d = min(min_d, d)
        return min_d


__all__ = ['SumCalculator', 'SumResult']
