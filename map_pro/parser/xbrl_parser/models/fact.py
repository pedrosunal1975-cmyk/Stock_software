# Path: xbrl_parser/models/fact.py
"""
Fact Data Model

XBRL fact representation with reliability tracking.

This module defines:
- Fact dataclass (core XBRL fact)
- FactReliability enum (data quality tracking)
- Support for numeric, text block, tuple, and nil facts
- Provenance and error tracking
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from pathlib import Path

from ..models.error import ParsingError, ReliabilityLevel


# ==============================================================================
# FACT RELIABILITY
# ==============================================================================

class FactReliability(Enum):
    """
    Fact-level reliability classification.
    
    Levels:
        HIGH: Fact extracted cleanly, no issues
        MEDIUM: Fact extracted with minor warnings
        LOW: Fact extracted with errors or recovery
        SUSPECT: Fact may be incorrect, major issues
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SUSPECT = "SUSPECT"
    
    def __str__(self) -> str:
        return self.value


# ==============================================================================
# FACT TYPE
# ==============================================================================

class FactType(Enum):
    """
    Fact type classification.
    
    Types:
        NUMERIC: Numeric fact (monetary, shares, percent, etc.)
        TEXT: Text fact (string, normalized string)
        TEXT_BLOCK: HTML/XML content fact
        DATE: Date or datetime fact
        BOOLEAN: Boolean fact
        TUPLE: Deprecated tuple fact
    """
    NUMERIC = "NUMERIC"
    TEXT = "TEXT"
    TEXT_BLOCK = "TEXT_BLOCK"
    DATE = "DATE"
    BOOLEAN = "BOOLEAN"
    TUPLE = "TUPLE"
    
    def __str__(self) -> str:
        return self.value


# ==============================================================================
# FACT DATA MODEL
# ==============================================================================

