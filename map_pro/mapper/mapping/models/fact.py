# Path: mapping/models/fact.py
"""
Fact Model

XBRL fact representation (REUSED from parser with no changes).
A fact is the most fundamental unit of XBRL data.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Fact:
    """
    XBRL fact representation.
    
    Attributes:
        name: Concept name (QName)
        value: Fact value
        context_ref: Context reference ID
        unit_ref: Unit reference ID (for numeric facts)
        decimals: Decimal precision
        precision: Significant figures
        footnote: Associated footnote text
        id: Fact ID
        metadata: Additional metadata
    """
    name: str
    value: any
    context_ref: str
    unit_ref: Optional[str] = None
    decimals: Optional[str] = None
    precision: Optional[str] = None
    footnote: Optional[str] = None
    id: Optional[str] = None
    metadata: dict[str, any] = field(default_factory=dict)
    
    def is_numeric(self) -> bool:
        """Check if fact is numeric."""
        return self.unit_ref is not None
    
    def is_text(self) -> bool:
        """Check if fact is text."""
        return self.unit_ref is None and isinstance(self.value, str)


__all__ = ['Fact']