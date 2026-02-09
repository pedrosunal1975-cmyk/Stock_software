# Path: verification/engine/processors/stage3_verification/horizontal_checks.py
"""
Horizontal Checks - Calculation Linkbase Verification

Verifies that parent concepts equal the sum of their children
as defined in the calculation linkbase. Also checks for duplicate facts.

RESPONSIBILITY: Verify calculation relationships within the same context.
Uses binding checker to determine which calculations apply.

TOOLS USED:
- hierarchy/: BindingChecker for calculation binding rules
- calculation/: SumCalculator for weighted sum verification
- tolerance/: ToleranceChecker for value comparison
- sign/: SignLookup for sign corrections during verification
- context/: ContextGrouper, ContextGroup for context organization
"""

import logging
from typing import Optional

from ..pipeline_data import (
    PreparationResult,
    VerificationResult,
    VerificationCheck,
)

# Import tools
from ...tools.hierarchy import BindingChecker
from ...tools.calculation import SumCalculator
from ...tools.sign import SignLookup
from ...tools.context import ContextGrouper, ContextGroup

# Import constants
from ...constants.tolerances import (
    DEFAULT_CALCULATION_TOLERANCE,
    DEFAULT_ROUNDING_TOLERANCE,
    OVERSHOOT_ROUNDING_THRESHOLD,
)
from ...constants.check_names import (
    CHECK_CALCULATION_CONSISTENCY,
    CHECK_DUPLICATE_FACTS,
)
from ...constants.enums import DuplicateType


