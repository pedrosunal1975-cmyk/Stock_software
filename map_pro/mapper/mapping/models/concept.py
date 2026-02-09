# Path: mapping/models/concept.py
"""
Concept Model

XBRL concept definition (REUSED from parser with no changes).

A concept defines the meaning of a fact.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Concept:
    """
    XBRL concept definition.
    
    Attributes:
        name: Concept QName
        type: Data type (monetary, integer, string, etc.)
        period_type: instant or duration
        balance: debit or credit (for monetary items)
        abstract: Whether concept is abstract
        nillable: Whether concept can be nil
        label: Human-readable label
        documentation: Concept documentation
        metadata: Additional metadata
    """
    name: str
    type: str
    period_type: Optional[str] = None
    balance: Optional[str] = None
    abstract: bool = False
    nillable: bool = True
    label: Optional[str] = None
    documentation: Optional[str] = None
    metadata: dict[str, any] = field(default_factory=dict)
    
    def is_monetary(self) -> bool:
        """Check if concept is monetary."""
        return 'monetary' in self.type.lower()
    
    def is_numeric(self) -> bool:
        """Check if concept is numeric."""
        numeric_types = ['monetary', 'integer', 'decimal', 'float', 'percent']
        return any(t in self.type.lower() for t in numeric_types)


__all__ = ['Concept']
