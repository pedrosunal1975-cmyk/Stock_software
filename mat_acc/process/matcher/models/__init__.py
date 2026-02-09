# Path: mat_acc/process/matcher/models/__init__.py
"""
Matcher Models

Data models for the matching engine:
- ComponentDefinition: Parsed component definition
- MatchResult: Result of matching a single component
- ResolutionMap: Complete mapping for a filing
- ConceptMetadata: Concept attributes for matching
"""

from .component_definition import (
    ComponentDefinition,
    Characteristics,
    MatchingRules,
    LabelRule,
    HierarchyRule,
    CalculationRule,
    DefinitionRule,
    ReferenceRule,
    LocalNameRule,
    ScoringConfig,
    ConfidenceLevels,
    RejectionCondition,
    Composition,
    Validation,
    BalanceType,
    PeriodType,
    DataType,
    Category,
)

from .match_result import (
    MatchResult,
    ScoredMatch,
    RuleScore,
    MatchStatus,
    Confidence,
)

from .resolution_map import (
    ResolutionMap,
    ResolvedComponent,
    CompositeResolution,
)

from .concept_metadata import (
    ConceptMetadata,
    ConceptIndex,
)

__all__ = [
    # Component Definition
    'ComponentDefinition',
    'Characteristics',
    'MatchingRules',
    'LabelRule',
    'HierarchyRule',
    'CalculationRule',
    'DefinitionRule',
    'ReferenceRule',
    'LocalNameRule',
    'ScoringConfig',
    'ConfidenceLevels',
    'RejectionCondition',
    'Composition',
    'Validation',
    'BalanceType',
    'PeriodType',
    'DataType',
    'Category',
    # Match Result
    'MatchResult',
    'ScoredMatch',
    'RuleScore',
    'MatchStatus',
    'Confidence',
    # Resolution Map
    'ResolutionMap',
    'ResolvedComponent',
    'CompositeResolution',
    # Concept Metadata
    'ConceptMetadata',
    'ConceptIndex',
]
