# Path: mat_acc/ratio_check/math_verify/fact_reconciler.py
"""
Fact Reconciler - Layer 2 of Mathematical Integrity Unit

Cross-validates numeric values across independent sources:
1. iXBRL source (Layer 1 output) - the mathematical truth
2. parsed.json - parser's interpretation
3. mapped statements - structured presentation

KEY INSIGHT: iXBRL extractor applies 10^scale to get absolute
values, while parsed.json stores values in the filing's display
scale (thousands, millions, etc.). This means a 1000x difference
is EXPECTED when scale=3, not a real discrepancy.

The reconciler normalizes for scale before comparing, and only
produces corrections for SIGN mismatches (where the parser missed
the sign="-" attribute). Corrections preserve the parsed value's
magnitude and only fix the polarity.
"""

import math
from dataclasses import dataclass
from typing import Optional

from core.logger.ipo_logging import get_process_logger

from .ixbrl_extractor import VerifiedFact


logger = get_process_logger('math_verify.reconciler')


# Tolerance for precision comparisons (0.5% relative difference)
_PRECISION_TOLERANCE = 0.005

# How close log10(ratio) must be to an integer to count as scale
_SCALE_DETECT_TOLERANCE = 0.15


@dataclass
class ReconciliationResult:
    """Result of reconciling a fact across sources."""
    concept: str
    context_ref: str = ''
    ixbrl_value: Optional[float] = None
    parsed_value: Optional[float] = None
    mapped_value: Optional[float] = None
    corrected_value: Optional[float] = None
    discrepancy: str = 'VALUE_MATCH'
    severity: str = 'none'
    scale_factor: int = 0


