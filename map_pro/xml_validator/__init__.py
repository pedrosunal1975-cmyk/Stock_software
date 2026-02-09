"""
XML Validation Module
=====================
Pre-validation for XBRL documents.
"""
from .xml_validator import (
XMLValidator,
ValidationResult,
ValidationError,
ValidationLevel,
ValidationStatus,
WellFormednessValidator,
SchemaValidator,
CustomRulesValidator,
validate_batch
)
__all__ = [
'XMLValidator',
'ValidationResult',
'ValidationError',
'ValidationLevel',
'ValidationStatus',
'WellFormednessValidator',
'SchemaValidator',
'CustomRulesValidator',
'validate_batch'
]
__version__ = '1.0.0'