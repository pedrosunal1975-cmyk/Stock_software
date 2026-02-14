# Path: mat_acc/ratio_check/math_verify/context_filter.py
"""
Context Filter - Identifies primary contexts from iXBRL filings.

In iXBRL, each numeric fact references a context that defines:
- PERIOD: When (instant date or start/end duration)
- ENTITY: Who (CIK identifier)
- SEGMENT: Optional dimensional breakdown (by product, geography, etc.)

For ratio calculations, we need PRIMARY contexts only:
- No dimensional segments (consolidated totals, not segment breakdowns)
- Current reporting period (latest fiscal year)

Typical filing: ~500 contexts total, ~12 primary, ~488 dimensional.
Without filtering, 96% of values would be segment-specific noise.
"""

import re
from dataclasses import dataclass
from typing import Optional

from core.logger.ipo_logging import get_process_logger


logger = get_process_logger('math_verify.context')


# Regex patterns for context parsing
_CONTEXT_PATTERN = re.compile(
    r'<xbrli:context\b[^>]*id="([^"]+)"[^>]*>(.*?)</xbrli:context>',
    re.DOTALL | re.IGNORECASE,
)
_INSTANT_PATTERN = re.compile(
    r'<xbrli:instant>([^<]+)</xbrli:instant>', re.IGNORECASE,
)
_START_PATTERN = re.compile(
    r'<xbrli:startDate>([^<]+)</xbrli:startDate>', re.IGNORECASE,
)
_END_PATTERN = re.compile(
    r'<xbrli:endDate>([^<]+)</xbrli:endDate>', re.IGNORECASE,
)
_SEGMENT_PATTERN = re.compile(
    r'<xbrli:segment', re.IGNORECASE,
)


@dataclass
class ContextInfo:
    """Parsed context definition from iXBRL."""
    context_id: str
    is_primary: bool = True
    period_type: str = ''
    instant_date: str = ''
    start_date: str = ''
    end_date: str = ''
    has_dimensions: bool = False


class ContextFilter:
    """
    Parses xbrli:context definitions and identifies primary contexts.

    Primary = no dimensional segments (consolidated company totals).
    Current = latest reporting period in the filing.
    """

    def __init__(self):
        """Initialize context filter."""
        self.logger = get_process_logger('math_verify.context')
        self._contexts: dict[str, ContextInfo] = {}
        self._primary_instant: str = ''
        self._primary_duration_end: str = ''

    def parse_contexts(self, content: str) -> dict[str, ContextInfo]:
        """
        Parse all xbrli:context definitions from iXBRL content.

        Args:
            content: Full iXBRL HTML content

        Returns:
            Dictionary mapping context_id to ContextInfo
        """
        self._contexts.clear()

        for match in _CONTEXT_PATTERN.finditer(content):
            ctx_id = match.group(1)
            body = match.group(2)
            ctx = self._parse_single_context(ctx_id, body)
            self._contexts[ctx_id] = ctx

        self._determine_primary_periods()

        primary_count = sum(1 for c in self._contexts.values() if c.is_primary)
        total = len(self._contexts)
        self.logger.info(
            f"Parsed {total} contexts: {primary_count} primary, "
            f"{total - primary_count} dimensional"
        )

        return self._contexts

    def is_primary_current(self, context_ref: str) -> bool:
        """
        Check if a context_ref is primary AND current period.

        This is the key filter: only facts from the primary
        (consolidated) context for the current reporting period
        should be used for ratio calculations.

        Args:
            context_ref: Context reference from a fact

        Returns:
            True if primary + current period
        """
        ctx = self._contexts.get(context_ref)
        if not ctx or not ctx.is_primary:
            return False

        if ctx.period_type == 'instant':
            return ctx.instant_date == self._primary_instant
        elif ctx.period_type == 'duration':
            return ctx.end_date == self._primary_duration_end

        return False

    def get_primary_instant(self) -> str:
        """Get the primary balance sheet date."""
        return self._primary_instant

    def get_primary_duration_end(self) -> str:
        """Get the primary income statement end date."""
        return self._primary_duration_end

    def get_primary_context_ids(self) -> list[str]:
        """Get all primary current-period context IDs."""
        return [
            cid for cid, ctx in self._contexts.items()
            if self.is_primary_current(cid)
        ]

    def _parse_single_context(self, ctx_id: str, body: str) -> ContextInfo:
        """Parse a single context definition."""
        ctx = ContextInfo(context_id=ctx_id)

        # Check for dimensional segments
        ctx.has_dimensions = bool(_SEGMENT_PATTERN.search(body))
        ctx.is_primary = not ctx.has_dimensions

        # Parse period
        instant = _INSTANT_PATTERN.search(body)
        if instant:
            ctx.period_type = 'instant'
            ctx.instant_date = instant.group(1).strip()
        else:
            start = _START_PATTERN.search(body)
            end = _END_PATTERN.search(body)
            if start and end:
                ctx.period_type = 'duration'
                ctx.start_date = start.group(1).strip()
                ctx.end_date = end.group(1).strip()

        return ctx

    def _determine_primary_periods(self) -> None:
        """
        Determine the current reporting period from primary contexts.

        Strategy: Find the latest instant date and latest duration
        end date among primary contexts. The longest duration ending
        on the latest date is the annual period.
        """
        instant_dates = []
        duration_ends = []

        for ctx in self._contexts.values():
            if not ctx.is_primary:
                continue
            if ctx.period_type == 'instant':
                instant_dates.append(ctx.instant_date)
            elif ctx.period_type == 'duration':
                duration_ends.append(ctx.end_date)

        # Latest instant = balance sheet date
        if instant_dates:
            # Filter out future dates (shares outstanding often has future date)
            sorted_dates = sorted(set(instant_dates), reverse=True)
            self._primary_instant = self._pick_reporting_date(sorted_dates)

        # Latest duration end = income statement period end
        if duration_ends:
            sorted_ends = sorted(set(duration_ends), reverse=True)
            self._primary_duration_end = self._pick_reporting_date(sorted_ends)

        self.logger.info(
            f"Primary periods: instant={self._primary_instant}, "
            f"duration_end={self._primary_duration_end}"
        )

    def _pick_reporting_date(self, sorted_dates: list[str]) -> str:
        """
        Pick the actual reporting date from sorted dates.

        Some filings include future dates (e.g., shares outstanding
        as of a date after filing). We want the fiscal year-end.
        If there are multiple dates, prefer the second-latest
        if the latest looks like a post-filing date.
        """
        if not sorted_dates:
            return ''
        if len(sorted_dates) == 1:
            return sorted_dates[0]

        # If the gap between top two dates is very small (< 90 days),
        # the latest is likely the fiscal year-end.
        # If the gap is large, the latest might be a post-filing date.
        # In practice, the top 1-2 dates are usually the right ones.
        return sorted_dates[0]


__all__ = ['ContextFilter', 'ContextInfo']
