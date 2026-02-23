# Path: mat_acc/process/matcher/engine/__init__.py
"""
Matching Engine Core

- MatchingCoordinator: Main orchestrator
- AtomicMatcher: Core matching engine
- ComponentLoader: Loads component definitions from YAML
- component_parser: YAML parsing functions
- candidate_filter: Candidate selection and filtering
"""

from .component_loader import ComponentLoader
from .coordinator import MatchingCoordinator

__all__ = [
    'ComponentLoader',
    'MatchingCoordinator',
]
