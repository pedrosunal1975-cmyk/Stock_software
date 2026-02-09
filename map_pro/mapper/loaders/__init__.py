# Path: loaders/__init__.py
"""
Loaders Module

Universal data access layer for the mapper system.

DESIGN PRINCIPLES:
- Loaders are doorkeepers: they provide paths and access, not interpretation
- Structure readers discover format without expectations
- Deserializers adapt to discovered structure
- No assumptions about what data should look like

ARCHITECTURE:
Each data source has loader components that answer:
- WHERE: Location discovery (paths to files/resources)
- HOW: Structure discovery (what format is the data in)
- WHAT: Semantic interpretation (what does the data mean)

All loaders follow the "read as is" principle:
- Discover what exists, don't expect what should exist
- Adapt to actual structure, don't enforce expected structure
- Report what's found, don't assume what's missing is wrong

This design ensures compatibility across:
- Multiple regulatory markets (SEC, FRC, ESMA, etc.)
- Multiple taxonomies (US-GAAP, IFRS, UK-GAAP, etc.)
- Multiple file formats (JSON, XML, iXBRL, etc.)
- Multiple versions and variants of standards
"""

# Import all available loaders
# These imports are explicit to show what's available, but the system
# doesn't assume these are the only loaders that will ever exist

# Data structure components
from .parsed_data import ParsedDataLoader, ParsedFilingEntry
from .json_structure_reader import JSONStructureReader, JSONStructure
from .parser_output import (
    ParserOutputDeserializer,
    ParsedFiling,
    FilingCharacteristics
)
from .filing_analyzer import FilingAnalyzer

# Data source loaders
from .xbrl_filings import XBRLFilingsLoader
from .taxonomy import TaxonomyLoader
from .taxonomy_structure_reader import (
    TaxonomyStructureReader,
    TaxonomyStructure
)
from .linkbase_locator import (
    LinkbaseLocator,
    LinkbaseSet,
    PresentationNetwork,
    CalculationNetwork,
    DefinitionNetwork,
)
from .schema_reader import (
    SchemaReader,
    SchemaSet,
    RoleDefinition,
    ElementDefinition,
)

# Validation
from .input_validator import (
    InputValidator,
    ValidationResult
)

# Constants
from .constants import (
    TAXONOMY_RECOGNITION_PATTERNS,  # Renamed from TAXONOMY_URI_PATTERNS
    FACT_CONTAINER_PATTERNS,
    CONTEXT_CONTAINER_PATTERNS,
    # MARKET_DETECTION_PATTERNS removed - read from filing metadata instead
)

__all__ = [
    # Parsed data access
    'ParsedDataLoader',
    'ParsedFilingEntry',
    
    # Structure discovery
    'JSONStructureReader',
    'JSONStructure',
    
    # Semantic interpretation
    'ParserOutputDeserializer',
    'ParsedFiling',
    'FilingCharacteristics',
    'FilingAnalyzer',
    
    # Source data access
    'XBRLFilingsLoader',
    'TaxonomyLoader',
    'TaxonomyStructureReader',
    'TaxonomyStructure',
    'LinkbaseLocator',
    'LinkbaseSet',
    'PresentationNetwork',
    'CalculationNetwork',
    'DefinitionNetwork',
    
    # Schema reading (NEW)
    'SchemaReader',
    'SchemaSet',
    'RoleDefinition',
    'ElementDefinition',
    
    # Validation
    'InputValidator',
    'ValidationResult',
    
    # Constants (updated names)
    'TAXONOMY_RECOGNITION_PATTERNS',  
    'FACT_CONTAINER_PATTERNS',
    'CONTEXT_CONTAINER_PATTERNS',
]