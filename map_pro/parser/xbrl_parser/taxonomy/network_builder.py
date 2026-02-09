# Path: xbrl_parser/taxonomy/network_builder.py
"""
Network Builder

Builds relationship networks from loaded linkbases.

Features:
- Presentation tree building
- Calculation network organization
- Definition network structuring
- Root concept identification
- Network validation

Example:
    from ..taxonomy import NetworkBuilder
    
    builder = NetworkBuilder()
    network = builder.build_presentation_network(relationships)
"""

import logging
from typing import Optional
from dataclasses import dataclass, field

from ..models.relationship import (
    PresentationRelationship,
    CalculationRelationship,
    DefinitionRelationship
)


@dataclass
class PresentationNetwork:
    """
    Organized presentation network.
    
    Represents display hierarchy for financial statement presentation.
    """
    role: str
    roots: list[str] = field(default_factory=list)
    relationships: list[PresentationRelationship] = field(default_factory=list)
    concept_children: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class CalculationNetwork:
    """
    Organized calculation network.
    
    Represents arithmetic relationships for validation.
    """
    role: str
    roots: list[str] = field(default_factory=list)
    relationships: list[CalculationRelationship] = field(default_factory=list)
    summation_items: dict[str, list[tuple]] = field(default_factory=dict)


class NetworkBuilder:
    """
    Builds organized relationship networks.
    
    Takes flat relationship lists and builds hierarchical networks
    with roots, children mappings, and validation structures.
    
    Example:
        builder = NetworkBuilder()
        
        pres_network = builder.build_presentation_network(
            pres_relationships,
            role="http://example.com/role/BalanceSheet"
        )
        
        for root in pres_network.roots:
            print(f"Root: {root}")
    """
    
    def __init__(self):
        """Initialize network builder."""
        self.logger = logging.getLogger(__name__)
    
    def build_presentation_network(
        self,
        relationships: list[PresentationRelationship],
        role: Optional[str] = None
    ) -> PresentationNetwork:
        """
        Build presentation network from relationships.
        
        Args:
            relationships: list of presentation relationships
            role: Optional role URI to filter by
            
        Returns:
            PresentationNetwork with organized hierarchy
            
        Example:
            network = builder.build_presentation_network(relationships)
            print(f"Roots: {network.roots}")
        """
        self.logger.debug(f"Building presentation network: {len(relationships)} relationships")
        
        # Filter by role if specified
        if role:
            relationships = [r for r in relationships if r.role == role]
        
        # Filter out prohibited relationships
        active_rels = [r for r in relationships if not r.prohibited]
        
        # Sort by order
        active_rels.sort(key=lambda r: r.order)
        
        # Build children mapping
        concept_children = {}
        for rel in active_rels:
            if rel.from_concept not in concept_children:
                concept_children[rel.from_concept] = []
            concept_children[rel.from_concept].append(rel.to_concept)
        
        # Identify roots (concepts that appear as 'from' but never as 'to')
        from_concepts = set(r.from_concept for r in active_rels)
        to_concepts = set(r.to_concept for r in active_rels)
        roots = list(from_concepts - to_concepts)
        
        network = PresentationNetwork(
            role=role or "default",
            roots=roots,
            relationships=active_rels,
            concept_children=concept_children
        )
        
        self.logger.info(
            f"Presentation network built: {len(roots)} roots, "
            f"{len(active_rels)} relationships"
        )
        
        return network
    
    def build_calculation_network(
        self,
        relationships: list[CalculationRelationship],
        role: Optional[str] = None
    ) -> CalculationNetwork:
        """
        Build calculation network from relationships.
        
        Args:
            relationships: list of calculation relationships
            role: Optional role URI to filter by
            
        Returns:
            CalculationNetwork with summation items
            
        Example:
            network = builder.build_calculation_network(relationships)
            for parent, items in network.summation_items.items():
                print(f"{parent} = sum of {len(items)} items")
        """
        self.logger.debug(f"Building calculation network: {len(relationships)} relationships")
        
        # Filter by role if specified
        if role:
            relationships = [r for r in relationships if r.role == role]
        
        # Filter out prohibited relationships
        active_rels = [r for r in relationships if not r.prohibited]
        
        # Sort by order
        active_rels.sort(key=lambda r: r.order)
        
        # Build summation items mapping
        summation_items = {}
        for rel in active_rels:
            if rel.from_concept not in summation_items:
                summation_items[rel.from_concept] = []
            summation_items[rel.from_concept].append((rel.to_concept, rel.weight))
        
        # Identify roots
        from_concepts = set(r.from_concept for r in active_rels)
        to_concepts = set(r.to_concept for r in active_rels)
        roots = list(from_concepts - to_concepts)
        
        network = CalculationNetwork(
            role=role or "default",
            roots=roots,
            relationships=active_rels,
            summation_items=summation_items
        )
        
        self.logger.info(
            f"Calculation network built: {len(roots)} roots, "
            f"{len(summation_items)} summations"
        )
        
        return network
    
    def get_children(
        self,
        network: PresentationNetwork,
        concept: str
    ) -> list[str]:
        """
        Get children of a concept in presentation network.
        
        Args:
            network: Presentation network
            concept: Parent concept QName
            
        Returns:
            list of child concept QNames
            
        Example:
            children = builder.get_children(network, "us-gaap:Assets")
            for child in children:
                print(f"  - {child}")
        """
        return network.concept_children.get(concept, [])
    
    def get_calculation_components(
        self,
        network: CalculationNetwork,
        concept: str
    ) -> list[tuple]:
        """
        Get calculation components for a concept.
        
        Args:
            network: Calculation network
            concept: Parent concept QName
            
        Returns:
            list of (child_concept, weight) tuples
            
        Example:
            components = builder.get_calculation_components(network, "us-gaap:Assets")
            for child, weight in components:
                print(f"  {'+' if weight > 0 else '-'} {child}")
        """
        return network.summation_items.get(concept, [])


__all__ = ['NetworkBuilder', 'PresentationNetwork', 'CalculationNetwork']
