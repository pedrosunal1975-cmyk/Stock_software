# Path: xbrl_parser/validation/dimensions.py
"""
Dimensional Validator

Validates dimensional constraints and hypercube compliance.

This module validates:
- Hypercube compliance
- Required dimension checks
- Closed dimension member validation
- Dimension depth limits

Example:
    from ..validation import DimensionalValidator
    
    validator = DimensionalValidator()
    errors = validator.validate(parsed_filing)
"""

import logging
from typing import Optional

from ...core.config_loader import ConfigLoader
from ..models.parsed_filing import ParsedFiling
from ..models.error import ParsingError, ErrorSeverity, ErrorCategory
from ..validation.constants import (
    VALIDATOR_DIMENSIONAL,
    CATEGORY_DIMENSIONAL,
    ERR_DIMENSION_NOT_IN_HYPERCUBE,
    ERR_REQUIRED_DIMENSION_MISSING,
    ERR_CLOSED_DIMENSION_INVALID_MEMBER,
    ERR_DIMENSION_DEPTH_EXCEEDED,
    MSG_DIMENSION_NOT_IN_HYPERCUBE,
    MSG_REQUIRED_DIMENSION_MISSING,
    MSG_CLOSED_DIMENSION_INVALID_MEMBER,
    MSG_DIMENSION_DEPTH_EXCEEDED,
    MAX_DIMENSION_DEPTH,
    MAX_DIMENSIONS_PER_HYPERCUBE
)


