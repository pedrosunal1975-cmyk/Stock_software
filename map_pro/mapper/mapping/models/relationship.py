# Path: mapping/models/relationship.py
"""
Relationship Model

XBRL relationship representation (REUSED from parser with no changes).

Relationships define structure (presentation, calculation, definition).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Relationship:
    """
    XBRL relationship representation.
    
    Attributes:
        from_concept: Source concept
        to_concept: Target concept
        arcrole: Relationship arcrole
        order: Presentation order
        weight: Calculation weight
        preferred_label: Preferred label role
        metadata: Additional metadata
    """
    from_concept: str
    to_concept: str
    arcrole: str
    order: Optional[float] = None
    weight: Optional[float] = None
    preferred_label: Optional[str] = None
    metadata: dict[str, any] = field(default_factory=dict)
    
    def is_presentation(self) -> bool:
        """Check if relationship is presentation."""
        return 'parent-child' in self.arcrole
    
    def is_calculation(self) -> bool:
        """Check if relationship is calculation."""
        return 'summation-item' in self.arcrole


__all__ = ['Relationship']
