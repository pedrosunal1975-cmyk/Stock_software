# Path: components/relationship_navigator.py
"""
Relationship Navigator

Navigate company-declared taxonomy relationships from linkbases.

DESIGN PRINCIPLES:
- Reads relationships from LinkbaseSet (presentation, calculation, definition)
- NO hardcoded relationships
- Follows company declarations exactly
- Market and taxonomy agnostic

RESPONSIBILITY:
- Navigate presentation hierarchies
- Navigate calculation relationships (with weights)
- Navigate definition relationships (dimensions)
- Provide relationship metadata (order, preferred labels)

THREE LINKBASE TYPES:
1. Presentation: Display hierarchy (parent-child)
2. Calculation: Mathematical relationships (summation-item with weights)
3. Definition: Dimensional relationships (hypercube-dimension, etc.)

Example:
    navigator = RelationshipNavigator(linkbase_set)
    
    # Get presentation children
    children = navigator.get_children('us-gaap:Assets', role_uri, 'presentation')
    
    # Get calculation weight
    weight = navigator.get_weight('us-gaap:Assets', 'us-gaap:Cash', role_uri)
    
    # Navigate hierarchy
    path = navigator.get_path_to_root('us-gaap:Cash', role_uri)
"""

import logging
from typing import Optional
from dataclasses import dataclass, field

from ..loaders.linkbase_locator import (
    LinkbaseSet,
    PresentationNetwork,
    CalculationNetwork,
    DefinitionNetwork
)
from ..components.constants import (
    ARCROLE_PARENT_CHILD,
    ARCROLE_SUMMATION_ITEM,
)


@dataclass
class Relationship:
    """A relationship between two concepts."""
    from_concept: str
    to_concept: str
    arcrole: str
    role_uri: str
    order: Optional[float] = None
    weight: Optional[float] = None
    preferred_label: Optional[str] = None
    priority: Optional[int] = None
    use: Optional[str] = None
    metadata: dict[str, any] = field(default_factory=dict)


