# Path: xbrl_parser/taxonomy/__init__.py
"""
Taxonomy Module

Taxonomy loading and management components.

This module provides:
- Schema loading (XSD parsing)
- Linkbase loading (presentation, calculation, definition)
- Network building (relationship organization)
- Version management (compatibility checking)
- High-level taxonomy service
- Constants (namespace URIs, patterns)

Example:
    from ..taxonomy import TaxonomyService
    
    service = TaxonomyService()
    result = service.load_from_instance(Path("filing.xml"))
    
    # Access loaded concepts
    concept = service.get_concept("us-gaap:Assets")
"""

from ..taxonomy.service import (
    TaxonomyService,
    TaxonomyLoadResult
)

from ..taxonomy.schema_loader import (
    SchemaLoader,
    SchemaLoadResult,
    SchemaImport
)

from ..taxonomy.linkbase_loader import (
    LinkbaseLoader,
    LinkbaseLoadResult,
    LinkbaseType
)

from ..taxonomy.network_builder import (
    NetworkBuilder,
    PresentationNetwork,
    CalculationNetwork
)

from ..taxonomy.version_manager import (
    VersionManager,
    TaxonomyVersion,
    TaxonomyFamily,
    VersionCompatibility
)

from ..taxonomy import constants


__all__ = [
    # High-level service
    'TaxonomyService',
    'TaxonomyLoadResult',
    
    # Schema loading
    'SchemaLoader',
    'SchemaLoadResult',
    'SchemaImport',
    
    # Linkbase loading
    'LinkbaseLoader',
    'LinkbaseLoadResult',
    'LinkbaseType',
    
    # Network building
    'NetworkBuilder',
    'PresentationNetwork',
    'CalculationNetwork',
    
    # Version management
    'VersionManager',
    'TaxonomyVersion',
    'TaxonomyFamily',
    'VersionCompatibility',
    
    # Constants
    'constants',
]
