# Path: verification/engine/checks_v2/tools/fact/fact_finder.py
"""
Fact Finder for XBRL Verification

Finds facts across contexts with various strategies.

Techniques consolidated from:
- checks/context/fact_finder.py

DESIGN: Stateless tool for locating facts with fallback strategies.
"""

import logging
from typing import Optional

from ..context.classifier import ContextClassifier
from ..context.matcher import ContextMatcher
from .fact_entry import FactMatch


# Match type constants
MATCH_TYPE_EXACT = 'exact'
MATCH_TYPE_FALLBACK = 'fallback'
MATCH_TYPE_PERIOD_MATCH = 'period_match'
MATCH_TYPE_NONE = 'none'


class FactFinder:
    """
    Find facts across contexts with various strategies.

    Provides:
    - Exact matching (same context_id, C-Equal)
    - Period-compatible fallback (different context, same period)
    - Dimensional-aware filtering

    This is a STATELESS tool that operates on a facts dictionary.

    Strategies:
    - 'strict': Exact context match only (C-Equal)
    - 'period': Allow period-compatible fallback
    - 'any': Allow any matching context

    Usage:
        all_facts = {'assets': [(ctx1, 1000, 'USD', -3), (ctx2, 1000, 'USD', -3)]}
        finder = FactFinder(all_facts)

        # Find with fallback
        match = finder.find_compatible(
            concept='assets',
            parent_context='Duration_1_1_2024_To_12_31_2024',
            parent_unit='USD'
        )
    """

    def __init__(
        self,
        all_facts: dict[str, list[tuple]] = None,
        strategy: str = 'period'
    ):
        """
        Initialize fact finder.

        Args:
            all_facts: Dictionary mapping concept -> list of fact tuples.
                       Tuples can be 4 or 5 elements:
                       - Legacy: (context_id, value, unit, decimals)
                       - New:    (context_id, value, unit, decimals, is_dimensional)
            strategy: Finding strategy ('strict', 'period', or 'any')
        """
        self.all_facts = all_facts or {}
        self._strategy = strategy
        self.logger = logging.getLogger('tools.fact.fact_finder')
        self._classifier = ContextClassifier()
        self._matcher = ContextMatcher()

    def set_strategy(self, strategy: str) -> None:
        """
        Set the finding strategy.

        Args:
            strategy: 'strict', 'period', or 'any'
        """
        if strategy not in ('strict', 'period', 'any'):
            raise ValueError(f"Unknown strategy: {strategy}")
        self._strategy = strategy

    def find_in_context(
        self,
        concept: str,
        context_id: str
    ) -> FactMatch:
        """
        Find a fact in a specific context (strict C-Equal).

        Args:
            concept: Normalized concept name
            context_id: Context to search in

        Returns:
            FactMatch with result
        """
        if concept not in self.all_facts:
            return FactMatch()

        # Handle both 4-element and 5-element tuples
        for fact_tuple in self.all_facts[concept]:
            ctx = fact_tuple[0]
            value = fact_tuple[1]
            unit = fact_tuple[2]
            decimals = fact_tuple[3]

            if ctx == context_id:
                return FactMatch(
                    found=True,
                    context_id=ctx,
                    value=value,
                    unit=unit,
                    decimals=decimals,
                    match_type=MATCH_TYPE_EXACT,
                )

        return FactMatch()

    def find_compatible(
        self,
        concept: str,
        parent_context: str,
        parent_unit: Optional[str] = None,
        allow_dimensional_child: bool = False,
        parent_is_dimensional: Optional[bool] = None,
        parent_period_key: Optional[str] = None
    ) -> FactMatch:
        """
        Find a fact compatible with parent context.

        First tries exact match (same context), then fallback (compatible period).

        Args:
            concept: Normalized concept name
            parent_context: Parent's context_id
            parent_unit: Parent's unit (for u-equal check)
            allow_dimensional_child: Whether to allow children from dimensional contexts
                                     when parent is non-dimensional
            parent_is_dimensional: Explicit flag for whether parent context is dimensional.
                                   If None, falls back to pattern matching (legacy behavior).
            parent_period_key: Period key from parent's context. When provided, period
                              matching uses this directly instead of parsing context_id.

        Returns:
            FactMatch with result
        """
        if concept not in self.all_facts:
            return FactMatch()

        # Use explicit dimensional flag if provided, otherwise fallback to pattern matching
        if parent_is_dimensional is None:
            parent_is_dimensional = self._classifier.is_dimensional(parent_context)

        # First pass: exact context match
        for fact_tuple in self.all_facts[concept]:
            ctx = fact_tuple[0]
            value = fact_tuple[1]
            unit = fact_tuple[2]
            decimals = fact_tuple[3]

            if ctx == parent_context:
                # Check unit compatibility
                if parent_unit and unit and parent_unit != unit:
                    continue

                return FactMatch(
                    found=True,
                    context_id=ctx,
                    value=value,
                    unit=unit,
                    decimals=decimals,
                    match_type=MATCH_TYPE_EXACT,
                )

        # If strict strategy, don't try fallback
        if self._strategy == 'strict':
            return FactMatch()

        # Second pass: compatible context fallback
        for fact_tuple in self.all_facts[concept]:
            ctx = fact_tuple[0]
            value = fact_tuple[1]
            unit = fact_tuple[2]
            decimals = fact_tuple[3]

            # Get dimensional status and period_key from tuple if available
            # Tuple format: (context_id, value, unit, decimals, is_dimensional, period_key)
            if len(fact_tuple) >= 5:
                child_is_dimensional = fact_tuple[4]
            else:
                child_is_dimensional = self._classifier.is_dimensional(ctx)

            if len(fact_tuple) >= 6:
                child_period_key = fact_tuple[5]
            else:
                child_period_key = None

            # Skip if already checked (exact match)
            if ctx == parent_context:
                continue

            # Rule: If parent is non-dimensional, skip dimensional children
            # unless explicitly allowed
            if not parent_is_dimensional and child_is_dimensional and not allow_dimensional_child:
                self.logger.debug(
                    f"Skipping '{concept}' from dimensional context {ctx} "
                    f"(parent is non-dimensional)"
                )
                continue

            # Rule: If parent is dimensional, only accept children from same
            # dimensional context (strict C-Equal required)
            if parent_is_dimensional:
                # For dimensional parents, we don't do fallback
                continue

            # Check period compatibility (unless 'any' strategy)
            if self._strategy == 'period':
                # Use actual period_key from filing data if available
                if parent_period_key and child_period_key:
                    # Direct period_key comparison - no pattern matching needed!
                    if parent_period_key != child_period_key:
                        self.logger.debug(
                            f"Skipping '{concept}' from {ctx} - period mismatch "
                            f"(parent: {parent_period_key}, child: {child_period_key})"
                        )
                        continue
                else:
                    # Fallback to context_id parsing (legacy behavior)
                    if not self._matcher.is_period_compatible(parent_context, ctx):
                        self.logger.debug(
                            f"Skipping '{concept}' from {ctx} - period incompatible"
                        )
                        continue

            # Check unit compatibility
            if parent_unit and unit and parent_unit != unit:
                continue

            # Found compatible match
            return FactMatch(
                found=True,
                context_id=ctx,
                value=value,
                unit=unit,
                decimals=decimals,
                match_type=MATCH_TYPE_FALLBACK,
            )

        return FactMatch()

    def find_all_in_period(
        self,
        concept: str,
        period_key: str
    ) -> list[FactMatch]:
        """
        Find all instances of a concept in a specific period.

        Useful for consistency checking across statements.

        Args:
            concept: Normalized concept name
            period_key: Period key to match

        Returns:
            List of FactMatch for all matching instances
        """
        matches = []

        if concept not in self.all_facts:
            return matches

        # Handle both 4-element and 5-element tuples
        for fact_tuple in self.all_facts[concept]:
            ctx = fact_tuple[0]
            value = fact_tuple[1]
            unit = fact_tuple[2]
            decimals = fact_tuple[3]

            # Extract period from context
            from ..period.extractor import PeriodExtractor
            extractor = PeriodExtractor()
            ctx_period = extractor.extract(ctx)

            if ctx_period.period_key == period_key:
                matches.append(FactMatch(
                    found=True,
                    context_id=ctx,
                    value=value,
                    unit=unit,
                    decimals=decimals,
                    match_type=MATCH_TYPE_EXACT,
                ))

        return matches

    def has_concept(self, concept: str) -> bool:
        """Check if concept exists in any context."""
        return concept in self.all_facts

    def get_contexts_for_concept(self, concept: str) -> list[str]:
        """Get all context IDs where concept exists."""
        if concept not in self.all_facts:
            return []
        # Handle both 4-element and 5-element tuples (context_id is always first)
        return [fact_tuple[0] for fact_tuple in self.all_facts[concept]]


__all__ = [
    'FactFinder',
    'MATCH_TYPE_EXACT',
    'MATCH_TYPE_FALLBACK',
    'MATCH_TYPE_PERIOD_MATCH',
    'MATCH_TYPE_NONE',
]
