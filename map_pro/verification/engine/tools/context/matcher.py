# Path: verification/engine/checks_v2/tools/context/matcher.py
"""
Context Matcher for XBRL Verification

Determines if two contexts are compatible for fact comparison.

Techniques consolidated from:
- checks/context/context_matching.py

DESIGN: Stateless tool that can be reused across all processing stages.
Uses PeriodExtractor from period/ tools for period comparison.
"""

import logging
from typing import Optional

from ..period.extractor import PeriodExtractor, PeriodInfo
from .classifier import ContextClassifier
from ...constants.enums import PeriodType


class ContextMatcher:
    """
    Match and compare XBRL contexts for compatibility.

    Determines if contexts from different facts are compatible enough
    to allow comparison (e.g., for dimensional fallback).

    This is a STATELESS tool - it performs matching based on
    context_id strings without maintaining any state.

    Strategies:
    - 'strict': Exact context_id match only
    - 'period': Match by period (same dates)
    - 'year': Match by year only (loosest)

    Usage:
        matcher = ContextMatcher()

        # Check period compatibility
        compatible = matcher.is_period_compatible(
            'Duration_1_1_2024_To_12_31_2024',
            'Duration_1_1_2024_To_12_31_2024_extra'
        )
        # -> True (same period)

        # Set different strategy
        matcher.set_strategy('strict')
    """

    def __init__(self, strategy: str = 'period'):
        """
        Initialize the matcher.

        Args:
            strategy: Matching strategy ('strict', 'period', or 'year')
        """
        self.logger = logging.getLogger('tools.context.matcher')
        self._strategy = strategy
        self._period_extractor = PeriodExtractor()
        self._classifier = ContextClassifier()

    def set_strategy(self, strategy: str) -> None:
        """
        Set the matching strategy.

        Args:
            strategy: 'strict', 'period', or 'year'
        """
        if strategy not in ('strict', 'period', 'year'):
            raise ValueError(f"Unknown strategy: {strategy}")
        self._strategy = strategy

    def are_compatible(
        self,
        parent_context: str,
        child_context: str,
        strict: bool = False
    ) -> bool:
        """
        Check if two contexts are compatible for comparison.

        Args:
            parent_context: Parent's context_id
            child_context: Child's context_id
            strict: If True, require exact match (overrides strategy)

        Returns:
            True if contexts are compatible
        """
        if not parent_context or not child_context:
            return False

        # Exact match always compatible
        if parent_context == child_context:
            return True

        # Strict mode requires exact match
        if strict or self._strategy == 'strict':
            return False

        # Check period compatibility
        return self.is_period_compatible(parent_context, child_context)

    def is_period_compatible(
        self,
        parent_context: str,
        child_context: str
    ) -> bool:
        """
        Check if two contexts have compatible periods.

        Args:
            parent_context: Parent's context_id
            child_context: Child's context_id

        Returns:
            True if periods are compatible
        """
        parent_period = self._period_extractor.extract(parent_context)
        child_period = self._period_extractor.extract(child_context)

        return self.periods_match(parent_period, child_period)

    def periods_match(
        self,
        period1: PeriodInfo,
        period2: PeriodInfo
    ) -> bool:
        """
        Check if two periods match for comparison purposes.

        Matching rules (in order of strictness):
        1. Same period_key: always match
        2. Same period_type + same dates: match
        3. Same period_type + same year: match (if strategy is 'year')
        4. Otherwise: no match

        Args:
            period1: First period info
            period2: Second period info

        Returns:
            True if periods match according to current strategy
        """
        # Exact period key match
        if period1.period_key and period2.period_key:
            if period1.period_key == period2.period_key:
                return True

        # Check period type compatibility
        if period1.period_type != PeriodType.UNKNOWN and period2.period_type != PeriodType.UNKNOWN:
            if period1.period_type != period2.period_type:
                # Duration vs instant - not compatible
                return False

            # Same period type - check dates
            if period1.start_date == period2.start_date and period1.end_date == period2.end_date:
                return True

            # Year-based matching (looser)
            if self._strategy == 'year' and period1.year and period2.year:
                if period1.year == period2.year:
                    return True

        # Fallback: just same year (if year strategy)
        if self._strategy == 'year':
            if period1.year and period2.year and period1.year == period2.year:
                return True

        return False

    def is_c_equal(self, context1: str, context2: str) -> bool:
        """
        Check if two contexts are C-Equal (exact same context).

        Per XBRL 2.1, C-Equal means identical context_id.

        Args:
            context1: First context_id
            context2: Second context_id

        Returns:
            True if contexts are C-Equal
        """
        return context1 == context2

    def classify_match(
        self,
        parent_context: str,
        child_context: str
    ) -> str:
        """
        Classify the type of match between two contexts.

        Args:
            parent_context: Parent's context_id
            child_context: Child's context_id

        Returns:
            'exact', 'period_match', 'year_match', or 'none'
        """
        if parent_context == child_context:
            return 'exact'

        parent_period = self._period_extractor.extract(parent_context)
        child_period = self._period_extractor.extract(child_context)

        # Check exact period match
        if parent_period.period_key and parent_period.period_key == child_period.period_key:
            return 'period_match'

        # Check date match
        if (parent_period.start_date == child_period.start_date and
            parent_period.end_date == child_period.end_date):
            return 'period_match'

        # Check year match
        if parent_period.year and parent_period.year == child_period.year:
            return 'year_match'

        return 'none'


__all__ = ['ContextMatcher']
