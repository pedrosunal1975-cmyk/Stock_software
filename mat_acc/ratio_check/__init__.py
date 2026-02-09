# Path: mat_acc_files/ratio_check/__init__.py
"""
Ratio Check Module

Orchestrates financial ratio calculation using the Dynamic Concept Matching Engine.

Architecture:
    ratio_check.py        - Main orchestrator and CLI entry point
    filing_menu.py        - Clean CLI menu for company selection
    concept_builder.py    - Build ConceptMetadata from source files
    ratio_calculator.py   - Run matcher engine and calculate ratios
    fact_value_lookup.py  - CRITICAL: Retrieves actual values from source files
    database_checker.py   - Check/populate HierarchyNode data
    data_preparer.py      - Run enrichment scripts if needed
    source_checker.py     - Utility for source verification (internal use)
    debug_reporter.py     - Debug status reporting for process tracking

Value Retrieval:
    The FactValueLookup class is the CRITICAL link between concept matching
    and ratio calculation. It reads actual numeric values from:
    - parsed.json (comprehensive fact data)
    - Mapped statements (company's declared presentation)

    Without FactValueLookup, ratios would show "Values not available".

Usage:
    cd mat_acc_files
    python -m ratio_check

Logging:
    Uses IPO (Input-Process-Output) logging system.
    Logs are written to the configured log directory:
    - input_activity.log: Filing selection, database queries
    - process_activity.log: Concept building, matching, calculation
    - output_activity.log: Report generation, debug output
    - full_activity.log: All activities combined
"""

from .database_checker import DatabaseChecker
from .data_preparer import DataPreparer
from .filing_menu import FilingMenu, FilingSelection
from .concept_builder import ConceptBuilder
from .ratio_calculator import (
    RatioCalculator,
    ComponentMatch,
    RatioResult,
    AnalysisResult,
)
from .ratio_check import RatioCheckOrchestrator, main
from .debug_reporter import DebugReporter, ComponentDebugInfo, ProcessState
from .fact_value_lookup import FactValueLookup, FactValue


__all__ = [
    # Core orchestrator
    'RatioCheckOrchestrator',
    'main',
    # Filing selection
    'FilingMenu',
    'FilingSelection',
    # Concept building
    'ConceptBuilder',
    # Ratio calculation
    'RatioCalculator',
    'ComponentMatch',
    'RatioResult',
    'AnalysisResult',
    # Value lookup (CRITICAL for retrieving actual values from sources)
    'FactValueLookup',
    'FactValue',
    # Database operations
    'DatabaseChecker',
    # Data preparation
    'DataPreparer',
    # Debug/Reporting
    'DebugReporter',
    'ComponentDebugInfo',
    'ProcessState',
]
