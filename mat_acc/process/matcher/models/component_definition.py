# Path: mat_acc/process/matcher/models/component_definition.py
"""
Component Definition Model

Pydantic models representing component definitions loaded from YAML files.
These define what characteristics identify a financial concept.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class BalanceType(str, Enum):
    """XBRL balance type attribute."""
    DEBIT = "debit"
    CREDIT = "credit"
    NONE = "none"


class PeriodType(str, Enum):
    """XBRL period type attribute."""
    INSTANT = "instant"
    DURATION = "duration"


class DataType(str, Enum):
    """Expected data type for the component."""
    MONETARY = "monetary"
    SHARES = "shares"
    PURE = "pure"
    PER_SHARE = "per_share"


class Category(str, Enum):
    """Primary statement category."""
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW = "cash_flow"
    EQUITY = "equity"
    PER_SHARE = "per_share"
    MARKET_DATA = "market_data"


class MatchType(str, Enum):
    """How to match patterns against text."""
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    EXACT = "exact"
    REGEX = "regex"


class HierarchyRuleType(str, Enum):
    """Type of hierarchy matching rule."""
    PARENT_MATCHES = "parent_matches"
    CHILD_OF_ROOT = "child_of_root"
    HAS_SIBLINGS = "has_siblings"
    DEPTH_LEVEL = "depth_level"
    POSITION_ORDINAL = "position_ordinal"


class CalculationRuleType(str, Enum):
    """Type of calculation matching rule."""
    CONTRIBUTES_TO = "contributes_to"
    PARENT_OF = "parent_of"
    HAS_CHILDREN = "has_children"
    WEIGHT_SIGN = "weight_sign"


class TiebreakerType(str, Enum):
    """How to resolve ties between equal scores."""
    HIGHEST_IN_HIERARCHY = "highest_in_hierarchy"
    MOST_CHILDREN = "most_children"
    EXACT_LABEL_MATCH = "exact_label_match"
    FIRST_IN_PRESENTATION = "first_in_presentation"


class RelationType(str, Enum):
    """Expected relationship with another component."""
    LESS_THAN = "less_than"
    GREATER_THAN = "greater_than"
    APPROXIMATELY_EQUAL = "approximately_equal"


class ExpectedSign(str, Enum):
    """Expected sign of the value."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    EITHER = "either"


# =============================================================================
# MATCHING RULES
# =============================================================================

class LabelRule(BaseModel):
    """Rule for matching against concept labels."""
    patterns: list[str] = Field(
        description="List of patterns to match against labels"
    )
    match_type: MatchType = Field(
        default=MatchType.CONTAINS,
        description="How to match patterns"
    )
    case_sensitive: bool = Field(
        default=False,
        description="Whether matching is case-sensitive"
    )
    weight: int = Field(
        ge=1, le=25,
        description="Score contribution if matched (1-25)"
    )


class HierarchyRule(BaseModel):
    """Rule for matching based on hierarchy position."""
    rule_type: HierarchyRuleType = Field(
        description="Type of hierarchy rule"
    )
    pattern: Optional[str] = Field(
        default=None,
        description="Pattern to match (supports wildcards)"
    )
    weight: int = Field(
        ge=1, le=15,
        description="Score contribution if matched (1-15)"
    )


class CalculationRule(BaseModel):
    """Rule for matching based on calculation relationships."""
    rule_type: CalculationRuleType = Field(
        description="Type of calculation rule"
    )
    pattern: Optional[str] = Field(
        default=None,
        description="Pattern to match"
    )
    patterns: Optional[list[str]] = Field(
        default=None,
        description="Multiple patterns (for has_children)"
    )
    min_matches: int = Field(
        default=1,
        description="Minimum matches required (for has_children)"
    )
    weight: int = Field(
        ge=1, le=15,
        description="Score contribution if matched (1-15)"
    )


class DefinitionRule(BaseModel):
    """Rule for matching against definition text."""
    keywords: list[str] = Field(
        description="Keywords that should appear in definition"
    )
    all_required: bool = Field(
        default=False,
        description="Whether all keywords must match"
    )
    weight: int = Field(
        ge=1, le=10,
        description="Score contribution if matched (1-10)"
    )


class ReferenceRule(BaseModel):
    """Rule for matching against accounting standard references."""
    standard: str = Field(
        description="Standard name (ASC, IAS, IFRS)"
    )
    section: str = Field(
        description="Section reference (e.g., 210-10-45)"
    )
    weight: int = Field(
        ge=1, le=15,
        description="Score contribution if matched (1-15)"
    )


