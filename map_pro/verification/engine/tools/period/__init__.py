# Path: verification/engine/checks_v2/tools/period/__init__.py
"""
Period Tools for XBRL Verification

Provides period extraction, parsing, and comparison across all processing stages.

Key Components:
- PeriodExtractor: Extract period info from context_id strings
- PeriodComparator: Compare periods for compatibility
- PeriodInfo: Data class holding extracted period information

Context IDs encode period information in various formats:
- Duration_1_1_2024_To_12_31_2024_<hash>
- Instant_12_31_2024_<hash>
- From2024-01-01To2024-12-31_<hash>
- AsOf_12_31_2024_<hash>

These tools extract period data in a market-agnostic way.
"""

from .extractor import PeriodExtractor, PeriodInfo
from .comparator import PeriodComparator

__all__ = [
    'PeriodExtractor',
    'PeriodComparator',
    'PeriodInfo',
]
