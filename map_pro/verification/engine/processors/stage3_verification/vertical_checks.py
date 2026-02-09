# Path: verification/engine/processors/stage3_verification/vertical_checks.py
"""
Vertical Checks - Cross-Statement Consistency Verification

Verifies that the same concept reported in different contexts
for the same period has consistent values. For example, Net Income
appearing in both Income Statement and Cash Flow Statement should match.

RESPONSIBILITY: Verify cross-statement consistency for same concept/period.
Uses period_key from preparation.contexts (built by Stage 2 from actual dates).

TOOLS USED:
- tolerance/: ToleranceChecker for value comparison with decimal handling
- context/: For context grouping and period determination

IMPORTANT:
- Only compares values within the SAME period AND SAME dimensional signature
- Dimensional signatures are extracted from each filing's actual dimension data
- NO hardcoded concept lists - dimensions are detected from filing data
- Facts with different dimensional qualifiers are NEVER compared
"""

import logging
from typing import Optional

from ..pipeline_data import (
    PreparationResult,
    VerificationResult,
    VerificationCheck,
)

# Import tools
from ...tools.tolerance import ToleranceChecker

# Import constants
from ...constants.tolerances import (
    CROSS_STATEMENT_TOLERANCE,
    MIN_CROSS_STATEMENT_CONTEXTS,
)
from ...constants.check_names import CHECK_CROSS_STATEMENT_CONSISTENCY


