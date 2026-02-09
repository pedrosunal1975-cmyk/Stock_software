# Path: xbrl_parser/taxonomy/linkbase_loader.py
"""
Linkbase Loader

Loads and parses XBRL linkbase files.

Supports:
- Presentation linkbases (display hierarchies)
- Calculation linkbases (arithmetic relationships)
- Definition linkbases (dimensional relationships)
- Label linkbases (human-readable labels)
- Reference linkbases (authoritative citations)

Example:
    from ..taxonomy import LinkbaseLoader
    
    loader = LinkbaseLoader()
    result = loader.load_linkbase(Path("pre.xml"))
"""

import logging
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field
from lxml import etree
from enum import Enum

from ...core.config_loader import ConfigLoader
from ..foundation.xml_parser import XMLParser
from ..models.relationship import (
    PresentationRelationship,
    CalculationRelationship,
    DefinitionRelationship,
    RelationshipType
)
from ..models.error import ParsingError, ErrorCategory
from ..taxonomy.constants import (
    LINK_NS,
    XLINK_NS
)


class LinkbaseType(Enum):
    """Type of linkbase file."""
    PRESENTATION = "presentation"
    CALCULATION = "calculation"
    DEFINITION = "definition"
    LABEL = "label"
    REFERENCE = "reference"
    UNKNOWN = "unknown"


@dataclass
class LinkbaseLoadResult:
    """Result of loading a linkbase."""
    linkbase_path: str
    linkbase_type: LinkbaseType
    relationships: list = field(default_factory=list)
    errors: list[ParsingError] = field(default_factory=list)
    role_uris: list[str] = field(default_factory=list)


