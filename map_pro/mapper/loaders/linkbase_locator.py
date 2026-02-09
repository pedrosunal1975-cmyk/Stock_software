# Path: loaders/linkbase_locator.py
"""
Linkbase Locator and Reader

Discovers and reads XBRL linkbase files from company filings.

DESIGN PRINCIPLES:
- Uses XBRLFilingsLoader for file access (NO direct file system access)
- Discovers linkbase types by reading XML content (NO filename patterns)
- NO hardcoded concept names or role URIs
- Market and taxonomy agnostic
- Returns generic data structures

RESPONSIBILITY: 
- Locate presentation/calculation/definition linkbases
- Extract role networks, calculation arcs, dimension definitions
- Extract role definitions from linkbase XML (SOURCE 2)
- Return what company DECLARED in their filings

NOT RESPONSIBLE FOR:
- Interpreting what linkbases mean
- Validating linkbase correctness
- Making assumptions about structure
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from ..loaders.xbrl_filings import XBRLFilingsLoader
from ..loaders.constants import (
    XLINK_ATTRS,
    LINKBASE_ELEMENT_NAMES,
)
from ..loaders.schema_reader import RoleDefinition


@dataclass
class PresentationNetwork:
    """A presentation role network from linkbase."""
    role_uri: str
    role_definition: Optional[str] = None
    arcs: list[dict[str, any]] = field(default_factory=list)
    metadata: dict[str, any] = field(default_factory=dict)


@dataclass
class CalculationNetwork:
    """A calculation role network from linkbase."""
    role_uri: str
    role_definition: Optional[str] = None
    arcs: list[dict[str, any]] = field(default_factory=list)
    metadata: dict[str, any] = field(default_factory=dict)


@dataclass
class DefinitionNetwork:
    """A definition role network from linkbase."""
    role_uri: str
    role_definition: Optional[str] = None
    arcs: list[dict[str, any]] = field(default_factory=list)
    metadata: dict[str, any] = field(default_factory=dict)


@dataclass
class LinkbaseSet:
    """Complete set of linkbases discovered in a filing."""
    presentation_networks: list[PresentationNetwork] = field(default_factory=list)
    calculation_networks: list[CalculationNetwork] = field(default_factory=list)
    definition_networks: list[DefinitionNetwork] = field(default_factory=list)
    label_linkbases: list[Path] = field(default_factory=list)
    reference_linkbases: list[Path] = field(default_factory=list)
    discovered_roles: set[str] = field(default_factory=set)
    metadata: dict[str, any] = field(default_factory=dict)
    role_definitions: dict[str, RoleDefinition] = field(default_factory=dict)


class LinkbaseLocator:
    """
    Discovers and reads linkbase files from XBRL filings.
    
    Uses XBRLFilingsLoader to access files, then reads XML to identify
    linkbase types and extract their content.
    
    NO hardcoded patterns - discovers everything from actual XML content.
    """
    
    # XBRL namespace patterns (used only for XML parsing, not assumptions)
    XBRL_NAMESPACES = {
        'link': 'http://www.xbrl.org/2003/linkbase',
        'xlink': 'http://www.w3.org/1999/xlink',
        'xbrldt': 'http://xbrl.org/2005/xbrldt',
    }
    
    def __init__(self, xbrl_loader: Optional[XBRLFilingsLoader] = None):
        """
        Initialize linkbase locator.
        
        Args:
            xbrl_loader: Optional XBRLFilingsLoader instance
        """
        self.xbrl_loader = xbrl_loader if xbrl_loader else XBRLFilingsLoader()
        self.logger = logging.getLogger('input.linkbase_locator')
        self.logger.info("LinkbaseLocator initialized")
    
    def discover_linkbases(self, filing_subdirectory: str) -> LinkbaseSet:
        """
        Discover and read all linkbases in a filing directory.
        
        Args:
            filing_subdirectory: Subdirectory path relative to XBRL root
            
        Returns:
            LinkbaseSet with all discovered linkbase content
        """
        self.logger.info(f"Discovering linkbases in: {filing_subdirectory}")
        
        # Get all files in filing directory
        all_files = self.xbrl_loader.discover_all_files(subdirectory=filing_subdirectory)
        
        # Filter to XML files only
        xml_files = [f for f in all_files if f.suffix.lower() == '.xml']
        
        self.logger.info(f"Found {len(xml_files)} XML files to examine")
        
        linkbase_set = LinkbaseSet()
        
        # Examine each XML file to discover linkbases
        for xml_file in xml_files:
            try:
                self._examine_xml_file(xml_file, linkbase_set)
            except Exception as e:
                self.logger.warning(f"Could not read {xml_file.name}: {e}")
        
        self.logger.info(
            f"Discovery complete: "
            f"{len(linkbase_set.presentation_networks)} presentation, "
            f"{len(linkbase_set.calculation_networks)} calculation, "
            f"{len(linkbase_set.definition_networks)} definition networks, "
            f"{len(linkbase_set.role_definitions)} role definitions from linkbase"
        )
        
        return linkbase_set
    
    def _examine_xml_file(self, xml_file: Path, linkbase_set: LinkbaseSet) -> None:
        """
        Examine XML file to determine if it's a linkbase and extract content.
        
        Args:
            xml_file: Path to XML file
            linkbase_set: LinkbaseSet to populate
        """
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Discover namespaces from the actual file
            namespaces = self._extract_namespaces(root)
            
            # Extract role definitions from linkbase XML (SOURCE 2)
            self._extract_role_definitions_from_linkbase(root, namespaces, linkbase_set)
            
            # Check if this is a linkbase file by looking for linkbase element
            if self._is_linkbase(root, namespaces):
                self._extract_linkbase_content(xml_file, root, namespaces, linkbase_set)
            
        except ET.ParseError as e:
            self.logger.debug(f"XML parse error in {xml_file.name}: {e}")
    
    def _extract_namespaces(self, root: ET.Element) -> dict[str, str]:
        """
        Extract namespace mappings from XML root element.
        
        Args:
            root: XML root element
            
        Returns:
            Dictionary mapping prefixes to namespace URIs
        """
        namespaces = {}
        
        # Extract from root tag
        if '}' in root.tag:
            ns_uri = root.tag.split('}')[0].strip('{')
            namespaces['default'] = ns_uri
        
        # Extract from attributes
        for key, value in root.attrib.items():
            if key.startswith('{http://www.w3.org/2000/xmlns/}'):
                prefix = key.split('}')[1]
                namespaces[prefix] = value
            elif key == 'xmlns':
                namespaces['default'] = value
        
        return namespaces
    
    def _extract_role_definitions_from_linkbase(
        self,
        root: ET.Element,
        namespaces: dict[str, str],
        linkbase_set: LinkbaseSet
    ) -> None:
        """
        Extract roleType definitions from linkbase XML file.
        
        RoleType definitions can be embedded in linkbase files.
        This is SOURCE 2 (checked after schema files).
        
        Args:
            root: XML root element
            namespaces: Namespace mappings
            linkbase_set: LinkbaseSet to populate
        """
        # Find all roleType elements
        role_types = root.findall('.//link:roleType', self.XBRL_NAMESPACES)
        
        # If not found with namespace, try without
        if not role_types:
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag_name == 'roleType':
                    role_types.append(elem)
        
        for role_type in role_types:
            try:
                # Get roleURI attribute
                role_uri = role_type.get('roleURI')
                if not role_uri:
                    continue
                
                # Get id attribute
                role_id = role_type.get('id')
                
                # Find definition element
                definition = None
                def_elem = role_type.find('link:definition', self.XBRL_NAMESPACES)
                if def_elem is None:
                    for child in role_type:
                        tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if tag_name == 'definition':
                            def_elem = child
                            break
                
                if def_elem is not None and def_elem.text:
                    definition = def_elem.text.strip()
                
                # Find usedOn element
                used_on = None
                used_on_elem = role_type.find('link:usedOn', self.XBRL_NAMESPACES)
                if used_on_elem is None:
                    for child in role_type:
                        tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if tag_name == 'usedOn':
                            used_on_elem = child
                            break
                
                if used_on_elem is not None and used_on_elem.text:
                    used_on = used_on_elem.text.strip()
                
                # Create role definition
                if role_uri not in linkbase_set.role_definitions:
                    role_def = RoleDefinition(
                        role_uri=role_uri,
                        definition=definition or "",
                        used_on=used_on,
                        role_id=role_id
                    )
                    linkbase_set.role_definitions[role_uri] = role_def
                    self.logger.debug(f"Found role in linkbase: {role_uri}")
                    
            except Exception as e:
                self.logger.warning(f"Error parsing roleType in linkbase: {e}")
                continue
    
    def _is_linkbase(self, root: ET.Element, namespaces: dict[str, str]) -> bool:
        """
        Determine if XML is a linkbase file.
        
        Args:
            root: XML root element
            namespaces: Namespace mappings
            
        Returns:
            True if this is a linkbase file
        """
        # Check root tag name
        tag_name = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        
        if tag_name == 'linkbase':
            return True
        
        # Check for linkbase namespace in discovered namespaces
        for ns_uri in namespaces.values():
            if 'linkbase' in ns_uri.lower():
                return True
        
        return False
    
    def _extract_linkbase_content(
        self,
        xml_file: Path,
        root: ET.Element,
        namespaces: dict[str, str],
        linkbase_set: LinkbaseSet
    ) -> None:
        """
        Extract linkbase content from XML root.
        
        Args:
            xml_file: Path to XML file
            root: XML root element
            namespaces: Namespace mappings
            linkbase_set: LinkbaseSet to populate
        """
        # Iterate through all child elements
        for link_elem in root:
            tag_name = link_elem.tag.split('}')[-1] if '}' in link_elem.tag else link_elem.tag
            
            if 'presentationLink' in tag_name:
                network = self._extract_presentation_network(link_elem, namespaces)
                if network:
                    linkbase_set.presentation_networks.append(network)
            
            elif 'calculationLink' in tag_name:
                network = self._extract_calculation_network(link_elem, namespaces)
                if network:
                    linkbase_set.calculation_networks.append(network)
            
            elif 'definitionLink' in tag_name:
                network = self._extract_definition_network(link_elem, namespaces)
                if network:
                    linkbase_set.definition_networks.append(network)
            
            elif 'labelLink' in tag_name:
                linkbase_set.label_linkbases.append(xml_file)
            
            elif 'referenceLink' in tag_name:
                linkbase_set.reference_linkbases.append(xml_file)
    
    def _extract_presentation_network(
        self,
        link_elem: ET.Element,
        namespaces: dict[str, str]
    ) -> Optional[PresentationNetwork]:
        """
        Extract presentation network from presentationLink element.
        
        Args:
            link_elem: presentationLink XML element
            namespaces: Namespace mappings
            
        Returns:
            PresentationNetwork or None
        """
        # Get role URI (company declares what this network represents)
        role_uri = link_elem.get(XLINK_ATTRS['role'], '')
        
        if not role_uri:
            return None
        
        # FIRST: Build locator ID → concept name mapping
        locator_map = {}
        for loc_elem in link_elem.iter():
            tag_name = loc_elem.tag.split('}')[-1] if '}' in loc_elem.tag else loc_elem.tag
            
            if tag_name == LINKBASE_ELEMENT_NAMES['locator']:
                loc_id = loc_elem.get(XLINK_ATTRS['label'])
                href = loc_elem.get(XLINK_ATTRS['href'], '')
                
                if loc_id and href:
                    # Extract concept from href AS-IS (no format conversion)
                    # Format: "#concept" or "file.xsd#concept" → just "concept"
                    concept = href.split('#')[-1] if '#' in href else href
                    locator_map[loc_id] = concept
        
        # SECOND: Extract arcs and resolve locator references
        arcs = []
        for arc_elem in link_elem.iter():
            tag_name = arc_elem.tag.split('}')[-1] if '}' in arc_elem.tag else arc_elem.tag
            
            if LINKBASE_ELEMENT_NAMES['presentation_arc'] in tag_name:
                from_loc = arc_elem.get(XLINK_ATTRS['from'])
                to_loc = arc_elem.get(XLINK_ATTRS['to'])
                
                # Resolve locator IDs to actual concept names
                from_concept = locator_map.get(from_loc, from_loc)
                to_concept = locator_map.get(to_loc, to_loc)
                
                arc_data = {
                    'from': from_concept,  # Resolved concept name
                    'to': to_concept,      # Resolved concept name
                    'from_locator': from_loc,  # Keep original for debugging
                    'to_locator': to_loc,      # Keep original for debugging
                    'order': arc_elem.get('order'),
                    'priority': arc_elem.get('priority'),
                    'use': arc_elem.get('use'),
                    'preferredLabel': arc_elem.get('preferredLabel'),
                }
                arcs.append(arc_data)
        
        return PresentationNetwork(
            role_uri=role_uri,
            arcs=arcs
        )
    
    def _extract_calculation_network(
        self,
        link_elem: ET.Element,
        namespaces: dict[str, str]
    ) -> Optional[CalculationNetwork]:
        """
        Extract calculation network from calculationLink element.
        
        Args:
            link_elem: calculationLink XML element
            namespaces: Namespace mappings
            
        Returns:
            CalculationNetwork or None
        """
        role_uri = link_elem.get(XLINK_ATTRS['role'], '')
        
        if not role_uri:
            return None
        
        # Build locator map
        locator_map = {}
        for loc_elem in link_elem.iter():
            tag_name = loc_elem.tag.split('}')[-1] if '}' in loc_elem.tag else loc_elem.tag
            
            if tag_name == LINKBASE_ELEMENT_NAMES['locator']:
                loc_id = loc_elem.get(XLINK_ATTRS['label'])
                href = loc_elem.get(XLINK_ATTRS['href'], '')
                
                if loc_id and href:
                    concept = href.split('#')[-1] if '#' in href else href
                    if '_' in concept and ':' not in concept:
                        parts = concept.split('_', 1)
                        if len(parts) == 2:
                            concept = f"{parts[0]}:{parts[1]}"
                    locator_map[loc_id] = concept
        
        # Extract calculation arcs
        arcs = []
        for arc_elem in link_elem.iter():
            tag_name = arc_elem.tag.split('}')[-1] if '}' in arc_elem.tag else arc_elem.tag
            
            if LINKBASE_ELEMENT_NAMES['calculation_arc'] in tag_name:
                from_loc = arc_elem.get(XLINK_ATTRS['from'])
                to_loc = arc_elem.get(XLINK_ATTRS['to'])
                
                arc_data = {
                    'from': locator_map.get(from_loc, from_loc),
                    'to': locator_map.get(to_loc, to_loc),
                    'from_locator': from_loc,
                    'to_locator': to_loc,
                    'order': arc_elem.get('order'),
                    'weight': arc_elem.get('weight'),
                    'priority': arc_elem.get('priority'),
                    'use': arc_elem.get('use'),
                }
                arcs.append(arc_data)
        
        return CalculationNetwork(
            role_uri=role_uri,
            arcs=arcs
        )
    
    def _extract_definition_network(
        self,
        link_elem: ET.Element,
        namespaces: dict[str, str]
    ) -> Optional[DefinitionNetwork]:
        """
        Extract definition network from definitionLink element.
        
        Args:
            link_elem: definitionLink XML element
            namespaces: Namespace mappings
            
        Returns:
            DefinitionNetwork or None
        """
        role_uri = link_elem.get(XLINK_ATTRS['role'], '')
        
        if not role_uri:
            return None
        
        # Build locator map
        locator_map = {}
        for loc_elem in link_elem.iter():
            tag_name = loc_elem.tag.split('}')[-1] if '}' in loc_elem.tag else loc_elem.tag
            
            if tag_name == LINKBASE_ELEMENT_NAMES['locator']:
                loc_id = loc_elem.get(XLINK_ATTRS['label'])
                href = loc_elem.get(XLINK_ATTRS['href'], '')
                
                if loc_id and href:
                    concept = href.split('#')[-1] if '#' in href else href
                    if '_' in concept and ':' not in concept:
                        parts = concept.split('_', 1)
                        if len(parts) == 2:
                            concept = f"{parts[0]}:{parts[1]}"
                    locator_map[loc_id] = concept
        
        # Extract definition arcs (dimension relationships)
        arcs = []
        for arc_elem in link_elem.iter():
            tag_name = arc_elem.tag.split('}')[-1] if '}' in arc_elem.tag else arc_elem.tag
            
            if LINKBASE_ELEMENT_NAMES['definition_arc'] in tag_name:
                from_loc = arc_elem.get(XLINK_ATTRS['from'])
                to_loc = arc_elem.get(XLINK_ATTRS['to'])
                
                arc_data = {
                    'from': locator_map.get(from_loc, from_loc),
                    'to': locator_map.get(to_loc, to_loc),
                    'from_locator': from_loc,
                    'to_locator': to_loc,
                    'order': arc_elem.get('order'),
                    'priority': arc_elem.get('priority'),
                    'use': arc_elem.get('use'),
                    'arcrole': arc_elem.get(XLINK_ATTRS['arcrole']),
                }
                arcs.append(arc_data)
        
        return DefinitionNetwork(
            role_uri=role_uri,
            arcs=arcs
        )


__all__ = [
    'LinkbaseLocator',
    'LinkbaseSet',
    'PresentationNetwork',
    'CalculationNetwork',
    'DefinitionNetwork',
]