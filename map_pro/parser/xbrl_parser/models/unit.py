# Path: xbrl_parser/models/unit.py
"""
Unit Data Model

XBRL unit representation for numeric facts.

This module defines:
- Unit dataclass (simple and complex units)
- UnitType enum
- Currency extraction
- Unit validation
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ==============================================================================
# UNIT TYPE
# ==============================================================================

class UnitType(Enum):
    """
    Unit type classification.
    
    Types:
        SIMPLE: Single measure (e.g., USD, shares, pure)
        COMPLEX: Ratio with numerator and denominator (e.g., USD/share)
    """
    SIMPLE = "SIMPLE"
    COMPLEX = "COMPLEX"
    
    def __str__(self) -> str:
        return self.value


# ==============================================================================
# UNIT
# ==============================================================================

@dataclass
class Unit:
    """
    XBRL unit representation.
    
    Attributes:
        id: Unit ID (unique within filing)
        unit_type: Type of unit (SIMPLE or COMPLEX)
        measures: list of measure QNames (for simple units)
        numerator: list of measure QNames (for complex units)
        denominator: list of measure QNames (for complex units)
        
    Examples:
        # Simple unit (USD)
        Unit(
            id="usd",
            unit_type=UnitType.SIMPLE,
            measures=["iso4217:USD"]
        )
        
        # Complex unit (USD per share)
        Unit(
            id="usd_per_share",
            unit_type=UnitType.COMPLEX,
            numerator=["iso4217:USD"],
            denominator=["xbrli:shares"]
        )
    """
    id: str
    unit_type: UnitType
    measures: list[str] = field(default_factory=list)
    numerator: list[str] = field(default_factory=list)
    denominator: list[str] = field(default_factory=list)
    
    def is_simple(self) -> bool:
        """Check if unit is simple type."""
        return self.unit_type == UnitType.SIMPLE
    
    def is_complex(self) -> bool:
        """Check if unit is complex type."""
        return self.unit_type == UnitType.COMPLEX
    
    def is_monetary(self) -> bool:
        """
        Check if unit is monetary (currency).
        
        Returns:
            True if unit contains ISO 4217 currency code
        """
        all_measures = self.measures + self.numerator
        return any('iso4217:' in m.lower() or 'currency:' in m.lower() 
                  for m in all_measures)
    
    def is_shares(self) -> bool:
        """Check if unit is shares."""
        all_measures = self.measures + self.numerator + self.denominator
        return any('shares' in m.lower() for m in all_measures)
    
    def is_pure(self) -> bool:
        """Check if unit is pure (dimensionless)."""
        all_measures = self.measures + self.numerator
        return any('pure' in m.lower() for m in all_measures)
    
    def get_currency_code(self) -> Optional[str]:
        """
        Extract currency code from unit.
        
        Returns:
            Currency code (e.g., 'USD', 'EUR') or None
            
        Example:
            unit.measures = ['iso4217:USD']
            unit.get_currency_code()  # Returns 'USD'
        """
        all_measures = self.measures + self.numerator
        
        for measure in all_measures:
            measure_lower = measure.lower()
            if 'iso4217:' in measure_lower:
                # Extract after colon
                parts = measure.split(':')
                if len(parts) > 1:
                    return parts[-1].upper()
            elif 'currency:' in measure_lower:
                parts = measure.split(':')
                if len(parts) > 1:
                    return parts[-1].upper()
        
        return None
    
    def get_display_name(self) -> str:
        """
        Get human-readable unit name.
        
        Returns:
            Display name for unit
        """
        if self.is_simple():
            if self.is_monetary():
                currency = self.get_currency_code()
                return currency if currency else "Currency"
            elif self.is_shares():
                return "Shares"
            elif self.is_pure():
                return "Pure"
            elif len(self.measures) == 1:
                # Extract local name from QName
                measure = self.measures[0]
                if ':' in measure:
                    return measure.split(':')[-1]
                return measure
            else:
                return ", ".join(self.measures)
        else:
            # Complex unit - show ratio
            num = "/".join(m.split(':')[-1] if ':' in m else m 
                          for m in self.numerator)
            den = "/".join(m.split(':')[-1] if ':' in m else m 
                          for m in self.denominator)
            return f"{num} per {den}"
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for serialization."""
        result = {
            'id': self.id,
            'unit_type': self.unit_type.value,
            'display_name': self.get_display_name(),
            'is_monetary': self.is_monetary(),
            'is_shares': self.is_shares(),
            'is_pure': self.is_pure(),
        }
        
        if self.is_simple():
            result['measures'] = self.measures
            if self.is_monetary():
                result['currency_code'] = self.get_currency_code()
        else:
            result['numerator'] = self.numerator
            result['denominator'] = self.denominator
        
        return result


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_unit(
    unit_id: str,
    unit_type: UnitType,
    **kwargs
) -> Unit:
    """
    Convenience function to create a Unit.
    
    Args:
        unit_id: Unit ID
        unit_type: Type of unit
        **kwargs: measures, numerator, or denominator
        
    Returns:
        Unit instance
    """
    return Unit(
        id=unit_id,
        unit_type=unit_type,
        **kwargs
    )


def create_simple_unit(unit_id: str, measures: list[str]) -> Unit:
    """
    Create simple unit.
    
    Args:
        unit_id: Unit ID
        measures: list of measure QNames
        
    Returns:
        Simple Unit
    """
    return Unit(
        id=unit_id,
        unit_type=UnitType.SIMPLE,
        measures=measures
    )


def create_complex_unit(
    unit_id: str,
    numerator: list[str],
    denominator: list[str]
) -> Unit:
    """
    Create complex unit (ratio).
    
    Args:
        unit_id: Unit ID
        numerator: Numerator measure QNames
        denominator: Denominator measure QNames
        
    Returns:
        Complex Unit
    """
    return Unit(
        id=unit_id,
        unit_type=UnitType.COMPLEX,
        numerator=numerator,
        denominator=denominator
    )


def create_currency_unit(unit_id: str, currency_code: str) -> Unit:
    """
    Create currency unit.
    
    Args:
        unit_id: Unit ID
        currency_code: ISO 4217 currency code (e.g., 'USD', 'EUR')
        
    Returns:
        Currency Unit
    """
    return Unit(
        id=unit_id,
        unit_type=UnitType.SIMPLE,
        measures=[f"iso4217:{currency_code}"]
    )


def create_shares_unit(unit_id: str = "shares") -> Unit:
    """Create shares unit."""
    return Unit(
        id=unit_id,
        unit_type=UnitType.SIMPLE,
        measures=["xbrli:shares"]
    )


def create_pure_unit(unit_id: str = "pure") -> Unit:
    """Create pure (dimensionless) unit."""
    return Unit(
        id=unit_id,
        unit_type=UnitType.SIMPLE,
        measures=["xbrli:pure"]
    )


__all__ = [
    'UnitType',
    'Unit',
    'create_unit',
    'create_simple_unit',
    'create_complex_unit',
    'create_currency_unit',
    'create_shares_unit',
    'create_pure_unit',
]