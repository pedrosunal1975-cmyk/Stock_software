# Path: mat_acc/process/matcher/scoring/__init__.py
"""
Scoring Module

Components for aggregating rule scores and determining confidence:
- ScoreAggregator: Combines scores from multiple evaluators
- ConfidenceCalculator: Determines confidence level from score
- Tiebreaker: Resolves ties between equal-scoring matches
"""

from .aggregator import ScoreAggregator
from .confidence import ConfidenceCalculator
from .tiebreaker import Tiebreaker

__all__ = [
    'ScoreAggregator',
    'ConfidenceCalculator',
    'Tiebreaker',
]
