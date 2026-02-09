# Path: mat_acc/loaders/__init__.py
"""
mat_acc Loaders Package

BLIND readers for all external data sources.
Single entry point for all data access across mat_acc.

Data Sources:
    - verification: Verification reports from map_pro
    - mapped: Mapped financial statements from map_pro/mapper
    - parsed: Parsed XBRL filings from map_pro/parser
    - xbrl: Raw XBRL filing files from map_pro/downloader
    - taxonomy: Standard taxonomy libraries (US-GAAP, IFRS, etc.)

Design Principles:
    - NO hardcoded directory structure assumptions
    - Recursive file discovery (up to 25 levels deep)
    - Market-agnostic, naming-convention-agnostic
    - Separation: Discovery (*_data.py) vs Interpretation (*_reader.py)

Example:
    from loaders import (
        VerificationDataLoader, VerificationReader,
        MappedDataLoader, MappedReader,
        ParsedDataLoader, ParsedReader,
        XBRLDataLoader, XBRLReader,
        TaxonomyDataLoader, TaxonomyReader,
    )

    # Verification reports
    v_loader = VerificationDataLoader(config)
    v_reader = VerificationReader(config)
    filings = v_loader.discover_filings()

    # Mapped statements
    m_loader = MappedDataLoader(config)
    m_reader = MappedReader()
    statements = m_reader.read_statements(filing)

    # Parsed data
    p_loader = ParsedDataLoader(config)
    p_reader = ParsedReader()
    parsed = p_reader.read_parsed_filing(entry)

    # XBRL linkbases
    x_loader = XBRLDataLoader(config)
    x_reader = XBRLReader(config)
    calcs = x_reader.read_calculation_linkbase(path)

    # Taxonomy libraries
    t_loader = TaxonomyDataLoader(config)
    t_reader = TaxonomyReader(config)
    labels = t_reader.get_labels_for_concepts(['us-gaap:Assets'])
"""

# Verification reports
from .verification_data import VerificationDataLoader, VerifiedFilingEntry
from .verification_reader import (
    VerificationReader,
    VerificationReport,
    VerificationSummary,
    VerificationCheck,
)

# Mapped statements
from .mapped_data import MappedDataLoader, MappedFilingEntry
from .mapped_reader import (
    MappedReader,
    MappedStatements,
    Statement,
    StatementFact,
)

# Parsed filings
from .parsed_data import ParsedDataLoader, ParsedFilingEntry
from .parsed_reader import (
    ParsedReader,
    ParsedFiling,
    ParsedFact,
    ParsedContext,
    ParsedUnit,
)

# XBRL raw files
from .xbrl_data import XBRLDataLoader
from .xbrl_reader import (
    XBRLReader,
    CalculationNetwork,
    CalculationArc,
    PresentationNetwork,
    PresentationArc,
    DefinitionNetwork,
    DefinitionArc,
)

# Taxonomy libraries
from .taxonomy_data import TaxonomyDataLoader, TaxonomyEntry
from .taxonomy_reader import (
    TaxonomyReader,
    TaxonomyInfo,
    TaxonomyElement,
    TaxonomyLabel,
)
from .taxonomy_analyzer import (
    TaxonomyFileAnalyzer,
    FileCapabilities,
    DirectoryAnalysis,
)

# Constants
from .constants import (
    VERIFICATION_REPORT_FILE,
    MAPPED_STATEMENT_MARKERS,
    PARSED_JSON_FILE,
    normalize_form_name,
    get_form_variations,
    normalize_name,
    dates_match_flexible,
)


__all__ = [
    # Verification
    'VerificationDataLoader',
    'VerifiedFilingEntry',
    'VerificationReader',
    'VerificationReport',
    'VerificationSummary',
    'VerificationCheck',

    # Mapped
    'MappedDataLoader',
    'MappedFilingEntry',
    'MappedReader',
    'MappedStatements',
    'Statement',
    'StatementFact',

    # Parsed
    'ParsedDataLoader',
    'ParsedFilingEntry',
    'ParsedReader',
    'ParsedFiling',
    'ParsedFact',
    'ParsedContext',
    'ParsedUnit',

    # XBRL
    'XBRLDataLoader',
    'XBRLReader',
    'CalculationNetwork',
    'CalculationArc',
    'PresentationNetwork',
    'PresentationArc',
    'DefinitionNetwork',
    'DefinitionArc',

    # Taxonomy
    'TaxonomyDataLoader',
    'TaxonomyEntry',
    'TaxonomyReader',
    'TaxonomyInfo',
    'TaxonomyElement',
    'TaxonomyLabel',
    'TaxonomyFileAnalyzer',
    'FileCapabilities',
    'DirectoryAnalysis',

    # Utilities
    'VERIFICATION_REPORT_FILE',
    'MAPPED_STATEMENT_MARKERS',
    'PARSED_JSON_FILE',
    'normalize_form_name',
    'get_form_variations',
    'normalize_name',
    'dates_match_flexible',
]
