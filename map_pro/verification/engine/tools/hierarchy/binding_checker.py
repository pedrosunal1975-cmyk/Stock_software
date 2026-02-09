# Path: verification/engine/checks_v2/tools/hierarchy/binding_checker.py
"""
Binding Checker for XBRL Verification

Determines whether a calculation should "bind" (be verified) based on
XBRL 2.1 and Calculations 1.1 specification rules.

Techniques consolidated from:
- checks/binding/binding_checker.py

BINDING RULES (from XBRL spec + completeness enhancement):
A calculation binds (is checked) ONLY when:
1. The summation item (parent/total) EXISTS in the context
2. At least one contributing item (child) EXISTS in the same context
3. NO inconsistent duplicate facts exist for parent or children
4. All items are c-equal (same context_id)
5. All items are u-equal (same unit)
6. COMPLETENESS: At least threshold % of children found

If ANY of these conditions is not met, the calculation is SKIPPED (not failed).
Skipping is different from failing - it means the check cannot be performed.

DESIGN: Stateless tool for checking binding conditions.
"""

import logging
from typing import Optional

from ..context.grouper import ContextGroup
from ..context.classifier import ContextClassifier
from ..context.matcher import ContextMatcher
from ..fact.fact_finder import FactFinder
from .binding_result import BindingResult
from ...constants.enums import BindingStatus, DuplicateType
from ...constants.tolerances import CALCULATION_COMPLETENESS_THRESHOLD


