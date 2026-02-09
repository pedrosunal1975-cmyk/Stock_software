# Path: components/validators.py
"""
Validators

Common validation functions for facts and contexts.
Water paradigm - no transformation/mapping validation.
"""

from ..mapping.models.fact import Fact
from ..mapping.models.context import Context
from ..components.constants import (
    PERIOD_TYPE_INSTANT,
    PERIOD_TYPE_DURATION,
)


class ValidationError(Exception):
    """Validation error exception."""
    pass


class Validators:
    """
    Common validation functions.
    
    Example:
        # Validate fact
        Validators.validate_fact(fact)
        
        # Validate context
        Validators.validate_context(context)
    """
    
    @staticmethod
    def validate_fact(fact: Fact) -> list[str]:
        """
        Validate fact.
        
        Args:
            fact: Fact to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not fact.name:
            errors.append("Fact missing name")
        
        if fact.value is None:
            errors.append("Fact missing value")
        
        if not fact.context_ref:
            errors.append("Fact missing context_ref")
        
        # Numeric facts must have unit
        if fact.is_numeric() and not fact.unit_ref:
            errors.append("Numeric fact missing unit_ref")
        
        return errors
    
    @staticmethod
    def validate_context(context: Context) -> list[str]:
        """
        Validate context.
        
        Args:
            context: Context to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not context.id:
            errors.append("Context missing ID")
        
        if not context.entity:
            errors.append("Context missing entity")
        
        if not context.period_type:
            errors.append("Context missing period_type")
        
        # Instant must have instant date
        if context.period_type == PERIOD_TYPE_INSTANT and not context.instant:
            errors.append("Instant context missing instant date")
        
        # Duration must have start and end
        if context.period_type == PERIOD_TYPE_DURATION:
            if not context.start_date:
                errors.append("Duration context missing start_date")
            if not context.end_date:
                errors.append("Duration context missing end_date")
            if context.start_date and context.end_date and context.start_date > context.end_date:
                errors.append("Duration start_date after end_date")
        
        return errors


def validate_fact(fact: Fact) -> None:
    """
    Validate fact (raises exception if invalid).
    
    Args:
        fact: Fact to validate
        
    Raises:
        ValidationError: If validation fails
    """
    errors = Validators.validate_fact(fact)
    if errors:
        raise ValidationError(f"Fact validation failed: {', '.join(errors)}")


def validate_context(context: Context) -> None:
    """
    Validate context (raises exception if invalid).
    
    Args:
        context: Context to validate
        
    Raises:
        ValidationError: If validation fails
    """
    errors = Validators.validate_context(context)
    if errors:
        raise ValidationError(f"Context validation failed: {', '.join(errors)}")


__all__ = [
    'Validators',
    'ValidationError',
    'validate_fact',
    'validate_context',
]