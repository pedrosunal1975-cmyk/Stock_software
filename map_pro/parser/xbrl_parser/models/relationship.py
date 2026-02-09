# Path: xbrl_parser/models/relationship.py
"""
Relationship Data Model

XBRL relationship network representation.

This module defines:
- Relationship base class
- Presentation, calculation, definition relationships
- Label and reference linkbases
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ==============================================================================
# RELATIONSHIP TYPE
# ==============================================================================

class RelationshipType(Enum):
    """
    Relationship type classification.
    
    Types:
        PRESENTATION: Display hierarchy relationships
        CALCULATION: Arithmetic relationships
        DEFINITION: Dimensional relationships
        LABEL: Concept labels
        REFERENCE: Concept references
    """
    PRESENTATION = "presentation"
    CALCULATION = "calculation"
    DEFINITION = "definition"
    LABEL = "label"
    REFERENCE = "reference"
    
    def __str__(self) -> str:
        return self.value


# ==============================================================================
# BASE RELATIONSHIP
# ==============================================================================

@dataclass
class Relationship:
    """
    Base XBRL relationship.
    
    Attributes:
        relationship_type: Type of relationship
        from_concept: Source concept QName
        to_concept: Target concept QName
        role: Extended link role URI
        arcrole: Arc role URI
        order: Ordering attribute
        priority: Priority for override resolution
        prohibited: True if relationship is prohibited
    """
    relationship_type: RelationshipType
    from_concept: str
    to_concept: str
    role: str
    arcrole: Optional[str] = None
    order: float = 1.0
    priority: int = 0
    prohibited: bool = False
    
    def is_prohibited(self) -> bool:
        """Check if relationship is prohibited."""
        return self.prohibited
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'relationship_type': self.relationship_type.value,
            'from_concept': self.from_concept,
            'to_concept': self.to_concept,
            'role': self.role,
            'arcrole': self.arcrole,
            'order': self.order,
            'priority': self.priority,
            'prohibited': self.prohibited,
        }


# ==============================================================================
# PRESENTATION RELATIONSHIP
# ==============================================================================

@dataclass
class PresentationRelationship(Relationship):
    """
    Presentation relationship (display hierarchy).
    
    Additional Attributes:
        preferred_label: Label role for display
        
    Example:
        PresentationRelationship(
            from_concept="us-gaap:Assets",
            to_concept="us-gaap:CurrentAssets",
            role="http://example.com/role/BalanceSheet",
            order=1.0,
            preferred_label="http://www.xbrl.org/2003/role/periodStartLabel"
        )
    """
    preferred_label: Optional[str] = None
    
    def __post_init__(self):
        """set relationship type."""
        self.relationship_type = RelationshipType.PRESENTATION
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result['preferred_label'] = self.preferred_label
        return result


# ==============================================================================
# CALCULATION RELATIONSHIP
# ==============================================================================

@dataclass
class CalculationRelationship(Relationship):
    """
    Calculation relationship (arithmetic).
    
    Additional Attributes:
        weight: Calculation weight (+1 or -1)
        
    Example:
        CalculationRelationship(
            from_concept="us-gaap:Assets",
            to_concept="us-gaap:CurrentAssets",
            role="http://example.com/role/BalanceSheet",
            weight=1.0,
            order=1.0
        )
    """
    weight: float = 1.0
    
    def __post_init__(self):
        """set relationship type."""
        self.relationship_type = RelationshipType.CALCULATION
    
    def is_addition(self) -> bool:
        """Check if calculation is addition (weight = +1)."""
        return self.weight > 0
    
    def is_subtraction(self) -> bool:
        """Check if calculation is subtraction (weight = -1)."""
        return self.weight < 0
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result['weight'] = self.weight
        result['is_addition'] = self.is_addition()
        return result


# ==============================================================================
# DEFINITION RELATIONSHIP
# ==============================================================================

@dataclass
class DefinitionRelationship(Relationship):
    """
    Definition relationship (dimensional).
    
    Used for:
        - Dimension-domain relationships
        - Domain-member relationships
        - Hypercube-dimension relationships
        
    Additional Attributes:
        target_role: Target role for closed hypercubes
        context_element: Context element (segment/scenario)
        closed: True if closed dimension
        
    Example:
        DefinitionRelationship(
            from_concept="us-gaap:StatementTable",
            to_concept="us-gaap:StatementGeographicalAxis",
            role="http://example.com/role/Disclosure",
            arcrole="http://xbrl.org/int/dim/arcrole/hypercube-dimension"
        )
    """
    target_role: Optional[str] = None
    context_element: Optional[str] = None
    closed: bool = False
    
    def __post_init__(self):
        """set relationship type."""
        self.relationship_type = RelationshipType.DEFINITION
    
    def is_hypercube_dimension(self) -> bool:
        """Check if relationship is hypercube-dimension."""
        return self.arcrole and 'hypercube-dimension' in self.arcrole
    
    def is_dimension_domain(self) -> bool:
        """Check if relationship is dimension-domain."""
        return self.arcrole and 'dimension-domain' in self.arcrole
    
    def is_domain_member(self) -> bool:
        """Check if relationship is domain-member."""
        return self.arcrole and 'domain-member' in self.arcrole
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result['target_role'] = self.target_role
        result['context_element'] = self.context_element
        result['closed'] = self.closed
        return result


# ==============================================================================
# LABEL
# ==============================================================================

@dataclass
class Label:
    """
    Concept label (human-readable text).
    
    Attributes:
        concept: Concept QName
        label: Label text
        role: Label role (standard, verbose, documentation, etc.)
        language: Language code (e.g., 'en', 'en-US')
        
    Example:
        Label(
            concept="us-gaap:Assets",
            label="Assets",
            role="http://www.xbrl.org/2003/role/label",
            language="en"
        )
    """
    concept: str
    label: str
    role: str
    language: str = "en"
    
    def is_standard_label(self) -> bool:
        """Check if label is standard label role."""
        return self.role.endswith('/role/label')
    
    def is_verbose_label(self) -> bool:
        """Check if label is verbose label role."""
        return self.role.endswith('/verboseLabel')
    
    def is_documentation(self) -> bool:
        """Check if label is documentation."""
        return self.role.endswith('/documentation')
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'concept': self.concept,
            'label': self.label,
            'role': self.role,
            'language': self.language,
        }


# ==============================================================================
# REFERENCE
# ==============================================================================

@dataclass
class Reference:
    """
    Concept reference (authoritative citation).
    
    Attributes:
        concept: Concept QName
        role: Reference role
        parts: Dictionary of reference parts (e.g., Name, Number, Section)
        
    Example:
        Reference(
            concept="us-gaap:Assets",
            role="http://www.xbrl.org/2003/role/reference",
            parts={
                "Name": "Accounting Standards Codification",
                "Topic": "210",
                "SubTopic": "10",
                "Section": "S99"
            }
        )
    """
    concept: str
    role: str
    parts: dict[str, str] = field(default_factory=dict)
    
    def get_part(self, part_name: str) -> Optional[str]:
        """Get reference part by name."""
        return self.parts.get(part_name)
    
    def get_citation(self) -> str:
        """
        Get formatted citation string.
        
        Returns:
            Formatted citation
        """
        if not self.parts:
            return ""
        
        # Try common citation formats
        if 'Name' in self.parts:
            citation = self.parts['Name']
            if 'Topic' in self.parts:
                citation += f" {self.parts['Topic']}"
            if 'SubTopic' in self.parts:
                citation += f"-{self.parts['SubTopic']}"
            if 'Section' in self.parts:
                citation += f"-{self.parts['Section']}"
            return citation
        
        # Fallback: join all parts
        return ", ".join(f"{k}: {v}" for k, v in self.parts.items())
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'concept': self.concept,
            'role': self.role,
            'parts': self.parts,
            'citation': self.get_citation(),
        }


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_presentation_relationship(
    from_concept: str,
    to_concept: str,
    role: str,
    order: float = 1.0,
    **kwargs
) -> PresentationRelationship:
    """Create presentation relationship."""
    return PresentationRelationship(
        relationship_type=RelationshipType.PRESENTATION,
        from_concept=from_concept,
        to_concept=to_concept,
        role=role,
        order=order,
        **kwargs
    )


def create_calculation_relationship(
    from_concept: str,
    to_concept: str,
    role: str,
    weight: float = 1.0,
    order: float = 1.0,
    **kwargs
) -> CalculationRelationship:
    """Create calculation relationship."""
    return CalculationRelationship(
        relationship_type=RelationshipType.CALCULATION,
        from_concept=from_concept,
        to_concept=to_concept,
        role=role,
        weight=weight,
        order=order,
        **kwargs
    )


def create_definition_relationship(
    from_concept: str,
    to_concept: str,
    role: str,
    arcrole: str,
    **kwargs
) -> DefinitionRelationship:
    """Create definition relationship."""
    return DefinitionRelationship(
        relationship_type=RelationshipType.DEFINITION,
        from_concept=from_concept,
        to_concept=to_concept,
        role=role,
        arcrole=arcrole,
        **kwargs
    )


__all__ = [
    'RelationshipType',
    'Relationship',
    'PresentationRelationship',
    'CalculationRelationship',
    'DefinitionRelationship',
    'Label',
    'Reference',
    'create_presentation_relationship',
    'create_calculation_relationship',
    'create_definition_relationship',
]