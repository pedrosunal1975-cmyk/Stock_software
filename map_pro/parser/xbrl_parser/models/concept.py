# Path: xbrl_parser/models/concept.py
"""
Concept Data Model

XBRL concept (taxonomy element) representation.

This module defines:
- Concept dataclass (element definition from taxonomy)
- ConceptType classification
- Period type and balance type
- Deprecation tracking
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ==============================================================================
# CONCEPT TYPE
# ==============================================================================

class ConceptType(Enum):
    """
    Concept type classification.
    
    Types:
        MONETARY: Currency values
        SHARES: Share counts
        PERCENT: Percentages
        PER_SHARE: Per share values
        STRING: Text values
        DATE: Date/datetime values
        BOOLEAN: True/false values
        INTEGER: Integer values
        DECIMAL: Decimal values
        TEXT_BLOCK: HTML/XML content blocks
        DOMAIN: Domain member item
        ABSTRACT: Abstract grouping element
        OTHER: Other types
    """
    MONETARY = "monetary"
    SHARES = "shares"
    PERCENT = "percent"
    PER_SHARE = "per_share"
    STRING = "string"
    DATE = "date"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DECIMAL = "decimal"
    TEXT_BLOCK = "text_block"
    DOMAIN = "domain"
    ABSTRACT = "abstract"
    OTHER = "other"
    
    def __str__(self) -> str:
        return self.value


# ==============================================================================
# PERIOD TYPE
# ==============================================================================

class ConceptPeriodType(Enum):
    """
    Concept period type (from taxonomy).
    
    Types:
        INSTANT: Point-in-time values (balance sheet items)
        DURATION: Period values (income statement items)
    """
    INSTANT = "instant"
    DURATION = "duration"
    
    def __str__(self) -> str:
        return self.value


# ==============================================================================
# BALANCE TYPE
# ==============================================================================

class BalanceType(Enum):
    """
    Balance type for monetary concepts.
    
    Types:
        DEBIT: Debit balance (assets, expenses)
        CREDIT: Credit balance (liabilities, equity, revenue)
    """
    DEBIT = "debit"
    CREDIT = "credit"
    
    def __str__(self) -> str:
        return self.value


# ==============================================================================
# CONCEPT
# ==============================================================================

@dataclass
class Concept:
    """
    XBRL concept (taxonomy element definition).
    
    Core Attributes:
        qname: Qualified name (e.g., 'us-gaap:Assets')
        name: Local name (e.g., 'Assets')
        namespace: Namespace URI
        type: Data type QName
        concept_type: Classified type (monetary, shares, etc.)
        
    XBRL Attributes:
        period_type: Instant or duration
        balance: Debit or credit (for monetary items)
        abstract: True if abstract (non-reportable)
        nillable: True if can be nil
        
    Hierarchy:
        substitution_group: Parent concept in type hierarchy
        
    Labels and Documentation:
        standard_label: Standard label
        documentation: Element documentation
        
    Deprecation:
        deprecated: True if deprecated
        deprecated_date: When deprecated
        replacement_concept: Replacement concept QName
        
    Metadata:
        taxonomy_namespace: Which taxonomy this is from
        is_extension: True if from company extension taxonomy
    """
    # Core attributes
    qname: str
    name: str
    namespace: str
    type: str
    concept_type: ConceptType = ConceptType.OTHER
    
    # XBRL attributes
    period_type: Optional[ConceptPeriodType] = None
    balance: Optional[BalanceType] = None
    abstract: bool = False
    nillable: bool = True
    
    # Hierarchy
    substitution_group: Optional[str] = None
    
    # Labels and documentation
    standard_label: Optional[str] = None
    documentation: Optional[str] = None
    
    # Deprecation
    deprecated: bool = False
    deprecated_date: Optional[str] = None
    replacement_concept: Optional[str] = None
    
    # Metadata
    taxonomy_namespace: Optional[str] = None
    is_extension: bool = False
    
    def is_monetary(self) -> bool:
        """Check if concept is monetary type."""
        return self.concept_type == ConceptType.MONETARY
    
    def is_numeric(self) -> bool:
        """Check if concept is numeric type."""
        return self.concept_type in (
            ConceptType.MONETARY,
            ConceptType.SHARES,
            ConceptType.PERCENT,
            ConceptType.PER_SHARE,
            ConceptType.INTEGER,
            ConceptType.DECIMAL
        )
    
    def is_text_block(self) -> bool:
        """Check if concept is text block type."""
        return self.concept_type == ConceptType.TEXT_BLOCK
    
    def is_abstract(self) -> bool:
        """Check if concept is abstract (non-reportable)."""
        return self.abstract
    
    def is_instant(self) -> bool:
        """Check if concept is instant period type."""
        return self.period_type == ConceptPeriodType.INSTANT
    
    def is_duration(self) -> bool:
        """Check if concept is duration period type."""
        return self.period_type == ConceptPeriodType.DURATION
    
    def is_debit(self) -> bool:
        """Check if concept has debit balance."""
        return self.balance == BalanceType.DEBIT
    
    def is_credit(self) -> bool:
        """Check if concept has credit balance."""
        return self.balance == BalanceType.CREDIT
    
    def get_prefix(self) -> Optional[str]:
        """
        Extract namespace prefix from QName.
        
        Returns:
            Prefix (e.g., 'us-gaap' from 'us-gaap:Assets')
        """
        if ':' in self.qname:
            return self.qname.split(':')[0]
        return None
    
    def get_local_name(self) -> str:
        """
        Extract local name from QName.
        
        Returns:
            Local name (e.g., 'Assets' from 'us-gaap:Assets')
        """
        if ':' in self.qname:
            return self.qname.split(':')[-1]
        return self.qname
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for serialization."""
        return {
            'qname': self.qname,
            'name': self.name,
            'namespace': self.namespace,
            'type': self.type,
            'concept_type': self.concept_type.value,
            'period_type': self.period_type.value if self.period_type else None,
            'balance': self.balance.value if self.balance else None,
            'abstract': self.abstract,
            'nillable': self.nillable,
            'substitution_group': self.substitution_group,
            'standard_label': self.standard_label,
            'documentation': self.documentation,
            'deprecated': self.deprecated,
            'deprecated_date': self.deprecated_date,
            'replacement_concept': self.replacement_concept,
            'taxonomy_namespace': self.taxonomy_namespace,
            'is_extension': self.is_extension,
            'is_monetary': self.is_monetary(),
            'is_numeric': self.is_numeric(),
        }


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_concept(
    qname: str,
    name: str,
    namespace: str,
    type_qname: str,
    **kwargs
) -> Concept:
    """
    Convenience function to create a Concept.
    
    Args:
        qname: Qualified name
        name: Local name
        namespace: Namespace URI
        type_qname: Type QName
        **kwargs: Additional concept attributes
        
    Returns:
        Concept instance
    """
    return Concept(
        qname=qname,
        name=name,
        namespace=namespace,
        type=type_qname,
        **kwargs
    )


