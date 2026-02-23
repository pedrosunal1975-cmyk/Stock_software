# Path: mat_acc/process/matcher/engine/component_parser.py
"""
Component Parser

Standalone functions for parsing YAML data into
ComponentDefinition models. Used by ComponentLoader.
"""

from pathlib import Path

from ..models.component_definition import (
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
    AlternativeFormula,
    Validation,
    RelationshipCheck,
    TypicalRange,
    BalanceType,
    PeriodType,
    DataType,
    Category,
    MatchType,
    HierarchyRuleType,
    CalculationRuleType,
    TiebreakerType,
    RelationType,
    ExpectedSign,
)


def parse_enum(value, enum_class):
    """Parse string value to enum, None if value is None."""
    if value is None:
        return None
    if isinstance(value, enum_class):
        return value
    return enum_class(value)


def parse_component(
    data: dict, source_file: Path,
) -> ComponentDefinition:
    """Parse raw YAML data into ComponentDefinition."""
    chars_data = data.get('characteristics', {})
    characteristics = Characteristics(
        balance_type=parse_enum(
            chars_data.get('balance_type'), BalanceType,
        ),
        period_type=parse_enum(
            chars_data.get('period_type'), PeriodType,
        ),
        is_monetary=chars_data.get('is_monetary', True),
        is_abstract=chars_data.get('is_abstract', False),
        data_type=parse_enum(
            chars_data.get('data_type', 'monetary'),
            DataType,
        ),
    )

    rules_data = data.get('matching_rules', {})
    matching_rules = parse_matching_rules(rules_data)

    scoring_data = data.get('scoring', {})
    scoring = parse_scoring(scoring_data)

    comp_data = data.get('composition', {})
    composition = parse_composition(comp_data)

    val_data = data.get('validation', {})
    validation = parse_validation(val_data)

    return ComponentDefinition(
        component_id=data['component_id'],
        display_name=data['display_name'],
        description=data.get('description'),
        category=parse_enum(data['category'], Category),
        subcategory=data.get('subcategory'),
        characteristics=characteristics,
        matching_rules=matching_rules,
        scoring=scoring,
        composition=composition,
        validation=validation,
    )


def parse_matching_rules(data: dict) -> MatchingRules:
    """Parse matching rules section from YAML."""
    label_rules = []
    for rule in data.get('label_rules', []):
        label_rules.append(LabelRule(
            patterns=rule['patterns'],
            match_type=parse_enum(
                rule.get('match_type', 'contains'),
                MatchType,
            ),
            case_sensitive=rule.get(
                'case_sensitive', False,
            ),
            weight=rule['weight'],
        ))

    hierarchy_rules = []
    for rule in data.get('hierarchy_rules', []):
        hierarchy_rules.append(HierarchyRule(
            rule_type=parse_enum(
                rule['rule_type'], HierarchyRuleType,
            ),
            pattern=rule.get('pattern'),
            weight=rule['weight'],
        ))

    calculation_rules = []
    for rule in data.get('calculation_rules', []):
        calculation_rules.append(CalculationRule(
            rule_type=parse_enum(
                rule['rule_type'], CalculationRuleType,
            ),
            pattern=rule.get('pattern'),
            patterns=rule.get('patterns'),
            min_matches=rule.get('min_matches', 1),
            weight=rule['weight'],
        ))

    definition_rules = []
    for rule in data.get('definition_rules', []):
        definition_rules.append(DefinitionRule(
            keywords=rule['keywords'],
            all_required=rule.get(
                'all_required', False,
            ),
            weight=rule['weight'],
        ))

    reference_rules = []
    for rule in data.get('reference_rules', []):
        reference_rules.append(ReferenceRule(
            standard=rule['standard'],
            section=rule['section'],
            weight=rule['weight'],
        ))

    local_name_rules = []
    for rule in data.get('local_name_rules', []):
        local_name_rules.append(LocalNameRule(
            patterns=rule['patterns'],
            match_type=parse_enum(
                rule.get('match_type', 'contains'),
                MatchType,
            ),
            weight=rule['weight'],
        ))

    return MatchingRules(
        label_rules=label_rules,
        hierarchy_rules=hierarchy_rules,
        calculation_rules=calculation_rules,
        definition_rules=definition_rules,
        reference_rules=reference_rules,
        local_name_rules=local_name_rules,
    )


def parse_scoring(data: dict) -> ScoringConfig:
    """Parse scoring configuration from YAML."""
    conf_data = data.get('confidence_levels', {})
    confidence_levels = ConfidenceLevels(
        high=conf_data.get('high', 35),
        medium=conf_data.get('medium', 25),
        low=conf_data.get('low', 15),
    )

    reject_conditions = []
    for cond in data.get('reject_if', []):
        reject_conditions.append(RejectionCondition(
            condition=cond['condition'],
            pattern=cond['pattern'],
        ))

    return ScoringConfig(
        min_score=data.get('min_score', 15),
        confidence_levels=confidence_levels,
        tiebreaker=parse_enum(
            data.get(
                'tiebreaker', 'highest_in_hierarchy',
            ),
            TiebreakerType,
        ),
        reject_if=reject_conditions,
    )


def parse_composition(data: dict) -> Composition:
    """Parse composition section from YAML."""
    alternatives = []
    for alt in data.get('alternatives', []):
        alternatives.append(AlternativeFormula(
            components=alt['components'],
            formula=alt['formula'],
        ))

    return Composition(
        is_composite=data.get('is_composite', False),
        components=data.get('components', []),
        formula=data.get('formula'),
        alternatives=alternatives,
    )


def parse_validation(data: dict) -> Validation:
    """Parse validation section from YAML."""
    relationships = []
    for rel in data.get('relationships', []):
        relationships.append(RelationshipCheck(
            other=rel['other'],
            relation=parse_enum(
                rel['relation'], RelationType,
            ),
        ))

    typical_range = None
    range_data = data.get('typical_range')
    if range_data:
        typical_range = TypicalRange(
            min_value=range_data.get('min'),
            max_value=range_data.get('max'),
        )

    return Validation(
        expected_sign=parse_enum(
            data.get('expected_sign', 'either'),
            ExpectedSign,
        ),
        typical_range=typical_range,
        relationships=relationships,
        required_for=data.get('required_for', []),
    )


__all__ = [
    'parse_component',
    'parse_matching_rules',
    'parse_scoring',
    'parse_composition',
    'parse_validation',
    'parse_enum',
]
