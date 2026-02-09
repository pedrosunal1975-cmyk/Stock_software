# Path: xbrl_parser/validation/structural.py
"""
Structural Validator

Validates XBRL document structure and reference integrity.

This module validates:
- Fact-level structure (context/unit references)
- Context structure (entity, period, dimensions)
- Unit structure (measures, divide operations)
- Required attributes and mutual exclusivity
- XBRL 2.1 specification compliance

Example:
    from ..validation import StructuralValidator
    
    validator = StructuralValidator()
    errors = validator.validate(parsed_filing)
    
    for error in errors:
        print(f"{error.code}: {error.message}")
"""

import logging
from typing import Optional
from datetime import date, datetime

from ...core.config_loader import ConfigLoader
from ..models.parsed_filing import ParsedFiling
from ..models.error import ParsingError, ErrorSeverity, ErrorCategory
from ..models.fact import FactType
from ..validation.constants import (
    VALIDATOR_STRUCTURAL,
    CATEGORY_STRUCTURAL,
    ERR_MISSING_CONTEXT,
    ERR_MISSING_UNIT,
    ERR_INVALID_CONTEXT_REF,
    ERR_INVALID_UNIT_REF,
    ERR_INVALID_DIMENSION_REF,
    ERR_INVALID_MEMBER_REF,
    ERR_MISSING_REQUIRED_ATTRIBUTE,
    ERR_MUTUALLY_EXCLUSIVE_ATTRIBUTES,
    ERR_INVALID_PERIOD,
    ERR_INVALID_DATE_FORMAT,
    MSG_MISSING_CONTEXT,
    MSG_MISSING_UNIT,
    MSG_INVALID_CONTEXT_REF,
    MSG_INVALID_UNIT_REF,
    MSG_INVALID_DIMENSION_REF,
    MSG_INVALID_MEMBER_REF,
    MSG_MISSING_REQUIRED_ATTRIBUTE,
    MSG_MUTUALLY_EXCLUSIVE_ATTRIBUTES,
    MSG_INVALID_PERIOD,
    MSG_INVALID_DATE_FORMAT,
    REQUIRED_FACT_ATTRIBUTES,
    REQUIRED_NUMERIC_FACT_ATTRIBUTES,
    MAX_CONTEXTS_WARNING_THRESHOLD,
    MAX_UNITS_WARNING_THRESHOLD,
    MAX_FACTS_WARNING_THRESHOLD,
    MAX_DIMENSION_DEPTH
)