class DimensionalValidator:
    """
    Validates dimensional constraints.
    
    Checks that facts comply with hypercube definitions,
    required dimensions are present, and closed dimensions
    only use valid members.
    
    Example:
        config = ConfigLoader()
        validator = DimensionalValidator(config)
        
        errors = validator.validate(parsed_filing)
        
        if errors:
            print(f"Found {len(errors)} dimensional issues")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize dimensional validator.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        
        # Get configuration
        self.enabled = self.config.get('enable_dimensional_validation', True)
        
        self.logger.debug(f"DimensionalValidator initialized: enabled={self.enabled}")
    
    def get_name(self) -> str:
        """Get validator name."""
        return VALIDATOR_DIMENSIONAL
    
    def get_category(self) -> str:
        """Get validator category."""
        return CATEGORY_DIMENSIONAL
    
    def requires_taxonomy(self) -> bool:
        """Whether validator requires taxonomy data."""
        return True
    
    def validate(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate dimensional constraints.
        
        Args:
            filing: Parsed filing to validate
            
        Returns:
            list of dimensional validation errors
        """
        if not self.enabled:
            self.logger.debug("Dimensional validation disabled")
            return []
        
        if not filing.taxonomy:
            self.logger.warning("No taxonomy available for dimensional validation")
            return []
        
        errors: list[ParsingError] = []
        
        self.logger.info(f"Validating dimensions: {filing.metadata.entry_point}")
        
        # Validate dimension depth
        errors.extend(self._validate_dimension_depth(filing))
        
        # Validate hypercube compliance (if taxonomy has hypercube info)
        if hasattr(filing.taxonomy, 'hypercubes'):
            errors.extend(self._validate_hypercube_compliance(filing))
        
        self.logger.info(f"Dimensional validation completed: {len(errors)} issues")
        return errors
    
    def _validate_dimension_depth(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate dimension depth doesn't exceed limits.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of depth validation errors
        """
        errors: list[ParsingError] = []
        
        for context_id, context in filing.instance.contexts.items():
            # Count dimensions in segment
            dimension_count = 0
            
            if context.segment:
                if hasattr(context.segment, 'explicit_dimensions'):
                    dimension_count += len(context.segment.explicit_dimensions)
                if hasattr(context.segment, 'typed_dimensions'):
                    dimension_count += len(context.segment.typed_dimensions)
            
            # Count dimensions in scenario
            if context.scenario:
                if hasattr(context.scenario, 'explicit_dimensions'):
                    dimension_count += len(context.scenario.explicit_dimensions)
                if hasattr(context.scenario, 'typed_dimensions'):
                    dimension_count += len(context.scenario.typed_dimensions)
            
            # Check depth
            if dimension_count > MAX_DIMENSION_DEPTH:
                errors.append(ParsingError(
                    category=ErrorCategory.DIMENSION_INVALID,
                    severity=ErrorSeverity.WARNING,
                    message=MSG_DIMENSION_DEPTH_EXCEEDED,
                    details={
                        'context_id': context_id,
                        'dimension_count': dimension_count,
                        'max_depth': MAX_DIMENSION_DEPTH
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _validate_hypercube_compliance(
        self,
        filing: ParsedFiling
    ) -> list[ParsingError]:
        """
        Validate facts comply with hypercube definitions.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of hypercube compliance errors
        """
        errors: list[ParsingError] = []
        
        # Get hypercube definitions from taxonomy
        hypercubes = getattr(filing.taxonomy, 'hypercubes', {})
        
        if not hypercubes:
            self.logger.debug("No hypercube definitions found")
            return errors
        
        # For each fact, check if it should comply with a hypercube
        for fact in filing.instance.facts:
            if not fact.context_ref:
                continue
            
            context = filing.instance.contexts.get(fact.context_ref)
            if not context:
                continue
            
            # Get dimensions from context
            dimensions = self._extract_dimensions(context)
            
            if not dimensions:
                continue
            
            # Find applicable hypercubes for this concept
            applicable_hypercubes = self._find_applicable_hypercubes(
                fact.concept,
                hypercubes
            )
            
            # Validate against each applicable hypercube
            for hypercube_id, hypercube_def in applicable_hypercubes.items():
                errors.extend(
                    self._validate_against_hypercube(
                        fact,
                        dimensions,
                        hypercube_id,
                        hypercube_def,
                        filing
                    )
                )
        
        return errors
    
    def _extract_dimensions(self, context: 'Context') -> dict[str, str]:
        """
        Extract dimensions from context.
        
        Args:
            context: Context object
            
        Returns:
            dict mapping dimension to member
        """
        dimensions: dict[str, str] = {}
        
        # Extract from segment
        if context.segment and hasattr(context.segment, 'explicit_dimensions'):
            for dim in context.segment.explicit_dimensions:
                if hasattr(dim, 'dimension') and hasattr(dim, 'member'):
                    dimensions[dim.dimension] = dim.member
        
        # Extract from scenario
        if context.scenario and hasattr(context.scenario, 'explicit_dimensions'):
            for dim in context.scenario.explicit_dimensions:
                if hasattr(dim, 'dimension') and hasattr(dim, 'member'):
                    dimensions[dim.dimension] = dim.member
        
        return dimensions
    
    def _find_applicable_hypercubes(
        self,
        concept: str,
        hypercubes: dict
    ) -> dict:
        """
        Find hypercubes applicable to a concept.
        
        Args:
            concept: Concept QName
            hypercubes: Hypercube definitions
            
        Returns:
            dict of applicable hypercubes
        """
        applicable: dict = {}
        
        for hypercube_id, hypercube_def in hypercubes.items():
            # Check if concept is in hypercube's primary items
            primary_items = hypercube_def.get('primary_items', [])
            
            if concept in primary_items:
                applicable[hypercube_id] = hypercube_def
        
        return applicable
    
    def _validate_against_hypercube(
        self,
        fact: 'Fact',
        dimensions: dict[str, str],
        hypercube_id: str,
        hypercube_def: dict,
        filing: ParsedFiling
    ) -> list[ParsingError]:
        """
        Validate fact against hypercube definition.
        
        Args:
            fact: Fact to validate
            dimensions: Dimensions from fact's context
            hypercube_id: Hypercube identifier
            hypercube_def: Hypercube definition
            filing: Parsed filing
            
        Returns:
            list of validation errors
        """
        errors: list[ParsingError] = []
        
        # Check required dimensions
        required_dimensions = hypercube_def.get('required_dimensions', [])
        
        for required_dim in required_dimensions:
            if required_dim not in dimensions:
                errors.append(ParsingError(
                    category=ErrorCategory.DIMENSION_INVALID,
                    severity=ErrorSeverity.ERROR,
                    message=MSG_REQUIRED_DIMENSION_MISSING,
                    details={
                        'concept': fact.concept,
                        'context_ref': fact.context_ref,
                        'hypercube': hypercube_id,
                        'required_dimension': required_dim
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
        
        # Check closed dimensions
        closed_dimensions = hypercube_def.get('closed_dimensions', {})
        
        for dim, member in dimensions.items():
            if dim in closed_dimensions:
                valid_members = closed_dimensions[dim]
                
                if member not in valid_members:
                    errors.append(ParsingError(
                        category=ErrorCategory.DIMENSION_INVALID,
                        severity=ErrorSeverity.ERROR,
                        message=MSG_CLOSED_DIMENSION_INVALID_MEMBER,
                        details={
                            'concept': fact.concept,
                            'context_ref': fact.context_ref,
                            'dimension': dim,
                            'member': member,
                            'valid_members': valid_members[:10]
                        },
                        source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                    ))
        
        return errors


__all__ = ['DimensionalValidator']
