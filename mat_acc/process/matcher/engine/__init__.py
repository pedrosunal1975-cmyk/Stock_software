# Path: mat_acc/process/matcher/engine/__init__.py
"""
Matching Engine Core

Core components of the matching engine:
- MatchingCoordinator: Main orchestrator
- ComponentLoader: Loads component definitions from YAML
- ConceptIndexer: Builds indexes for fast lookup
- ResolutionCache: Caches resolution results
"""

from .component_loader import ComponentLoader
from .coordinator import MatchingCoordinator

__all__ = [
    'ComponentLoader',
    'MatchingCoordinator',
]
