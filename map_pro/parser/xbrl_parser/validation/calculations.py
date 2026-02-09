# Path: xbrl_parser/validation/calculations.py
"""
Calculation Validator

Validates XBRL calculation relationships and arithmetic consistency.

This module validates:
- Calculation relationship discovery
- Arithmetic verification with tolerance
- Context matching for calculations
- Inconsistency reporting

Example:
    from ..validation import CalculationValidator
    
    validator = CalculationValidator()
    errors = validator.validate(parsed_filing)
    
    for error in errors:
        print(f"{error.severity}: {error.message}")
"""

import logging
from typing import Optional
from decimal import Decimal, InvalidOperation

from ...core.config_loader import ConfigLoader
from ..models.parsed_filing import ParsedFiling
from ..models.error import ParsingError, ErrorSeverity, ErrorCategory
from ..models.fact import FactType
from ..validation.constants import (
    VALIDATOR_CALCULATION,
    CATEGORY_CALCULATION,
    ERR_CALCULATION_INCONSISTENT,
    ERR_CALCULATION_MISSING_FACT,
    ERR_CALCULATION_CONTEXT_MISMATCH,
    ERR_CALCULATION_TOLERANCE_EXCEEDED,
    MSG_CALCULATION_INCONSISTENT,
    MSG_CALCULATION_MISSING_FACT,
    MSG_CALCULATION_CONTEXT_MISMATCH,
    MSG_CALCULATION_TOLERANCE_EXCEEDED,
    DEFAULT_CALCULATION_TOLERANCE,
    INFINITE_PRECISION,
    TOLERANCE_DECIMAL_PRECISION
)


