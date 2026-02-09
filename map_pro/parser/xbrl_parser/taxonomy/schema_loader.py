# Path: xbrl_parser/taxonomy/schema_loader.py
"""
Schema Loader

Loads and parses XSD taxonomy schema files.

Features:
- Element definition extraction
- Type resolution
- Import following
- Circular reference detection
- Standard vs extension classification

Example:
    from ..taxonomy import SchemaLoader
    
    loader = SchemaLoader()
    elements = loader.load_schema(Path("us-gaap-2023.xsd"))
"""

import logging
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field
from lxml import etree

from ...core.config_loader import ConfigLoader
from ..foundation.xml_parser import XMLParser
from ..foundation.namespace_registry import NamespaceRegistry
from ..foundation.qname import QName, QNameResolver
from ..models.concept import Concept, ConceptType, ConceptPeriodType
from ..models.error import ParsingError, ErrorCategory
from ..taxonomy.constants import XSD_NS
from ..foundation.url_addresses import (
    SEC_NAMESPACE_PATTERNS,
    ESMA_NAMESPACE_PATTERNS,
    FRC_NAMESPACE_PATTERNS,
    IFRS_NAMESPACE_PATTERNS
)


@dataclass
class SchemaImport:
    """Represents an import statement in a schema."""
    namespace: str
    schema_location: Optional[str]
    source_schema: str


@dataclass
class SchemaLoadResult:
    """Result of loading a single schema."""
    schema_path: str
    namespace: str
    elements: dict[str, Concept] = field(default_factory=dict)
    imports: list[SchemaImport] = field(default_factory=list)
    errors: list[ParsingError] = field(default_factory=list)
    is_extension: bool = False


