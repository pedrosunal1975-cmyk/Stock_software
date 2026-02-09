# Path: components/dimension_handler.py
"""
Dimension Handler

Handles XBRL dimensional data with definition linkbase integration.

DESIGN PRINCIPLES:
- Reads dimension definitions from definition linkbases
- NO hardcoded dimension/member names
- Cross-validates context dimensions against definitions
- Market and taxonomy agnostic

XBRL DIMENSIONS:
XBRL uses dimensions to provide breakdowns:
- Primary items: Base concepts (Revenue, Assets, etc.)
- Dimensions: Axes for breakdown (Geographic, Product, etc.)
- Members: Values on dimension (US, Europe, ProductA, etc.)
- Hypercubes: Define which dimensions apply to which concepts

Example:
    Revenue[Geographic=US, Product=ProductA] = $1M
    
    Hypercube defines:
    - Primary: Revenue
    - Dimensions: Geographic, Product
    - Domain: US/Europe/Asia, ProductA/ProductB

THREE DATA SOURCES:
1. Definition Linkbases: Dimension-domain relationships
2. Context Data: Actual dimension values in facts
3. Taxonomy: Dimension metadata

RESPONSIBILITY:
- Extract dimension definitions from definition linkbases
- Build hypercube-dimension-member hierarchies
- Validate context dimensions against definitions
- Organize dimensional facts
"""

import logging
from typing import Optional
from dataclasses import dataclass, field

from ..loaders.linkbase_locator import LinkbaseSet, DefinitionNetwork
from ..mapping.models.context import Context
from ..components.constants import DIMENSION_ARCROLES


@dataclass
class DimensionMember:
    """A member on a dimension axis."""
    member_qname: str
    label: Optional[str] = None
    metadata: dict[str, any] = field(default_factory=dict)


@dataclass
class DimensionAxis:
    """A dimension axis with its domain."""
    dimension_qname: str
    domain_qname: Optional[str] = None
    members: list[DimensionMember] = field(default_factory=list)
    is_typed: bool = False
    metadata: dict[str, any] = field(default_factory=dict)


@dataclass
class Hypercube:
    """
    A hypercube defining dimensional structure.
    
    Hypercubes define which dimensions apply to which primary items.
    """
    hypercube_qname: str
    dimensions: list[DimensionAxis] = field(default_factory=list)
    primary_items: set[str] = field(default_factory=set)
    is_closed: bool = False
    metadata: dict[str, any] = field(default_factory=dict)


@dataclass
class DimensionalContext:
    """Extracted dimensional information from a context."""
    context_id: str
    explicit_dimensions: dict[str, str] = field(default_factory=dict)  # dimension -> member
    typed_dimensions: dict[str, any] = field(default_factory=dict)  # dimension -> value
    has_dimensions: bool = False


