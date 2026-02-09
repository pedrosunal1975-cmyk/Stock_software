# Path: mat_acc/process/matcher/evaluators/__init__.py
"""
Rule Evaluators

Each evaluator handles one type of matching rule and returns
a score contribution based on how well a concept matches.

Evaluators:
- LabelEvaluator: Match against concept labels
- HierarchyEvaluator: Match based on hierarchy position
- CalculationEvaluator: Match based on calculation relationships
- DefinitionEvaluator: Match against definition text
- ReferenceEvaluator: Match against accounting standard references
- LocalNameEvaluator: Match against concept local name
"""

from .base_evaluator import BaseEvaluator, EvaluationResult
from .label_evaluator import LabelEvaluator
from .hierarchy_evaluator import HierarchyEvaluator
from .calculation_evaluator import CalculationEvaluator
from .definition_evaluator import DefinitionEvaluator

__all__ = [
    'BaseEvaluator',
    'EvaluationResult',
    'LabelEvaluator',
    'HierarchyEvaluator',
    'CalculationEvaluator',
    'DefinitionEvaluator',
]
