# Path: xbrl_parser/validation/completeness.py
"""
Completeness Auditor

Validates data completeness and detects orphaned elements.

This module validates:
- Coverage audit (elements parsed vs expected)
- Orphan detection (unreferenced contexts, units)
- Missing data identification
- Taxonomy coverage

Example:
    from ..validation import CompletenessValidator
    
    validator = CompletenessValidator()
    errors = validator.validate(parsed_filing)
"""

import logging
from typing import Optional

from ...core.config_loader import ConfigLoader
from ..models.parsed_filing import ParsedFiling
from ..models.error import ParsingError, ErrorSeverity, ErrorCategory
from ..validation.constants import (
    VALIDATOR_COMPLETENESS,
    CATEGORY_COMPLETENESS,
    ERR_ORPHAN_CONTEXT,
    ERR_ORPHAN_UNIT,
    ERR_COVERAGE_INSUFFICIENT,
    MSG_ORPHAN_CONTEXT,
    MSG_ORPHAN_UNIT,
    MSG_COVERAGE_INSUFFICIENT,
    MAX_ORPHAN_CONTEXTS_PERCENT,
    MAX_ORPHAN_UNITS_PERCENT,
    MIN_COVERAGE_PERCENT
)


class CompletenessValidator:
    """
    Validates data completeness.
    
    Detects orphaned elements and ensures data coverage meets
    quality standards.
    
    Example:
        config = ConfigLoader()
        validator = CompletenessValidator(config)
        
        errors = validator.validate(parsed_filing)
        
        orphans = [e for e in errors if 'orphan' in e.message.lower()]
        print(f"Found {len(orphans)} orphaned elements")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize completeness validator.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("CompletenessValidator initialized")
    
    def get_name(self) -> str:
        """Get validator name."""
        return VALIDATOR_COMPLETENESS
    
    def get_category(self) -> str:
        """Get validator category."""
        return CATEGORY_COMPLETENESS
    
    def requires_taxonomy(self) -> bool:
        """Whether validator requires taxonomy data."""
        return False
    
    def validate(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate data completeness.
        
        Args:
            filing: Parsed filing to validate
            
        Returns:
            list of completeness validation errors
        """
        errors: list[ParsingError] = []
        
        self.logger.info(f"Validating completeness: {filing.metadata.entry_point}")
        
        # Detect orphaned contexts
        errors.extend(self._detect_orphan_contexts(filing))
        
        # Detect orphaned units
        errors.extend(self._detect_orphan_units(filing))
        
        # Validate coverage
        errors.extend(self._validate_coverage(filing))
        
        self.logger.info(f"Completeness validation completed: {len(errors)} issues")
        return errors
    
    def _detect_orphan_contexts(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Detect contexts not referenced by any facts.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of orphan context warnings
        """
        errors: list[ParsingError] = []
        
        if not filing.instance.contexts:
            return errors
        
        # Build set of referenced contexts
        referenced_contexts: set[str] = set()
        for fact in filing.instance.facts:
            if fact.context_ref:
                referenced_contexts.add(fact.context_ref)
        
        # Find orphaned contexts
        orphan_contexts = []
        for context_id in filing.instance.contexts.keys():
            if context_id not in referenced_contexts:
                orphan_contexts.append(context_id)
        
        # Check if orphan percentage exceeds threshold
        total_contexts = len(filing.instance.contexts)
        orphan_count = len(orphan_contexts)
        
        if total_contexts > 0:
            orphan_percent = (orphan_count / total_contexts) * 100
            
            if orphan_percent > MAX_ORPHAN_CONTEXTS_PERCENT:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.WARNING,
                    message=MSG_ORPHAN_CONTEXT,
                    details={
                        'orphan_count': orphan_count,
                        'total_count': total_contexts,
                        'orphan_percent': round(orphan_percent, 2),
                        'threshold_percent': MAX_ORPHAN_CONTEXTS_PERCENT,
                        'sample_orphans': orphan_contexts[:5]
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _detect_orphan_units(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Detect units not referenced by any facts.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of orphan unit warnings
        """
        errors: list[ParsingError] = []
        
        if not filing.instance.units:
            return errors
        
        # Build set of referenced units
        referenced_units: set[str] = set()
        for fact in filing.instance.facts:
            if fact.unit_ref:
                referenced_units.add(fact.unit_ref)
        
        # Find orphaned units
        orphan_units = []
        for unit_id in filing.instance.units.keys():
            if unit_id not in referenced_units:
                orphan_units.append(unit_id)
        
        # Check if orphan percentage exceeds threshold
        total_units = len(filing.instance.units)
        orphan_count = len(orphan_units)
        
        if total_units > 0:
            orphan_percent = (orphan_count / total_units) * 100
            
            if orphan_percent > MAX_ORPHAN_UNITS_PERCENT:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.INFO,
                    message=MSG_ORPHAN_UNIT,
                    details={
                        'orphan_count': orphan_count,
                        'total_count': total_units,
                        'orphan_percent': round(orphan_percent, 2),
                        'threshold_percent': MAX_ORPHAN_UNITS_PERCENT,
                        'sample_orphans': orphan_units[:5]
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _validate_coverage(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate parsing coverage.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of coverage warnings
        """
        errors: list[ParsingError] = []
        
        # Check if we have basic data
        has_facts = len(filing.instance.facts) > 0
        has_contexts = len(filing.instance.contexts) > 0
        
        if not has_facts and has_contexts:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.WARNING,
                message="Filing has contexts but no facts",
                details={
                    'context_count': len(filing.instance.contexts),
                    'fact_count': 0
                },
                source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
            ))
        
        # Check taxonomy coverage if available
        if filing.taxonomy:
            errors.extend(self._validate_taxonomy_coverage(filing))
        
        return errors
    
    def _validate_taxonomy_coverage(
        self,
        filing: ParsedFiling
    ) -> list[ParsingError]:
        """
        Validate taxonomy concept coverage.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of taxonomy coverage warnings
        """
        errors: list[ParsingError] = []
        
        # Get concepts used in facts
        concepts_used: set[str] = set()
        for fact in filing.instance.facts:
            if fact.concept:
                concepts_used.add(fact.concept)
        
        # Get concepts defined in taxonomy
        if hasattr(filing.taxonomy, 'concepts'):
            concepts_defined = len(filing.taxonomy.concepts)
            concepts_used_count = len(concepts_used)
            
            if concepts_defined > 0:
                coverage_percent = (concepts_used_count / concepts_defined) * 100
                
                # This is informational - low coverage is normal
                self.logger.debug(
                    f"Taxonomy coverage: {coverage_percent:.1f}% "
                    f"({concepts_used_count}/{concepts_defined} concepts used)"
                )
        
        return errors


__all__ = ['CompletenessValidator']
