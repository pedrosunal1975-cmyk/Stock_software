# Path: xbrl_parser/validation/registry.py
"""
Validation Registry

Coordinates all validators and manages validation pipeline execution.

This module provides:
- Validator registration
- Validation pipeline orchestration
- Result aggregation
- Severity-based filtering
- Validation reporting

Example:
    from ..validation import ValidationRegistry
    
    registry = ValidationRegistry()
    results = registry.validate_filing(parsed_filing)
    
    if results.has_errors():
        print(f"Found {len(results.errors)} errors")
"""

import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

from ...core.config_loader import ConfigLoader
from ..models.error import ParsingError, ErrorSeverity, ErrorCategory
from ..models.parsed_filing import ParsedFiling
from ..models.validation import ValidationSummary, ValidationStatus, ReliabilityLevel
from ..validation.constants import (
    VALIDATION_LEVEL_NONE,
    VALIDATION_LEVEL_BASIC,
    VALIDATION_LEVEL_FULL,
    VALIDATION_CATEGORIES,
    STATUS_PASSED,
    STATUS_FAILED,
    STATUS_SKIPPED,
    MAX_CRITICAL_ERRORS,
    MAX_ERRORS
)


@dataclass
class ValidatorInfo:
    """
    Metadata about a registered validator.
    
    Attributes:
        name: Validator identifier
        category: Validation category
        enabled: Whether validator is enabled
        priority: Execution priority (lower runs first)
        requires_taxonomy: Whether validator needs taxonomy data
    """
    name: str
    category: str
    enabled: bool = True
    priority: int = 100
    requires_taxonomy: bool = False


