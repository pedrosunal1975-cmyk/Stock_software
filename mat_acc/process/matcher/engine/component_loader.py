# Path: mat_acc/process/matcher/engine/component_loader.py
"""
Component Loader

Loads component definitions from YAML files in the dictionary directory.
Validates definitions against the schema and converts to Pydantic models.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

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


class ComponentLoader:
    """
    Loads component definitions from YAML files.

    Scans the dictionary/components/ directory for YAML files and
    parses them into ComponentDefinition objects.

    Example:
        loader = ComponentLoader()
        components = loader.load_all()

        # Get specific component
        current_assets = components.get('current_assets')

        # Load single file
        component = loader.load_file(Path('dictionary/components/balance_sheet/assets/current_assets.yaml'))
    """

    def __init__(self, dictionary_path: Optional[Path] = None):
        """
        Initialize component loader.

        Args:
            dictionary_path: Path to dictionary directory.
                           Defaults to mat_acc_files/dictionary/
        """
        self.logger = logging.getLogger('matcher.component_loader')

        if dictionary_path is None:
            # Default to dictionary directory relative to this file
            self.dictionary_path = Path(__file__).parent.parent.parent.parent / 'dictionary'
        else:
            self.dictionary_path = Path(dictionary_path)

        self.components_path = self.dictionary_path / 'components'
        self.formulas_path = self.dictionary_path / 'formulas'

        self._components_cache: Optional[dict[str, ComponentDefinition]] = None

    def load_all(self, use_cache: bool = True) -> dict[str, ComponentDefinition]:
        """
        Load all component definitions from the dictionary.

        Args:
            use_cache: Whether to use cached results

        Returns:
            Dictionary mapping component_id to ComponentDefinition
        """
        if use_cache and self._components_cache is not None:
            return self._components_cache

        components = {}

        if not self.components_path.exists():
            self.logger.warning(
                f"Components directory not found: {self.components_path}"
            )
            return components

        # Find all YAML files
        yaml_files = list(self.components_path.rglob('*.yaml'))
        yaml_files.extend(self.components_path.rglob('*.yml'))

        self.logger.info(f"Found {len(yaml_files)} component definition files")

        for yaml_file in yaml_files:
            try:
                component = self.load_file(yaml_file)
                if component:
                    if component.component_id in components:
                        self.logger.warning(
                            f"Duplicate component_id: {component.component_id} "
                            f"in {yaml_file}"
                        )
                    components[component.component_id] = component
            except Exception as e:
                self.logger.error(
                    f"Failed to load component from {yaml_file}: {e}"
                )

        self.logger.info(f"Loaded {len(components)} component definitions")
        self._components_cache = components
        return components

    def load_file(self, file_path: Path) -> Optional[ComponentDefinition]:
        """
        Load a single component definition from a YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            ComponentDefinition or None if loading fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if data is None:
                self.logger.warning(f"Empty file: {file_path}")
                return None

            return self._parse_component(data, file_path)

        except yaml.YAMLError as e:
            self.logger.error(f"YAML parse error in {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading {file_path}: {e}")
            raise

    def _parse_component(
        self,
        data: dict,
        source_file: Path
    ) -> ComponentDefinition:
        """
        Parse raw YAML data into ComponentDefinition.

        Args:
            data: Parsed YAML dictionary
            source_file: Source file path (for error messages)

        Returns:
            ComponentDefinition object
        """
        # Parse characteristics
        chars_data = data.get('characteristics', {})
        characteristics = Characteristics(
            balance_type=self._parse_enum(
                chars_data.get('balance_type'),
                BalanceType
            ),
            period_type=self._parse_enum(
                chars_data.get('period_type'),
                PeriodType
            ),
            is_monetary=chars_data.get('is_monetary', True),
            is_abstract=chars_data.get('is_abstract', False),
            data_type=self._parse_enum(
                chars_data.get('data_type', 'monetary'),
                DataType
            ),
        )

        # Parse matching rules
        rules_data = data.get('matching_rules', {})
        matching_rules = self._parse_matching_rules(rules_data)

        # Parse scoring config
        scoring_data = data.get('scoring', {})
        scoring = self._parse_scoring(scoring_data)

        # Parse composition
        comp_data = data.get('composition', {})
        composition = self._parse_composition(comp_data)

        # Parse validation
        val_data = data.get('validation', {})
        validation = self._parse_validation(val_data)

        # Create component definition
        return ComponentDefinition(
            component_id=data['component_id'],
            display_name=data['display_name'],
            description=data.get('description'),
            category=self._parse_enum(data['category'], Category),
            subcategory=data.get('subcategory'),
            characteristics=characteristics,
            matching_rules=matching_rules,
            scoring=scoring,
            composition=composition,
            validation=validation,
        )

    def _parse_matching_rules(self, data: dict) -> MatchingRules:
        """Parse matching rules section."""
        label_rules = []
        for rule in data.get('label_rules', []):
            label_rules.append(LabelRule(
                patterns=rule['patterns'],
                match_type=self._parse_enum(
                    rule.get('match_type', 'contains'),
                    MatchType
                ),
                case_sensitive=rule.get('case_sensitive', False),
                weight=rule['weight'],
            ))

        hierarchy_rules = []
        for rule in data.get('hierarchy_rules', []):
            hierarchy_rules.append(HierarchyRule(
                rule_type=self._parse_enum(rule['rule_type'], HierarchyRuleType),
                pattern=rule.get('pattern'),
                weight=rule['weight'],
            ))

        calculation_rules = []
        for rule in data.get('calculation_rules', []):
            calculation_rules.append(CalculationRule(
                rule_type=self._parse_enum(rule['rule_type'], CalculationRuleType),
                pattern=rule.get('pattern'),
                patterns=rule.get('patterns'),
                min_matches=rule.get('min_matches', 1),
                weight=rule['weight'],
            ))

        definition_rules = []
        for rule in data.get('definition_rules', []):
            definition_rules.append(DefinitionRule(
                keywords=rule['keywords'],
                all_required=rule.get('all_required', False),
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
                match_type=self._parse_enum(
                    rule.get('match_type', 'contains'),
                    MatchType
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

    def _parse_scoring(self, data: dict) -> ScoringConfig:
        """Parse scoring configuration."""
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
            tiebreaker=self._parse_enum(
                data.get('tiebreaker', 'highest_in_hierarchy'),
                TiebreakerType
            ),
            reject_if=reject_conditions,
        )

    def _parse_composition(self, data: dict) -> Composition:
        """Parse composition section."""
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

    def _parse_validation(self, data: dict) -> Validation:
        """Parse validation section."""
        relationships = []
        for rel in data.get('relationships', []):
            relationships.append(RelationshipCheck(
                other=rel['other'],
                relation=self._parse_enum(rel['relation'], RelationType),
            ))

        typical_range = None
        range_data = data.get('typical_range')
        if range_data:
            typical_range = TypicalRange(
                min_value=range_data.get('min'),
                max_value=range_data.get('max'),
            )

        return Validation(
            expected_sign=self._parse_enum(
                data.get('expected_sign', 'either'),
                ExpectedSign
            ),
            typical_range=typical_range,
            relationships=relationships,
            required_for=data.get('required_for', []),
        )

    def _parse_enum(self, value, enum_class):
        """Parse string value to enum, returning None if value is None."""
        if value is None:
            return None
        if isinstance(value, enum_class):
            return value
        return enum_class(value)

    def load_industry(self, industry: str) -> dict[str, ComponentDefinition]:
        """
        Load industry-specific component definitions.

        Industry components live under components/<industry>/
        (e.g., components/banking/). These are also included
        in load_all() via rglob, but this method allows loading
        only the industry-specific subset.

        Args:
            industry: Industry type (banking, insurance, reit)

        Returns:
            Dictionary mapping component_id to ComponentDefinition
        """
        industry_path = self.components_path / industry
        if not industry_path.exists():
            self.logger.info(f"No industry components for: {industry}")
            return {}

        components = {}
        yaml_files = list(industry_path.rglob('*.yaml'))
        yaml_files.extend(industry_path.rglob('*.yml'))

        for yaml_file in yaml_files:
            try:
                component = self.load_file(yaml_file)
                if component:
                    components[component.component_id] = component
            except Exception as e:
                self.logger.error(
                    f"Failed to load {yaml_file}: {e}"
                )

        self.logger.info(
            f"Loaded {len(components)} {industry} components"
        )
        return components

    def get_component(self, component_id: str) -> Optional[ComponentDefinition]:
        """
        Get a specific component by ID.

        Args:
            component_id: Component identifier

        Returns:
            ComponentDefinition or None
        """
        components = self.load_all()
        return components.get(component_id)

    def get_atomic_components(self) -> dict[str, ComponentDefinition]:
        """Get all atomic (non-composite) components."""
        components = self.load_all()
        return {
            cid: comp for cid, comp in components.items()
            if comp.is_atomic
        }

    def get_composite_components(self) -> dict[str, ComponentDefinition]:
        """Get all composite components."""
        components = self.load_all()
        return {
            cid: comp for cid, comp in components.items()
            if comp.is_composite
        }

    def get_components_by_category(
        self,
        category: Category
    ) -> dict[str, ComponentDefinition]:
        """Get components filtered by category."""
        components = self.load_all()
        return {
            cid: comp for cid, comp in components.items()
            if comp.category == category
        }

    def validate_all(self) -> list[str]:
        """
        Validate all component definitions.

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []
        components = self.load_all(use_cache=False)

        for cid, comp in components.items():
            # Check min_score is achievable
            max_score = comp.get_max_possible_score()
            if max_score < comp.scoring.min_score:
                errors.append(
                    f"{cid}: min_score ({comp.scoring.min_score}) > "
                    f"max possible score ({max_score})"
                )

            # Check confidence levels are ordered
            conf = comp.scoring.confidence_levels
            if not (conf.high > conf.medium >= conf.low):
                errors.append(
                    f"{cid}: confidence levels not properly ordered"
                )

            # Check composite components reference valid components
            if comp.is_composite:
                for child_id in comp.composition.components:
                    if child_id not in components and child_id != cid:
                        errors.append(
                            f"{cid}: references unknown component '{child_id}'"
                        )

            # Check validation relationships reference valid components
            for rel in comp.validation.relationships:
                if rel.other not in components:
                    errors.append(
                        f"{cid}: validation references unknown component "
                        f"'{rel.other}'"
                    )

        return errors

    def clear_cache(self) -> None:
        """Clear the components cache."""
        self._components_cache = None


__all__ = ['ComponentLoader']