class LocalNameRule(BaseModel):
    """Rule for matching against concept local name (fallback)."""
    patterns: list[str] = Field(
        description="Patterns for local name matching"
    )
    match_type: MatchType = Field(
        default=MatchType.CONTAINS,
        description="How to match patterns"
    )
    weight: int = Field(
        ge=1, le=5,
        description="Score contribution if matched (1-5, low weight)"
    )


class MatchingRules(BaseModel):
    """Collection of all matching rules for a component."""
    label_rules: list[LabelRule] = Field(
        default_factory=list,
        description="Label pattern matching rules"
    )
    hierarchy_rules: list[HierarchyRule] = Field(
        default_factory=list,
        description="Hierarchy position matching rules"
    )
    calculation_rules: list[CalculationRule] = Field(
        default_factory=list,
        description="Calculation relationship matching rules"
    )
    definition_rules: list[DefinitionRule] = Field(
        default_factory=list,
        description="Definition keyword matching rules"
    )
    reference_rules: list[ReferenceRule] = Field(
        default_factory=list,
        description="Accounting reference matching rules"
    )
    local_name_rules: list[LocalNameRule] = Field(
        default_factory=list,
        description="Local name matching rules (fallback)"
    )


# =============================================================================
# SCORING CONFIGURATION
# =============================================================================

class ConfidenceLevels(BaseModel):
    """Thresholds for confidence levels."""
    high: int = Field(
        ge=1,
        description="Score threshold for high confidence"
    )
    medium: int = Field(
        ge=1,
        description="Score threshold for medium confidence"
    )
    low: int = Field(
        ge=1,
        description="Score threshold for low confidence (= min_score)"
    )


class RejectionCondition(BaseModel):
    """Condition that causes a match to be rejected."""
    condition: str = Field(
        description="Human-readable description of rejection condition"
    )
    pattern: str = Field(
        description="Pattern that triggers rejection"
    )


class ScoringConfig(BaseModel):
    """Configuration for scoring and match acceptance."""
    min_score: int = Field(
        ge=1,
        description="Minimum total score to accept a match"
    )
    confidence_levels: ConfidenceLevels = Field(
        description="Thresholds for confidence rating"
    )
    tiebreaker: TiebreakerType = Field(
        default=TiebreakerType.HIGHEST_IN_HIERARCHY,
        description="How to choose among equal scores"
    )
    reject_if: list[RejectionCondition] = Field(
        default_factory=list,
        description="Conditions that reject a match"
    )


# =============================================================================
# CHARACTERISTICS
# =============================================================================

class Characteristics(BaseModel):
    """Intrinsic properties of the concept."""
    balance_type: Optional[BalanceType] = Field(
        default=None,
        description="XBRL balance attribute (debit/credit)"
    )
    period_type: Optional[PeriodType] = Field(
        default=None,
        description="XBRL period type (instant/duration)"
    )
    is_monetary: bool = Field(
        default=True,
        description="Whether values are monetary"
    )
    is_abstract: bool = Field(
        default=False,
        description="Whether concept can have values"
    )
    data_type: DataType = Field(
        default=DataType.MONETARY,
        description="Expected data type"
    )


# =============================================================================
# COMPOSITION (for derived components)
# =============================================================================

class AlternativeFormula(BaseModel):
    """Alternative calculation path for a composite component."""
    components: list[str] = Field(
        description="Component IDs required for this formula"
    )
    formula: str = Field(
        description="How to combine components"
    )


class Composition(BaseModel):
    """Defines how composite components are calculated."""
    is_composite: bool = Field(
        default=False,
        description="Whether this is calculated from other components"
    )
    components: list[str] = Field(
        default_factory=list,
        description="Component IDs for primary formula"
    )
    formula: Optional[str] = Field(
        default=None,
        description="Primary formula (e.g., 'a - b', 'a + b')"
    )
    alternatives: list[AlternativeFormula] = Field(
        default_factory=list,
        description="Alternative calculation paths"
    )


# =============================================================================
# VALIDATION
# =============================================================================

class RelationshipCheck(BaseModel):
    """Expected relationship with another component."""
    other: str = Field(
        description="Other component ID"
    )
    relation: RelationType = Field(
        description="Expected relationship"
    )


