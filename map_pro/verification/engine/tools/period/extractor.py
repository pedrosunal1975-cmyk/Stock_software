# Path: verification/engine/checks_v2/tools/period/extractor.py
"""
Period Extractor for XBRL Context IDs

Extracts period information from context_id strings using multiple
pattern-matching strategies.

Context IDs encode period information in various formats:
- Duration_1_1_2024_To_12_31_2024_<dimensional_hash>
- Instant_12_31_2024_<dimensional_hash>
- From2024-01-01To2024-12-31_<hash>
- AsOf_2024-12-31_<hash>

The extractor uses compiled regex patterns from constants and
tries them in order until one matches.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from ...constants.patterns import (
    PERIOD_TYPE_INDICATORS,
    DATE_COMPONENT_PATTERNS,
    PERIOD_EXTRACTION_PATTERNS,
    REGEX_YEAR_PATTERN,
)
from ...constants.enums import PeriodType


@dataclass
class PeriodInfo:
    """
    Extracted period information from a context_id.

    Attributes:
        period_type: 'duration', 'instant', or 'unknown'
        start_date: Start date as 'YYYY-MM-DD' (for duration) or None
        end_date: End date as 'YYYY-MM-DD' (for duration/instant)
        year: Year only if full date not extractable
        period_key: Normalized key for comparison (e.g., 'd_2024-01-01_2024-12-31')
        raw_match: The raw string that matched the pattern
        pattern_used: Name of the pattern that matched
    """
    period_type: PeriodType = PeriodType.UNKNOWN
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    year: Optional[str] = None
    period_key: str = ''
    raw_match: str = ''
    pattern_used: str = ''

    @property
    def is_duration(self) -> bool:
        """Check if this is a duration period."""
        return self.period_type == PeriodType.DURATION

    @property
    def is_instant(self) -> bool:
        """Check if this is an instant period."""
        return self.period_type == PeriodType.INSTANT

    @property
    def has_full_dates(self) -> bool:
        """Check if full dates are available."""
        if self.period_type == PeriodType.DURATION:
            return self.start_date is not None and self.end_date is not None
        elif self.period_type == PeriodType.INSTANT:
            return self.end_date is not None
        return False


class PeriodExtractor:
    """
    Extract period information from context_id strings.

    Provides multiple strategies for period extraction:
    1. Full pattern matching (Duration_M_D_YYYY_To_M_D_YYYY)
    2. ISO format matching (Duration_YYYY-MM-DD_To_YYYY-MM-DD)
    3. Year-only fallback (any 4-digit year)

    The extractor compiles patterns at initialization for efficiency.

    Usage:
        extractor = PeriodExtractor()

        # Extract from duration context
        period = extractor.extract('Duration_1_1_2024_To_12_31_2024_abc123')
        # -> PeriodInfo(period_type=DURATION, start_date='2024-01-01',
        #               end_date='2024-12-31', period_key='d_2024-01-01_2024-12-31')

        # Extract from instant context
        period = extractor.extract('AsOf_12_31_2024_xyz789')
        # -> PeriodInfo(period_type=INSTANT, end_date='2024-12-31',
        #               period_key='i_2024-12-31')

        # Extract period portion only (strip dimensional hash)
        period_only = extractor.extract_period_portion('Duration_1_1_2024_To_12_31_2024_abc123')
        # -> 'Duration_1_1_2024_To_12_31_2024'
    """

    # Regex flags for case-insensitive matching
    REGEX_FLAGS = re.IGNORECASE

    def __init__(self):
        """Initialize extractor with compiled patterns."""
        self.logger = logging.getLogger('tools.period.extractor')
        self._compiled_patterns = self._compile_patterns()
        self._period_portion_patterns = self._compile_period_portion_patterns()

    def _compile_patterns(self) -> list:
        """
        Compile regex patterns from constants.

        Substitutes placeholders with actual regex fragments.
        """
        compiled = []

        # Build substitution map from DATE_COMPONENT_PATTERNS
        subs = {
            'sep': DATE_COMPONENT_PATTERNS['separator'],
            'month': DATE_COMPONENT_PATTERNS['month'],
            'day': DATE_COMPONENT_PATTERNS['day'],
            'year': DATE_COMPONENT_PATTERNS['year'],
            'range': DATE_COMPONENT_PATTERNS['range_indicator'],
        }

        for name, template, groups in PERIOD_EXTRACTION_PATTERNS:
            try:
                # Substitute placeholders
                pattern_str = template.format(**subs)
                pattern = re.compile(pattern_str, self.REGEX_FLAGS)
                compiled.append((name, pattern, groups))
            except (re.error, KeyError) as e:
                self.logger.warning(f"Failed to compile pattern '{name}': {e}")

        return compiled

    def _compile_period_portion_patterns(self) -> list:
        """
        Compile patterns for extracting period portion from context_id.

        These patterns extract the period part before the dimensional hash.
        """
        patterns = [
            # Duration: Duration_M_D_YYYY_To_M_D_YYYY_<hash>
            re.compile(
                r'^(Duration_\d+_\d+_\d{4}_To_\d+_\d+_\d{4})_[A-Za-z0-9]+$',
                self.REGEX_FLAGS
            ),
            # Instant: Instant_M_D_YYYY_<hash>
            re.compile(
                r'^(Instant_\d+_\d+_\d{4})_[A-Za-z0-9]+$',
                self.REGEX_FLAGS
            ),
            # Alternative: From2022-01-01To2022-12-31_<hash>
            re.compile(
                r'^(From\d{4}-\d{2}-\d{2}To\d{4}-\d{2}-\d{2})_[A-Za-z0-9]+$',
                self.REGEX_FLAGS
            ),
            # AsOf date: AsOf2022-12-31_<hash>
            re.compile(
                r'^(AsOf\d{4}-\d{2}-\d{2})_[A-Za-z0-9]+$',
                self.REGEX_FLAGS
            ),
        ]
        return patterns

    def extract(self, context_id: str) -> PeriodInfo:
        """
        Extract period information from a context_id.

        Args:
            context_id: The XBRL context identifier

        Returns:
            PeriodInfo with extracted period data
        """
        if not context_id:
            return PeriodInfo()

        context_lower = context_id.lower()

        # Determine period type from indicators
        period_type = self._detect_period_type(context_lower)

        # Try each pattern until one matches
        for name, pattern, groups in self._compiled_patterns:
            match = pattern.search(context_lower)
            if match:
                return self._build_period_info(name, match, groups, period_type)

        # No pattern matched - return with any year found
        years = re.findall(REGEX_YEAR_PATTERN, context_id)
        if years:
            unique_years = sorted(set(years))
            return PeriodInfo(
                period_type=PeriodType.UNKNOWN,
                year=unique_years[0],
                period_key=f"y_{'_'.join(unique_years)}",
                raw_match=context_id,
                pattern_used='year_fallback',
            )

        return PeriodInfo(raw_match=context_id)

    def extract_period_portion(self, context_id: str) -> Optional[str]:
        """
        Extract the period portion from a context_id, stripping the dimensional hash.

        XBRL context IDs often have format:
        - Duration_1_1_2022_To_12_31_2022_<dimensional_hash>
        - Instant_12_31_2022_<dimensional_hash>

        The hash suffix varies based on dimensional context (segment, axis).
        This method extracts just the period portion.

        Args:
            context_id: Full XBRL context reference

        Returns:
            Period portion without hash, or None if format not recognized
        """
        if not context_id:
            return None

        # Try each pattern
        for pattern in self._period_portion_patterns:
            match = pattern.match(context_id)
            if match:
                return match.group(1)

        # Simple context IDs (no hash suffix) - return as-is
        if re.match(r'^[a-z]-\d+$', context_id):
            return context_id

        return None

    def _detect_period_type(self, context_lower: str) -> PeriodType:
        """Detect period type from context_id using indicators from constants."""
        for indicator, ptype_str in PERIOD_TYPE_INDICATORS:
            if indicator in context_lower:
                if ptype_str == 'duration':
                    return PeriodType.DURATION
                elif ptype_str == 'instant':
                    return PeriodType.INSTANT
        return PeriodType.UNKNOWN

    def _build_period_info(
        self,
        pattern_name: str,
        match: re.Match,
        groups: list,
        period_type: PeriodType
    ) -> PeriodInfo:
        """
        Build PeriodInfo from a regex match.

        Args:
            pattern_name: Name of the pattern that matched
            match: The regex match object
            groups: List of group names for extraction
            period_type: Detected period type

        Returns:
            PeriodInfo with extracted data
        """
        # Extract matched groups
        extracted = {}
        for i, group_name in enumerate(groups):
            if i + 1 <= len(match.groups()):
                extracted[group_name] = match.group(i + 1)

        # Build dates based on pattern type
        if pattern_name.startswith('duration'):
            # Duration pattern - extract start and end dates
            start_date = self._format_date(
                extracted.get('start_year'),
                extracted.get('start_month'),
                extracted.get('start_day')
            )
            end_date = self._format_date(
                extracted.get('end_year'),
                extracted.get('end_month'),
                extracted.get('end_day')
            )
            period_key = f"d_{start_date}_{end_date}" if start_date and end_date else ''

            return PeriodInfo(
                period_type=PeriodType.DURATION,
                start_date=start_date,
                end_date=end_date,
                year=extracted.get('end_year'),
                period_key=period_key,
                raw_match=match.group(0),
                pattern_used=pattern_name,
            )

        elif pattern_name.startswith('instant'):
            # Instant pattern - extract single date
            end_date = self._format_date(
                extracted.get('year'),
                extracted.get('month'),
                extracted.get('day')
            )
            period_key = f"i_{end_date}" if end_date else ''

            return PeriodInfo(
                period_type=PeriodType.INSTANT,
                end_date=end_date,
                year=extracted.get('year'),
                period_key=period_key,
                raw_match=match.group(0),
                pattern_used=pattern_name,
            )

        elif pattern_name == 'year_only':
            # Year-only fallback
            year = extracted.get('year')
            return PeriodInfo(
                period_type=period_type,
                year=year,
                period_key=f"y_{year}" if year else '',
                raw_match=match.group(0),
                pattern_used=pattern_name,
            )

        return PeriodInfo(period_type=period_type, raw_match=match.group(0))

    def _format_date(
        self,
        year: Optional[str],
        month: Optional[str],
        day: Optional[str]
    ) -> Optional[str]:
        """
        Format date components into YYYY-MM-DD string.

        Args:
            year: Year string
            month: Month string (1-12 or 01-12)
            day: Day string (1-31 or 01-31)

        Returns:
            Formatted date string or None if components missing
        """
        if not all([year, month, day]):
            return None

        try:
            month_int = int(month)
            day_int = int(day)
            return f"{year}-{month_int:02d}-{day_int:02d}"
        except (ValueError, TypeError):
            return None


__all__ = ['PeriodExtractor', 'PeriodInfo']
