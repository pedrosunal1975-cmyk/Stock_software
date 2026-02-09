# Path: mapping/statement/__init__.py
"""
Statement Module
Handles statement building from presentation networks.
"""

from .statement_builder import StatementBuilder
from .models import (
    Statement,
    StatementSet,
    StatementFact,
)
from .helpers import (
    determine_statement_date,
    determine_period_type,
    build_context_map,
)
from .statistics import (
    StatementBuildingStatistics,
    FilteringStatistics,
    DimensionalStatistics,
)
from .unmapped_tracker import (
    UnmappedFactsTracker,
    UnmappedFactsReport,
    UnmappedFact,
)
from .hierarchy_builder import HierarchyBuilder
from .fact_extractor import FactExtractor
from .fact_enricher import FactEnricher

__all__ = [
    # Main builder
    'StatementBuilder',
    
    # Data classes (from models.py)
    'Statement',
    'StatementSet',
    'StatementFact',
    
    # Helpers
    'determine_statement_date',
    'determine_period_type',
    'build_context_map',
    
    # Statistics
    'StatementBuildingStatistics',
    'FilteringStatistics',
    'DimensionalStatistics',
    
    # Tracking
    'UnmappedFactsTracker',
    'UnmappedFactsReport',
    'UnmappedFact',
    
    # Builders
    'HierarchyBuilder',
    'FactExtractor',
    'FactEnricher',  # NEW: Value enrichment
]