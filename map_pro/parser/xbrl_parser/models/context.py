# Path: xbrl_parser/models/context.py
"""
Context Data Model

XBRL context representation with entity, period, and dimensions.

This module defines:
- Context dataclass (complete context)
- EntityIdentifier (company identifiers)
- Period types (instant, duration, forever)
- Explicit and typed dimensions
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import date, datetime
from enum import Enum


# ==============================================================================
# PERIOD TYPE
# ==============================================================================

class PeriodType(Enum):
    """
    Period type classification.
    
    Types:
        INSTANT: Single point in time
        DURATION: Time range (start to end)
        FOREVER: Permanent/unlimited timeframe (rare)
    """
    INSTANT = "instant"
    DURATION = "duration"
    FOREVER = "forever"
    
    def __str__(self) -> str:
        return self.value


# ==============================================================================
# ENTITY IDENTIFIER
# ==============================================================================

@dataclass
class EntityIdentifier:
    """
    Entity identifier with scheme.
    
    Attributes:
        scheme: Identifier scheme URI
        value: Identifier value
        
    Common Schemes:
        - CIK (US SEC): http://www.sec.gov/CIK
        - LEI (International): http://standards.iso.org/iso/17442
        - CRN (UK): http://www.companieshouse.gov.uk/
    """
    scheme: str
    value: str
    
    def is_cik(self) -> bool:
        """Check if identifier is SEC CIK."""
        return 'sec.gov/CIK' in self.scheme
    
    def is_lei(self) -> bool:
        """Check if identifier is LEI."""
        return 'iso/17442' in self.scheme
    
    def is_crn(self) -> bool:
        """Check if identifier is UK Companies House number."""
        return 'companieshouse.gov.uk' in self.scheme
    
    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {
            'scheme': self.scheme,
            'value': self.value
        }


# ==============================================================================
# PERIOD
# ==============================================================================

@dataclass
class Period:
    """
    Period (temporal context).
    
    Attributes:
        period_type: Type of period (instant, duration, forever)
        instant: Date for instant period
        start_date: Start date for duration period
        end_date: End date for duration period
        
    Usage:
        # Instant period
        Period(period_type=PeriodType.INSTANT, instant=date(2023, 12, 31))
        
        # Duration period
        Period(
            period_type=PeriodType.DURATION,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31)
        )
    """
    period_type: PeriodType
    instant: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    def is_instant(self) -> bool:
        """Check if instant period."""
        return self.period_type == PeriodType.INSTANT
    
    def is_duration(self) -> bool:
        """Check if duration period."""
        return self.period_type == PeriodType.DURATION
    
    def is_forever(self) -> bool:
        """Check if forever period."""
        return self.period_type == PeriodType.FOREVER
    
    def get_label(self) -> str:
        """
        Get human-readable period label.
        
        Returns:
            Formatted period string
        """
        if self.is_instant() and self.instant:
            return f"As of {self.instant.isoformat()}"
        elif self.is_duration() and self.start_date and self.end_date:
            return f"{self.start_date.isoformat()} to {self.end_date.isoformat()}"
        elif self.is_forever():
            return "Forever"
        else:
            return "Unknown period"
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'period_type': self.period_type.value,
            'instant': self.instant.isoformat() if self.instant else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'label': self.get_label()
        }


# ==============================================================================
# DIMENSION
# ==============================================================================

@dataclass
class ExplicitDimension:
    """
    Explicit dimension (dimension-member pair).
    
    Attributes:
        dimension: Dimension QName
        member: Member QName
        
    Example:
        ExplicitDimension(
            dimension="us-gaap:StatementGeographicalAxis",
            member="company:AmericasMember"
        )
    """
    dimension: str
    member: str
    
    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {
            'dimension': self.dimension,
            'member': self.member,
            'type': 'explicit'
        }


@dataclass
class TypedDimension:
    """
    Typed dimension (dimension with XML value).
    
    Attributes:
        dimension: Dimension QName
        value_xml: XML fragment as string (preserved exactly)
        
    Example:
        TypedDimension(
            dimension="example:CustomDimension",
            value_xml="<value>123</value>"
        )
    """
    dimension: str
    value_xml: str
    
    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {
            'dimension': self.dimension,
            'value_xml': self.value_xml,
            'type': 'typed'
        }


# ==============================================================================
# SEGMENT AND SCENARIO
# ==============================================================================

@dataclass
class Segment:
    """
    Segment section of context (entity breakdown).
    
    Attributes:
        explicit_dimensions: list of explicit dimension-member pairs
        typed_dimensions: list of typed dimensions with XML values
    """
    explicit_dimensions: list[ExplicitDimension] = field(default_factory=list)
    typed_dimensions: list[TypedDimension] = field(default_factory=list)
    
    def has_dimensions(self) -> bool:
        """Check if segment has any dimensions."""
        return len(self.explicit_dimensions) > 0 or len(self.typed_dimensions) > 0
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'explicit_dimensions': [d.to_dict() for d in self.explicit_dimensions],
            'typed_dimensions': [d.to_dict() for d in self.typed_dimensions]
        }


@dataclass
class Scenario:
    """
    Scenario section of context (scenario breakdown).
    
    Attributes:
        explicit_dimensions: list of explicit dimension-member pairs
        typed_dimensions: list of typed dimensions with XML values
    """
    explicit_dimensions: list[ExplicitDimension] = field(default_factory=list)
    typed_dimensions: list[TypedDimension] = field(default_factory=list)
    
    def has_dimensions(self) -> bool:
        """Check if scenario has any dimensions."""
        return len(self.explicit_dimensions) > 0 or len(self.typed_dimensions) > 0
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'explicit_dimensions': [d.to_dict() for d in self.explicit_dimensions],
            'typed_dimensions': [d.to_dict() for d in self.typed_dimensions]
        }


# ==============================================================================
# CONTEXT
# ==============================================================================

@dataclass
class Context:
    """
    Complete XBRL context.
    
    Attributes:
        id: Context ID (unique within filing)
        entity: Entity identifier
        period: Period information
        segment: Segment (optional, entity breakdown)
        scenario: Scenario (optional, scenario breakdown)
        
    Example:
        Context(
            id="c1",
            entity=EntityIdentifier(
                scheme="http://www.sec.gov/CIK",
                value="0000320193"
            ),
            period=Period(
                period_type=PeriodType.INSTANT,
                instant=date(2023, 12, 31)
            )
        )
    """
    id: str
    entity: EntityIdentifier
    period: Period
    segment: Optional[Segment] = None
    scenario: Optional[Scenario] = None
    
    def has_dimensions(self) -> bool:
        """
        Check if context has any dimensions.
        
        Returns:
            True if segment or scenario has dimensions
        """
        if self.segment and self.segment.has_dimensions():
            return True
        if self.scenario and self.scenario.has_dimensions():
            return True
        return False
    
    def get_all_dimensions(self) -> list[ExplicitDimension]:
        """
        Get all explicit dimensions from segment and scenario.
        
        Returns:
            list of all explicit dimensions
        """
        dimensions = []
        if self.segment:
            dimensions.extend(self.segment.explicit_dimensions)
        if self.scenario:
            dimensions.extend(self.scenario.explicit_dimensions)
        return dimensions
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'entity': self.entity.to_dict(),
            'period': self.period.to_dict(),
            'segment': self.segment.to_dict() if self.segment else None,
            'scenario': self.scenario.to_dict() if self.scenario else None,
            'has_dimensions': self.has_dimensions()
        }


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_context(
    context_id: str,
    entity_scheme: str,
    entity_value: str,
    period_type: PeriodType,
    **kwargs
) -> Context:
    """
    Convenience function to create a Context.
    
    Args:
        context_id: Context ID
        entity_scheme: Entity identifier scheme
        entity_value: Entity identifier value
        period_type: Type of period
        **kwargs: Additional period and context attributes
        
    Returns:
        Context instance
    """
    entity = EntityIdentifier(scheme=entity_scheme, value=entity_value)
    period = Period(period_type=period_type, **kwargs)
    
    return Context(
        id=context_id,
        entity=entity,
        period=period
    )


def create_instant_context(
    context_id: str,
    entity_scheme: str,
    entity_value: str,
    instant: date
) -> Context:
    """Create instant period context."""
    return Context(
        id=context_id,
        entity=EntityIdentifier(scheme=entity_scheme, value=entity_value),
        period=Period(period_type=PeriodType.INSTANT, instant=instant)
    )


def create_duration_context(
    context_id: str,
    entity_scheme: str,
    entity_value: str,
    start_date: date,
    end_date: date
) -> Context:
    """Create duration period context."""
    return Context(
        id=context_id,
        entity=EntityIdentifier(scheme=entity_scheme, value=entity_value),
        period=Period(
            period_type=PeriodType.DURATION,
            start_date=start_date,
            end_date=end_date
        )
    )


__all__ = [
    'PeriodType',
    'EntityIdentifier',
    'Period',
    'ExplicitDimension',
    'TypedDimension',
    'Segment',
    'Scenario',
    'Context',
    'create_context',
    'create_instant_context',
    'create_duration_context',
]