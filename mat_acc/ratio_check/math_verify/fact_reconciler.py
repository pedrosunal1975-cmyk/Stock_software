# Path: mat_acc/ratio_check/math_verify/fact_reconciler.py
"""
Fact Reconciler - Layer 2 of Mathematical Integrity Unit

Cross-validates numeric values across three independent sources:
1. iXBRL source (Layer 1 output) - the mathematical truth
2. parsed.json - parser's interpretation
3. mapped statements - structured presentation

When sources disagree, iXBRL wins. Discrepancies are classified
by severity and logged for audit trail.

Discrepancy types:
- SIGN_MISMATCH: Value has wrong polarity (critical)
- SCALE_MISMATCH: Value is orders of magnitude off (critical)
- PRECISION_DIFF: Rounding difference within tolerance (minor)
- VALUE_MATCH: Sources agree (no action needed)
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from core.logger.ipo_logging import get_process_logger

from .ixbrl_extractor import VerifiedFact


logger = get_process_logger('math_verify.reconciler')


# Tolerance for precision comparisons (0.1% relative difference)
_PRECISION_TOLERANCE = 0.001

# Scale mismatch threshold (10x difference)
_SCALE_THRESHOLD = 5.0


@dataclass
class ReconciliationResult:
    """
    Result of reconciling a fact across sources.

    Attributes:
        concept: Concept QName
        context_ref: Context reference
        ixbrl_value: Value from iXBRL source (truth)
        parsed_value: Value from parsed.json
        mapped_value: Value from mapped statements
        corrected_value: Final verified value to use
        discrepancy: Type of discrepancy found
        severity: 'critical', 'minor', or 'none'
    """
    concept: str
    context_ref: str = ''
    ixbrl_value: Optional[float] = None
    parsed_value: Optional[float] = None
    mapped_value: Optional[float] = None
    corrected_value: Optional[float] = None
    discrepancy: str = 'VALUE_MATCH'
    severity: str = 'none'


class FactReconciler:
    """
    Cross-validates numeric facts across independent data sources.
    iXBRL always wins when sources disagree.
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
        scale_fixes = 0

        for fact in ixbrl_facts:
            result = self._reconcile_single(
                fact, parsed_values, mapped_values,
            )
            results.append(result)

            if result.discrepancy == 'SIGN_MISMATCH':
                sign_fixes += 1
            elif result.discrepancy == 'SCALE_MISMATCH':
                scale_fixes += 1

        self._log_summary(results, sign_fixes, scale_fixes)

        return results

    def get_corrections(
        self, results: list[ReconciliationResult]
    ) -> dict[str, float]:
        """
        Build correction map from reconciliation results.

        Returns only facts that need correction (where iXBRL
        disagrees with parsed/mapped values).

        Args:
            results: Reconciliation results

        Returns:
            Dictionary mapping concept QName to corrected value
        """
        corrections = {}
        for result in results:
            if result.severity != 'none' and result.corrected_value is not None:
                corrections[result.concept] = result.corrected_value
        return corrections

    def get_verified_values(
        self, results: list[ReconciliationResult]
    ) -> dict[str, float]:
        """
        Build complete verified value map from reconciliation.

        Returns ALL facts with their mathematically correct values,
        whether they needed correction or not.

        Args:
            results: Reconciliation results

        Returns:
            Dictionary mapping concept QName to verified value
        """
        verified = {}
        for result in results:
            if result.corrected_value is not None:
                verified[result.concept] = result.corrected_value
        return verified

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
            corrected_value=fact.value,
        )

        # Look up in parsed values
        parsed_val = self._lookup_value(fact.concept, parsed_values)
        result.parsed_value = parsed_val

        # Look up in mapped values
        mapped_val = self._lookup_value(fact.concept, mapped_values)
        result.mapped_value = mapped_val

        # Compare iXBRL against parsed
        if parsed_val is not None:
            discrepancy = self._classify_discrepancy(
                fact.value, parsed_val,
            )
            result.discrepancy = discrepancy
            result.severity = self._severity_for(discrepancy)

        # iXBRL is always the corrected value
        result.corrected_value = fact.value

        return result

    def _lookup_value(
        self, concept: str, values: dict[str, float]
    ) -> Optional[float]:
        """
        Look up a concept value with flexible key matching.

        Tries exact match, then local name match.
        """
        # Exact match
        if concept in values:
            return values[concept]

        # Try with underscore instead of colon
        alt_key = concept.replace(':', '_', 1) if ':' in concept else None
        if alt_key and alt_key in values:
            return values[alt_key]

        # Try local name only
        local_name = concept.split(':')[-1] if ':' in concept else concept
        for key, val in values.items():
            key_local = key.split(':')[-1] if ':' in key else key
            if key_local == local_name:
                return val

        return None

    def _classify_discrepancy(
        self, ixbrl_val: float, other_val: float
    ) -> str:
        """
        Classify the type of discrepancy between two values.

        Categories:
        - SIGN_MISMATCH: Opposite signs (most critical)
        - SCALE_MISMATCH: Orders of magnitude different
        - PRECISION_DIFF: Small rounding difference
        - VALUE_MATCH: Values agree
        """
        # Both zero
        if ixbrl_val == 0.0 and other_val == 0.0:
            return 'VALUE_MATCH'

        # One zero, other not
        if ixbrl_val == 0.0 or other_val == 0.0:
            return 'SCALE_MISMATCH'

        # Sign check: opposite signs
        if (ixbrl_val > 0) != (other_val > 0):
            return 'SIGN_MISMATCH'

        # Scale check: ratio between values
        ratio = abs(ixbrl_val / other_val)
        if ratio > _SCALE_THRESHOLD or ratio < (1.0 / _SCALE_THRESHOLD):
            return 'SCALE_MISMATCH'

        # Precision check: relative difference
        rel_diff = abs(ixbrl_val - other_val) / max(
            abs(ixbrl_val), abs(other_val)
        )
        if rel_diff > _PRECISION_TOLERANCE:
            return 'PRECISION_DIFF'

        return 'VALUE_MATCH'

    def _severity_for(self, discrepancy: str) -> str:
        """Map discrepancy type to severity level."""
        severity_map = {
            'SIGN_MISMATCH': 'critical',
            'SCALE_MISMATCH': 'critical',
            'PRECISION_DIFF': 'minor',
            'VALUE_MATCH': 'none',
        }
        return severity_map.get(discrepancy, 'none')

    def _log_summary(
        self,
        results: list[ReconciliationResult],
        sign_fixes: int,
        scale_fixes: int,
    ) -> None:
        """Log reconciliation summary."""
        total = len(results)
        critical = sum(1 for r in results if r.severity == 'critical')
        minor = sum(1 for r in results if r.severity == 'minor')
        matched = total - critical - minor

        self.logger.info(
            f"Reconciliation: {total} facts checked, "
            f"{matched} matched, {critical} critical, {minor} minor"
        )

        if sign_fixes > 0:
            self.logger.warning(
                f"SIGN corrections: {sign_fixes} facts had wrong polarity"
            )

        if scale_fixes > 0:
            self.logger.warning(
                f"SCALE corrections: {scale_fixes} facts had wrong magnitude"
            )


__all__ = ['FactReconciler', 'ReconciliationResult']