class RelationshipNavigator:
    """
    Navigate company-declared taxonomy relationships.
    
    Builds navigation structures from LinkbaseSet for efficient
    relationship traversal.
    
    Example:
        navigator = RelationshipNavigator(linkbase_set)
        
        # Get children in specific role
        children = navigator.get_presentation_children(
            'us-gaap:Assets',
            'http://company.com/role/BalanceSheet'
        )
        
        # Get calculation weight
        weight = navigator.get_calculation_weight(
            parent='us-gaap:Assets',
            child='us-gaap:Cash',
            role_uri='http://company.com/role/BalanceSheet'
        )
        
        # Check if relationship exists
        is_child = navigator.is_child_of(
            child='us-gaap:Cash',
            parent='us-gaap:Assets',
            role_uri='http://company.com/role/BalanceSheet'
        )
    """
    
    def __init__(self, linkbase_set: LinkbaseSet):
        """
        Initialize navigator with linkbase set.
        
        Args:
            linkbase_set: LinkbaseSet with discovered networks
        """
        self.logger = logging.getLogger('components.relationship_navigator')
        self.linkbase_set = linkbase_set
        
        # Build relationship indexes
        self._presentation_rels: list[Relationship] = []
        self._calculation_rels: list[Relationship] = []
        self._definition_rels: list[Relationship] = []
        
        # Build indexes for fast lookup
        self._children_index: dict[tuple[str, str, str], list[str]] = {}  # (concept, role, type) -> children
        self._parents_index: dict[tuple[str, str, str], list[str]] = {}   # (concept, role, type) -> parents
        self._weight_index: dict[tuple[str, str, str], float] = {}        # (parent, child, role) -> weight
        
        self._build_relationships()
        
        self.logger.info(
            f"RelationshipNavigator initialized: "
            f"{len(self._presentation_rels)} presentation, "
            f"{len(self._calculation_rels)} calculation, "
            f"{len(self._definition_rels)} definition relationships"
        )
    
    def get_presentation_children(
        self,
        concept: str,
        role_uri: str
    ) -> list[str]:
        """
        Get presentation children of a concept in a specific role.
        
        Args:
            concept: Parent concept
            role_uri: Role URI
            
        Returns:
            List of child concepts (ordered)
        """
        return self._get_children(concept, role_uri, 'presentation')
    
    def get_calculation_children(
        self,
        concept: str,
        role_uri: str
    ) -> list[str]:
        """
        Get calculation children of a concept in a specific role.
        
        Args:
            concept: Parent concept
            role_uri: Role URI
            
        Returns:
            List of child concepts (ordered)
        """
        return self._get_children(concept, role_uri, 'calculation')
    
    def get_definition_children(
        self,
        concept: str,
        role_uri: str
    ) -> list[str]:
        """
        Get definition children of a concept in a specific role.
        
        Args:
            concept: Parent concept
            role_uri: Role URI
            
        Returns:
            List of child concepts
        """
        return self._get_children(concept, role_uri, 'definition')
    
    def get_calculation_weight(
        self,
        parent: str,
        child: str,
        role_uri: str
    ) -> Optional[float]:
        """
        Get calculation weight for parent-child relationship.
        
        Args:
            parent: Parent concept
            child: Child concept
            role_uri: Role URI
            
        Returns:
            Weight (typically 1.0 or -1.0) or None
        """
        key = (parent, child, role_uri)
        return self._weight_index.get(key)
    
    def get_parents(
        self,
        concept: str,
        role_uri: str,
        linkbase_type: str = 'presentation'
    ) -> list[str]:
        """
        Get parent concepts.
        
        Args:
            concept: Child concept
            role_uri: Role URI
            linkbase_type: 'presentation', 'calculation', or 'definition'
            
        Returns:
            List of parent concepts
        """
        key = (concept, role_uri, linkbase_type)
        return self._parents_index.get(key, [])
    
    def is_child_of(
        self,
        child: str,
        parent: str,
        role_uri: str,
        linkbase_type: str = 'presentation'
    ) -> bool:
        """
        Check if concept is child of another.
        
        Args:
            child: Child concept
            parent: Parent concept
            role_uri: Role URI
            linkbase_type: Type of linkbase
            
        Returns:
            True if relationship exists
        """
        children = self._get_children(parent, role_uri, linkbase_type)
        return child in children
    
    def get_path_to_root(
        self,
        concept: str,
        role_uri: str,
        linkbase_type: str = 'presentation'
    ) -> list[str]:
        """
        Get path from concept to root.
        
        Args:
            concept: Starting concept
            role_uri: Role URI
            linkbase_type: Type of linkbase
            
        Returns:
            List of concepts from concept to root
        """
        path = [concept]
        current = concept
        visited = {concept}
        
        while True:
            parents = self.get_parents(current, role_uri, linkbase_type)
            
            if not parents:
                break
            
            # Take first parent (in case of multiple)
            parent = parents[0]
            
            if parent in visited:
                # Cycle detected
                break
            
            path.append(parent)
            visited.add(parent)
            current = parent
        
        return path
    
    def get_relationship(
        self,
        from_concept: str,
        to_concept: str,
        role_uri: str,
        linkbase_type: str = 'presentation'
    ) -> Optional[Relationship]:
        """
        Get specific relationship.
        
        Args:
            from_concept: From concept
            to_concept: To concept
            role_uri: Role URI
            linkbase_type: Type of linkbase
            
        Returns:
            Relationship or None
        """
        rels = {
            'presentation': self._presentation_rels,
            'calculation': self._calculation_rels,
            'definition': self._definition_rels
        }.get(linkbase_type, [])
        
        for rel in rels:
            if (rel.from_concept == from_concept and
                rel.to_concept == to_concept and
                rel.role_uri == role_uri):
                return rel
        
        return None
    
    def _build_relationships(self) -> None:
        """Build relationship structures from linkbase set."""
        # Build from presentation networks
        for network in self.linkbase_set.presentation_networks:
            self._build_from_presentation(network)
        
        # Build from calculation networks
        for network in self.linkbase_set.calculation_networks:
            self._build_from_calculation(network)
        
        # Build from definition networks
        for network in self.linkbase_set.definition_networks:
            self._build_from_definition(network)
    
    def _build_from_presentation(self, network: PresentationNetwork) -> None:
        """Build relationships from presentation network."""
        for arc in network.arcs:
            from_loc = arc.get('from')
            to_loc = arc.get('to')
            
            if not from_loc or not to_loc:
                continue
            
            from_concept = self._extract_concept_from_locator(from_loc)
            to_concept = self._extract_concept_from_locator(to_loc)
            
            if not from_concept or not to_concept:
                continue
            
            # Create relationship
            rel = Relationship(
                from_concept=from_concept,
                to_concept=to_concept,
                arcrole=ARCROLE_PARENT_CHILD,
                role_uri=network.role_uri,
                order=self._safe_float(arc.get('order')),
                preferred_label=arc.get('preferredLabel'),
                priority=self._safe_int(arc.get('priority')),
                use=arc.get('use')
            )
            
            self._presentation_rels.append(rel)
            
            # Index for fast lookup
            self._index_relationship(from_concept, to_concept, network.role_uri, 'presentation', rel.order)
    
    def _build_from_calculation(self, network: CalculationNetwork) -> None:
        """Build relationships from calculation network."""
        for arc in network.arcs:
            from_loc = arc.get('from')
            to_loc = arc.get('to')
            
            if not from_loc or not to_loc:
                continue
            
            from_concept = self._extract_concept_from_locator(from_loc)
            to_concept = self._extract_concept_from_locator(to_loc)
            
            if not from_concept or not to_concept:
                continue
            
            # Create relationship
            weight = self._safe_float(arc.get('weight'))
            
            rel = Relationship(
                from_concept=from_concept,
                to_concept=to_concept,
                arcrole=ARCROLE_SUMMATION_ITEM,
                role_uri=network.role_uri,
                order=self._safe_float(arc.get('order')),
                weight=weight,
                priority=self._safe_int(arc.get('priority')),
                use=arc.get('use')
            )
            
            self._calculation_rels.append(rel)
            
            # Index for fast lookup
            self._index_relationship(from_concept, to_concept, network.role_uri, 'calculation', rel.order)
            
            # Index weight
            if weight is not None:
                self._weight_index[(from_concept, to_concept, network.role_uri)] = weight
    
    def _build_from_definition(self, network: DefinitionNetwork) -> None:
        """Build relationships from definition network."""
        for arc in network.arcs:
            from_loc = arc.get('from')
            to_loc = arc.get('to')
            arcrole = arc.get('arcrole', '')
            
            if not from_loc or not to_loc:
                continue
            
            from_concept = self._extract_concept_from_locator(from_loc)
            to_concept = self._extract_concept_from_locator(to_loc)
            
            if not from_concept or not to_concept:
                continue
            
            # Create relationship
            rel = Relationship(
                from_concept=from_concept,
                to_concept=to_concept,
                arcrole=arcrole,
                role_uri=network.role_uri,
                order=self._safe_float(arc.get('order')),
                priority=self._safe_int(arc.get('priority')),
                use=arc.get('use')
            )
            
            self._definition_rels.append(rel)
            
            # Index for fast lookup
            self._index_relationship(from_concept, to_concept, network.role_uri, 'definition', rel.order)
    
    def _index_relationship(
        self,
        from_concept: str,
        to_concept: str,
        role_uri: str,
        linkbase_type: str,
        order: Optional[float]
    ) -> None:
        """Index relationship for fast lookup."""
        # Index children
        key = (from_concept, role_uri, linkbase_type)
        if key not in self._children_index:
            self._children_index[key] = []
        self._children_index[key].append(to_concept)
        
        # Index parents
        key = (to_concept, role_uri, linkbase_type)
        if key not in self._parents_index:
            self._parents_index[key] = []
        self._parents_index[key].append(from_concept)
    
    def _get_children(
        self,
        concept: str,
        role_uri: str,
        linkbase_type: str
    ) -> list[str]:
        """Get children from index."""
        key = (concept, role_uri, linkbase_type)
        return self._children_index.get(key, [])
    
    def _extract_concept_from_locator(self, locator: str) -> Optional[str]:
        """Extract QName from locator ID."""
        if not locator or not locator.startswith('loc_'):
            return None
        
        rest = locator[4:]
        parts = rest.split('_')
        
        if len(parts) < 2:
            return None
        
        prefix = parts[0]
        local_name = parts[1]
        
        return f"{prefix}:{local_name}"
    
    def _safe_float(self, value: any) -> Optional[float]:
        """Safely convert to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value: any) -> Optional[int]:
        """Safely convert to int."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


__all__ = ['RelationshipNavigator', 'Relationship']