class FactReconciler:
    """
    Cross-validates numeric facts across independent data sources.

    Scale-aware: detects power-of-10 differences between iXBRL
    (absolute values) and parsed (filing-scale values).

    Sign-correcting: when iXBRL and parsed disagree on sign,
    the parsed value is negated (preserving its magnitude).
    """

    def __init__(self):
        """Initialize fact reconciler."""
        self.logger = get_process_logger('math_verify.reconciler')

    def reconcile(
        self,
        ixbrl_facts: list[VerifiedFact],
        parsed_values: dict[str, float] = None,
        mapped_values: dict[str, float] = None,
    ) -> list[ReconciliationResult]:
        """
        Reconcile facts across all available sources.

        Args:
            ixbrl_facts: Verified facts from Layer 1
            parsed_values: concept -> value from parsed.json
            mapped_values: concept -> value from mapped statements

        Returns:
            List of reconciliation results
        """
        parsed_values = parsed_values or {}
        mapped_values = mapped_values or {}

        results = []
        sign_fixes = 0
        scale_diffs = 0

        for fact in ixbrl_facts:
            result = self._reconcile_single(
                fact, parsed_values, mapped_values,
            )
            results.append(result)

            if result.discrepancy == 'SIGN_MISMATCH':
                sign_fixes += 1
            elif result.discrepancy == 'SCALE_DIFF':
                scale_diffs += 1

        self._log_summary(results, sign_fixes, scale_diffs)

        return results

    def get_corrections(
        self, results: list[ReconciliationResult]
    ) -> dict[str, float]:
        """
        Build correction map for sign mismatches only.

        Only returns corrections where the parsed value has the
        wrong sign (parser missed sign="-" attribute). The
        corrected value preserves the parsed magnitude.

        Returns:
            Dictionary mapping concept QName to corrected value
        """
        corrections = {}
        for result in results:
            if result.discrepancy != 'SIGN_MISMATCH':
                continue
            if result.corrected_value is None:
                continue
            corrections[result.concept] = result.corrected_value
        return corrections

    def get_summary(
        self, results: list[ReconciliationResult]
    ) -> dict:
        """Produce summary statistics from reconciliation."""
        total = len(results)
        sign_fixes = sum(
            1 for r in results if r.discrepancy == 'SIGN_MISMATCH'
        )
        scale_diffs = sum(
            1 for r in results if r.discrepancy == 'SCALE_DIFF'
        )
        matched = sum(
            1 for r in results if r.discrepancy == 'VALUE_MATCH'
        )
        no_parsed = sum(
            1 for r in results if r.discrepancy == 'NO_PARSED'
        )

        return {
            'total': total,
            'sign_corrections': sign_fixes,
            'scale_diffs': scale_diffs,
            'value_matches': matched,
            'no_parsed_value': no_parsed,
        }

    def _reconcile_single(
        self,
        fact: VerifiedFact,
        parsed_values: dict[str, float],
        mapped_values: dict[str, float],
    ) -> ReconciliationResult:
        """Reconcile a single fact against other sources."""
        result = ReconciliationResult(
            concept=fact.concept,
            context_ref=fact.context_ref,
            ixbrl_value=fact.value,
        )

        # Look up in parsed values
        parsed_val = self._lookup_value(fact.concept, parsed_values)
        result.parsed_value = parsed_val

        # Look up in mapped values
        mapped_val = self._lookup_value(fact.concept, mapped_values)
        result.mapped_value = mapped_val

        # No parsed value to compare against
        if parsed_val is None:
            result.discrepancy = 'NO_PARSED'
            result.severity = 'none'
            return result

        # Both zero - perfect match
        if fact.value == 0.0 and parsed_val == 0.0:
            result.discrepancy = 'VALUE_MATCH'
            result.corrected_value = parsed_val
            return result

        # One zero, other not - unusual but not actionable
        if fact.value == 0.0 or parsed_val == 0.0:
            result.discrepancy = 'ZERO_NONZERO'
            result.severity = 'minor'
            result.corrected_value = parsed_val
            return result

        # Detect scale factor (power of 10 between iXBRL and parsed)
        scale_factor = self._detect_scale_factor(
            fact.value, parsed_val,
        )
        result.scale_factor = scale_factor

        # Normalize iXBRL to parsed scale for comparison
        if scale_factor != 0:
            normalized = fact.value / (10 ** scale_factor)
        else:
            normalized = fact.value

        # Compare signs after normalization
        ixbrl_positive = normalized >= 0
        parsed_positive = parsed_val >= 0

        if ixbrl_positive != parsed_positive:
            result.discrepancy = 'SIGN_MISMATCH'
            result.severity = 'critical'
            result.corrected_value = -parsed_val
            return result

        # Signs agree - scale difference is expected (not an error)
        if scale_factor != 0:
            result.discrepancy = 'SCALE_DIFF'
            result.severity = 'none'
            result.corrected_value = parsed_val
            return result

        # Same scale, same sign - check precision
        denom = max(abs(normalized), abs(parsed_val))
        rel_diff = abs(normalized - parsed_val) / denom

        if rel_diff > _PRECISION_TOLERANCE:
            result.discrepancy = 'PRECISION_DIFF'
            result.severity = 'minor'
        else:
            result.discrepancy = 'VALUE_MATCH'

        result.corrected_value = parsed_val
        return result

    def _lookup_value(
        self, concept: str, values: dict[str, float]
    ) -> Optional[float]:
        """Look up a concept value with flexible key matching."""
        # Exact match
        if concept in values:
            return values[concept]

        # Try with underscore instead of colon
        if ':' in concept:
            alt_key = concept.replace(':', '_', 1)
            if alt_key in values:
                return values[alt_key]

        # Try local name only
        local_name = concept.split(':')[-1] if ':' in concept else concept
        for key, val in values.items():
            key_local = key.split(':')[-1] if ':' in key else key
            if key_local == local_name:
                return val

        return None

    def _detect_scale_factor(
        self, ixbrl_val: float, parsed_val: float
    ) -> int:
        """
        Detect power-of-10 difference between values.

        Returns the integer N where ixbrl_val ~ parsed_val * 10^N.
        Returns 0 if values are in the same scale.
        """
        if ixbrl_val == 0 or parsed_val == 0:
            return 0

        ratio = abs(ixbrl_val / parsed_val)
        if ratio == 0:
            return 0

        log_ratio = math.log10(ratio)
        rounded = round(log_ratio)

        # Scale factor must be non-zero and close to an integer
        if rounded == 0:
            return 0
        if abs(log_ratio - rounded) < _SCALE_DETECT_TOLERANCE:
            return rounded

        return 0

    def _log_summary(
        self,
        results: list[ReconciliationResult],
        sign_fixes: int,
        scale_diffs: int,
    ) -> None:
        """Log reconciliation summary."""
        total = len(results)
        matched = sum(
            1 for r in results if r.discrepancy == 'VALUE_MATCH'
        )

        self.logger.info(
            f"Reconciliation: {total} facts, "
            f"{matched} matched, {sign_fixes} sign corrections, "
            f"{scale_diffs} scale diffs (expected)"
        )

        if sign_fixes > 0:
            self.logger.warning(
                f"SIGN corrections needed: {sign_fixes} facts "
                f"have wrong polarity in parsed data"
            )


__all__ = ['FactReconciler', 'ReconciliationResult']