class StructuralValidator:
    """
    Validates XBRL structural integrity.
    
    Checks that all references are valid, required attributes are present,
    and structures conform to XBRL specification.
    
    Example:
        config = ConfigLoader()
        validator = StructuralValidator(config)
        
        errors = validator.validate(parsed_filing)
        
        if errors:
            print(f"Found {len(errors)} structural issues")
            for error in errors:
                print(f"  {error.code}: {error.message}")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize structural validator.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("StructuralValidator initialized")
    
    def get_name(self) -> str:
        """Get validator name."""
        return VALIDATOR_STRUCTURAL
    
    def get_category(self) -> str:
        """Get validator category."""
        return CATEGORY_STRUCTURAL
    
    def requires_taxonomy(self) -> bool:
        """Whether validator requires taxonomy data."""
        return True
    
    def validate(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate filing structure.
        
        Args:
            filing: Parsed filing to validate
            
        Returns:
            list of structural validation errors
        """
        errors: list[ParsingError] = []
        
        self.logger.info(f"Validating structure: {filing.metadata.entry_point}")
        
        # Validate fact references
        errors.extend(self._validate_fact_references(filing))
        
        # Validate context structure
        errors.extend(self._validate_contexts(filing))
        
        # Validate unit structure
        errors.extend(self._validate_units(filing))
        
        # Validate thresholds
        errors.extend(self._validate_thresholds(filing))
        
        self.logger.info(f"Structural validation completed: {len(errors)} issues")
        return errors
    
    def _validate_fact_references(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate that facts reference valid contexts and units.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of reference validation errors
        """
        errors: list[ParsingError] = []
        
        # Build context and unit ID sets
        context_ids = set(filing.instance.contexts.keys())
        unit_ids = set(filing.instance.units.keys())
        
        for fact in filing.instance.facts:
            # Check contextRef
            if not fact.context_ref:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.ERROR,
                    message=f"Fact {fact.concept} missing contextRef",
                    details={'concept': fact.concept, 'attribute': 'contextRef'},
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
            elif fact.context_ref not in context_ids:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.ERROR,
                    message=MSG_INVALID_CONTEXT_REF,
                    details={
                        'concept': fact.concept,
                        'context_ref': fact.context_ref
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
            
            # Check unitRef for numeric facts
            if fact.fact_type == FactType.NUMERIC:
                if not fact.unit_ref:
                    errors.append(ParsingError(
                        category=ErrorCategory.XBRL_INVALID,
                        severity=ErrorSeverity.ERROR,
                        message=f"Numeric fact {fact.concept} missing unitRef",
                        details={'concept': fact.concept, 'attribute': 'unitRef'},
                        source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                    ))
                elif fact.unit_ref not in unit_ids:
                    errors.append(ParsingError(
                        category=ErrorCategory.XBRL_INVALID,
                        severity=ErrorSeverity.ERROR,
                        message=MSG_INVALID_UNIT_REF,
                        details={
                            'concept': fact.concept,
                            'unit_ref': fact.unit_ref
                        },
                        source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                    ))
            
            # Check mutually exclusive attributes
            if fact.decimals is not None and fact.precision is not None:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.ERROR,
                    message=MSG_MUTUALLY_EXCLUSIVE_ATTRIBUTES,
                    details={
                        'concept': fact.concept,
                        'attributes': ['decimals', 'precision']
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _validate_contexts(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate context structure.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of context validation errors
        """
        errors: list[ParsingError] = []
        
        for context_id, context in filing.instance.contexts.items():
            # Validate period dates
            if context.period.start_date and context.period.end_date:
                if context.period.start_date > context.period.end_date:
                    errors.append(ParsingError(
                        category=ErrorCategory.XBRL_INVALID,
                        severity=ErrorSeverity.ERROR,
                        message=MSG_INVALID_PERIOD,
                        details={
                            'context_id': context_id,
                            'start_date': str(context.period.start_date),
                            'end_date': str(context.period.end_date)
                        },
                        source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                    ))
            
            # Validate dimensions if taxonomy available
            if filing.taxonomy:
                if context.segment:
                    errors.extend(
                        self._validate_dimensions(
                            context.segment.explicit_dimensions,
                            context.segment.typed_dimensions,
                            filing,
                            context_id
                        )
                    )
                
                if context.scenario:
                    errors.extend(
                        self._validate_dimensions(
                            context.scenario.explicit_dimensions,
                            context.scenario.typed_dimensions,
                            filing,
                            context_id
                        )
                    )
        
        return errors
    
    def _validate_dimensions(
        self,
        explicit_dims: list,
        typed_dims: list,
        filing: ParsedFiling,
        context_id: str
    ) -> list[ParsingError]:
        """
        Validate dimensional references.
        
        Args:
            explicit_dims: list of explicit dimensions
            typed_dims: list of typed dimensions
            filing: Parsed filing
            context_id: Context identifier
            
        Returns:
            list of dimension validation errors
        """
        errors: list[ParsingError] = []
        
        # Validate explicit dimensions
        for dim in explicit_dims:
            # Check if dimension exists in taxonomy
            if filing.taxonomy and not filing.taxonomy.has_concept(dim.dimension):
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.ERROR,
                    message=MSG_INVALID_DIMENSION_REF,
                    details={
                        'context_id': context_id,
                        'dimension': dim.dimension,
                        'member': dim.member
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
            
            # Check if member exists in taxonomy
            if filing.taxonomy and not filing.taxonomy.has_concept(dim.member):
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.ERROR,
                    message=MSG_INVALID_MEMBER_REF,
                    details={
                        'context_id': context_id,
                        'dimension': dim.dimension,
                        'member': dim.member
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
        
        # Validate typed dimensions
        for dim in typed_dims:
            # Check if dimension exists in taxonomy
            if filing.taxonomy and not filing.taxonomy.has_concept(dim.dimension):
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.ERROR,
                    message=MSG_INVALID_DIMENSION_REF,
                    details={
                        'context_id': context_id,
                        'dimension': dim.dimension,
                        'type': 'typed'
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _validate_units(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate unit structure.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of unit validation errors
        """
        errors: list[ParsingError] = []
        
        for unit_id, unit in filing.instance.units.items():
            # Validate measures exist
            if not unit.measures and not unit.numerator:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.ERROR,
                    message="Unit has no measures defined",
                    details={'unit_id': unit_id},
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
            
            # Validate divide units have both numerator and denominator
            if unit.numerator and not unit.denominator:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.ERROR,
                    message="Unit has numerator but no denominator",
                    details={'unit_id': unit_id},
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
            elif unit.denominator and not unit.numerator:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.ERROR,
                    message="Unit has denominator but no numerator",
                    details={'unit_id': unit_id},
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _validate_thresholds(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate element count thresholds.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of threshold warnings
        """
        errors: list[ParsingError] = []
        
        # Check context count
        context_count = len(filing.instance.contexts)
        if context_count > MAX_CONTEXTS_WARNING_THRESHOLD:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.WARNING,
                message=f"High context count: {context_count}",
                details={
                    'count': context_count,
                    'threshold': MAX_CONTEXTS_WARNING_THRESHOLD
                },
                source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
            ))
        
        # Check unit count
        unit_count = len(filing.instance.units)
        if unit_count > MAX_UNITS_WARNING_THRESHOLD:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.WARNING,
                message=f"High unit count: {unit_count}",
                details={
                    'count': unit_count,
                    'threshold': MAX_UNITS_WARNING_THRESHOLD
                },
                source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
            ))
        
        # Check fact count
        fact_count = len(filing.instance.facts)
        if fact_count > MAX_FACTS_WARNING_THRESHOLD:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.WARNING,
                message=f"High fact count: {fact_count}",
                details={
                    'count': fact_count,
                    'threshold': MAX_FACTS_WARNING_THRESHOLD
                },
                source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
            ))
        
        return errors


__all__ = ['StructuralValidator']