class DimensionHandler:
    """
    Handles dimensional data with definition linkbase integration.
    
    Reads dimension definitions from company filings, validates
    dimensional facts, and organizes facts by dimensions.
    
    Example:
        handler = DimensionHandler(linkbase_set)
        
        # Extract dimension definitions
        hypercubes = handler.get_hypercubes()
        
        # Extract dimensions from context
        dim_context = handler.extract_dimensions(context)
        
        # Check if fact is dimensional
        is_dim = handler.is_dimensional_fact(fact, context)
        
        # Organize facts by dimensions
        organized = handler.organize_by_dimensions(facts, contexts)
    """
    
    def __init__(self, linkbase_set: Optional[LinkbaseSet] = None):
        """
        Initialize dimension handler.
        
        Args:
            linkbase_set: Optional LinkbaseSet with definition networks
        """
        self.logger = logging.getLogger('components.dimension_handler')
        self.linkbase_set = linkbase_set
        
        # Build dimension structures from definition linkbases
        self._hypercubes: dict[str, Hypercube] = {}
        self._dimensions: dict[str, DimensionAxis] = {}
        
        if linkbase_set:
            self._build_dimension_structures()
            self.logger.info(
                f"DimensionHandler initialized: "
                f"{len(self._hypercubes)} hypercubes, "
                f"{len(self._dimensions)} dimensions"
            )
    
    def extract_dimensions(self, context: Context) -> DimensionalContext:
        """
        Extract all dimensional information from context.
        
        Args:
            context: XBRL context
            
        Returns:
            DimensionalContext with extracted dimensions
        """
        dim_context = DimensionalContext(context_id=context.id)
        
        # Extract from segment
        if context.segment:
            self._extract_from_container(context.segment, dim_context)
        
        # Extract from scenario
        if context.scenario:
            self._extract_from_container(context.scenario, dim_context)
        
        dim_context.has_dimensions = bool(
            dim_context.explicit_dimensions or dim_context.typed_dimensions
        )
        
        return dim_context
    
    def is_dimensional_fact(self, concept: str, context: Context) -> bool:
        """
        Check if a fact is dimensional.
        
        Args:
            concept: Fact concept
            context: Fact context
            
        Returns:
            True if fact has dimensional context
        """
        dim_context = self.extract_dimensions(context)
        return dim_context.has_dimensions
    
    def get_hypercubes(self) -> list[Hypercube]:
        """
        Get all discovered hypercubes.
        
        Returns:
            List of Hypercube definitions
        """
        return list(self._hypercubes.values())
    
    def get_dimensions_for_concept(self, concept: str) -> list[DimensionAxis]:
        """
        Get applicable dimensions for a concept.
        
        Args:
            concept: Concept QName
            
        Returns:
            List of applicable DimensionAxis
        """
        applicable_dims = []
        
        for hypercube in self._hypercubes.values():
            if concept in hypercube.primary_items:
                applicable_dims.extend(hypercube.dimensions)
        
        return applicable_dims
    
    def organize_by_dimensions(
        self,
        facts: list[any],
        contexts: dict[str, Context]
    ) -> dict[str, list[any]]:
        """
        Organize facts by their dimensional breakdowns.
        
        Args:
            facts: List of facts
            contexts: Dictionary of contexts
            
        Returns:
            Dictionary mapping dimension signatures to facts
        """
        organized = {}
        
        for fact in facts:
            context = contexts.get(fact.context_ref)
            if not context:
                continue
            
            dim_context = self.extract_dimensions(context)
            
            # Create signature from dimensions
            signature = self._create_dimension_signature(dim_context)
            
            if signature not in organized:
                organized[signature] = []
            organized[signature].append(fact)
        
        return organized
    
    def dimensions_match(
        self,
        context1: Context,
        context2: Context,
        strict: bool = True
    ) -> bool:
        """
        Check if two contexts have matching dimensions.
        
        Args:
            context1: First context
            context2: Second context
            strict: If True, dimensions must match exactly
            
        Returns:
            True if dimensions match
        """
        dim1 = self.extract_dimensions(context1)
        dim2 = self.extract_dimensions(context2)
        
        if strict:
            return (
                dim1.explicit_dimensions == dim2.explicit_dimensions and
                dim1.typed_dimensions == dim2.typed_dimensions
            )
        else:
            # Lenient: context1 dimensions subset of context2
            return (
                all(k in dim2.explicit_dimensions and v == dim2.explicit_dimensions[k]
                    for k, v in dim1.explicit_dimensions.items()) and
                all(k in dim2.typed_dimensions and v == dim2.typed_dimensions[k]
                    for k, v in dim1.typed_dimensions.items())
            )
    
    def get_dimension_value(
        self,
        context: Context,
        dimension: str
    ) -> Optional[str]:
        """
        Get value for specific dimension.
        
        Args:
            context: XBRL context
            dimension: Dimension QName
            
        Returns:
            Dimension member value or None
        """
        dim_context = self.extract_dimensions(context)
        
        # Check explicit dimensions
        if dimension in dim_context.explicit_dimensions:
            return dim_context.explicit_dimensions[dimension]
        
        # Check typed dimensions
        if dimension in dim_context.typed_dimensions:
            return str(dim_context.typed_dimensions[dimension])
        
        return None
    
    def _build_dimension_structures(self) -> None:
        """Build hypercube and dimension structures from definition linkbases."""
        if not self.linkbase_set:
            return
        
        for network in self.linkbase_set.definition_networks:
            self._process_definition_network(network)
    
    def _process_definition_network(self, network: DefinitionNetwork) -> None:
        """
        Process a definition network to extract dimension relationships.
        
        Args:
            network: Definition network from linkbase
        """
        # Build arc lookup by arcrole
        arcs_by_role = {}
        for arc in network.arcs:
            arcrole = arc.get('arcrole', '')
            if arcrole not in arcs_by_role:
                arcs_by_role[arcrole] = []
            arcs_by_role[arcrole].append(arc)
        
        # Extract hypercube-dimension relationships
        hypercube_dim_arcs = arcs_by_role.get(DIMENSION_ARCROLES['hypercube-dimension'], [])
        for arc in hypercube_dim_arcs:
            hypercube_locator = arc.get('from')
            dimension_locator = arc.get('to')
            
            if not hypercube_locator or not dimension_locator:
                continue
            
            # Extract QNames from locators
            hypercube_qname = self._extract_qname_from_locator(hypercube_locator)
            dimension_qname = self._extract_qname_from_locator(dimension_locator)
            
            if not hypercube_qname or not dimension_qname:
                continue
            
            # Get or create hypercube
            if hypercube_qname not in self._hypercubes:
                self._hypercubes[hypercube_qname] = Hypercube(
                    hypercube_qname=hypercube_qname
                )
            
            # Get or create dimension
            if dimension_qname not in self._dimensions:
                self._dimensions[dimension_qname] = DimensionAxis(
                    dimension_qname=dimension_qname
                )
            
            # Link dimension to hypercube
            hypercube = self._hypercubes[hypercube_qname]
            dimension = self._dimensions[dimension_qname]
            
            if dimension not in hypercube.dimensions:
                hypercube.dimensions.append(dimension)
        
        # Extract dimension-domain relationships
        dim_domain_arcs = arcs_by_role.get(DIMENSION_ARCROLES['dimension-domain'], [])
        for arc in dim_domain_arcs:
            dimension_locator = arc.get('from')
            domain_locator = arc.get('to')
            
            if not dimension_locator or not domain_locator:
                continue
            
            dimension_qname = self._extract_qname_from_locator(dimension_locator)
            domain_qname = self._extract_qname_from_locator(domain_locator)
            
            if dimension_qname in self._dimensions:
                self._dimensions[dimension_qname].domain_qname = domain_qname
        
        # Extract domain-member relationships
        domain_member_arcs = arcs_by_role.get(DIMENSION_ARCROLES['domain-member'], [])
        for arc in domain_member_arcs:
            domain_locator = arc.get('from')
            member_locator = arc.get('to')
            
            if not domain_locator or not member_locator:
                continue
            
            member_qname = self._extract_qname_from_locator(member_locator)
            
            if not member_qname:
                continue
            
            # Find dimension with this domain
            for dimension in self._dimensions.values():
                if dimension.domain_qname == self._extract_qname_from_locator(domain_locator):
                    member = DimensionMember(member_qname=member_qname)
                    if member not in dimension.members:
                        dimension.members.append(member)
    
    def _extract_qname_from_locator(self, locator: str) -> Optional[str]:
        """
        Extract QName from locator ID.
        
        Locator pattern: loc_prefix_ConceptName_uuid
        Result: prefix:ConceptName
        
        Args:
            locator: Locator ID
            
        Returns:
            QName or None
        """
        if not locator or not locator.startswith('loc_'):
            return None
        
        # Remove 'loc_' prefix
        rest = locator[4:]
        
        # Split by underscores
        parts = rest.split('_')
        
        if len(parts) < 2:
            return None
        
        # Reconstruct QName
        prefix = parts[0]
        local_name = parts[1]
        
        return f"{prefix}:{local_name}"
    
    def _extract_from_container(
        self,
        container: dict[str, any],
        dim_context: DimensionalContext
    ) -> None:
        """
        Extract dimensions from segment/scenario container.
        
        Args:
            container: Segment or scenario dictionary
            dim_context: DimensionalContext to populate
        """
        if not isinstance(container, dict):
            return
        
        for key, value in container.items():
            # Explicit dimension (member reference)
            if isinstance(value, str):
                dim_context.explicit_dimensions[key] = value
            
            # Typed dimension (custom value)
            elif isinstance(value, dict):
                dim_context.typed_dimensions[key] = value
            
            # Could be other structures
            else:
                dim_context.typed_dimensions[key] = value
    
    def _create_dimension_signature(self, dim_context: DimensionalContext) -> str:
        """
        Create unique signature for dimensional context.
        
        Args:
            dim_context: Dimensional context
            
        Returns:
            Signature string
        """
        if not dim_context.has_dimensions:
            return "default"
        
        parts = []
        
        # Add explicit dimensions
        for dim, member in sorted(dim_context.explicit_dimensions.items()):
            parts.append(f"{dim}={member}")
        
        # Add typed dimensions
        for dim, value in sorted(dim_context.typed_dimensions.items()):
            parts.append(f"{dim}={value}")
        
        return ",".join(parts) if parts else "default"


__all__ = [
    'DimensionHandler',
    'DimensionMember',
    'DimensionAxis',
    'Hypercube',
    'DimensionalContext',
]