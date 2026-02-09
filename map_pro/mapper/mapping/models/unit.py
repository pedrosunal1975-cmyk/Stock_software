# Path: mapping/models/unit.py
"""
Unit Model

XBRL unit representation (REUSED from parser with no changes).

A unit defines the measurement unit for numeric facts.
"""

from dataclasses import dataclass, field


@dataclass
class Unit:
    """
    XBRL unit representation.
    
    Attributes:
        id: Unit ID
        measures: List of measures
        is_divide: Whether this is a divide unit
        numerator: Numerator measures (for divide units)
        denominator: Denominator measures (for divide units)
        metadata: Additional metadata
    """
    id: str
    measures: list[str] = field(default_factory=list)
    is_divide: bool = False
    numerator: list[str] = field(default_factory=list)
    denominator: list[str] = field(default_factory=list)
    metadata: dict[str, any] = field(default_factory=dict)
    
    def is_pure(self) -> bool:
        """Check if unit is pure (dimensionless)."""
        return 'pure' in self.measures or 'xbrli:pure' in self.measures
    
    def is_currency(self) -> bool:
        """Check if unit is currency."""
        return any('iso4217:' in m or 'USD' in m or 'EUR' in m for m in self.measures)


__all__ = ['Unit']