class CalculationValidator:
    """
    Validates calculation relationships.
    
    Checks that calculation relationships balance within tolerance,
    all required facts are present, and contexts match.
    
    Example:
        config = ConfigLoader()
        validator = CalculationValidator(config)
        
        errors = validator.validate(parsed_filing)
        
        if errors:
            print(f"Found {len(errors)} calculation issues")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize calculation validator.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        
        # Get configuration
        self.enabled = self.config.get('enable_calculation_validation', True)
        self.tolerance = self.config.get('calculation_tolerance', DEFAULT_CALCULATION_TOLERANCE)
        
        self.logger.debug(
            f"CalculationValidator initialized: enabled={self.enabled}, "
            f"tolerance={self.tolerance}"
        )
    
    def get_name(self) -> str:
        """Get validator name."""
        return VALIDATOR_CALCULATION
    
    def get_category(self) -> str:
        """Get validator category."""
        return CATEGORY_CALCULATION
    
    def requires_taxonomy(self) -> bool:
        """Whether validator requires taxonomy data."""
        return True
    
    def validate(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate calculation relationships.
        
        Args:
            filing: Parsed filing to validate
            
        Returns:
            list of calculation validation errors
        """
        if not self.enabled:
            self.logger.debug("Calculation validation disabled")
            return []
        
        if not filing.taxonomy:
            self.logger.warning("No taxonomy available for calculation validation")
            return []
        
        errors: list[ParsingError] = []
        
        self.logger.info(f"Validating calculations: {filing.metadata.entry_point}")
        
        # Get calculation relationships from taxonomy
        calc_relationships = self._discover_calculations(filing)
        
        if not calc_relationships:
            self.logger.debug("No calculation relationships found")
            return []
        
        # Validate each calculation
        for parent_concept, children in calc_relationships.items():
            errors.extend(
                self._validate_calculation(
                    parent_concept,
                    children,
                    filing
                )
            )
        
        self.logger.info(f"Calculation validation completed: {len(errors)} issues")
        return errors
    
    def _discover_calculations(
        self,
        filing: ParsedFiling
    ) -> dict[str, list[tuple[str, float]]]:
        """
        Discover calculation relationships from taxonomy.
        
        Args:
            filing: Parsed filing
            
        Returns:
            dict mapping parent concepts to list of (child_concept, weight) tuples
        """
        calculations: dict[str, list[tuple[str, float]]] = {}
        
        if not filing.taxonomy or not filing.taxonomy.calculation_networks:
            return calculations
        
        # Extract calculation relationships from networks
        for network in filing.taxonomy.calculation_networks:
            for parent, children in network.items():
                if parent not in calculations:
                    calculations[parent] = []
                
                for child in children:
                    # Child should have concept and weight
                    concept = child.get('concept', child.get('to_concept'))
                    weight = child.get('weight', 1.0)
                    
                    if concept:
                        calculations[parent].append((concept, float(weight)))
        
        return calculations
    
    def _validate_calculation(
        self,
        parent_concept: str,
        children: list[tuple[str, float]],
        filing: ParsedFiling
    ) -> list[ParsingError]:
        """
        Validate a single calculation relationship.
        
        Args:
            parent_concept: Parent concept
            children: list of (child_concept, weight) tuples
            filing: Parsed filing
            
        Returns:
            list of errors for this calculation
        """
        errors: list[ParsingError] = []
        
        # Get all facts for parent concept
        parent_facts = [
            f for f in filing.instance.facts
            if f.concept == parent_concept and f.fact_type == FactType.NUMERIC
        ]
        
        if not parent_facts:
            # Parent concept has no facts - not necessarily an error
            return errors
        
        # Validate calculation for each parent fact (by context)
        contexts_checked: set[str] = set()
        
        for parent_fact in parent_facts:
            if not parent_fact.context_ref:
                continue
            
            # Only check each context once
            if parent_fact.context_ref in contexts_checked:
                continue
            contexts_checked.add(parent_fact.context_ref)
            
            # Find all child facts in same context
            child_facts = self._find_child_facts(
                children,
                parent_fact.context_ref,
                filing
            )
            
            # Validate arithmetic
            errors.extend(
                self._verify_arithmetic(
                    parent_fact,
                    child_facts,
                    children,
                    filing
                )
            )
        
        return errors
    
    def _find_child_facts(
        self,
        children: list[tuple[str, float]],
        context_ref: str,
        filing: ParsedFiling
    ) -> dict[str, 'Fact']:
        """
        Find child facts in the same context.
        
        Args:
            children: list of (child_concept, weight) tuples
            context_ref: Context reference
            filing: Parsed filing
            
        Returns:
            dict mapping child concept to fact
        """
        child_facts: dict[str, 'Fact'] = {}
        
        for child_concept, weight in children:
            # Find fact for this child in same context
            matching_facts = [
                f for f in filing.instance.facts
                if (f.concept == child_concept and
                    f.context_ref == context_ref and
                    f.fact_type == FactType.NUMERIC)
            ]
            
            if matching_facts:
                # Use first matching fact
                child_facts[child_concept] = matching_facts[0]
        
        return child_facts
    
    def _verify_arithmetic(
        self,
        parent_fact: 'Fact',
        child_facts: dict[str, 'Fact'],
        children: list[tuple[str, float]],
        filing: ParsedFiling
    ) -> list[ParsingError]:
        """
        Verify arithmetic consistency.
        
        Args:
            parent_fact: Parent fact
            child_facts: dict of child facts by concept
            children: list of (child_concept, weight) tuples
            filing: Parsed filing
            
        Returns:
            list of arithmetic errors
        """
        errors: list[ParsingError] = []
        
        # Check if all children are present
        missing_children = []
        for child_concept, weight in children:
            if child_concept not in child_facts:
                missing_children.append(child_concept)
        
        if missing_children:
            errors.append(ParsingError(
                category=ErrorCategory.CALCULATION_MISSING,
                severity=ErrorSeverity.WARNING,
                message=MSG_CALCULATION_MISSING_FACT,
                details={
                    'parent_concept': parent_fact.concept,
                    'context_ref': parent_fact.context_ref,
                    'missing_children': missing_children
                },
                source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
            ))
            # Don't validate arithmetic if children missing
            return errors
        
        # Calculate expected value
        try:
            calculated_sum = Decimal('0')
            
            for child_concept, weight in children:
                child_fact = child_facts[child_concept]
                
                # Parse child value
                try:
                    child_value = Decimal(child_fact.value)
                except (InvalidOperation, ValueError):
                    continue
                
                # Apply weight
                calculated_sum += child_value * Decimal(str(weight))
            
            # Parse parent value
            try:
                parent_value = Decimal(parent_fact.value)
            except (InvalidOperation, ValueError):
                return errors
            
            # Calculate difference
            difference = abs(calculated_sum - parent_value)
            
            # Calculate tolerance
            tolerance = self._calculate_tolerance(parent_fact, child_facts)
            
            # Check if difference exceeds tolerance
            if difference > tolerance:
                errors.append(ParsingError(
                    category=ErrorCategory.CALCULATION_INCONSISTENT,
                    severity=ErrorSeverity.ERROR,
                    message=MSG_CALCULATION_INCONSISTENT,
                    details={
                        'parent_concept': parent_fact.concept,
                        'context_ref': parent_fact.context_ref,
                        'expected': str(calculated_sum),
                        'actual': str(parent_value),
                        'difference': str(difference),
                        'tolerance': str(tolerance)
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
        
        except Exception as e:
            self.logger.error(f"Error validating calculation: {e}", exc_info=True)
        
        return errors
    
    def _calculate_tolerance(
        self,
        parent_fact: 'Fact',
        child_facts: dict[str, 'Fact']
    ) -> Decimal:
        """
        Calculate tolerance for arithmetic comparison.
        
        Args:
            parent_fact: Parent fact
            child_facts: Child facts
            
        Returns:
            Tolerance value as Decimal
        """
        # Check if parent has infinite precision
        if parent_fact.decimals == INFINITE_PRECISION:
            return Decimal('0')
        
        # Use decimals attribute if available
        if parent_fact.decimals is not None:
            try:
                decimals = int(parent_fact.decimals)
                
                # Negative decimals mean rounding to that power of 10
                # e.g., decimals=-3 means rounded to nearest 1000
                if decimals < 0:
                    # Tolerance is 0.5 * 10^(-decimals)
                    return Decimal('0.5') * Decimal(10) ** abs(decimals)
                else:
                    # Tolerance is 0.5 * 10^(-decimals)
                    return Decimal('0.5') * Decimal(10) ** (-decimals)
            except (ValueError, InvalidOperation):
                pass
        
        # Default tolerance from config
        return Decimal(str(self.tolerance))


__all__ = ['CalculationValidator']