class ValidationRegistry:
    """
    Registry for managing and executing validators.
    
    Coordinates multiple validators, manages execution order,
    and aggregates results.
    
    Example:
        config = ConfigLoader()
        registry = ValidationRegistry(config)
        
        # Register validators
        registry.register_validator(structural_validator, priority=10)
        registry.register_validator(calculation_validator, priority=20)
        
        # Run all validators
        results = registry.validate_filing(parsed_filing)
        
        # Filter by severity
        errors = results.get_by_severity(ErrorSeverity.ERROR)
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize validation registry.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        
        # Validator registry
        self.validators: dict[str, 'BaseValidator'] = {}
        self.validator_info: dict[str, ValidatorInfo] = {}
        
        # Get validation configuration
        self.validation_level = self.config.get('validation_level', VALIDATION_LEVEL_FULL)
        self.strict_mode = self.config.get('strict_mode', False)
        
        self.logger.debug(
            f"ValidationRegistry initialized: level={self.validation_level}, "
            f"strict={self.strict_mode}"
        )
    
    def register_validator(
        self,
        validator: 'BaseValidator',
        priority: int = 100,
        enabled: bool = True
    ) -> None:
        """
        Register a validator.
        
        Args:
            validator: Validator instance
            priority: Execution priority (lower runs first)
            enabled: Whether validator is enabled
            
        Example:
            registry.register_validator(structural_validator, priority=10)
        """
        validator_name = validator.get_name()
        
        if validator_name in self.validators:
            self.logger.warning(f"Validator '{validator_name}' already registered, replacing")
        
        self.validators[validator_name] = validator
        self.validator_info[validator_name] = ValidatorInfo(
            name=validator_name,
            category=validator.get_category(),
            enabled=enabled,
            priority=priority,
            requires_taxonomy=validator.requires_taxonomy()
        )
        
        self.logger.info(f"Registered validator: {validator_name} (priority={priority})")
    
    def unregister_validator(self, validator_name: str) -> None:
        """
        Unregister a validator.
        
        Args:
            validator_name: Name of validator to remove
        """
        if validator_name in self.validators:
            del self.validators[validator_name]
            del self.validator_info[validator_name]
            self.logger.info(f"Unregistered validator: {validator_name}")
    
    def get_validator(self, validator_name: str) -> Optional['BaseValidator']:
        """
        Get a registered validator by name.
        
        Args:
            validator_name: Name of validator
            
        Returns:
            Validator instance or None if not found
        """
        return self.validators.get(validator_name)
    
    def list_validators(self) -> list[ValidatorInfo]:
        """
        list all registered validators.
        
        Returns:
            list of validator metadata sorted by priority
        """
        return sorted(
            self.validator_info.values(),
            key=lambda v: v.priority
        )
    
    def validate_filing(
        self,
        filing: ParsedFiling,
        categories: Optional[list[str]] = None
    ) -> ValidationSummary:
        """
        Run all enabled validators on a filing.
        
        Args:
            filing: Parsed filing to validate
            categories: Optional list of categories to validate (None = all)
            
        Returns:
            Aggregated validation results
            
        Example:
            # Validate all categories
            results = registry.validate_filing(filing)
            
            # Validate specific categories
            results = registry.validate_filing(
                filing,
                categories=['structural', 'calculation']
            )
        """
        start_time = datetime.now()
        self.logger.info(f"Starting validation: {filing.metadata.entry_point}")
        
        # Check validation level
        if self.validation_level == VALIDATION_LEVEL_NONE:
            self.logger.info("Validation disabled (level=none)")
            return self._create_skipped_result()
        
        # Filter validators by category if specified
        validators_to_run = self._get_validators_to_run(categories)
        
        # Run validators in priority order
        all_errors: list[ParsingError] = []
        validation_results: dict[str, bool] = {}
        
        for info in validators_to_run:
            if not info.enabled:
                self.logger.debug(f"Skipping disabled validator: {info.name}")
                validation_results[info.name] = False
                continue
            
            validator = self.validators[info.name]
            
            try:
                self.logger.info(f"Running validator: {info.name}")
                errors = validator.validate(filing)
                all_errors.extend(errors)
                validation_results[info.name] = len(errors) == 0
                
                self.logger.info(
                    f"Validator {info.name} completed: {len(errors)} issues found"
                )
                
                # Check if we should stop in strict mode
                if self.strict_mode and self._should_stop_validation(all_errors):
                    self.logger.warning("Stopping validation in strict mode due to errors")
                    break
                    
            except Exception as e:
                self.logger.error(f"Validator {info.name} failed: {e}", exc_info=True)
                # Create error for validator failure
                error = ParsingError(
                    category=ErrorCategory.UNKNOWN,
                    severity=ErrorSeverity.ERROR,
                    message=f"Validator {info.name} failed: {str(e)}",
                    details="VAL_SYSTEM_001",
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                )
                all_errors.append(error)
                validation_results[info.name] = False
        
        # Calculate elapsed time
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Determine overall status
        if len(all_errors) == 0:
            overall_status = ValidationStatus.PASSED
            reliability = ReliabilityLevel.COMPLETE
        else:
            overall_status = ValidationStatus.FAILED
            # Determine reliability based on error severity
            critical_count = sum(1 for e in all_errors if e.severity == ErrorSeverity.CRITICAL)
            error_count = sum(1 for e in all_errors if e.severity == ErrorSeverity.ERROR)
            
            if critical_count > 0:
                reliability = ReliabilityLevel.FAILED
            elif error_count > 10:
                reliability = ReliabilityLevel.DEGRADED
            else:
                reliability = ReliabilityLevel.PARTIAL
        
        # Create validation summary
        summary = ValidationSummary(
            overall_status=overall_status,
            reliability=reliability,
            total_errors=sum(1 for e in all_errors if e.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR]),
            total_warnings=sum(1 for e in all_errors if e.severity == ErrorSeverity.WARNING),
            timestamp=datetime.now()
        )
        
        # Add all errors to summary (they'll be in results list)
        for error in all_errors:
            summary.total_errors += 1
        
        self.logger.info(
            f"Validation completed: {len(all_errors)} issues found in {elapsed:.2f}s"
        )
        
        return summary
    
    def validate_batch(
        self,
        filings: list[ParsedFiling],
        categories: Optional[list[str]] = None
    ) -> list[ValidationSummary]:
        """
        Validate multiple filings.
        
        Args:
            filings: list of parsed filings
            categories: Optional list of categories to validate
            
        Returns:
            list of validation summaries (one per filing)
            
        Example:
            results = registry.validate_batch(filings)
            for result in results:
                print(f"Status: {result.overall_status}")
        """
        results = []
        
        for filing in filings:
            try:
                result = self.validate_filing(filing, categories)
                results.append(result)
            except Exception as e:
                self.logger.error(
                    f"Failed to validate {filing.metadata.entry_point}: {e}",
                    exc_info=True
                )
                # Create failed result
                summary = ValidationSummary(
                    overall_status=ValidationStatus.FAILED,
                    reliability=ReliabilityLevel.FAILED,
                    total_errors=1,
                    total_warnings=0,
                    timestamp=datetime.now()
                )
                results.append(summary)
        
        return results
    
    def _get_validators_to_run(
        self,
        categories: Optional[list[str]] = None
    ) -> list[ValidatorInfo]:
        """
        Get list of validators to run based on filters.
        
        Args:
            categories: Optional category filter
            
        Returns:
            list of validator info sorted by priority
        """
        validators = []
        
        for info in sorted(self.validator_info.values(), key=lambda v: v.priority):
            # Filter by category if specified
            if categories and info.category not in categories:
                continue
            
            validators.append(info)
        
        return validators
    
    def _should_stop_validation(self, errors: list[ParsingError]) -> bool:
        """
        Determine if validation should stop due to errors.
        
        Args:
            errors: list of errors so far
            
        Returns:
            True if should stop validation
        """
        if not self.strict_mode:
            return False
        
        # Count critical errors
        critical_count = sum(
            1 for e in errors if e.severity == ErrorSeverity.CRITICAL
        )
        
        if critical_count >= MAX_CRITICAL_ERRORS:
            return True
        
        # Count total errors
        error_count = sum(
            1 for e in errors 
            if e.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR]
        )
        
        return error_count >= MAX_ERRORS
    
    def _create_skipped_result(self) -> ValidationSummary:
        """
        Create a skipped validation result.
        
        Returns:
            Validation summary marked as skipped
        """
        return ValidationSummary(
            overall_status=ValidationStatus.SKIPPED,
            reliability=ReliabilityLevel.COMPLETE,
            total_errors=0,
            total_warnings=0,
            timestamp=datetime.now()
        )


class BaseValidator:
    """
    Base class for all validators.
    
    All validators must inherit from this class and implement:
    - get_name()
    - get_category()
    - validate()
    """
    
    def get_name(self) -> str:
        """Get validator name."""
        raise NotImplementedError
    
    def get_category(self) -> str:
        """Get validator category."""
        raise NotImplementedError
    
    def requires_taxonomy(self) -> bool:
        """Whether validator requires taxonomy data."""
        return False
    
    def validate(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate a filing.
        
        Args:
            filing: Parsed filing to validate
            
        Returns:
            list of validation errors (empty if valid)
        """
        raise NotImplementedError


__all__ = [
    'ValidationRegistry',
    'BaseValidator',
    'ValidatorInfo'
]
