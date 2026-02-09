# Path: xbrl_parser/validation/__init__.py
"""
Validation Module

Components for validating XBRL documents.

This module provides:
- Validation registry (coordinator)
- Structural validator (references, structure)
- Calculation validator (arithmetic relationships)
- Dimensional validator (hypercube compliance)
- Completeness validator (orphan detection)
- Constants (thresholds, error codes, messages)

Example:
    from ..validation import (
        ValidationRegistry,
        StructuralValidator,
        CalculationValidator,
        DimensionalValidator,
        CompletenessValidator
    )
    
    # Create registry
    registry = ValidationRegistry()
    
    # Register validators
    registry.register_validator(StructuralValidator(), priority=10)
    registry.register_validator(CalculationValidator(), priority=20)
    registry.register_validator(DimensionalValidator(), priority=30)
    registry.register_validator(CompletenessValidator(), priority=40)
    
    # Validate filing
    results = registry.validate_filing(parsed_filing)
    
    if results.has_errors():
        print(f"Validation failed: {results.total_errors} errors")
"""

from ..validation.registry import (
    ValidationRegistry,
    BaseValidator,
    ValidatorInfo
)
from ..validation.structural import StructuralValidator
from ..validation.calculations import CalculationValidator
from ..validation.dimensions import DimensionalValidator
from ..validation.completeness import CompletenessValidator
from ..validation import constants


__all__ = [
    # Registry
    'ValidationRegistry',
    'BaseValidator',
    'ValidatorInfo',
    
    # Validators
    'StructuralValidator',
    'CalculationValidator',
    'DimensionalValidator',
    'CompletenessValidator',
    
    # Constants
    'constants'
]