class VerticalCheckRunner:
    """
    Runs vertical (cross-statement consistency) verification checks.

    Vertical checks verify that the same concept reported in different
    contexts for the same period has consistent values.

    IMPORTANT:
    - Only compares facts with IDENTICAL dimensional qualifiers
    - Dimensional qualifiers are read from each filing's actual data
    - NO hardcoded concept lists - fully data-driven

    Usage:
        runner = VerticalCheckRunner()
        runner.run_checks(preparation, result)
    """

    def __init__(self):
        self.logger = logging.getLogger('processors.stage3.vertical')
        self._tolerance_checker = ToleranceChecker()
        self._cross_statement_tolerance = CROSS_STATEMENT_TOLERANCE

    def set_cross_statement_tolerance(self, tolerance: float) -> None:
        """Set cross-statement tolerance (percentage)."""
        self._cross_statement_tolerance = tolerance

    def run_checks(
        self,
        preparation: PreparationResult,
        result: VerificationResult
    ) -> None:
        """
        Run vertical checks on prepared data.

        Args:
            preparation: PreparationResult from Stage 2
            result: VerificationResult to append checks to
        """
        self.logger.info("Running vertical checks")

        # Find concepts that appear in multiple comparable contexts
        cross_statement_concepts = self._find_cross_statement_concepts(preparation)

        if not cross_statement_concepts:
            self.logger.info("No cross-statement concepts found")
            return

        self.logger.info(
            f"Checking {len(cross_statement_concepts)} cross-statement concepts"
        )

        # Check each concept for cross-statement consistency
        for concept in cross_statement_concepts:
            checks = self._check_concept_cross_statement(concept, preparation)
            for check in checks:
                result.checks.append(check)
                result.vertical_checks.append(check)

    def _get_dimensional_signature(self, ctx_id: str, ctx_info) -> str:
        """
        Create a signature based on actual dimensional data from the filing.

        Contexts with no dimensions get signature 'default'.
        Contexts with dimensions get a signature based on their actual
        axis/member combinations from the filing data.

        Args:
            ctx_id: Context identifier
            ctx_info: PreparedContext with dimensional info

        Returns:
            String signature for grouping comparable contexts
        """
        if not ctx_info:
            return 'default'

        # Get actual dimensions from the filing
        dimensions = getattr(ctx_info, 'dimensions', {}) or {}

        if not dimensions:
            return 'default'

        # Create deterministic signature from actual dimension data
        # Sort to ensure consistent ordering
        dim_items = sorted(dimensions.items())
        return '|'.join(f"{k}={v}" for k, v in dim_items)

    def _find_cross_statement_concepts(
        self,
        preparation: PreparationResult
    ) -> list[str]:
        """
        Find concepts that appear in multiple comparable contexts.

        A concept is comparable across contexts if:
        - It appears in multiple contexts for the same period
        - Those contexts have the SAME dimensional signature

        No hardcoded lists - dimensional grouping is based entirely
        on actual dimension data from the filing.

        Args:
            preparation: PreparationResult with all facts

        Returns:
            List of concept names suitable for cross-statement checks
        """
        cross_statement = []

        for concept, facts in preparation.all_facts_by_concept.items():
            if len(facts) < MIN_CROSS_STATEMENT_CONTEXTS:
                continue

            # Get context IDs for this concept
            # Handle both 4-element and 5-element tuples (context_id is always first)
            context_ids = [fact_tuple[0] for fact_tuple in facts]

            # Group by period AND dimensional signature
            period_dim_groups = self._group_contexts_by_period_and_dimensions(
                context_ids, preparation.contexts
            )

            # Check if any group has multiple comparable contexts
            # (same period AND same dimensional signature)
            for group_key, group_contexts in period_dim_groups.items():
                if len(group_contexts) >= MIN_CROSS_STATEMENT_CONTEXTS:
                    cross_statement.append(concept)
                    break

        return cross_statement

    def _group_contexts_by_period_and_dimensions(
        self,
        context_ids: list[str],
        contexts: dict
    ) -> dict[str, list[str]]:
        """
        Group context IDs by period_key AND dimensional signature.

        This ensures only truly comparable contexts are grouped together:
        - Same period (from period_key)
        - Same dimensional qualifiers (from actual filing data)

        Args:
            context_ids: List of context_id strings
            contexts: dict[context_id, PreparedContext] from preparation

        Returns:
            Dictionary mapping group_key -> list of context_ids
        """
        groups = {}

        for ctx_id in context_ids:
            ctx_info = contexts.get(ctx_id)

            if ctx_info:
                period_key = ctx_info.period_key
            else:
                period_key = ctx_id

            # Get dimensional signature from actual filing data
            dim_signature = self._get_dimensional_signature(ctx_id, ctx_info)

            # Create compound grouping key: period + dimensions
            group_key = f"{period_key}|{dim_signature}"

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(ctx_id)

        return groups

    def _check_concept_cross_statement(
        self,
        concept: str,
        preparation: PreparationResult
    ) -> list[VerificationCheck]:
        """
        Check cross-statement consistency for a single concept.

        Only compares facts within the same period AND with the same
        dimensional signature. This is entirely data-driven - no
        hardcoded concept lists.

        Args:
            concept: Normalized concept name
            preparation: PreparationResult with all facts

        Returns:
            List of VerificationCheck results
        """
        checks = []
        facts = preparation.all_facts_by_concept.get(concept, [])

        if len(facts) < MIN_CROSS_STATEMENT_CONTEXTS:
            return checks

        # Build context -> (value, unit, decimals) mapping
        # Handle both 4-element and 5-element tuples
        context_values = {}
        for fact_tuple in facts:
            ctx_id = fact_tuple[0]
            value = fact_tuple[1]
            unit = fact_tuple[2]
            decimals = fact_tuple[3]
            if value is not None:
                context_values[ctx_id] = (value, unit, decimals)

        # Group contexts by period AND dimensions
        context_ids = list(context_values.keys())
        period_dim_groups = self._group_contexts_by_period_and_dimensions(
            context_ids, preparation.contexts
        )

        # Check each comparable group
        for group_key, group_contexts in period_dim_groups.items():
            if len(group_contexts) < MIN_CROSS_STATEMENT_CONTEXTS:
                continue

            # Extract period_key and dim_signature from group_key
            parts = group_key.split('|', 1)
            period_key = parts[0]
            dim_signature = parts[1] if len(parts) > 1 else 'default'

            # Get values for this group
            group_values = []
            for ctx_id in group_contexts:
                if ctx_id in context_values:
                    value, unit, decimals = context_values[ctx_id]
                    group_values.append((ctx_id, value, unit, decimals))

            if len(group_values) < MIN_CROSS_STATEMENT_CONTEXTS:
                continue

            # Compare all values to reference
            check = self._compare_period_values(
                concept, period_key, dim_signature, group_values
            )
            if check:
                checks.append(check)

        return checks

    def _compare_period_values(
        self,
        concept: str,
        period_key: str,
        dim_signature: str,
        period_values: list[tuple[str, float, str, int]]
    ) -> Optional[VerificationCheck]:
        """
        Compare values within a period and dimensional group for consistency.

        Args:
            concept: Concept name
            period_key: Period identifier
            dim_signature: Dimensional signature (or 'default')
            period_values: List of (context_id, value, unit, decimals) tuples

        Returns:
            VerificationCheck result
        """
        if not period_values:
            return None

        # Use first value as reference
        ref_ctx, ref_value, ref_unit, ref_decimals = period_values[0]

        # Track differences
        all_match = True
        max_diff = 0.0
        max_diff_pct = 0.0
        mismatched_contexts = []

        for ctx_id, value, unit, decimals in period_values[1:]:
            # Use tolerance checker for comparison
            tol_result = self._tolerance_checker.check(
                expected=ref_value,
                actual=value,
                expected_decimals=ref_decimals,
                actual_decimals=decimals,
            )

            if not tol_result.values_equal:
                all_match = False
                diff = abs(value - ref_value)
                if diff > max_diff:
                    max_diff = diff

                # Calculate percentage difference
                if ref_value != 0:
                    diff_pct = diff / abs(ref_value)
                    if diff_pct > max_diff_pct:
                        max_diff_pct = diff_pct

                mismatched_contexts.append({
                    'context_id': ctx_id,
                    'value': value,
                    'difference': diff,
                })

        # Determine severity
        if all_match:
            severity = 'info'
            message = (
                f"{concept}: values consistent across "
                f"{len(period_values)} contexts for {period_key}"
            )
        else:
            if max_diff_pct > self._cross_statement_tolerance:
                severity = 'critical'
            else:
                severity = 'warning'
            message = (
                f"{concept}: value mismatch in {period_key}, "
                f"ref={ref_value:,.0f}, max_diff={max_diff:,.0f} ({max_diff_pct:.2%})"
            )

        return VerificationCheck(
            check_name=CHECK_CROSS_STATEMENT_CONSISTENCY,
            check_type='vertical',
            passed=all_match,
            severity=severity,
            message=message,
            expected_value=ref_value,
            actual_value=period_values[-1][1] if not all_match else ref_value,
            difference=max_diff if not all_match else 0.0,
            concept=concept,
            context_id=ref_ctx,
            details={
                'period_key': period_key,
                'dim_signature': dim_signature,
                'contexts_checked': len(period_values),
                'mismatched_contexts': mismatched_contexts if not all_match else [],
                'reference_context': ref_ctx,
            },
        )


__all__ = ['VerticalCheckRunner']
