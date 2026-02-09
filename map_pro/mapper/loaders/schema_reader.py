# Path: loaders/schema_reader.py
"""
Schema Reader

Reads XBRL schema files (.xsd) to extract taxonomy definitions declared by companies.

DESIGN PRINCIPLES:
- Uses XBRLFilingsLoader for file access (NO direct file system access)
- Reads role definitions from <roleType> elements (NO assumptions)
- Reads element definitions from <element> declarations (NO hardcoding)
- Market and taxonomy agnostic
- Returns what company DECLARED in their schemas

RESPONSIBILITY:
- Locate schema files in filing directory
- Extract roleType definitions (role URI -> definition text)
- Extract element definitions (element name -> type, period type)
- Return discovered definitions AS-IS

NOT RESPONSIBLE FOR:
- Interpreting what definitions mean
- Validating definition correctness
- Classifying or categorizing roles
- Making assumptions about structure
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from ..loaders.xbrl_filings import XBRLFilingsLoader


@dataclass
class RoleDefinition:
    """
    A role definition from schema roleType element.
    
    Contains what the company declared about a presentation/calculation/definition role.
    """
    role_uri: str
    definition: str
    used_on: Optional[str] = None
    role_id: Optional[str] = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ElementDefinition:
    """
    An element definition from schema.
    
    Contains what the company declared about a concept/element.
    """
    name: str
    qname: str
    element_type: Optional[str] = None
    substitution_group: Optional[str] = None
    period_type: Optional[str] = None
    balance: Optional[str] = None
    abstract: bool = False
    nillable: bool = True
    documentation: Optional[str] = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class SchemaSet:
    """Complete set of definitions discovered from schema files."""
    role_definitions: dict[str, RoleDefinition] = field(default_factory=dict)
    element_definitions: dict[str, ElementDefinition] = field(default_factory=dict)
    namespaces: dict[str, str] = field(default_factory=dict)
    schema_files: list[Path] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


class SchemaReader:
    """
    Reads XBRL schema files (.xsd) to extract taxonomy definitions.
    
    Discovers schema files using XBRLFilingsLoader, then parses XML to extract
    roleType and element definitions as declared by the company.
    
    NO hardcoded expectations - discovers everything from actual schema content.
    """
    
    # XBRL namespace URIs (from specification, used only for XML parsing)
    XBRL_NAMESPACES = {
        'xsd': 'http://www.w3.org/2001/XMLSchema',
        'xbrli': 'http://www.xbrl.org/2003/instance',
        'link': 'http://www.xbrl.org/2003/linkbase',
        'xlink': 'http://www.w3.org/1999/xlink',
    }
    
    def __init__(self, xbrl_loader: Optional[XBRLFilingsLoader] = None):
        """
        Initialize schema reader.
        
        Args:
            xbrl_loader: Optional XBRLFilingsLoader instance
        """
        self.xbrl_loader = xbrl_loader
        self.logger = logging.getLogger('input.schema_reader')
    
    def read_schemas(self, filing_subdirectory: str) -> SchemaSet:
        """
        Read all schema files in filing directory and extract definitions.
        
        Args:
            filing_subdirectory: Subdirectory path within XBRL filings directory
            
        Returns:
            SchemaSet with all discovered definitions
            
        Raises:
            FileNotFoundError: If filing directory doesn't exist
            ValueError: If xbrl_loader not provided
        """
        if not self.xbrl_loader:
            raise ValueError("XBRLFilingsLoader required for file access")
        
        self.logger.info(f"Reading schemas from: {filing_subdirectory}")
        
        # Create schema set
        schema_set = SchemaSet()
        
        # Discover all files in filing directory
        try:
            all_files = self.xbrl_loader.discover_all_files(filing_subdirectory)
        except FileNotFoundError as e:
            self.logger.error(f"Filing directory not found: {e}")
            raise
        
        # Filter for schema files (.xsd extension)
        schema_files = [f for f in all_files if f.suffix.lower() == '.xsd']
        
        if not schema_files:
            self.logger.warning(f"No schema files found in {filing_subdirectory}")
            return schema_set
        
        self.logger.info(f"Found {len(schema_files)} schema files")
        schema_set.schema_files = schema_files
        
        # Read each schema file
        for schema_file in schema_files:
            try:
                self._read_schema_file(schema_file, schema_set)
            except Exception as e:
                self.logger.error(f"Error reading schema {schema_file}: {e}")
                continue
        
        self.logger.info(
            f"Schema reading completed: "
            f"{len(schema_set.role_definitions)} roles, "
            f"{len(schema_set.element_definitions)} elements"
        )
        
        return schema_set
    
    def get_role_definition(self, schema_set: SchemaSet, role_uri: str) -> Optional[RoleDefinition]:
        """
        Get role definition for a specific role URI.
        
        Args:
            schema_set: SchemaSet to search in
            role_uri: Role URI to look up
            
        Returns:
            RoleDefinition if found, None otherwise
        """
        return schema_set.role_definitions.get(role_uri)
    
    def get_element_definition(self, schema_set: SchemaSet, qname: str) -> Optional[ElementDefinition]:
        """
        Get element definition for a specific element QName.
        
        Args:
            schema_set: SchemaSet to search in
            qname: Element QName to look up
            
        Returns:
            ElementDefinition if found, None otherwise
        """
        return schema_set.element_definitions.get(qname)
    
    def _read_schema_file(self, schema_file: Path, schema_set: SchemaSet) -> None:
        """
        Read a single schema file and extract definitions.
        
        Args:
            schema_file: Path to schema file
            schema_set: SchemaSet to populate
        """
        self.logger.debug(f"Reading schema: {schema_file.name}")
        
        try:
            tree = ET.parse(schema_file)
            root = tree.getroot()
        except ET.ParseError as e:
            self.logger.error(f"XML parse error in {schema_file}: {e}")
            return
        
        # Extract namespaces from root element
        namespaces = self._extract_namespaces(root)
        schema_set.namespaces.update(namespaces)
        
        # Get target namespace (the namespace this schema defines)
        target_namespace = root.get('targetNamespace', '')
        
        # Extract role definitions
        self._extract_role_definitions(root, namespaces, schema_set)
        
        # Extract element definitions
        self._extract_element_definitions(root, namespaces, target_namespace, schema_set)
    
    def _extract_namespaces(self, root: ET.Element) -> dict[str, str]:
        """
        Extract namespace declarations from schema root element.
        
        Args:
            root: Schema root element
            
        Returns:
            Dict mapping prefix -> namespace URI
        """
        namespaces = {}
        
        # ElementTree stores namespaces in tag
        for prefix, uri in root.nsmap.items() if hasattr(root, 'nsmap') else []:
            if prefix:
                namespaces[prefix] = uri
        
        # Also check standard XBRL namespaces
        namespaces.update(self.XBRL_NAMESPACES)
        
        return namespaces
    
    def _extract_role_definitions(
        self,
        root: ET.Element,
        namespaces: dict[str, str],
        schema_set: SchemaSet
    ) -> None:
        """
        Extract roleType definitions from schema.
        
        Looks for <link:roleType> elements in <annotation><appinfo> sections.
        
        Args:
            root: Schema root element
            namespaces: Namespace mappings
            schema_set: SchemaSet to populate
        """
        # Find all roleType elements
        # They're typically in: schema > annotation > appinfo > roleType
        
        # Try with namespace
        role_types = root.findall('.//link:roleType', namespaces)
        
        # If not found, try without namespace (some schemas don't use prefixes)
        if not role_types:
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag_name == 'roleType':
                    role_types.append(elem)
        
        for role_type in role_types:
            try:
                role_def = self._parse_role_type(role_type, namespaces)
                if role_def:
                    schema_set.role_definitions[role_def.role_uri] = role_def
                    self.logger.debug(
                        f"Found role: {role_def.role_uri} -> {role_def.definition}"
                    )
            except Exception as e:
                self.logger.warning(f"Error parsing roleType: {e}")
                continue
    
    def _parse_role_type(
        self,
        role_type_elem: ET.Element,
        namespaces: dict[str, str]
    ) -> Optional[RoleDefinition]:
        """
        Parse a single roleType element.
        
        Example XML:
        <link:roleType roleURI="http://company.com/role/BS" id="BalanceSheet">
          <link:definition>01 - Statement - Consolidated Balance Sheets</link:definition>
          <link:usedOn>link:presentationLink</link:usedOn>
        </link:roleType>
        
        Args:
            role_type_elem: roleType XML element
            namespaces: Namespace mappings
            
        Returns:
            RoleDefinition or None
        """
        # Get roleURI attribute (required)
        role_uri = role_type_elem.get('roleURI')
        if not role_uri:
            return None
        
        # Get id attribute (optional)
        role_id = role_type_elem.get('id')
        
        # Find definition element
        definition = None
        def_elem = role_type_elem.find('link:definition', namespaces)
        if def_elem is None:
            # Try without namespace
            for child in role_type_elem:
                tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if tag_name == 'definition':
                    def_elem = child
                    break
        
        if def_elem is not None and def_elem.text:
            definition = def_elem.text.strip()
        
        # Find usedOn element
        used_on = None
        used_on_elem = role_type_elem.find('link:usedOn', namespaces)
        if used_on_elem is None:
            # Try without namespace
            for child in role_type_elem:
                tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if tag_name == 'usedOn':
                    used_on_elem = child
                    break
        
        if used_on_elem is not None and used_on_elem.text:
            used_on = used_on_elem.text.strip()
        
        # Create role definition
        return RoleDefinition(
            role_uri=role_uri,
            definition=definition or "",
            used_on=used_on,
            role_id=role_id
        )
    
    def _extract_element_definitions(
        self,
        root: ET.Element,
        namespaces: dict[str, str],
        target_namespace: str,
        schema_set: SchemaSet
    ) -> None:
        """
        Extract element definitions from schema.
        
        Looks for <element> declarations at schema level.
        
        Args:
            root: Schema root element
            namespaces: Namespace mappings
            target_namespace: Target namespace of this schema
            schema_set: SchemaSet to populate
        """
        # Find all element declarations
        elements = root.findall('.//xsd:element', namespaces)
        
        # If not found, try without namespace
        if not elements:
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag_name == 'element' and elem.get('name'):
                    elements.append(elem)
        
        for element in elements:
            try:
                elem_def = self._parse_element(element, namespaces, target_namespace)
                if elem_def:
                    schema_set.element_definitions[elem_def.qname] = elem_def
                    self.logger.debug(f"Found element: {elem_def.qname}")
            except Exception as e:
                self.logger.warning(f"Error parsing element: {e}")
                continue
    
    def _parse_element(
        self,
        element_elem: ET.Element,
        namespaces: dict[str, str],
        target_namespace: str
    ) -> Optional[ElementDefinition]:
        """
        Parse a single element declaration.
        
        Example XML:
        <element name="CustomAsset" 
                 type="xbrli:monetaryItemType" 
                 substitutionGroup="xbrli:item"
                 xbrli:periodType="instant"
                 xbrli:balance="debit"
                 id="company_CustomAsset">
          <annotation>
            <documentation>Custom asset description</documentation>
          </annotation>
        </element>
        
        Args:
            element_elem: element XML element
            namespaces: Namespace mappings
            target_namespace: Target namespace for this element
            
        Returns:
            ElementDefinition or None
        """
        # Get name attribute (required)
        name = element_elem.get('name')
        if not name:
            return None
        
        # Construct QName (target_namespace + name)
        qname = f"{target_namespace}#{name}" if target_namespace else name
        
        # Get type
        element_type = element_elem.get('type')
        
        # Get substitution group
        substitution_group = element_elem.get('substitutionGroup')
        
        # Get XBRL-specific attributes
        period_type = None
        balance = None
        
        # Try with xbrli namespace
        for attr_name, attr_value in element_elem.attrib.items():
            if 'periodType' in attr_name:
                period_type = attr_value
            elif 'balance' in attr_name:
                balance = attr_value
        
        # Get abstract attribute
        abstract = element_elem.get('abstract', 'false').lower() == 'true'
        
        # Get nillable attribute
        nillable = element_elem.get('nillable', 'true').lower() == 'true'
        
        # Get documentation
        documentation = None
        doc_elem = element_elem.find('.//xsd:documentation', namespaces)
        if doc_elem is None:
            # Try without namespace
            for elem in element_elem.iter():
                tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag_name == 'documentation':
                    doc_elem = elem
                    break
        
        if doc_elem is not None and doc_elem.text:
            documentation = doc_elem.text.strip()
        
        return ElementDefinition(
            name=name,
            qname=qname,
            element_type=element_type,
            substitution_group=substitution_group,
            period_type=period_type,
            balance=balance,
            abstract=abstract,
            nillable=nillable,
            documentation=documentation
        )


__all__ = [
    'SchemaReader',
    'SchemaSet',
    'RoleDefinition',
    'ElementDefinition',
]