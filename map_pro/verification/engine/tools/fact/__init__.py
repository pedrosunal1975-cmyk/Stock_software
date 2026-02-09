# Path: verification/engine/checks_v2/tools/fact/__init__.py
"""
Fact Tools for XBRL Verification

Provides fact parsing, entry structures, duplicate handling, and fact finding.

Modules:
- value_parser: Parse raw values to numeric form
- fact_entry: Data structures for fact entries
- duplicate_handler: Detect and classify duplicate facts
- fact_finder: Find facts across contexts with fallback

These tools are STATELESS and can be used across all processing stages.

Usage:
    from verification.engine.checks_v2.tools.fact import (
        ValueParser,
        FactEntry,
        FactMatch,
        ChildContribution,
        DuplicateHandler,
        DuplicateInfo,
        FactFinder,
    )

    # Parse values
    parser = ValueParser()
    value = parser.parse_value('1,234,567')

    # Handle duplicates
    handler = DuplicateHandler()
    info = handler.analyze([entry1, entry2])

    # Find facts
    finder = FactFinder(all_facts)
    match = finder.find_compatible('assets', 'c-1')
"""

from .value_parser import ValueParser
from .fact_entry import FactEntry, FactMatch, ChildContribution
from .duplicate_handler import DuplicateHandler, DuplicateInfo
from .fact_finder import (
    FactFinder,
    MATCH_TYPE_EXACT,
    MATCH_TYPE_FALLBACK,
    MATCH_TYPE_PERIOD_MATCH,
    MATCH_TYPE_NONE,
)


__all__ = [
    # Value parsing
    'ValueParser',

    # Data structures
    'FactEntry',
    'FactMatch',
    'ChildContribution',

    # Duplicate handling
    'DuplicateHandler',
    'DuplicateInfo',

    # Fact finding
    'FactFinder',
    'MATCH_TYPE_EXACT',
    'MATCH_TYPE_FALLBACK',
    'MATCH_TYPE_PERIOD_MATCH',
    'MATCH_TYPE_NONE',
]