class SchemaLoader:
    """
    Loads XSD taxonomy schemas.
    
    Parses element definitions, follows imports, and builds concept registry.
    
    Example:
        config = ConfigLoader()
        loader = SchemaLoader(config)
        
        result = loader.load_schema(schema_path)
        for qname, concept in result.elements.items():
            print(f"{qname}: {concept.type}")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize schema loader.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        self.xml_parser = XMLParser(self.config)
        
        # Track loaded schemas to prevent circular imports
        self.loaded_schemas: set[str] = set()
        self.loading_stack: list[str] = []
        
        # Namespace registry
        self.namespace_registry = NamespaceRegistry()
        self.qname_resolver = QNameResolver(self.namespace_registry)
        
        # Build standard namespace patterns from imported data
        self.STANDARD_NAMESPACES = (
            SEC_NAMESPACE_PATTERNS +
            ESMA_NAMESPACE_PATTERNS +
            FRC_NAMESPACE_PATTERNS +
            IFRS_NAMESPACE_PATTERNS
        )
    
    def load_schema(self, schema_path: Path) -> SchemaLoadResult:
        """
        Load and parse XSD schema file.
        
        Args:
            schema_path: Path to schema file
            
        Returns:
            SchemaLoadResult with elements and imports
            
        Example:
            result = loader.load_schema(Path("schema.xsd"))
            if result.errors:
                print(f"Errors: {len(result.errors)}")
        """
        schema_path_str = str(schema_path)
        self.logger.info(f"Loading schema: {schema_path_str}")
        
        result = SchemaLoadResult(schema_path=schema_path_str, namespace="")
        
        # Check for circular reference
        if schema_path_str in self.loading_stack:
            error_msg = f"Circular schema import detected: {schema_path_str}"
            self.logger.error(error_msg)
            result.errors.append(ParsingError(
                category=ErrorCategory.TAXONOMY_LOAD_FAILED,
                message=error_msg,
                severity="ERROR",
                source_file=schema_path_str
            ))
            return result
        
        # Mark as loading
        self.loading_stack.append(schema_path_str)
        
        try:
            # Parse XML
            parse_result = self.xml_parser.parse_file(schema_path)
            if not parse_result.well_formed:
                result.errors.extend(parse_result.errors)
                return result
            
            root = parse_result.root
            
            # Extract target namespace
            target_namespace = root.get('targetNamespace')
            if not target_namespace:
                self.logger.warning(f"Schema has no targetNamespace: {schema_path_str}")
                result.namespace = ""
            else:
                result.namespace = target_namespace
                
                # Register namespace
                self.namespace_registry.extract_from_element(root)
                
                # Determine if extension
                result.is_extension = not self._is_standard_namespace(target_namespace)
            
            # Extract imports
            result.imports = self._extract_imports(root, schema_path_str)
            
            # Extract element definitions
            result.elements = self._extract_elements(root, target_namespace, schema_path_str)
            
            self.logger.info(
                f"Schema loaded: {len(result.elements)} elements, "
                f"{len(result.imports)} imports"
            )
            
        except Exception as e:
            self.logger.error(f"Schema load failed: {e}", exc_info=True)
            result.errors.append(ParsingError(
                category=ErrorCategory.TAXONOMY_LOAD_FAILED,
                message=f"Failed to load schema: {e}",
                severity="ERROR",
                source_file=schema_path_str
            ))
        finally:
            # Remove from loading stack
            self.loading_stack.pop()
        
        return result
    
    def _extract_imports(
        self,
        root: etree._Element,
        source_schema: str
    ) -> list[SchemaImport]:
        """
        Extract import statements from schema.
        
        Args:
            root: Schema root element
            source_schema: Path to schema being parsed
            
        Returns:
            list of SchemaImport objects
        """
        imports = []
        
        # Find all import elements
        # XSD namespace
        xsd_ns = XSD_NS
        import_elements = root.findall(f".//{{{xsd_ns}}}import")
        
        for import_elem in import_elements:
            namespace = import_elem.get('namespace')
            schema_location = import_elem.get('schemaLocation')
            
            if namespace:
                imports.append(SchemaImport(
                    namespace=namespace,
                    schema_location=schema_location,
                    source_schema=source_schema
                ))
        
        return imports
    
    def _extract_elements(
        self,
        root: etree._Element,
        target_namespace: str,
        source_file: str
    ) -> dict[str, Concept]:
        """
        Extract element definitions from schema.
        
        Args:
            root: Schema root element
            target_namespace: Schema target namespace
            source_file: Path to schema file
            
        Returns:
            Dictionary of QName -> Concept
        """
        elements = {}
        
        # XSD namespace
        xsd_ns = XSD_NS
        
        # Find all element definitions
        element_defs = root.findall(f".//{{{xsd_ns}}}element")
        
        for elem_def in element_defs:
            name = elem_def.get('name')
            if not name:
                continue
            
            # Build QName
            qname = f"{target_namespace}#{name}" if target_namespace else name
            
            # Extract attributes
            type_attr = elem_def.get('type', 'xsd:string')
            substitution_group = elem_def.get('substitutionGroup')
            abstract = elem_def.get('abstract', 'false') == 'true'
            
            # Determine period type from substitution group
            period_type = self._infer_period_type(substitution_group)
            
            # Create concept
            concept = Concept(
                qname=qname,
                name=name,
                namespace=target_namespace,
                type=type_attr,
                period_type=period_type,
                abstract=abstract,
                substitution_group=substitution_group
            )
            
            elements[qname] = concept
        
        return elements
    
    def _infer_period_type(self, substitution_group: Optional[str]) -> ConceptPeriodType:
        """
        Infer period type from substitution group.
        
        Args:
            substitution_group: Substitution group QName
            
        Returns:
            ConceptPeriodType enum value
        """
        if not substitution_group:
            return ConceptPeriodType.DURATION
        
        # Check for instant indicators
        if 'instant' in substitution_group.lower():
            return ConceptPeriodType.INSTANT
        
        # Default to duration
        return ConceptPeriodType.DURATION
    
    def _is_standard_namespace(self, namespace: str) -> bool:
        """
        Check if namespace is from a standard taxonomy.
        
        Args:
            namespace: Namespace URI
            
        Returns:
            True if standard taxonomy
        """
        return any(pattern in namespace for pattern in self.STANDARD_NAMESPACES)


__all__ = ['SchemaLoader', 'SchemaLoadResult', 'SchemaImport']
