# Path: mapping/models/context.py
"""
Context Model

XBRL context representation (REUSED from parser with no changes).

A context defines when and what entity a fact applies to.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import date


@dataclass
class Context:
    """
    XBRL context representation.
    
    Attributes:
        id: Context ID
        entity: Entity identifier
        period_type: instant, duration, or forever
        instant: Instant date (for instant periods)
        start_date: Start date (for duration periods)
        end_date: End date (for duration periods)
        segment: Dimensional segment (explicit members)
        scenario: Dimensional scenario
        metadata: Additional metadata
    """
    id: str
    entity: str
    period_type: str  # instant, duration, forever
    instant: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    segment: dict[str, any] = field(default_factory=dict)
    scenario: dict[str, any] = field(default_factory=dict)
    metadata: dict[str, any] = field(default_factory=dict)
    
    def is_instant(self) -> bool:
        """Check if context is instant."""
        return self.period_type == 'instant'
    
    def is_duration(self) -> bool:
        """Check if context is duration."""
        return self.period_type == 'duration'
    
    def has_dimensions(self) -> bool:
        """Check if context has dimensions."""
        return bool(self.segment or self.scenario)


__all__ = ['Context']