@dataclass
class Fact:
    """
    XBRL fact representation.
    
    Core Attributes:
        concept: Concept QName (e.g., 'us-gaap:Assets')
        value: Fact value (preserved exactly as string)
        context_ref: Reference to context ID
        unit_ref: Reference to unit ID (optional, numeric facts only)
        
    Precision Attributes:
        decimals: Decimals attribute (e.g., '2', 'INF')
        precision: Precision attribute (rarely used, mutually exclusive with decimals)
        
    Metadata:
        id: Fact ID attribute (optional)
        is_nil: True if xsi:nil="true"
        fact_type: Type classification
        language: xml:lang attribute (for text facts)
        
    Extended Attributes:
        footnote_refs: References to footnotes
        tuple_parent: Parent fact ID (for tuple facts)
        tuple_order: Order within tuple
        
    Reliability Tracking:
        reliability: Quality level (HIGH, MEDIUM, LOW, SUSPECT)
        source_component: Which parser component extracted this
        errors: Errors encountered during extraction
        warnings: Warnings encountered during extraction
        
    Provenance:
        source_file: Source XML file path
        source_line: Line number in source file
        source_element: XML element that created this fact
    """
    # Core attributes (required)
    concept: str
    value: str
    context_ref: str
    
    # Optional core attributes
    unit_ref: Optional[str] = None
    decimals: Optional[str] = None
    precision: Optional[str] = None
    
    # Metadata
    id: Optional[str] = None
    is_nil: bool = False
    fact_type: FactType = FactType.TEXT
    language: Optional[str] = None
    
    # Extended attributes
    footnote_refs: list[str] = field(default_factory=list)
    tuple_parent: Optional[str] = None
    tuple_order: Optional[int] = None
    
    # Reliability tracking
    reliability: FactReliability = FactReliability.HIGH
    source_component: Optional[str] = None
    errors: list[ParsingError] = field(default_factory=list)
    warnings: list[ParsingError] = field(default_factory=list)
    
    # Provenance
    source_file: Optional[Path] = None
    source_line: Optional[int] = None
    source_element: Optional[str] = None
    
    def is_numeric(self) -> bool:
        """Check if fact is numeric type."""
        return self.fact_type == FactType.NUMERIC
    
    def is_text_block(self) -> bool:
        """Check if fact is text block (HTML/XML content)."""
        return self.fact_type == FactType.TEXT_BLOCK
    
    def is_tuple(self) -> bool:
        """Check if fact is tuple type."""
        return self.fact_type == FactType.TUPLE
    
    def has_unit(self) -> bool:
        """Check if fact has unit reference."""
        return self.unit_ref is not None
    
    def has_errors(self) -> bool:
        """Check if fact has errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if fact has warnings."""
        return len(self.warnings) > 0
    
    def add_error(self, error: ParsingError) -> None:
        """
        Add error to fact and downgrade reliability.
        
        Args:
            error: ParsingError to add
        """
        self.errors.append(error)
        # Downgrade reliability
        if self.reliability == FactReliability.HIGH:
            self.reliability = FactReliability.MEDIUM
        elif self.reliability == FactReliability.MEDIUM:
            self.reliability = FactReliability.LOW
        elif self.reliability == FactReliability.LOW:
            self.reliability = FactReliability.SUSPECT
    
    def add_warning(self, warning: ParsingError) -> None:
        """
        Add warning to fact (may downgrade reliability).
        
        Args:
            warning: ParsingError to add
        """
        self.warnings.append(warning)
        # Minor reliability downgrade for warnings
        if self.reliability == FactReliability.HIGH and len(self.warnings) >= 2:
            self.reliability = FactReliability.MEDIUM
    
    def get_numeric_value(self) -> Optional[float]:
        """
        Get numeric value as float (if numeric fact).
        
        Returns:
            Float value or None if not numeric or cannot parse
        """
        if not self.is_numeric() or self.is_nil:
            return None
        
        try:
            return float(self.value)
        except (ValueError, TypeError):
            return None
    
    def to_dict(self) -> dict[str, any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            'concept': self.concept,
            'value': self.value,
            'context_ref': self.context_ref,
            'unit_ref': self.unit_ref,
            'decimals': self.decimals,
            'precision': self.precision,
            'id': self.id,
            'is_nil': self.is_nil,
            'fact_type': self.fact_type.value,
            'language': self.language,
            'footnote_refs': self.footnote_refs,
            'tuple_parent': self.tuple_parent,
            'tuple_order': self.tuple_order,
            'reliability': self.reliability.value,
            'source_component': self.source_component,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings],
            'source_file': str(self.source_file) if self.source_file else None,
            'source_line': self.source_line,
            'source_element': self.source_element,
        }


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_fact(
    concept: str,
    value: str,
    context_ref: str,
    **kwargs
) -> Fact:
    """
    Convenience function to create a Fact.
    
    Args:
        concept: Concept QName
        value: Fact value
        context_ref: Context reference
        **kwargs: Additional fact attributes
        
    Returns:
        Fact instance
        
    Example:
        fact = create_fact(
            concept="us-gaap:Assets",
            value="1000000",
            context_ref="c1",
            unit_ref="usd",
            decimals="0",
            fact_type=FactType.NUMERIC
        )
    """
    return Fact(
        concept=concept,
        value=value,
        context_ref=context_ref,
        **kwargs
    )


def create_numeric_fact(
    concept: str,
    value: str,
    context_ref: str,
    unit_ref: str,
    decimals: Optional[str] = None,
    **kwargs
) -> Fact:
    """Create numeric fact."""
    return Fact(
        concept=concept,
        value=value,
        context_ref=context_ref,
        unit_ref=unit_ref,
        decimals=decimals,
        fact_type=FactType.NUMERIC,
        **kwargs
    )


def create_text_fact(
    concept: str,
    value: str,
    context_ref: str,
    **kwargs
) -> Fact:
    """Create text fact."""
    return Fact(
        concept=concept,
        value=value,
        context_ref=context_ref,
        fact_type=FactType.TEXT,
        **kwargs
    )


def create_nil_fact(
    concept: str,
    context_ref: str,
    **kwargs
) -> Fact:
    """Create nil fact (intentionally empty)."""
    return Fact(
        concept=concept,
        value="",
        context_ref=context_ref,
        is_nil=True,
        **kwargs
    )


__all__ = [
    'FactReliability',
    'FactType',
    'Fact',
    'create_fact',
    'create_numeric_fact',
    'create_text_fact',
    'create_nil_fact',
]
