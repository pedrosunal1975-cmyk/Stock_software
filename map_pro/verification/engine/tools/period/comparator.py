# Path: verification/engine/checks_v2/tools/period/comparator.py
"""
Period Comparator for XBRL Verification

Compares periods for compatibility and matching.

Provides multiple comparison strategies:
- Exact match: Same period_key
- Type and year match: Same period type and year
- Year-only match: Same year regardless of type

This is used for:
- Determining if facts can be compared (C-Equal)
- Dimensional fallback (finding compatible periods)
- Period grouping (organizing facts by period)
"""

import logging
from typing import Optional

from .extractor import PeriodExtractor, PeriodInfo
from ...constants.enums import PeriodType


class PeriodComparator:
    """
    Compare periods for compatibility.

    Provides multiple comparison strategies for different use cases:
    - Strict: Exact period_key match
    - Relaxed: Same period type and year
    - Loose: Same year only

    Usage:
        comparator = PeriodComparator()

        # Compare two period infos
        match = comparator.periods_match(period1, period2)

        # Check if two context_ids have compatible periods
        compatible = comparator.are_compatible(
            'Duration_1_1_2024_To_12_31_2024',
            'Duration_1_1_2024_To_12_31_2024_axis_member'
        )

        # Group contexts by period
        groups = comparator.group_by_period(context_ids)
    """

    def __init__(self):
        """Initialize comparator with period extractor."""
        self.logger = logging.getLogger('tools.period.comparator')
        self.extractor = PeriodExtractor()

    def periods_match(
        self,
        period1: PeriodInfo,
        period2: PeriodInfo,
        strict: bool = False
    ) -> bool:
        """
        Check if two periods match for comparison purposes.

        Matching rules (from strictest to loosest):
        1. Same period_key: always match (strictest)
        2. Same period_type + same year: match
        3. Same year only: match (loosest)

        Args:
            period1: First period info
            period2: Second period info
            strict: If True, require exact period_key match

        Returns:
            True if periods match
        """
        # Exact period key match
        if period1.period_key and period2.period_key:
            if period1.period_key == period2.period_key:
                return True
            if strict:
                return False  # Strict mode requires exact match

        # Same period type and year
        if (period1.period_type != PeriodType.UNKNOWN and
                period2.period_type != PeriodType.UNKNOWN):
            if (period1.period_type == period2.period_type and
                    period1.year == period2.year):
                return True

        # Fallback: just same year (loose match)
        if period1.year and period2.year and period1.year == period2.year:
            return True

        return False

    def are_compatible(
        self,
        context1: str,
        context2: str,
        strict: bool = False
    ) -> bool:
        """
        Check if two context_ids have compatible periods.

        Args:
            context1: First context_id
            context2: Second context_id
            strict: If True, require exact period match

        Returns:
            True if periods are compatible
        """
        if not context1 or not context2:
            return False

        # Exact context match always compatible
        if context1 == context2:
            return True

        # Extract periods and compare
        period1 = self.extractor.extract(context1)
        period2 = self.extractor.extract(context2)

        return self.periods_match(period1, period2, strict=strict)

    def have_same_period_portion(
        self,
        context1: str,
        context2: str
    ) -> bool:
        """
        Check if two context_ids have the same period portion (ignoring dimensional hash).

        This is more strict than are_compatible but allows different dimensional qualifiers.

        Args:
            context1: First context_id
            context2: Second context_id

        Returns:
            True if period portions match exactly
        """
        portion1 = self.extractor.extract_period_portion(context1)
        portion2 = self.extractor.extract_period_portion(context2)

        if portion1 is None or portion2 is None:
            return False

        return portion1.lower() == portion2.lower()

    def group_by_period(
        self,
        context_ids: list
    ) -> dict:
        """
        Group context_ids by their period.

        Args:
            context_ids: List of context_id strings

        Returns:
            Dictionary mapping period_key -> list of context_ids
        """
        groups = {}

        for ctx_id in context_ids:
            period = self.extractor.extract(ctx_id)
            key = period.period_key or 'unknown'

            if key not in groups:
                groups[key] = []
            groups[key].append(ctx_id)

        return groups

    def group_by_year(
        self,
        context_ids: list
    ) -> dict:
        """
        Group context_ids by year only.

        Args:
            context_ids: List of context_id strings

        Returns:
            Dictionary mapping year -> list of context_ids
        """
        groups = {}

        for ctx_id in context_ids:
            period = self.extractor.extract(ctx_id)
            year = period.year or 'unknown'

            if year not in groups:
                groups[year] = []
            groups[year].append(ctx_id)

        return groups

    def find_matching_contexts(
        self,
        target_context: str,
        all_contexts: list,
        strict: bool = False
    ) -> list:
        """
        Find all contexts that match the target period.

        Args:
            target_context: The context to match against
            all_contexts: List of all available context_ids
            strict: If True, require exact period match

        Returns:
            List of matching context_ids (excluding target)
        """
        matches = []

        for ctx in all_contexts:
            if ctx == target_context:
                continue

            if self.are_compatible(target_context, ctx, strict=strict):
                matches.append(ctx)

        return matches

    def get_period_summary(self, context_id: str) -> str:
        """
        Get a human-readable period summary for a context.

        Args:
            context_id: The context_id to summarize

        Returns:
            Human-readable string like "Year 2024" or "2024-01-01 to 2024-12-31"
        """
        period = self.extractor.extract(context_id)

        if period.period_type == PeriodType.DURATION:
            if period.start_date and period.end_date:
                return f"{period.start_date} to {period.end_date}"
            elif period.year:
                return f"Year {period.year}"
        elif period.period_type == PeriodType.INSTANT:
            if period.end_date:
                return f"As of {period.end_date}"
            elif period.year:
                return f"Year-end {period.year}"
        elif period.year:
            return f"Year {period.year}"

        return context_id  # Fallback to raw context_id


__all__ = ['PeriodComparator']
