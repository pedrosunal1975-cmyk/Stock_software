# Path: loaders/taxonomy_structure_reader.py
"""
Taxonomy Structure Reader

Discovers structure of taxonomy XSD files WITHOUT expectations.

RESPONSIBILITY: Read XSD files and discover what's in them.
NO assumptions about what should be there.

ARCHITECTURE LAYER: HOW
- WHERE: taxonomy.py (provides file paths)
- HOW: taxonomy_structure_reader.py (discovers XSD structure) ← THIS FILE
- WHAT: Components use discovered structure

CRITICAL PRINCIPLE:
Reads XSD "as is" - discovers elements, types, relationships.
Does NOT validate against expectations.
Reports what exists, not what's missing.
"""

import logging
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field
from lxml import etree


@dataclass
class TaxonomyStructure:
    """
    Discovered structure of a taxonomy file.
    
    Reports what was found in the XSD, no expectations.
    """
    file_path: Path
    target_namespace: Optional[str] = None
    schema_location: Optional[str] = None
    
    # Discovered elements
    elements: dict[str, dict[str, any]] = field(default_factory=dict)
    types: dict[str, dict[str, any]] = field(default_factory=dict)
    imports: list[dict[str, str]] = field(default_factory=list)
    
    # Counts
    element_count: int = 0
    type_count: int = 0
    import_count: int = 0
    
    # Namespaces found
    namespaces: dict[str, str] = field(default_factory=dict)


class TaxonomyStructureReader:
    """
    Discovers structure of taxonomy XSD files.
    
    NO expectations - discovers what's actually there.
    NO validation - just reports structure.
    
    Example:
        reader = TaxonomyStructureReader()
        structure = reader.discover_structure(Path("us-gaap-2024.xsd"))
        
        print(f"Found {structure.element_count} elements")
        print(f"Target namespace: {structure.target_namespace}")
    """
    
    # XSD namespace
    XSD_NS = "http://www.w3.org/2001/XMLSchema"
    
    def __init__(self):
        """Initialize structure reader."""
        self.logger = logging.getLogger('loaders.taxonomy_structure')
    
    def discover_structure(self, xsd_path: Path) -> TaxonomyStructure:
        """
        Discover structure of XSD file.
        
        Args:
            xsd_path: Path to XSD file
            
        Returns:
            TaxonomyStructure with discovered information
        """
        self.logger.debug(f"Discovering structure: {xsd_path}")
        
        structure = TaxonomyStructure(file_path=xsd_path)
        
        try:
            # Parse XSD
            tree = etree.parse(str(xsd_path))
            root = tree.getroot()
            
            # Extract namespaces
            structure.namespaces = dict(root.nsmap) if root.nsmap else {}
            
            # Extract schema attributes
            structure.target_namespace = root.get('targetNamespace')
            structure.schema_location = root.get('schemaLocation')
            
            # Discover elements
            structure.elements = self._discover_elements(root, structure.namespaces)
            structure.element_count = len(structure.elements)
            
            # Discover types
            structure.types = self._discover_types(root, structure.namespaces)
            structure.type_count = len(structure.types)
            
            # Discover imports
            structure.imports = self._discover_imports(root, structure.namespaces)
            structure.import_count = len(structure.imports)
            
            self.logger.debug(
                f"Structure discovered: {structure.element_count} elements, "
                f"{structure.type_count} types, {structure.import_count} imports"
            )
            
        except Exception as e:
            self.logger.error(f"Error discovering structure in {xsd_path}: {e}")
        
        return structure
    
    def _discover_elements(
        self,
        root: etree._Element,
        namespaces: dict[str, str]
    ) -> dict[str, dict[str, any]]:
        """
        Discover all element definitions in schema.
        
        Returns:
            Dictionary of elements {name: {attributes}}
        """
        elements = {}
        
        # Find all xs:element tags
        ns_prefix = self._find_xsd_prefix(namespaces)
        if not ns_prefix:
            return elements
        
        element_xpath = f".//{{{self.XSD_NS}}}element"
        
        for elem in root.findall(element_xpath):
            name = elem.get('name')
            if not name:
                continue
            
            elements[name] = {
                'name': name,
                'type': elem.get('type'),
                'substitution_group': elem.get('substitutionGroup'),
                'abstract': elem.get('abstract') == 'true',
                'nillable': elem.get('nillable') == 'true',
                'period_type': elem.get('{http://www.xbrl.org/2003/instance}periodType'),
                'balance': elem.get('{http://www.xbrl.org/2003/instance}balance'),
            }
        
        return elements
    
    def _discover_types(
        self,
        root: etree._Element,
        namespaces: dict[str, str]
    ) -> dict[str, dict[str, any]]:
        """
        Discover all type definitions in schema.
        
        Returns:
            Dictionary of types {name: {info}}
        """
        types = {}
        
        # Find complexType and simpleType
        for type_tag in ['complexType', 'simpleType']:
            type_xpath = f".//{{{self.XSD_NS}}}{type_tag}"
            
            for type_elem in root.findall(type_xpath):
                name = type_elem.get('name')
                if not name:
                    continue
                
                types[name] = {
                    'name': name,
                    'type': type_tag,
                    'base': self._get_base_type(type_elem),
                }
        
        return types
    
    def _discover_imports(
        self,
        root: etree._Element,
        namespaces: dict[str, str]
    ) -> list[dict[str, str]]:
        """
        Discover all import statements in schema.
        
        Returns:
            List of imports with namespace and schemaLocation
        """
        imports = []
        
        import_xpath = f".//{{{self.XSD_NS}}}import"
        
        for imp in root.findall(import_xpath):
            import_info = {
                'namespace': imp.get('namespace'),
                'schema_location': imp.get('schemaLocation'),
            }
            imports.append(import_info)
        
        return imports
    
    def _find_xsd_prefix(self, namespaces: dict[str, str]) -> Optional[str]:
        """Find prefix used for XSD namespace."""
        for prefix, uri in namespaces.items():
            if uri == self.XSD_NS:
                return prefix
        return None
    
    def _get_base_type(self, type_elem: etree._Element) -> Optional[str]:
        """Extract base type from complexType or simpleType."""
        # Try restriction
        restriction = type_elem.find(f".//{{{self.XSD_NS}}}restriction")
        if restriction is not None:
            return restriction.get('base')
        
        # Try extension
        extension = type_elem.find(f".//{{{self.XSD_NS}}}extension")
        if extension is not None:
            return extension.get('base')
        
        return None
    
    def discover_concept(
        self,
        structure: TaxonomyStructure,
        concept_name: str
    ) -> Optional[dict[str, any]]:
        """
        Find specific concept in discovered structure.
        
        Args:
            structure: Previously discovered structure
            concept_name: Concept name to find
            
        Returns:
            Concept info or None if not found
        """
        return structure.elements.get(concept_name)
    
    def list_all_concepts(self, structure: TaxonomyStructure) -> list[str]:
        """
        List all concept names in structure.
        
        Args:
            structure: Discovered structure
            
        Returns:
            List of concept names
        """
        return list(structure.elements.keys())


__all__ = ['TaxonomyStructureReader', 'TaxonomyStructure']