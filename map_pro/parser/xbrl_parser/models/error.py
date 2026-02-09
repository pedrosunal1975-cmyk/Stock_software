# Path: xbrl_parser/models/error.py
"""
Error Handling System

Comprehensive error classification and reliability framework for XBRL parsing.

This module defines:
- Error severity levels (CRITICAL, ERROR, WARNING, INFO)
- Reliability levels (COMPLETE, PARTIAL, DEGRADED, FAILED)
- Error classes with rich context
- Error recovery strategies
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
from pathlib import Path


# ==============================================================================
# ERROR SEVERITY LEVELS
# ==============================================================================

class ErrorSeverity(Enum):
    """
    Error severity classification.
    
    Levels:
        CRITICAL: Cannot continue, fatal errors (e.g., file not found, corrupt XML)
        ERROR: Spec violation, data may be incorrect (e.g., missing required context)
        WARNING: Unusual pattern, worth reviewing (e.g., deprecated element used)
        INFO: Informational, statistics (e.g., orphaned context detected)
    """
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    
    def __str__(self) -> str:
        return self.value
    
    def __lt__(self, other: 'ErrorSeverity') -> bool:
        """Enable severity comparison (CRITICAL > ERROR > WARNING > INFO)."""
        order = {
            ErrorSeverity.INFO: 0,
            ErrorSeverity.WARNING: 1,
            ErrorSeverity.ERROR: 2,
            ErrorSeverity.CRITICAL: 3
        }
        return order[self] < order[other]


# ==============================================================================
# RELIABILITY LEVELS
# ==============================================================================

class ReliabilityLevel(Enum):
    """
    Parsing result quality classification.
    
    Levels:
        COMPLETE: All data extracted successfully, no errors
        PARTIAL: Some data missing but usable, minor errors
        DEGRADED: Significant issues but structure intact, major errors
        FAILED: Cannot produce meaningful output, critical errors
    """
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    
    def __str__(self) -> str:
        return self.value
    
    def __lt__(self, other: 'ReliabilityLevel') -> bool:
        """Enable reliability comparison (COMPLETE > PARTIAL > DEGRADED > FAILED)."""
        order = {
            ReliabilityLevel.FAILED: 0,
            ReliabilityLevel.DEGRADED: 1,
            ReliabilityLevel.PARTIAL: 2,
            ReliabilityLevel.COMPLETE: 3
        }
        return order[self] < order[other]


# ==============================================================================
# ERROR CATEGORIES
# ==============================================================================

class ErrorCategory(Enum):
    """
    Error category classification for grouping related errors.
    """
    # XML Structure
    XML_MALFORMED = "XML_MALFORMED"
    XML_ENCODING = "XML_ENCODING"
    XML_WELLFORMEDNESS = "XML_WELLFORMEDNESS"
    
    # XBRL Specification
    XBRL_INVALID = "XBRL_INVALID"
    XBRL_SCHEMA_VIOLATION = "XBRL_SCHEMA_VIOLATION"
    XBRL_LINKBASE_ERROR = "XBRL_LINKBASE_ERROR"
    
    # Instance Document
    MISSING_CONTEXT = "MISSING_CONTEXT"
    MISSING_UNIT = "MISSING_UNIT"
    INVALID_FACT = "INVALID_FACT"
    INVALID_PERIOD = "INVALID_PERIOD"
    
    # Dimensions
    DIMENSION_INVALID = "DIMENSION_INVALID"
    DIMENSION_MEMBER_INVALID = "DIMENSION_MEMBER_INVALID"
    HYPERCUBE_VIOLATION = "HYPERCUBE_VIOLATION"
    
    # Calculations
    CALCULATION_INCONSISTENT = "CALCULATION_INCONSISTENT"
    CALCULATION_MISSING = "CALCULATION_MISSING"
    
    # Taxonomy
    TAXONOMY_LOAD_FAILED = "TAXONOMY_LOAD_FAILED"
    TAXONOMY_CIRCULAR_IMPORT = "TAXONOMY_CIRCULAR_IMPORT"
    CONCEPT_NOT_FOUND = "CONCEPT_NOT_FOUND"
    DEPRECATED_ELEMENT = "DEPRECATED_ELEMENT"
    
    # Network/Remote
    NETWORK_ERROR = "NETWORK_ERROR"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
    CACHE_ERROR = "CACHE_ERROR"
    
    # System
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    MEMORY_ERROR = "MEMORY_ERROR"
    TIMEOUT = "TIMEOUT"
    
    # Other
    UNKNOWN = "UNKNOWN"
    
    def __str__(self) -> str:
        return self.value


# ==============================================================================
# ERROR RECOVERY STRATEGIES
# ==============================================================================

class RecoveryStrategy(Enum):
    """
    Error recovery strategy options.
    
    Strategies:
        FAIL_FAST: Stop immediately on error (strict mode)
        CONTINUE: Accumulate errors, return partial results
        RETRY: Attempt operation again (network, file access)
        SKIP: Skip problematic element, continue with rest
        SUBSTITUTE: Use synthetic/default data for missing values
    """
    FAIL_FAST = "FAIL_FAST"
    CONTINUE = "CONTINUE"
    RETRY = "RETRY"
    SKIP = "SKIP"
    SUBSTITUTE = "SUBSTITUTE"
    
    def __str__(self) -> str:
        return self.value


# ==============================================================================
# PARSING ERROR CLASS
# ==============================================================================

@dataclass
class ParsingError:
    """
    Comprehensive error information for XBRL parsing.
    
    Attributes:
        severity: Error severity level
        category: Error category
        message: Human-readable error message
        details: Additional error details (optional)
        source_file: File where error occurred (optional)
        line_number: Line number in source file (optional)
        column_number: Column number in source file (optional)
        element_id: ID of problematic element (optional)
        context: Additional context data (optional)
        timestamp: When error occurred
        recovery_strategy: Suggested recovery strategy (optional)
        recovered: Whether error was successfully recovered
    """
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    details: Optional[str] = None
    source_file: Optional[Path] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    element_id: Optional[str] = None
    context: dict[str, any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    recovery_strategy: Optional[RecoveryStrategy] = None
    recovered: bool = False
    
    def __str__(self) -> str:
        """String representation for logging."""
        parts = [f"[{self.severity.value}] {self.category.value}: {self.message}"]
        
        if self.source_file:
            location = str(self.source_file)
            if self.line_number:
                location += f":{self.line_number}"
                if self.column_number:
                    location += f":{self.column_number}"
            parts.append(f"Location: {location}")
        
        if self.element_id:
            parts.append(f"Element: {self.element_id}")
        
        if self.details:
            parts.append(f"Details: {self.details}")
        
        return " | ".join(parts)
    
    def to_dict(self) -> dict[str, any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of error
        """
        return {
            'severity': self.severity.value,
            'category': self.category.value,
            'message': self.message,
            'details': self.details,
            'source_file': str(self.source_file) if self.source_file else None,
            'line_number': self.line_number,
            'column_number': self.column_number,
            'element_id': self.element_id,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'recovery_strategy': self.recovery_strategy.value if self.recovery_strategy else None,
            'recovered': self.recovered
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, any]) -> 'ParsingError':
        """
        Create error from dictionary.
        
        Args:
            data: Dictionary with error data
            
        Returns:
            ParsingError instance
        """
        return cls(
            severity=ErrorSeverity(data['severity']),
            category=ErrorCategory(data['category']),
            message=data['message'],
            details=data.get('details'),
            source_file=Path(data['source_file']) if data.get('source_file') else None,
            line_number=data.get('line_number'),
            column_number=data.get('column_number'),
            element_id=data.get('element_id'),
            context=data.get('context', {}),
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else datetime.now(),
            recovery_strategy=RecoveryStrategy(data['recovery_strategy']) if data.get('recovery_strategy') else None,
            recovered=data.get('recovered', False)
        )


