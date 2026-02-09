# Path: verification/engine/checks_v2/tools/fact/fact_entry.py
"""
Fact Entry Data Structures for XBRL Verification

Provides dataclasses for storing fact information during verification.

Techniques consolidated from:
- checks/context/duplicate_detection.py (FactEntry)

DESIGN: Simple data containers with no behavior.
Used by tools across all processing stages.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FactEntry:
    """
    A fact entry with full metadata for verification.

    Stores all information needed for c-equal, u-equal, and
    decimal tolerance checks.

    Attributes:
        concept: Normalized concept name (lowercase, local name only)
        original_concept: Original concept name as reported
        value: Numeric value
        unit: Unit of measurement (e.g., 'USD', 'shares')
        decimals: Decimal precision (e.g., -6 means millions)
        context_id: XBRL context identifier
        is_nil: Whether fact is nil-valued
        source: Optional source indicator (e.g., 'mapped', 'instance')
        fact_id: Optional iXBRL fact ID (id attribute on ix:nonFraction)
        is_dimensional: Whether fact is from a dimensional context
        dimensions: Optional dimension info (axis -> member mapping)
    """
    concept: str
    original_concept: str
    value: float
    unit: Optional[str] = None
    decimals: Optional[int] = None
    context_id: str = ""
    is_nil: bool = False
    source: str = ""
    fact_id: Optional[str] = None
    is_dimensional: bool = False
    dimensions: Optional[dict] = None


@dataclass
class FactMatch:
    """
    Result of finding a fact.

    Used by FactFinder to return match results with metadata.

    Attributes:
        found: Whether fact was found
        context_id: Context where fact was found
        value: Fact value
        unit: Unit of measurement
        decimals: Decimal precision
        match_type: 'exact' (same context), 'fallback' (different context), or 'none'
    """
    found: bool = False
    context_id: str = ''
    value: Optional[float] = None
    unit: Optional[str] = None
    decimals: Optional[int] = None
    match_type: str = 'none'


@dataclass
class ChildContribution:
    """
    Contribution of a child concept to a calculation.

    Used in calculation verification to track each child's contribution.

    Attributes:
        concept: Concept name
        value: Fact value (before weight applied)
        weight: Calculation weight (1.0 or -1.0)
        contribution: Weighted contribution (value * weight)
        found: Whether fact was found
        context_id: Context where fact was found
        decimals: Decimal precision
    """
    concept: str
    value: Optional[float]
    weight: float
    contribution: Optional[float]
    found: bool
    context_id: str = ""
    decimals: Optional[int] = None


__all__ = ['FactEntry', 'FactMatch', 'ChildContribution']
