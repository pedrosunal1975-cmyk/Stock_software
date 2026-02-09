# Path: xbrl_parser/models/validation.py
"""
Validation Results System

Validation result tracking and quality assessment for XBRL parsing.

This module defines:
- ValidationResult for individual validation checks
- ValidationSummary for aggregated results
- Quality score calculation
- Validation status tracking
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum

from ..models.error import (
    ErrorSeverity,
    ErrorCategory,
    ParsingError,
    ErrorCollection,
    ReliabilityLevel
)


# ==============================================================================
# VALIDATION STATUS
# ==============================================================================

class ValidationStatus(Enum):
    """
    Validation check status.
    
    Statuses:
        PASSED: Validation check passed
        FAILED: Validation check failed
        SKIPPED: Validation check skipped (not applicable)
        NOT_RUN: Validation check not yet executed
    """
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    NOT_RUN = "NOT_RUN"
    
    def __str__(self) -> str:
        return self.value


# ==============================================================================
# VALIDATION RESULT
# ==============================================================================

@dataclass
class ValidationResult:
    """
    Result of a single validation check.
    
    Attributes:
        name: Validation check name
        status: Validation status (PASSED/FAILED/SKIPPED/NOT_RUN)
        message: Description of result
        details: Additional details (optional)
        errors: Errors found during validation
        warnings: Warnings found during validation
        timestamp: When validation was performed
        duration_ms: How long validation took (milliseconds)
    """
    name: str
    status: ValidationStatus
    message: str
    details: Optional[str] = None
    errors: list[ParsingError] = field(default_factory=list)
    warnings: list[ParsingError] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[float] = None
    
    def add_error(self, error: ParsingError) -> None:
        """Add error to validation result."""
        self.errors.append(error)
        if self.status != ValidationStatus.FAILED:
            self.status = ValidationStatus.FAILED
    
    def add_warning(self, warning: ParsingError) -> None:
        """Add warning to validation result."""
        self.warnings.append(warning)
    
    def is_passed(self) -> bool:
        """Check if validation passed."""
        return self.status == ValidationStatus.PASSED
    
    def is_failed(self) -> bool:
        """Check if validation failed."""
        return self.status == ValidationStatus.FAILED
    
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0
    
    def to_dict(self) -> dict[str, any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'details': self.details,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings],
            'timestamp': self.timestamp.isoformat(),
            'duration_ms': self.duration_ms
        }


# ==============================================================================
# QUALITY SCORE CONSTANTS
# ==============================================================================

# Quality score calculation weights
QUALITY_SCORE_FAILED_VALIDATION_PENALTY = 20
QUALITY_SCORE_ERROR_PENALTY = 10
QUALITY_SCORE_WARNING_PENALTY = 5

# Reliability thresholds (0-100 scale)
RELIABILITY_FAILED_THRESHOLD = 30
RELIABILITY_DEGRADED_THRESHOLD = 60
RELIABILITY_PARTIAL_THRESHOLD = 90


# ==============================================================================
# VALIDATION SUMMARY
# ==============================================================================

@dataclass
class ValidationSummary:
    """
    Aggregated validation results across all checks.
    
    Attributes:
        results: list of individual validation results
        overall_status: Overall validation status
        reliability: Overall reliability level
        quality_score: Quality score (0-100)
        total_errors: Total error count
        total_warnings: Total warning count
        timestamp: When summary was generated
    """
    results: list[ValidationResult] = field(default_factory=list)
    overall_status: ValidationStatus = ValidationStatus.NOT_RUN
    reliability: ReliabilityLevel = ReliabilityLevel.COMPLETE
    quality_score: float = 100.0
    total_errors: int = 0
    total_warnings: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def add_result(self, result: ValidationResult) -> None:
        """Add validation result and update summary."""
        self.results.append(result)
        self._update_summary()
    
    def _update_summary(self) -> None:
        """Update summary statistics."""
        # Count errors and warnings
        self.total_errors = sum(len(r.errors) for r in self.results)
        self.total_warnings = sum(len(r.warnings) for r in self.results)
        
        # Determine overall status
        if any(r.status == ValidationStatus.FAILED for r in self.results):
            self.overall_status = ValidationStatus.FAILED
        elif all(r.status == ValidationStatus.PASSED for r in self.results):
            self.overall_status = ValidationStatus.PASSED
        elif all(r.status == ValidationStatus.SKIPPED for r in self.results):
            self.overall_status = ValidationStatus.SKIPPED
        else:
            self.overall_status = ValidationStatus.PASSED  # Partial pass
        
        # Calculate quality score
        self.quality_score = self._calculate_quality_score()
        
        # Determine reliability
        self.reliability = self._determine_reliability()
    
    def _calculate_quality_score(self) -> float:
        """
        Calculate quality score (0-100).

        Logic:
            - Start at 100
            - Deduct points per failed validation
            - Deduct points per error
            - Deduct points per warning
            - Minimum score is 0

        Returns:
            Quality score (0-100)
        """
        score = 100.0

        # Failed validations
        failed_count = sum(1 for r in self.results if r.status == ValidationStatus.FAILED)
        score -= failed_count * QUALITY_SCORE_FAILED_VALIDATION_PENALTY

        # Errors
        score -= self.total_errors * QUALITY_SCORE_ERROR_PENALTY

        # Warnings
        score -= self.total_warnings * QUALITY_SCORE_WARNING_PENALTY

        return max(0.0, score)
    
    def _determine_reliability(self) -> ReliabilityLevel:
        """
        Determine overall reliability level based on quality score.

        Returns:
            ReliabilityLevel
        """
        if self.quality_score < RELIABILITY_FAILED_THRESHOLD:
            return ReliabilityLevel.FAILED
        elif self.quality_score < RELIABILITY_DEGRADED_THRESHOLD:
            return ReliabilityLevel.DEGRADED
        elif self.quality_score < RELIABILITY_PARTIAL_THRESHOLD:
            return ReliabilityLevel.PARTIAL
        else:
            return ReliabilityLevel.COMPLETE
    
    def get_failed_validations(self) -> list[ValidationResult]:
        """Get all failed validation results."""
        return [r for r in self.results if r.status == ValidationStatus.FAILED]
    
    def get_passed_validations(self) -> list[ValidationResult]:
        """Get all passed validation results."""
        return [r for r in self.results if r.status == ValidationStatus.PASSED]
    
    def get_results_by_status(self, status: ValidationStatus) -> list[ValidationResult]:
        """Get all results with specific status."""
        return [r for r in self.results if r.status == status]
    
    def to_dict(self) -> dict[str, any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            'overall_status': self.overall_status.value,
            'reliability': self.reliability.value,
            'quality_score': round(self.quality_score, 2),
            'total_checks': len(self.results),
            'passed': len([r for r in self.results if r.status == ValidationStatus.PASSED]),
            'failed': len([r for r in self.results if r.status == ValidationStatus.FAILED]),
            'skipped': len([r for r in self.results if r.status == ValidationStatus.SKIPPED]),
            'total_errors': self.total_errors,
            'total_warnings': self.total_warnings,
            'results': [r.to_dict() for r in self.results],
            'timestamp': self.timestamp.isoformat()
        }


# ==============================================================================
# COMPLETENESS AUDIT RESULT
# ==============================================================================

@dataclass
class CompletenessAudit:
    """
    Result of completeness audit (what was parsed vs expected).
    
    Attributes:
        total_elements: Total elements in source
        parsed_elements: Successfully parsed elements
        failed_elements: Failed to parse elements
        skipped_elements: Skipped elements
        coverage_percentage: Parsing coverage percentage
        missing_items: list of missing/failed item descriptions
    """
    total_elements: int = 0
    parsed_elements: int = 0
    failed_elements: int = 0
    skipped_elements: int = 0
    coverage_percentage: float = 100.0
    missing_items: list[str] = field(default_factory=list)
    
    def calculate_coverage(self) -> None:
        """Calculate coverage percentage."""
        if self.total_elements > 0:
            self.coverage_percentage = (self.parsed_elements / self.total_elements) * 100
        else:
            self.coverage_percentage = 100.0
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for serialization."""
        return {
            'total_elements': self.total_elements,
            'parsed_elements': self.parsed_elements,
            'failed_elements': self.failed_elements,
            'skipped_elements': self.skipped_elements,
            'coverage_percentage': round(self.coverage_percentage, 2),
            'missing_items': self.missing_items
        }


