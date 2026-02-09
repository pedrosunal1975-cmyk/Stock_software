"""
XBRL Period Type Validation

This module contains validation rules for XBRL period types as defined
by the XBRL 2.1 Specification.

SOURCE AUTHORITY:
----------------
XBRL 2.1 Specification Section 4.9 "Tuples"
XBRL 2.1 Specification Section 5.1.1.1 "The @periodType attribute"

Published by: XBRL International (now IFRS Foundation)

CRITICAL NOTE:
-------------
This module contains ONLY the validation RULES from the specification.
The actual @periodType declarations come from taxonomy schema files - NOT here.

SCOPE:
------
UNIVERSAL - applies to all XBRL 2.1 filings globally
"""

from typing import Literal


# XBRL 2.1 Specification Section 4.7.2 - Period Type Values
PERIOD_TYPE_INSTANT = 'instant'
PERIOD_TYPE_DURATION = 'duration'
PERIOD_TYPE_FOREVER = 'forever'

# Type alias for period types
PeriodType = Literal['instant', 'duration', 'forever']

# Set of valid period types
VALID_PERIOD_TYPES = {PERIOD_TYPE_INSTANT, PERIOD_TYPE_DURATION, PERIOD_TYPE_FOREVER}


def validate_period_type(
    concept_period_type: str,
    context_period_type: str
) -> bool:
    """
    Validate that a concept's period type matches its context's period type.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 5.1.1.1 "The @periodType attribute"
    
    SPECIFICATION RULES:
    -------------------
    1. instant concept + instant period = âœ… VALID
    2. duration concept + duration period = âœ… VALID
    3. instant concept + duration period = âŒ INVALID
    4. duration concept + instant period = âŒ INVALID
    
    SPECIFICATION QUOTE:
    -------------------
    "Concepts whose @periodType attribute has the value 'instant' can only
    be associated with contexts that have instant periods. Concepts whose
    @periodType attribute has the value 'duration' can only be associated
    with contexts that have duration periods."
    
    IMPORTANT:
    ---------
    The @periodType attribute is defined in TAXONOMY SCHEMA files (.xsd).
    This function only validates the MATCHING RULE.
    
    Args:
        concept_period_type: The @periodType from concept definition (from .xsd)
        context_period_type: The period type from context (from instance)
        
    Returns:
        True if valid combination per specification
        
    Raises:
        ValueError: If invalid period type values provided
        
    Examples:
        >>> validate_period_type('instant', 'instant')
        True
        
        >>> validate_period_type('duration', 'duration')
        True
        
        >>> validate_period_type('instant', 'duration')
        False
        
        >>> validate_period_type('duration', 'instant')
        False
    """
    # Validate input values
    if concept_period_type not in VALID_PERIOD_TYPES:
        raise ValueError(
            f"Invalid concept_period_type: {concept_period_type}. "
            f"Must be '{PERIOD_TYPE_INSTANT}', '{PERIOD_TYPE_DURATION}', or '{PERIOD_TYPE_FOREVER}'"
        )
    
    if context_period_type not in VALID_PERIOD_TYPES:
        raise ValueError(
            f"Invalid context_period_type: {context_period_type}. "
            f"Must be '{PERIOD_TYPE_INSTANT}', '{PERIOD_TYPE_DURATION}', or '{PERIOD_TYPE_FOREVER}'"
        )
    
    # XBRL 2.1 Spec Section 5.1.1.1:
    # Period types must match exactly
    return concept_period_type == context_period_type


def get_validation_error_message(
    concept_name: str,
    concept_period_type: str,
    context_period_type: str
) -> str:
    """
    Generate error message for period type mismatch.
    
    Args:
        concept_name: Name of the concept
        concept_period_type: Expected period type from concept
        context_period_type: Actual period type from context
        
    Returns:
        Human-readable error message
        
    Example:
        >>> get_validation_error_message(
        ...     'us-gaap:Assets',
        ...     'instant',
        ...     'duration'
        ... )
        "Period type mismatch for 'us-gaap:Assets': concept requires 'instant' \
period but context has 'duration' period"
    """
    return (
        f"Period type mismatch for '{concept_name}': "
        f"concept requires '{concept_period_type}' period "
        f"but context has '{context_period_type}' period"
    )


# Export public functions and constants
__all__ = [
    # Period type constants
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_DURATION',
    'PERIOD_TYPE_FOREVER',
    'VALID_PERIOD_TYPES',
    'PeriodType',
    
    # Functions
    'validate_period_type',
    'get_validation_error_message',
]