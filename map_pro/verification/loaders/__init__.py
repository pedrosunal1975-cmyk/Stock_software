# Path: verification/loaders/__init__.py
"""
Verification Loaders Package

Data loading components for the verification module.

Architecture:
- Blind Doorkeepers: Discover paths without interpreting content
  - MappedDataLoader: Discover mapped statement folders
  - ParsedDataLoader: Discover parsed filing folders
  - XBRLFilingsLoader: Discover XBRL filing folders
  - TaxonomyLoader: Discover taxonomy libraries

- Readers: Load and interpret file contents
  - MappedReader: Read mapped statement JSON files
  - XBRLReader: Read calculation/presentation linkbases
  - TaxonomyReader: Read taxonomy definitions
"""

# Blind Doorkeepers (path discovery only)
from .mapped_data import MappedDataLoader, MappedFilingEntry
from .parsed_data import ParsedDataLoader, ParsedFilingEntry
from .xbrl_filings import XBRLFilingsLoader
from .taxonomy import TaxonomyLoader

# Readers (content interpretation)
from .mapped_reader import MappedReader, MappedStatements, Statement, StatementFact
from .xbrl_reader import (
    XBRLReader,
    CalculationNetwork,
    CalculationArc,
    PresentationNetwork,
    PresentationArc,
)
from .taxonomy_reader import TaxonomyReader, TaxonomyDefinition, ConceptDefinition
from .taxonomy_calc_reader import (
    TaxonomyCalcReader,
    TaxonomyCalculations,
    CalculationRelationship,
)


__all__ = [
    # Doorkeepers
    'MappedDataLoader',
    'MappedFilingEntry',
    'ParsedDataLoader',
    'ParsedFilingEntry',
    'XBRLFilingsLoader',
    'TaxonomyLoader',

    # Readers
    'MappedReader',
    'MappedStatements',
    'Statement',
    'StatementFact',
    'XBRLReader',
    'CalculationNetwork',
    'CalculationArc',
    'PresentationNetwork',
    'PresentationArc',
    'TaxonomyReader',
    'TaxonomyDefinition',
    'ConceptDefinition',
    'TaxonomyCalcReader',
    'TaxonomyCalculations',
    'CalculationRelationship',
]