# ==============================================================================
# CALCULATION VALIDATION RESULT
# ==============================================================================

@dataclass
class CalculationValidation:
    """
    Result of calculation validation.
    
    Attributes:
        total_calculations: Total calculations checked
        consistent_calculations: Calculations that passed
        inconsistent_calculations: Calculations that failed
        inconsistencies: list of inconsistency details
    """
    total_calculations: int = 0
    consistent_calculations: int = 0
    inconsistent_calculations: int = 0
    inconsistencies: list[dict[str, any]] = field(default_factory=list)
    
    def add_inconsistency(
        self,
        parent_concept: str,
        expected_value: float,
        actual_value: float,
        difference: float,
        context_id: str
    ) -> None:
        """Add calculation inconsistency."""
        self.inconsistencies.append({
            'parent_concept': parent_concept,
            'expected_value': expected_value,
            'actual_value': actual_value,
            'difference': difference,
            'context_id': context_id
        })
        self.inconsistent_calculations += 1
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for serialization."""
        return {
            'total_calculations': self.total_calculations,
            'consistent_calculations': self.consistent_calculations,
            'inconsistent_calculations': self.inconsistent_calculations,
            'consistency_rate': (
                (self.consistent_calculations / self.total_calculations * 100)
                if self.total_calculations > 0 else 100.0
            ),
            'inconsistencies': self.inconsistencies
        }


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_validation_result(
    name: str,
    status: ValidationStatus,
    message: str,
    **kwargs
) -> ValidationResult:
    """
    Convenience function to create ValidationResult.
    
    Args:
        name: Validation name
        status: Validation status
        message: Result message
        **kwargs: Additional attributes
        
    Returns:
        ValidationResult instance
    """
    return ValidationResult(
        name=name,
        status=status,
        message=message,
        **kwargs
    )


def create_passed_validation(name: str, message: str = "Check passed") -> ValidationResult:
    """Create PASSED validation result."""
    return ValidationResult(name=name, status=ValidationStatus.PASSED, message=message)


def create_failed_validation(name: str, message: str, errors: list[ParsingError] = None) -> ValidationResult:
    """Create FAILED validation result."""
    return ValidationResult(
        name=name,
        status=ValidationStatus.FAILED,
        message=message,
        errors=errors or []
    )


def create_skipped_validation(name: str, message: str = "Check skipped") -> ValidationResult:
    """Create SKIPPED validation result."""
    return ValidationResult(name=name, status=ValidationStatus.SKIPPED, message=message)


__all__ = [
    'ValidationStatus',
    'ValidationResult',
    'ValidationSummary',
    'CompletenessAudit',
    'CalculationValidation',
    'create_validation_result',
    'create_passed_validation',
    'create_failed_validation',
    'create_skipped_validation',
]