class LinkbaseLoader:
    """
    Loads XBRL linkbase files.
    
    Extracts relationships, labels, and references from linkbase XML.
    
    Example:
        config = ConfigLoader()
        loader = LinkbaseLoader(config)
        
        result = loader.load_linkbase(Path("pre.xml"))
        for rel in result.relationships:
            print(f"{rel.from_concept} -> {rel.to_concept}")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize linkbase loader.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        self.xml_parser = XMLParser(self.config)
    
    def load_linkbase(self, linkbase_path: Path) -> LinkbaseLoadResult:
        """
        Load and parse linkbase file.
        
        Args:
            linkbase_path: Path to linkbase file
            
        Returns:
            LinkbaseLoadResult with relationships
            
        Example:
            result = loader.load_linkbase(Path("cal.xml"))
            print(f"Type: {result.linkbase_type}")
        """
        linkbase_path_str = str(linkbase_path)
        self.logger.info(f"Loading linkbase: {linkbase_path_str}")
        
        result = LinkbaseLoadResult(
            linkbase_path=linkbase_path_str,
            linkbase_type=LinkbaseType.UNKNOWN
        )
        
        try:
            # Parse XML
            parse_result = self.xml_parser.parse_file(linkbase_path)
            if not parse_result.well_formed:
                result.errors.extend(parse_result.errors)
                return result
            
            root = parse_result.root
            
            # Detect linkbase type
            result.linkbase_type = self._detect_linkbase_type(root)
            
            # Extract relationships based on type
            if result.linkbase_type == LinkbaseType.PRESENTATION:
                result.relationships = self._extract_presentation_rels(root)
            elif result.linkbase_type == LinkbaseType.CALCULATION:
                result.relationships = self._extract_calculation_rels(root)
            elif result.linkbase_type == LinkbaseType.DEFINITION:
                result.relationships = self._extract_definition_rels(root)
            
            self.logger.info(
                f"Linkbase loaded: {result.linkbase_type.value}, "
                f"{len(result.relationships)} relationships"
            )
            
        except Exception as e:
            self.logger.error(f"Linkbase load failed: {e}", exc_info=True)
            result.errors.append(ParsingError(
                category=ErrorCategory.TAXONOMY_LOAD_FAILED,
                message=f"Failed to load linkbase: {e}",
                severity="ERROR",
                source_file=linkbase_path_str
            ))
        
        return result
    
    def _detect_linkbase_type(self, root: etree._Element) -> LinkbaseType:
        """
        Detect linkbase type from XML content.
        
        Args:
            root: Linkbase root element
            
        Returns:
            LinkbaseType enum
        """
        # Check for link elements
        if root.find(f".//{{{LINK_NS}}}presentationLink") is not None:
            return LinkbaseType.PRESENTATION
        elif root.find(f".//{{{LINK_NS}}}calculationLink") is not None:
            return LinkbaseType.CALCULATION
        elif root.find(f".//{{{LINK_NS}}}definitionLink") is not None:
            return LinkbaseType.DEFINITION
        elif root.find(f".//{{{LINK_NS}}}labelLink") is not None:
            return LinkbaseType.LABEL
        elif root.find(f".//{{{LINK_NS}}}referenceLink") is not None:
            return LinkbaseType.REFERENCE
        
        return LinkbaseType.UNKNOWN
    
    def _extract_presentation_rels(
        self,
        root: etree._Element
    ) -> list[PresentationRelationship]:
        """
        Extract presentation relationships.
        
        Args:
            root: Linkbase root element
            
        Returns:
            list of PresentationRelationship objects
        """
        relationships = []
        
        # Find all presentationLink elements
        pres_links = root.findall(f".//{{{LINK_NS}}}presentationLink")
        
        for link in pres_links:
            # Extract role URI
            role = link.get(f"{{{XLINK_NS}}}role")
            
            # Extract locators
            locators = self._extract_locators(link)
            
            # Extract arcs
            arcs = link.findall(f".//{{{LINK_NS}}}presentationArc")
            
            for arc in arcs:
                rel = self._parse_presentation_arc(arc, locators, role)
                if rel:
                    relationships.append(rel)
        
        return relationships
    
    def _extract_calculation_rels(
        self,
        root: etree._Element
    ) -> list[CalculationRelationship]:
        """
        Extract calculation relationships.
        
        Args:
            root: Linkbase root element
            
        Returns:
            list of CalculationRelationship objects
        """
        relationships = []
        
        # Find all calculationLink elements
        calc_links = root.findall(f".//{{{LINK_NS}}}calculationLink")
        
        for link in calc_links:
            # Extract role URI
            role = link.get(f"{{{XLINK_NS}}}role")
            
            # Extract locators
            locators = self._extract_locators(link)
            
            # Extract arcs
            arcs = link.findall(f".//{{{LINK_NS}}}calculationArc")
            
            for arc in arcs:
                rel = self._parse_calculation_arc(arc, locators, role)
                if rel:
                    relationships.append(rel)
        
        return relationships
    
    def _extract_definition_rels(
        self,
        root: etree._Element
    ) -> list[DefinitionRelationship]:
        """
        Extract definition relationships.
        
        Args:
            root: Linkbase root element
            
        Returns:
            list of DefinitionRelationship objects
        """
        relationships = []
        
        # Find all definitionLink elements
        def_links = root.findall(f".//{{{LINK_NS}}}definitionLink")
        
        for link in def_links:
            # Extract role URI
            role = link.get(f"{{{XLINK_NS}}}role")
            
            # Extract locators
            locators = self._extract_locators(link)
            
            # Extract arcs
            arcs = link.findall(f".//{{{LINK_NS}}}definitionArc")
            
            for arc in arcs:
                rel = self._parse_definition_arc(arc, locators, role)
                if rel:
                    relationships.append(rel)
        
        return relationships
    
    def _extract_locators(self, link_element: etree._Element) -> dict[str, str]:
        """
        Extract locators from link element.
        
        Args:
            link_element: Link element
            
        Returns:
            Dictionary mapping label -> concept QName
        """
        locators = {}
        
        loc_elements = link_element.findall(f".//{{{LINK_NS}}}loc")
        
        for loc in loc_elements:
            label = loc.get(f"{{{XLINK_NS}}}label")
            href = loc.get(f"{{{XLINK_NS}}}href")
            
            if label and href:
                # Extract concept from href (schema.xsd#concept_id)
                if '#' in href:
                    concept_id = href.split('#')[1]
                    locators[label] = concept_id
        
        return locators
    
    def _parse_presentation_arc(
        self,
        arc: etree._Element,
        locators: dict[str, str],
        role: Optional[str]
    ) -> Optional[PresentationRelationship]:
        """Parse presentation arc into relationship object."""
        from_label = arc.get(f"{{{XLINK_NS}}}from")
        to_label = arc.get(f"{{{XLINK_NS}}}to")
        order = arc.get('order', '1.0')
        priority = arc.get('priority', '0')
        preferred_label = arc.get('preferredLabel')
        use = arc.get('use', 'optional')
        
        from_concept = locators.get(from_label)
        to_concept = locators.get(to_label)
        
        if not from_concept or not to_concept:
            return None
        
        return PresentationRelationship(
            relationship_type=RelationshipType.PRESENTATION,
            from_concept=from_concept,
            to_concept=to_concept,
            role=role or "default",
            order=float(order),
            preferred_label=preferred_label,
            priority=int(priority),
            prohibited=(use == 'prohibited')
        )
    
    def _parse_calculation_arc(
        self,
        arc: etree._Element,
        locators: dict[str, str],
        role: Optional[str]
    ) -> Optional[CalculationRelationship]:
        """Parse calculation arc into relationship object."""
        from_label = arc.get(f"{{{XLINK_NS}}}from")
        to_label = arc.get(f"{{{XLINK_NS}}}to")
        weight = arc.get('weight', '1.0')
        order = arc.get('order', '1.0')
        use = arc.get('use', 'optional')
        
        from_concept = locators.get(from_label)
        to_concept = locators.get(to_label)
        
        if not from_concept or not to_concept:
            return None
        
        return CalculationRelationship(
            relationship_type=RelationshipType.CALCULATION,
            from_concept=from_concept,
            to_concept=to_concept,
            role=role or "default",
            weight=float(weight),
            order=float(order),
            prohibited=(use == 'prohibited')
        )
    
    def _parse_definition_arc(
        self,
        arc: etree._Element,
        locators: dict[str, str],
        role: Optional[str]
    ) -> Optional[DefinitionRelationship]:
        """Parse definition arc into relationship object."""
        from_label = arc.get(f"{{{XLINK_NS}}}from")
        to_label = arc.get(f"{{{XLINK_NS}}}to")
        arcrole = arc.get(f"{{{XLINK_NS}}}arcrole")
        order = arc.get('order', '1.0')
        use = arc.get('use', 'optional')
        
        from_concept = locators.get(from_label)
        to_concept = locators.get(to_label)
        
        if not from_concept or not to_concept:
            return None
        
        return DefinitionRelationship(
            relationship_type=RelationshipType.DEFINITION,
            from_concept=from_concept,
            to_concept=to_concept,
            role=role or "default",
            arcrole=arcrole,
            order=float(order),
            prohibited=(use == 'prohibited')
        )


__all__ = ['LinkbaseLoader', 'LinkbaseLoadResult', 'LinkbaseType']
