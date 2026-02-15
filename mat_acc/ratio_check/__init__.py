# Path: mat_acc/ratio_check/__init__.py
"""
Ratio Check Module

Orchestrates financial ratio calculation using the Dynamic Concept Matching Engine.

Architecture:
    ratio_check.py        - Main orchestrator and CLI entry point
    filing_menu.py        - Clean CLI menu for company selection
    concept_builder.py    - Build ConceptMetadata from source files
    ratio_calculator.py   - Run matcher engine and calculate ratios
    ratio_models.py       - Data classes (ComponentMatch, RatioResult, etc.)
    ratio_definitions.py  - Standard financial ratio definitions
    ratio_engine.py       - Ratio computation from matched components
    value_populator.py    - 4-pass value population pipeline
    fact_value_lookup.py  - Retrieves actual values from source files
    math_verify/          - Mathematical Integrity Unit (sign, scale, identity)
    database_checker.py   - Check/populate HierarchyNode data
    data_preparer.py      - Run enrichment scripts if needed
    debug_reporter.py     - Debug status reporting for process tracking

Usage:
    cd mat_acc
    python -m ratio_check
"""

from .database_checker import DatabaseChecker
from .data_preparer import DataPreparer
from .filing_menu import FilingMenu, FilingSelection
from .concept_builder import ConceptBuilder
from .ratio_models import ComponentMatch, RatioResult, AnalysisResult
from .ratio_calculator import RatioCalculator
from .industry_detector import IndustryDetector
from .industry_registry import IndustryRegistry
from .ratio_check import RatioCheckOrchestrator, main
from .debug_reporter import DebugReporter, ComponentDebugInfo, ProcessState
from .fact_value_lookup import FactValueLookup, FactValue
from .math_verify import (
    IXBRLExtractor,
    VerifiedFact,
    ContextFilter,
    ContextInfo,
    FactReconciler,
    ReconciliationResult,
    SignAnalyzer,
    SignCheck,
    IdentityValidator,
    IdentityCheck,
)


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
    # Value lookup
    'FactValueLookup',
    'FactValue',
    # Mathematical Integrity Unit
    'IXBRLExtractor',
    'VerifiedFact',
    'ContextFilter',
    'ContextInfo',
    'FactReconciler',
    'ReconciliationResult',
    'SignAnalyzer',
    'SignCheck',
    'IdentityValidator',
    'IdentityCheck',
    # Industry detection
    'IndustryDetector',
    'IndustryRegistry',
    # Database operations
    'DatabaseChecker',
    # Data preparation
    'DataPreparer',
    # Debug/Reporting
    'DebugReporter',
    'ComponentDebugInfo',
    'ProcessState',
]
