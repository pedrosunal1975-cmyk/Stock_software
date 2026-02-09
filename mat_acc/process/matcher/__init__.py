# Path: mat_acc/process/matcher/__init__.py
"""
Matching Engine - Dynamic Concept Matching

The matching engine is the heart of mat_acc. It dynamically identifies
financial concepts in XBRL filings by matching against characteristic-based
definitions rather than hardcoded concept names.

Core Components:
    - MatchingCoordinator: Main orchestrator
    - Evaluators: Rule evaluation (labels, hierarchy, calculations)
    - Scoring: Score aggregation and confidence calculation
    - Models: Data structures for matches and resolutions

Key Principle:
    Concepts are defined by their CHARACTERISTICS, not their names.
    This enables market-agnostic matching across US-GAAP, IFRS, and others.

Example:
    from process.matcher import MatchingCoordinator

    coordinator = MatchingCoordinator()
    resolution = coordinator.resolve_all(concept_index, filing_id="sec/APPLE/10-K")

    # resolution maps component_id -> matched concept
    # e.g., {"current_assets": "us-gaap:AssetsCurrent"}
"""

from .engine import MatchingCoordinator, ComponentLoader
from .models import (
    ComponentDefinition,
    MatchResult,
    ResolutionMap,
    ConceptMetadata,
    ConceptIndex,
    Confidence,
    MatchStatus,
)

__all__ = [
    'MatchingCoordinator',
    'ComponentLoader',
    'ComponentDefinition',
    'MatchResult',
    'ResolutionMap',
    'ConceptMetadata',
    'ConceptIndex',
    'Confidence',
    'MatchStatus',
]