def create_monetary_concept(
    qname: str,
    name: str,
    namespace: str,
    period_type: ConceptPeriodType,
    balance: BalanceType,
    **kwargs
) -> Concept:
    """Create monetary concept."""
    return Concept(
        qname=qname,
        name=name,
        namespace=namespace,
        type="xbrli:monetaryItemType",
        concept_type=ConceptType.MONETARY,
        period_type=period_type,
        balance=balance,
        **kwargs
    )


def create_shares_concept(
    qname: str,
    name: str,
    namespace: str,
    period_type: ConceptPeriodType,
    **kwargs
) -> Concept:
    """Create shares concept."""
    return Concept(
        qname=qname,
        name=name,
        namespace=namespace,
        type="xbrli:sharesItemType",
        concept_type=ConceptType.SHARES,
        period_type=period_type,
        **kwargs
    )


def create_abstract_concept(
    qname: str,
    name: str,
    namespace: str,
    **kwargs
) -> Concept:
    """Create abstract concept (non-reportable)."""
    return Concept(
        qname=qname,
        name=name,
        namespace=namespace,
        type="xbrli:stringItemType",
        concept_type=ConceptType.ABSTRACT,
        abstract=True,
        **kwargs
    )


__all__ = [
    'ConceptType',
    'ConceptPeriodType',
    'BalanceType',
    'Concept',
    'create_concept',
    'create_monetary_concept',
    'create_shares_concept',
    'create_abstract_concept',
]