class TypicalRange(BaseModel):
    """Reasonable value bounds for sanity checking."""
    min_value: Optional[float] = Field(
        default=None,
        description="Values below this trigger warning"
    )
    max_value: Optional[float] = Field(
        default=None,
        description="Values above this trigger warning"
    )


class Validation(BaseModel):
    """Sanity checks for matched values."""
    expected_sign: ExpectedSign = Field(
        default=ExpectedSign.EITHER,
        description="Expected sign of value"
    )
    typical_range: Optional[TypicalRange] = Field(
        default=None,
        description="Reasonable value bounds"
    )
    relationships: list[RelationshipCheck] = Field(
        default_factory=list,
        description="Expected relationships with other components"
    )
    required_for: list[str] = Field(
        default_factory=list,
        description="Ratio IDs that require this component"
    )


# =============================================================================
# COMPONENT DEFINITION (main model)
# =============================================================================

class ComponentDefinition(BaseModel):
    """
    Complete definition of a financial component.

    This is the core data structure that defines how to identify
    a financial concept in any XBRL filing.

    Example:
        component = ComponentDefinition(
            component_id="current_assets",
            display_name="Current Assets",
            category=Category.BALANCE_SHEET,
            subcategory="assets",
            characteristics=Characteristics(
                balance_type=BalanceType.DEBIT,
                period_type=PeriodType.INSTANT,
            ),
            matching_rules=MatchingRules(
                label_rules=[
                    LabelRule(
                        patterns=["current assets"],
                        weight=15
                    )
                ]
            ),
            scoring=ScoringConfig(
                min_score=20,
                confidence_levels=ConfidenceLevels(
                    high=35, medium=27, low=20
                )
            )
        )
    """

    # Identity
    component_id: str = Field(
        description="Unique identifier (snake_case)"
    )
    display_name: str = Field(
        description="Human-readable name"
    )
    description: Optional[str] = Field(
        default=None,
        description="What this component represents"
    )

    # Classification
    category: Category = Field(
        description="Primary categorization"
    )
    subcategory: Optional[str] = Field(
        default=None,
        description="Secondary categorization"
    )

    # Intrinsic properties
    characteristics: Characteristics = Field(
        default_factory=Characteristics,
        description="Intrinsic properties of the concept"
    )

    # Matching rules
    matching_rules: MatchingRules = Field(
        default_factory=MatchingRules,
        description="Rules for identifying this concept"
    )

    # Scoring configuration
    scoring: ScoringConfig = Field(
        description="Scoring and acceptance configuration"
    )

    # Composition (for derived components)
    composition: Composition = Field(
        default_factory=Composition,
        description="How composite components are calculated"
    )

    # Validation
    validation: Validation = Field(
        default_factory=Validation,
        description="Sanity checks for matched values"
    )

    @property
    def is_composite(self) -> bool:
        """Check if this is a composite (calculated) component."""
        return self.composition.is_composite

    @property
    def is_atomic(self) -> bool:
        """Check if this is an atomic (directly matched) component."""
        return not self.composition.is_composite

    def get_max_possible_score(self) -> int:
        """Calculate maximum possible score from all rules."""
        total = 0
        rules = self.matching_rules

        for rule in rules.label_rules:
            total += rule.weight
        for rule in rules.hierarchy_rules:
            total += rule.weight
        for rule in rules.calculation_rules:
            total += rule.weight
        for rule in rules.definition_rules:
            total += rule.weight
        for rule in rules.reference_rules:
            total += rule.weight
        for rule in rules.local_name_rules:
            total += rule.weight

        return total

    class Config:
        """Pydantic configuration."""
        use_enum_values = False  # Keep enums as enum objects


__all__ = [
    # Enums
    'BalanceType',
    'PeriodType',
    'DataType',
    'Category',
    'MatchType',
    'HierarchyRuleType',
    'CalculationRuleType',
    'TiebreakerType',
    'RelationType',
    'ExpectedSign',
    # Rule models
    'LabelRule',
    'HierarchyRule',
    'CalculationRule',
    'DefinitionRule',
    'ReferenceRule',
    'LocalNameRule',
    'MatchingRules',
    # Scoring
    'ConfidenceLevels',
    'RejectionCondition',
    'ScoringConfig',
    # Other models
    'Characteristics',
    'AlternativeFormula',
    'Composition',
    'RelationshipCheck',
    'TypicalRange',
    'Validation',
    # Main model
    'ComponentDefinition',
]
