# Path: xbrl_parser/taxonomy/service.py
"""
Taxonomy Service

High-level orchestrator for taxonomy loading and management.

This service coordinates:
- Schema loading and caching
- Linkbase loading
- Network building
- Version management
- Concept resolution

Example:
    from ..taxonomy import TaxonomyService
    
    service = TaxonomyService()
    taxonomy = service.load_taxonomy(schema_refs)
    concept = taxonomy.get_concept("us-gaap:Assets")
"""

import logging
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field

from ...core.config_loader import ConfigLoader
from ..foundation.namespace_registry import NamespaceRegistry
from ..foundation.taxonomy_cache import TaxonomyCache
from ..foundation.xml_parser import XMLParser
from ..models.concept import Concept
from ..models.error import ParsingError, ErrorCategory, ErrorSeverity


@dataclass
class TaxonomyLoadResult:
    """
    Result of taxonomy loading operation.
    
    Contains loaded concepts, relationships, and any errors encountered.
    """
    
    # Loaded data
    concepts: dict[str, Concept] = field(default_factory=dict)
    namespaces: dict[str, str] = field(default_factory=dict)
    
    # Loading statistics
    schemas_loaded: int = 0
    linkbases_loaded: int = 0
    concepts_loaded: int = 0
    
    # Errors
    errors: list[ParsingError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    # Metadata
    entry_point: Optional[str] = None
    load_time_seconds: float = 0.0
    from_cache: bool = False


class TaxonomyService:
    """
    High-level taxonomy management service.
    
    Orchestrates schema loading, linkbase loading, and concept management.
    
    Example:
        config = ConfigLoader()
        service = TaxonomyService(config)
        
        # Load taxonomy
        result = service.load_from_instance(instance_path)
        
        # Access concepts
        concept = service.get_concept("us-gaap:Assets")
"""
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize taxonomy service.
        
        Args:
            config: Configuration loader (creates default if None)
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache
        cache_dir = Path(self.config.get('taxonomy_cache_dir'))
        cache_size_mb = self.config.get('taxonomy_cache_size_mb', 1024)
        self.cache = TaxonomyCache(cache_dir, cache_size_mb)
        
        # Initialize namespace registry
        self.namespace_registry = NamespaceRegistry()
        
        # Loaded taxonomy data
        self.concepts: dict[str, Concept] = {}
        self.loaded_schemas: set[str] = set()
        self.loaded_linkbases: set[str] = set()
        
        # Lazy-loaded components
        self.schema_loader = None
        
        self.logger.info("TaxonomyService initialized")
    
    def load_from_instance(self, instance_path: Path) -> TaxonomyLoadResult:
        """
        Load taxonomy from instance document.
        
        Extracts schema references from instance and loads complete taxonomy.
        
        Args:
            instance_path: Path to instance document
            
        Returns:
            TaxonomyLoadResult with loaded data and statistics
            
        Example:
            result = service.load_from_instance(Path("filing.xml"))
            print(f"Loaded {result.concepts_loaded} concepts")
        """
        self.logger.info(f"Loading taxonomy from instance: {instance_path}")
        
        import time
        start_time = time.time()
        
        result = TaxonomyLoadResult()
        result.entry_point = str(instance_path)
        
        try:
            # Check if file exists
            if not instance_path.exists():
                raise FileNotFoundError(f"Instance file not found: {instance_path}")
            
            # Extract schema references from instance
            schema_refs = self._extract_schema_refs(instance_path)
            
            if not schema_refs:
                self.logger.warning("No schema references found in instance document")
                result.warnings.append("No schema references found - taxonomy will be empty")
            else:
                self.logger.info(f"Found {len(schema_refs)} schema references")
            
            # Load each schema
            for schema_ref in schema_refs:
                try:
                    self._load_schema(schema_ref, result)
                except Exception as e:
                    self.logger.warning(f"Failed to load schema {schema_ref}: {e}")
                    result.errors.append(ParsingError(
                        category=ErrorCategory.TAXONOMY_LOAD_FAILED,
                        message=f"Failed to load schema {schema_ref}: {e}",
                        severity=ErrorSeverity.WARNING
                    ))
            
            # TODO: Load linkbases (calculation, presentation, definition)
            # This would require following linkbaseRef elements
            # For now, we have the basic concepts from schemas
            
            # Populate result
            result.concepts = self.concepts
            result.namespaces = dict(self.namespace_registry.by_prefix)
            result.schemas_loaded = len(self.loaded_schemas)
            result.linkbases_loaded = len(self.loaded_linkbases)
            result.concepts_loaded = len(self.concepts)
            
        except Exception as e:
            self.logger.error(f"Taxonomy loading failed: {e}", exc_info=True)
            result.errors.append(ParsingError(
                category=ErrorCategory.TAXONOMY_LOAD_FAILED,
                message=f"Failed to load taxonomy: {e}",
                severity=ErrorSeverity.ERROR,
                source_file=str(instance_path)
            ))
        
        result.load_time_seconds = time.time() - start_time
        self.logger.info(
            f"Taxonomy loading complete: {result.concepts_loaded} concepts, "
            f"{result.schemas_loaded} schemas in {result.load_time_seconds:.2f}s"
        )
        
        return result
    
    def _extract_schema_refs(self, instance_path: Path) -> list[str]:
        """
        Extract schema references from instance document.
        
        Looks for <link:schemaRef> elements with xlink:href attributes.
        
        Args:
            instance_path: Path to instance document
            
        Returns:
            list of schema reference URIs
        """
        schema_refs = []
        
        try:
            # Parse instance document
            parser = XMLParser()
            result = parser.parse_file(instance_path)
            
            # XMLParser returns XMLParseResult with .root attribute
            if result.root is None:
                self.logger.warning("Failed to parse instance document")
                return schema_refs
            
            root = result.root
            
            # Define namespaces
            LINK_NS = 'http://www.xbrl.org/2003/linkbase'
            XLINK_NS = 'http://www.w3.org/1999/xlink'
            
            # Find all schemaRef elements
            schema_elements = root.findall(f".//{{{LINK_NS}}}schemaRef")
            
            for elem in schema_elements:
                href = elem.get(f'{{{XLINK_NS}}}href')
                if href:
                    # Resolve relative paths
                    if not href.startswith('http'):
                        # Make absolute path relative to instance directory
                        instance_dir = instance_path.parent
                        schema_path = (instance_dir / href).resolve()
                        schema_refs.append(str(schema_path))
                    else:
                        schema_refs.append(href)
            
            self.logger.debug(f"Extracted {len(schema_refs)} schema references")
            
        except Exception as e:
            self.logger.error(f"Failed to extract schema refs: {e}", exc_info=True)
        
        return schema_refs
    
    def _load_schema(self, schema_ref: str, result: TaxonomyLoadResult) -> None:
        """
        Load a single schema and add concepts to result.
        
        Args:
            schema_ref: Schema URI or file path
            result: TaxonomyLoadResult to populate
        """
        # Check if already loaded
        if schema_ref in self.loaded_schemas:
            self.logger.debug(f"Schema already loaded: {schema_ref}")
            return
        
        try:
            from ..taxonomy.schema_loader import SchemaLoader
            
            if self.schema_loader is None:
                self.schema_loader = SchemaLoader(self.config)
            
            # Load schema
            schema_path = Path(schema_ref) if not schema_ref.startswith('http') else schema_ref
            schema_result = self.schema_loader.load_schema(schema_path)
            
            # Add concepts to service registry
            for qname, concept in schema_result.elements.items():
                self.concepts[qname] = concept
            
            # Track loaded schema
            self.loaded_schemas.add(schema_ref)
            
            self.logger.debug(f"Loaded schema {schema_ref}: {len(schema_result.elements)} concepts")
            
        except Exception as e:
            self.logger.warning(f"Failed to load schema {schema_ref}: {e}")
            raise
    
    def get_concept(self, qname: str) -> Optional[Concept]:
        """
        Get concept by QName.
        
        Args:
            qname: Qualified name (e.g., "us-gaap:Assets")
            
        Returns:
            Concept if found, None otherwise
            
        Example:
            concept = service.get_concept("us-gaap:Assets")
            if concept:
                print(f"Type: {concept.type}")
        """
        return self.concepts.get(qname)
    
    def clear(self):
        """
        Clear all loaded taxonomy data.
        
        Useful for loading a new taxonomy.
        
        Example:
            service.clear()
            result = service.load_from_instance(new_path)
        """
        self.concepts.clear()
        self.loaded_schemas.clear()
        self.loaded_linkbases.clear()
        self.namespace_registry = NamespaceRegistry()
        self.logger.info("Taxonomy service cleared")


__all__ = ['TaxonomyService', 'TaxonomyLoadResult']
