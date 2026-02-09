# Path: mat_acc/process/matcher/evaluators/calculation_evaluator.py
"""
Calculation Evaluator

Evaluates calculation matching rules based on a concept's position
in the calculation linkbase (parent-child relationships with weights).
"""

from typing import Any, Optional

from .base_evaluator import BaseEvaluator, EvaluationResult
from ..models.concept_metadata import ConceptMetadata, ConceptIndex
from ..models.component_definition import CalculationRule, CalculationRuleType


class CalculationEvaluator(BaseEvaluator):
    """
    Evaluates calculation relationship rules.

    Rule types:
    - contributes_to: Concept is a child of (contributes to) another
    - parent_of: Concept is a parent of (sum of) other concepts
    - has_children: Concept has specific children in calculation
    - weight_sign: Concept has positive or negative weight

    The calculation linkbase shows mathematical relationships:
    - Parent = sum of (weight * child) for all children
    - Weight is typically 1.0 (add) or -1.0 (subtract)

    Example:
        evaluator = CalculationEvaluator()
        result = evaluator.evaluate(
            concept=concept,
            rules=[
                CalculationRule(
                    rule_type=CalculationRuleType.HAS_CHILDREN,
                    patterns=["*Cash*", "*Receivable*", "*Inventory*"],
                    min_matches=2,
                    weight=10
                )
            ],
            context={'concept_index': index}
        )
    """

    @property
    def evaluator_type(self) -> str:
        return "calculation"

    def evaluate(
        self,
        concept: ConceptMetadata,
        rules: list[CalculationRule],
        context: Optional[dict] = None
    ) -> EvaluationResult:
        """
        Evaluate calculation rules against concept relationships.

        Args:
            concept: Concept with calculation relationship info
            rules: List of CalculationRule objects
            context: Optional context with 'concept_index'

        Returns:
            EvaluationResult with total score and matched rules
        """
        total_score = 0
        matched_rules = []

        concept_index: Optional[ConceptIndex] = None
        if context:
            concept_index = context.get('concept_index')

        for rule in rules:
            matched = False
            match_details = {}

            if rule.rule_type == CalculationRuleType.CONTRIBUTES_TO:
                matched, match_details = self._check_contributes_to(
                    concept, rule.pattern
                )

            elif rule.rule_type == CalculationRuleType.PARENT_OF:
                matched, match_details = self._check_parent_of(
                    concept, rule.patterns or [rule.pattern]
                )

            elif rule.rule_type == CalculationRuleType.HAS_CHILDREN:
                matched, match_details = self._check_has_children(
                    concept,
                    rule.patterns or [],
                    rule.min_matches,
                    concept_index
                )

            elif rule.rule_type == CalculationRuleType.WEIGHT_SIGN:
                matched, match_details = self._check_weight_sign(
                    concept, rule.pattern
                )

            if matched:
                total_score += rule.weight
                matched_rules.append({
                    'rule_type': rule.rule_type.value,
                    'pattern': rule.pattern,
                    'patterns': rule.patterns,
                    'weight': rule.weight,
                    **match_details
                })

                self.logger.debug(
                    f"Calculation match: {rule.rule_type.value} for "
                    f"{concept.qname}, weight={rule.weight}"
                )

        return EvaluationResult(
            score=total_score,
            matched_rules=matched_rules,
            evaluator_type=self.evaluator_type
        )

    def _check_contributes_to(
        self,
        concept: ConceptMetadata,
        pattern: str
    ) -> tuple[bool, dict]:
        """Check if concept contributes to (is child of) a parent matching pattern."""
        if not concept.calculation_parents:
            return False, {}

        for parent_info in concept.calculation_parents:
            parent_qname = parent_info.get('qname', '')

            # Extract local name
            parent_local = parent_qname.split(':')[-1] if ':' in parent_qname else parent_qname
            parent_local = parent_local.replace('_', ':').split(':')[-1]

            if self._pattern_matches(parent_local, pattern):
                return True, {
                    'matched_parent': parent_qname,
                    'weight': parent_info.get('weight', 1.0),
                }

            # Also try full QName
            if self._pattern_matches(parent_qname, pattern):
                return True, {
                    'matched_parent': parent_qname,
                    'weight': parent_info.get('weight', 1.0),
                }

        return False, {}

    def _check_parent_of(
        self,
        concept: ConceptMetadata,
        patterns: list[str]
    ) -> tuple[bool, dict]:
        """Check if concept is parent of any child matching patterns."""
        if not concept.calculation_children:
            return False, {}

        for pattern in patterns:
            for child_info in concept.calculation_children:
                child_qname = child_info.get('qname', '')

                # Extract local name
                child_local = child_qname.split(':')[-1] if ':' in child_qname else child_qname

                if self._pattern_matches(child_local, pattern):
                    return True, {
                        'matched_child': child_qname,
                        'pattern': pattern,
                    }

        return False, {}

    def _check_has_children(
        self,
        concept: ConceptMetadata,
        patterns: list[str],
        min_matches: int,
        concept_index: Optional[ConceptIndex]
    ) -> tuple[bool, dict]:
        """
        Check if concept has at least min_matches children matching patterns.

        This is useful for identifying totals like "Current Assets" which
        should have children like Cash, Receivables, Inventory.
        """
        if not concept.calculation_children:
            return False, {}

        matched_children = []
        matched_patterns = set()

        for pattern in patterns:
            for child_info in concept.calculation_children:
                child_qname = child_info.get('qname', '')

                # Extract local name
                child_local = child_qname.split(':')[-1] if ':' in child_qname else child_qname

                if self._pattern_matches(child_local, pattern):
                    if child_qname not in matched_children:
                        matched_children.append(child_qname)
                        matched_patterns.add(pattern)

        if len(matched_children) >= min_matches:
            return True, {
                'required': min_matches,
                'found': len(matched_children),
                'matched_children': matched_children,
                'matched_patterns': list(matched_patterns),
            }

        return False, {}

    def _check_weight_sign(
        self,
        concept: ConceptMetadata,
        pattern: str
    ) -> tuple[bool, dict]:
        """
        Check if concept's weight in calculation has specific sign.

        Pattern:
        - "positive": weight > 0 (typically 1.0, meaning add)
        - "negative": weight < 0 (typically -1.0, meaning subtract)
        """
        if not concept.calculation_parents:
            return False, {}

        for parent_info in concept.calculation_parents:
            weight = parent_info.get('weight', 1.0)

            if pattern == "positive" and weight > 0:
                return True, {
                    'parent': parent_info.get('qname'),
                    'weight': weight,
                }
            elif pattern == "negative" and weight < 0:
                return True, {
                    'parent': parent_info.get('qname'),
                    'weight': weight,
                }

        return False, {}


__all__ = ['CalculationEvaluator']