# ==============================================================================
# ERROR COLLECTION
# ==============================================================================

@dataclass
class ErrorCollection:
    """
    Collection of parsing errors with statistics and filtering.
    
    Attributes:
        errors: list of parsing errors
    """
    errors: list[ParsingError] = field(default_factory=list)
    
    def add(self, error: ParsingError) -> None:
        """Add error to collection."""
        self.errors.append(error)
    
    def extend(self, errors: list[ParsingError]) -> None:
        """Add multiple errors to collection."""
        self.errors.extend(errors)
    
    def get_by_severity(self, severity: ErrorSeverity) -> list[ParsingError]:
        """Get all errors of specific severity."""
        return [e for e in self.errors if e.severity == severity]
    
    def get_by_category(self, category: ErrorCategory) -> list[ParsingError]:
        """Get all errors of specific category."""
        return [e for e in self.errors if e.category == category]
    
    def has_critical(self) -> bool:
        """Check if collection contains critical errors."""
        return any(e.severity == ErrorSeverity.CRITICAL for e in self.errors)
    
    def has_errors(self) -> bool:
        """Check if collection contains ERROR level or higher."""
        return any(e.severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL) 
                  for e in self.errors)
    
    def count_by_severity(self) -> dict[ErrorSeverity, int]:
        """Count errors by severity level."""
        counts = {severity: 0 for severity in ErrorSeverity}
        for error in self.errors:
            counts[error.severity] += 1
        return counts
    
    def count_by_category(self) -> dict[ErrorCategory, int]:
        """Count errors by category."""
        counts = {}
        for error in self.errors:
            counts[error.category] = counts.get(error.category, 0) + 1
        return counts
    
    def get_worst_severity(self) -> Optional[ErrorSeverity]:
        """Get worst (highest) severity level in collection."""
        if not self.errors:
            return None
        return max(e.severity for e in self.errors)
    
    def determine_reliability(self) -> ReliabilityLevel:
        """
        Determine overall reliability level based on errors.
        
        Logic:
            - FAILED: Has critical errors
            - DEGRADED: Has 5+ errors or 3+ ERROR level
            - PARTIAL: Has 1+ errors
            - COMPLETE: No errors
            
        Returns:
            ReliabilityLevel
        """
        if not self.errors:
            return ReliabilityLevel.COMPLETE
        
        if self.has_critical():
            return ReliabilityLevel.FAILED
        
        counts = self.count_by_severity()
        
        if counts[ErrorSeverity.ERROR] >= 3 or len(self.errors) >= 5:
            return ReliabilityLevel.DEGRADED
        
        if counts[ErrorSeverity.ERROR] >= 1:
            return ReliabilityLevel.PARTIAL
        
        return ReliabilityLevel.COMPLETE
    
    def to_dict_list(self) -> list[dict[str, any]]:
        """Convert all errors to list of dictionaries."""
        return [e.to_dict() for e in self.errors]
    
    def __len__(self) -> int:
        """Number of errors in collection."""
        return len(self.errors)
    
    def __bool__(self) -> bool:
        """True if collection has errors."""
        return len(self.errors) > 0
    
    def __iter__(self):
        """Iterate over errors."""
        return iter(self.errors)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_error(
    severity: ErrorSeverity,
    category: ErrorCategory,
    message: str,
    **kwargs
) -> ParsingError:
    """
    Convenience function to create a ParsingError.
    
    Args:
        severity: Error severity
        category: Error category
        message: Error message
        **kwargs: Additional error attributes
        
    Returns:
        ParsingError instance
        
    Example:
        error = create_error(
            ErrorSeverity.ERROR,
            ErrorCategory.MISSING_CONTEXT,
            "Context 'c1' not found",
            element_id="fact_123",
            source_file=Path("filing.xml"),
            line_number=450
        )
    """
    return ParsingError(
        severity=severity,
        category=category,
        message=message,
        **kwargs
    )


def create_critical_error(category: ErrorCategory, message: str, **kwargs) -> ParsingError:
    """Create CRITICAL severity error."""
    return create_error(ErrorSeverity.CRITICAL, category, message, **kwargs)


def create_standard_error(category: ErrorCategory, message: str, **kwargs) -> ParsingError:
    """Create ERROR severity error."""
    return create_error(ErrorSeverity.ERROR, category, message, **kwargs)


def create_warning(category: ErrorCategory, message: str, **kwargs) -> ParsingError:
    """Create WARNING severity error."""
    return create_error(ErrorSeverity.WARNING, category, message, **kwargs)


def create_info(category: ErrorCategory, message: str, **kwargs) -> ParsingError:
    """Create INFO severity error."""
    return create_error(ErrorSeverity.INFO, category, message, **kwargs)


__all__ = [
    'ErrorSeverity',
    'ReliabilityLevel',
    'ErrorCategory',
    'RecoveryStrategy',
    'ParsingError',
    'ErrorCollection',
    'create_error',
    'create_critical_error',
    'create_standard_error',
    'create_warning',
    'create_info',
]