class HorizontalCheckRunner:
    """
    Runs horizontal (calculation linkbase) verification checks.

    Horizontal checks verify that parent concepts equal the weighted
    sum of their children within the same context.

    Usage:
        runner = HorizontalCheckRunner()
        runner.setup_sign_lookup(preparation)
        runner.run_checks(preparation, result)
    """

    def __init__(self):
        self.logger = logging.getLogger('processors.stage3.horizontal')

        # Initialize tools with defaults
        self._binding_checker = BindingChecker(strategy='fallback')
        self._sum_calculator = SumCalculator()
        self._sign_lookup = None

        # Configuration
        self._calculation_tolerance = DEFAULT_CALCULATION_TOLERANCE
        self._rounding_tolerance = DEFAULT_ROUNDING_TOLERANCE

    def set_calculation_tolerance(self, tolerance: float) -> None:
        """Set calculation tolerance (percentage)."""
        self._calculation_tolerance = tolerance

    def set_rounding_tolerance(self, tolerance: float) -> None:
        """Set rounding tolerance (absolute value)."""
        self._rounding_tolerance = tolerance

    def set_binding_strategy(self, strategy: str) -> None:
        """
        Set binding strategy.

        Options: 'strict', 'fallback'
        """
        self._binding_checker.set_strategy(strategy)

    def setup_sign_lookup(self, preparation: PreparationResult) -> None:
        """Set up sign lookup from prepared sign corrections."""
        self._sign_lookup = SignLookup()

        for (concept, context_id), correction in preparation.sign_corrections.items():
            self._sign_lookup.add_correction(concept, context_id, correction)

        self._sum_calculator.set_sign_lookup(self._sign_lookup)

    def run_checks(
        self,
        preparation: PreparationResult,
        result: VerificationResult
    ) -> None:
        """
        Run horizontal checks on prepared data.

        Args:
            preparation: PreparationResult from Stage 2
            result: VerificationResult to append checks to
        """
        self.logger.info(
            f"Running horizontal checks on {len(preparation.calculations)} calculations"
        )

        # Build context groups for binding checker
        context_groups = self._build_context_groups(preparation)

        for calc in preparation.calculations:
            # Find all contexts where parent exists
            parent_contexts = self._get_contexts_for_concept(
                calc.parent_concept, preparation
            )

            if not parent_contexts:
                # No facts for this calculation - skip
                continue

            # Verify in each context
            for context_id in parent_contexts:
                check = self._verify_calculation_in_context(
                    calc, context_id, context_groups, preparation
                )
                if check:
                    result.checks.append(check)
                    result.horizontal_checks.append(check)

        # Duplicate fact checks
        self._check_duplicates(preparation, result)

    def _verify_calculation_in_context(
        self,
        calc,
        context_id: str,
        context_groups: dict[str, ContextGroup],
        preparation: PreparationResult
    ) -> Optional[VerificationCheck]:
        """Verify a single calculation in a specific context."""
        ctx_group = context_groups.get(context_id)
        if not ctx_group:
            return None

        # Get dimensional and period information from PreparedContext
        # This is the ACTUAL data from the mapped filing,
        # not pattern-matching on context_id string
        ctx_info = preparation.contexts.get(context_id)
        context_is_dimensional = ctx_info.is_dimensional if ctx_info else None
        # Get actual period_key from filing data (not parsed from context_id string)
        parent_period_key = ctx_info.period_key if ctx_info else None

        # Check binding using binding checker
        binding = self._binding_checker.check_binding_with_fallback(
            context_group=ctx_group,
            parent_concept=calc.parent_concept,
            children=calc.children,
            all_facts=preparation.all_facts_by_concept,
            context_is_dimensional=context_is_dimensional,
            parent_period_key=parent_period_key,  # Use actual period from filing
        )

        if not binding.binds:
            # Calculation doesn't bind - skip (not fail)
            return VerificationCheck(
                check_name=CHECK_CALCULATION_CONSISTENCY,
                check_type='horizontal',
                passed=False,
                severity='info',
                message=f"Skipped: {binding.message}",
                concept=calc.original_parent,
                context_id=context_id,
                role=calc.role,
                details={
                    'status': 'skipped',
                    'binding_status': binding.status.value,
                    'missing_children': binding.children_missing,
                },
            )

        # Calculate sum and compare
        # Use ONLY what the XBRL filing declares:
        # - Calculation linkbase weights define the parent-child relationships
        # - Sign corrections from iXBRL sign="-" attributes (if present in filing)
        # - NO hardcoded pattern matching or semantic inference
        sum_result = self._sum_calculator.calculate_and_compare(
            children=binding.children_found,
            parent_value=binding.parent_value,
            parent_decimals=binding.parent_decimals,
            parent_concept=calc.parent_concept,
            parent_context_id=context_id,
            apply_sign_corrections=True,  # Apply sign="-" from iXBRL if declared
        )

        # Determine severity
        if sum_result.passed:
            severity = 'info'
        else:
            severity = self._determine_severity(
                sum_result.expected_sum,
                sum_result.actual_value,
                binding.children_missing
            )

        # Build children details for debugging
        children_details = []
        for child in binding.children_found:
            children_details.append({
                'concept': child.get('original_concept', child.get('concept', '')),
                'value': child.get('value'),
                'weight': child.get('weight', 1.0),
                'contribution': child.get('value', 0) * child.get('weight', 1.0),
            })

        return VerificationCheck(
            check_name=CHECK_CALCULATION_CONSISTENCY,
            check_type='horizontal',
            passed=sum_result.passed,
            severity=severity,
            message=f"{calc.original_parent}: {sum_result.message}",
            expected_value=sum_result.expected_sum,
            actual_value=sum_result.actual_value,
            difference=sum_result.difference,
            concept=calc.original_parent,
            context_id=context_id,
            role=calc.role,
            details={
                'source': calc.source,
                'children_count': len(binding.children_found),
                'missing_children': binding.children_missing,
                'sign_corrections': sum_result.sign_corrections_applied,
                'children': children_details,
            },
        )

    def _determine_severity(
        self,
        expected: float,
        actual: float,
        missing_children: list
    ) -> str:
        """Determine severity of a failed check."""
        if expected == 0 and actual == 0:
            return 'info'

        # Check for sign mismatch
        if expected != 0 and actual != 0:
            if (expected > 0) != (actual > 0):
                return 'critical'

        # Calculate magnitude difference
        exp_mag = abs(expected)
        act_mag = abs(actual)

        overshooting = exp_mag > act_mag
        undershooting = exp_mag < act_mag

        if overshooting:
            if act_mag > 0:
                overshoot_ratio = (exp_mag - act_mag) / act_mag
            else:
                overshoot_ratio = 1.0

            if overshoot_ratio <= OVERSHOOT_ROUNDING_THRESHOLD:
                return 'warning'
            else:
                return 'critical'
        elif undershooting and missing_children:
            return 'warning'
        else:
            return 'critical'

    def _check_duplicates(
        self,
        preparation: PreparationResult,
        result: VerificationResult
    ) -> None:
        """
        Check for duplicate facts with detailed diagnostics.

        Severity is determined by actual filing data, not hardcoded lists:
        - If context has dimensions (from filing), downgrade to warning
        - If source is rounding_diff, downgrade to warning
        - Otherwise critical

        This is data-driven - no hardcoded concept lists.
        """
        for key, dup_info in preparation.duplicates.items():
            concept, context_id = key.split(':', 1)

            # Check if duplicates are inconsistent (different values)
            is_inconsistent = dup_info.duplicate_type == DuplicateType.INCONSISTENT

            # Check if this context has actual dimensions from the filing
            # This is determined in preparation_processor from ctx.dimensions dict
            is_dimensional = getattr(dup_info, 'is_dimensional', False)

            # Determine severity based on actual filing data (not hardcoded lists)
            if is_inconsistent:
                source = getattr(dup_info, 'duplicate_source', None)
                source_val = source.value if source and hasattr(source, 'value') else ''

                # Rounding differences are warnings, not critical
                if source_val == 'rounding_diff':
                    severity = 'warning'
                # If context has actual dimensions from filing, downgrade to warning
                # because different values may be from different dimensional slices
                elif is_dimensional:
                    severity = 'warning'
                else:
                    severity = 'critical'
            else:
                # COMPLETE and CONSISTENT duplicates are just informational
                severity = 'info'

            # Extract values from entries
            values = [entry.value for entry in dup_info.entries]

            # Build detailed message
            dup_type_str = dup_info.duplicate_type.value if dup_info.duplicate_type else 'unknown'
            source_str = ""
            if hasattr(dup_info, 'duplicate_source') and dup_info.duplicate_source:
                source_str = f" (source: {dup_info.duplicate_source.value})"

            dimensional_str = ""
            if is_dimensional:
                dimensional_str = " [dimensional context]"

            message = (
                f"Duplicate facts for {concept}: {dup_type_str}{source_str}{dimensional_str}"
            )

            # Build comprehensive details
            details = {
                'duplicate_type': dup_type_str,
                'count': len(dup_info.entries),
                'values': values,
                'is_dimensional': is_dimensional,
            }

            # Add source if available
            if hasattr(dup_info, 'duplicate_source') and dup_info.duplicate_source:
                details['duplicate_source'] = dup_info.duplicate_source.value

            # Add value range if available
            if hasattr(dup_info, 'value_range') and dup_info.value_range[0] is not None:
                details['value_range'] = {
                    'min': dup_info.value_range[0],
                    'max': dup_info.value_range[1],
                }

            # Add diagnostics if available
            if hasattr(dup_info, 'diagnostics') and dup_info.diagnostics:
                details['diagnostics'] = dup_info.diagnostics

            check = VerificationCheck(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=not is_inconsistent,
                severity=severity,
                message=message,
                concept=concept,
                context_id=context_id,
                details=details,
            )

            result.checks.append(check)
            result.horizontal_checks.append(check)

    def _build_context_groups(
        self,
        preparation: PreparationResult
    ) -> dict[str, ContextGroup]:
        """Build ContextGroup objects for binding checker."""
        groups = {}

        for context_id, fact_group in preparation.fact_groups.items():
            # Create a ContextGroup using the grouper
            grouper = ContextGrouper()

            for concept, fact in fact_group.facts.items():
                grouper.add_fact(
                    concept=fact.concept,
                    value=fact.value,
                    context_id=fact.context_id,
                    unit=fact.unit,
                    decimals=fact.decimals,
                    original_concept=fact.original_concept,
                )

            ctx_group = grouper.get_context(context_id)
            if ctx_group:
                groups[context_id] = ctx_group

        return groups

    def _get_contexts_for_concept(
        self,
        concept: str,
        preparation: PreparationResult
    ) -> list[str]:
        """Get all context IDs where a concept exists."""
        contexts = []
        if concept in preparation.all_facts_by_concept:
            # Handle both 4-element and 5-element tuples (context_id is always first)
            for fact_tuple in preparation.all_facts_by_concept[concept]:
                ctx_id = fact_tuple[0]
                if ctx_id not in contexts:
                    contexts.append(ctx_id)
        return contexts


__all__ = ['HorizontalCheckRunner']