class BindingChecker:
    """
    Checks if calculations should bind per XBRL specification.

    A calculation binds only when all required conditions are met.
    If a calculation doesn't bind, it is SKIPPED (not failed).

    This is a critical distinction:
    - SKIP: Cannot verify because data is incomplete or invalid
    - PASS: Verified successfully, values match
    - FAIL: Verified and found inconsistency

    This is a STATELESS tool that operates on context groups.

    Strategies:
    - 'strict': Exact C-Equal matching only
    - 'fallback': Allow dimensional fallback for missing children

    Usage:
        checker = BindingChecker()

        # Check if Assets = Liabilities + Equity binds in context c-1
        result = checker.check_binding(
            context_group=context,
            parent_concept='assets',
            children=[('liabilities', 1.0), ('stockholdersequity', 1.0)]
        )

        if result.binds:
            # Proceed with verification
            pass
        else:
            # Skip this calculation
            print(f"Skipped: {result.message}")
    """

    def __init__(self, strategy: str = 'fallback'):
        """
        Initialize the binding checker.

        Args:
            strategy: Binding strategy ('strict' or 'fallback')
        """
        self.logger = logging.getLogger('tools.hierarchy.binding_checker')
        self._strategy = strategy
        self._classifier = ContextClassifier()
        self._matcher = ContextMatcher()
        self._completeness_threshold = CALCULATION_COMPLETENESS_THRESHOLD

    def set_strategy(self, strategy: str) -> None:
        """
        Set the binding strategy.

        Args:
            strategy: 'strict' or 'fallback'
        """
        if strategy not in ('strict', 'fallback'):
            raise ValueError(f"Unknown strategy: {strategy}")
        self._strategy = strategy

    def set_completeness_threshold(self, threshold: float) -> None:
        """
        Set the completeness threshold.

        Args:
            threshold: Minimum fraction of children required (0.0 to 1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        self._completeness_threshold = threshold

    def check_binding(
        self,
        context_group: ContextGroup,
        parent_concept: str,
        children: list[tuple[str, float]],
        duplicate_info: dict = None
    ) -> BindingResult:
        """
        Check if a calculation binds in a given context.

        Args:
            context_group: ContextGroup with facts for this context
            parent_concept: Normalized parent concept name
            children: List of (child_concept, weight) tuples from calculation linkbase
            duplicate_info: Optional dict of concept -> DuplicateInfo for checking

        Returns:
            BindingResult indicating whether calculation binds and why
        """
        # Rule 1: Parent must exist
        if not context_group.has(parent_concept):
            return BindingResult(
                binds=False,
                status=BindingStatus.SKIP_NO_PARENT,
                message=f"Parent '{parent_concept}' not found in context {context_group.context_id}",
            )

        parent_value = context_group.get_value(parent_concept)
        parent_unit = context_group.get_unit(parent_concept)
        parent_decimals = context_group.get_decimals(parent_concept)

        # Rule 3: Check for inconsistent duplicates (if info provided)
        if duplicate_info and parent_concept in duplicate_info:
            info = duplicate_info[parent_concept]
            if hasattr(info, 'duplicate_type') and info.duplicate_type == DuplicateType.INCONSISTENT:
                return BindingResult(
                    binds=False,
                    status=BindingStatus.SKIP_INCONSISTENT_PARENT,
                    parent_value=None,
                    message=f"Parent '{parent_concept}' has inconsistent duplicates",
                )

        # Find children
        children_found = []
        children_missing = []

        for child_concept, weight in children:
            if not context_group.has(child_concept):
                children_missing.append(child_concept)
                continue

            # Rule 3: Check child for inconsistent duplicates
            if duplicate_info and child_concept in duplicate_info:
                info = duplicate_info[child_concept]
                if hasattr(info, 'duplicate_type') and info.duplicate_type == DuplicateType.INCONSISTENT:
                    return BindingResult(
                        binds=False,
                        status=BindingStatus.SKIP_INCONSISTENT_CHILD,
                        parent_value=parent_value,
                        parent_unit=parent_unit,
                        parent_decimals=parent_decimals,
                        message=f"Child '{child_concept}' has inconsistent duplicates",
                    )

            child_value = context_group.get_value(child_concept)
            child_unit = context_group.get_unit(child_concept)
            child_decimals = context_group.get_decimals(child_concept)

            # Rule 5: Check u-equal (same unit)
            if parent_unit and child_unit and parent_unit != child_unit:
                return BindingResult(
                    binds=False,
                    status=BindingStatus.SKIP_UNIT_MISMATCH,
                    parent_value=parent_value,
                    parent_unit=parent_unit,
                    parent_decimals=parent_decimals,
                    message=f"Unit mismatch: parent '{parent_unit}' != child '{child_unit}'",
                )

            children_found.append({
                'concept': child_concept,
                'original_concept': context_group.get_original_name(child_concept),
                'value': child_value,
                'weight': weight,
                'unit': child_unit,
                'decimals': child_decimals,
                'context_id': context_group.context_id,
            })

        # Rule 2: At least one child must exist
        if not children_found:
            return BindingResult(
                binds=False,
                status=BindingStatus.SKIP_NO_CHILDREN,
                parent_value=parent_value,
                parent_unit=parent_unit,
                parent_decimals=parent_decimals,
                children_missing=children_missing,
                message=f"No children found for '{parent_concept}' in context {context_group.context_id}",
            )

        # Rule 6: Completeness check
        total_children = len(children)
        found_count = len(children_found)
        completeness = found_count / total_children if total_children > 0 else 0.0

        if completeness < self._completeness_threshold:
            return BindingResult(
                binds=False,
                status=BindingStatus.SKIP_INCOMPLETE,
                parent_value=parent_value,
                parent_unit=parent_unit,
                parent_decimals=parent_decimals,
                children_found=children_found,
                children_missing=children_missing,
                message=(
                    f"Incomplete data for '{parent_concept}': "
                    f"{found_count}/{total_children} children found ({completeness:.0%}), "
                    f"threshold is {self._completeness_threshold:.0%}"
                ),
            )

        # All rules passed - calculation binds
        return BindingResult(
            binds=True,
            status=BindingStatus.BINDS,
            parent_value=parent_value,
            parent_unit=parent_unit,
            parent_decimals=parent_decimals,
            children_found=children_found,
            children_missing=children_missing,
            message=f"Calculation binds: {len(children_found)} children found, {len(children_missing)} missing",
        )

    def check_binding_with_fallback(
        self,
        context_group: ContextGroup,
        parent_concept: str,
        children: list[tuple[str, float]],
        all_facts: dict[str, list[tuple[str, float, Optional[str], Optional[int]]]] = None,
        duplicate_info: dict = None,
        context_is_dimensional: Optional[bool] = None,
        parent_period_key: Optional[str] = None
    ) -> BindingResult:
        """
        Check binding with dimensional fallback for missing children.

        When children are not found in the same context as the parent,
        this method searches for them in any available context.

        IMPORTANT: Dimensional fallback is ONLY used when the parent is in
        a non-dimensional (default) context. If the parent is in a dimensional
        context, children MUST be in the SAME dimensional context.

        Args:
            context_group: ContextGroup with facts for the parent context
            parent_concept: Normalized parent concept name
            children: List of (child_concept, weight) tuples
            all_facts: Dict of concept -> [(context_id, value, unit, decimals, is_dimensional, period_key)] for fallback
            duplicate_info: Optional dict of concept -> DuplicateInfo
            context_is_dimensional: Explicit flag from PreparedContext indicating if
                                    this context has dimensional qualifiers. If provided,
                                    overrides pattern-based detection.
            parent_period_key: Period key from parent's context. When provided, period
                              matching uses this directly instead of parsing context_id.

        Returns:
            BindingResult with dimensional fallback applied
        """
        # First try strict C-Equal binding
        strict_result = self.check_binding(
            context_group, parent_concept, children, duplicate_info
        )

        # If strict strategy or no fallback data, return strict result
        if self._strategy == 'strict' or not all_facts:
            return strict_result

        # Check if parent is in a dimensional context
        # PRIORITY: Use explicit flag if provided (from PreparedContext.is_dimensional)
        # FALLBACK: Pattern matching on context_id string (legacy behavior)
        parent_context = context_group.context_id
        if context_is_dimensional is not None:
            is_dimensional = context_is_dimensional
        else:
            is_dimensional = self._classifier.is_dimensional(parent_context)

        if is_dimensional:
            # Parent is in dimensional context - NO fallback allowed
            self.logger.debug(
                f"Parent '{parent_concept}' is in dimensional context - fallback disabled"
            )
            return strict_result

        # Parent is in non-dimensional context - fallback is allowed

        # If no children were found, try fallback
        if strict_result.status == BindingStatus.SKIP_NO_CHILDREN:
            return self._apply_fallback(
                strict_result, parent_concept, children, all_facts, parent_context,
                parent_period_key=parent_period_key
            )

        # If some children are missing, try to fill them
        if strict_result.children_missing:
            return self._fill_missing(
                strict_result, children, all_facts, parent_context,
                parent_period_key=parent_period_key
            )

        return strict_result

    def _apply_fallback(
        self,
        base_result: BindingResult,
        parent_concept: str,
        children: list[tuple[str, float]],
        all_facts: dict,
        parent_context: str,
        parent_period_key: Optional[str] = None
    ) -> BindingResult:
        """
        Apply dimensional fallback when no children found.

        NOTE: This method is only called when parent context is NON-dimensional.
        We pass parent_is_dimensional=False to finder to ensure proper filtering.
        When parent_period_key is provided, period matching uses actual filing
        data instead of parsing context_id strings.
        """
        children_found = []
        children_missing = []

        finder = FactFinder(all_facts, strategy='period')

        for child_concept, weight in children:
            match = finder.find_compatible(
                concept=child_concept,
                parent_context=parent_context,
                parent_unit=base_result.parent_unit,
                allow_dimensional_child=False,
                parent_is_dimensional=False,  # Parent is non-dimensional
                parent_period_key=parent_period_key,  # Use actual period from filing
            )

            if match.found:
                children_found.append({
                    'concept': child_concept,
                    'original_concept': child_concept,
                    'value': match.value,
                    'weight': weight,
                    'unit': match.unit,
                    'decimals': match.decimals,
                    'context_id': match.context_id,
                    'source': 'fallback',
                })
            else:
                children_missing.append(child_concept)

        if not children_found:
            return base_result  # No improvement

        # Completeness check
        total = len(children)
        found = len(children_found)
        completeness = found / total if total > 0 else 0.0

        if completeness < self._completeness_threshold:
            return BindingResult(
                binds=False,
                status=BindingStatus.SKIP_INCOMPLETE,
                parent_value=base_result.parent_value,
                parent_unit=base_result.parent_unit,
                parent_decimals=base_result.parent_decimals,
                children_found=children_found,
                children_missing=children_missing,
                message=f"Incomplete data (fallback): {found}/{total} ({completeness:.0%})",
            )

        return BindingResult(
            binds=True,
            status=BindingStatus.BINDS,
            parent_value=base_result.parent_value,
            parent_unit=base_result.parent_unit,
            parent_decimals=base_result.parent_decimals,
            children_found=children_found,
            children_missing=children_missing,
            message=f"Dimensional fallback: {found} children found via cross-context lookup",
        )

    def _fill_missing(
        self,
        base_result: BindingResult,
        children: list[tuple[str, float]],
        all_facts: dict,
        parent_context: str,
        parent_period_key: Optional[str] = None
    ) -> BindingResult:
        """
        Fill in missing children using fallback.

        NOTE: This method is only called when parent context is NON-dimensional.
        We pass parent_is_dimensional=False to finder to ensure proper filtering.
        When parent_period_key is provided, period matching uses actual filing
        data instead of parsing context_id strings.
        """
        children_found = list(base_result.children_found)
        children_missing = []
        fallback_count = 0

        finder = FactFinder(all_facts, strategy='period')

        for child_concept, weight in children:
            # Check if already found
            already_found = any(c['concept'] == child_concept for c in children_found)
            if already_found:
                continue

            match = finder.find_compatible(
                concept=child_concept,
                parent_context=parent_context,
                parent_unit=base_result.parent_unit,
                allow_dimensional_child=False,
                parent_is_dimensional=False,  # Parent is non-dimensional (we only get here when True)
                parent_period_key=parent_period_key,  # Use actual period from filing
            )

            if match.found:
                children_found.append({
                    'concept': child_concept,
                    'original_concept': child_concept,
                    'value': match.value,
                    'weight': weight,
                    'unit': match.unit,
                    'decimals': match.decimals,
                    'context_id': match.context_id,
                    'source': 'fallback',
                })
                fallback_count += 1
            else:
                children_missing.append(child_concept)

        # Completeness check
        total = len(children)
        found = len(children_found)
        completeness = found / total if total > 0 else 0.0

        if completeness < self._completeness_threshold:
            return BindingResult(
                binds=False,
                status=BindingStatus.SKIP_INCOMPLETE,
                parent_value=base_result.parent_value,
                parent_unit=base_result.parent_unit,
                parent_decimals=base_result.parent_decimals,
                children_found=children_found,
                children_missing=children_missing,
                message=f"Incomplete data: {found}/{total} ({completeness:.0%})",
            )

        return BindingResult(
            binds=True,
            status=BindingStatus.BINDS,
            parent_value=base_result.parent_value,
            parent_unit=base_result.parent_unit,
            parent_decimals=base_result.parent_decimals,
            children_found=children_found,
            children_missing=children_missing,
            message=f"Calculation binds: {found} children ({fallback_count} via fallback), {len(children_missing)} missing",
        )


__all__ = ['BindingChecker']
