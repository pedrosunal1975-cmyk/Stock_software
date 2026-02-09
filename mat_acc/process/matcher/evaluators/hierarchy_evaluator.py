# Path: mat_acc/process/matcher/evaluators/hierarchy_evaluator.py
"""
Hierarchy Evaluator

Evaluates hierarchy matching rules based on a concept's position
in the presentation linkbase hierarchy.
"""

from typing import Any, Optional

from .base_evaluator import BaseEvaluator, EvaluationResult
from ..models.concept_metadata import ConceptMetadata, ConceptIndex
from ..models.component_definition import HierarchyRule, HierarchyRuleType


class HierarchyEvaluator(BaseEvaluator):
    """
    Evaluates hierarchy position rules.

    Rule types:
    - parent_matches: Parent concept matches pattern
    - child_of_root: Direct child of statement root
    - has_siblings: Has siblings matching patterns
    - depth_level: At specific hierarchy depth
    - position_ordinal: Position among siblings (first, last, etc.)

    Example:
        evaluator = HierarchyEvaluator()
        result = evaluator.evaluate(
            concept=concept,
            rules=[
                HierarchyRule(
                    rule_type=HierarchyRuleType.PARENT_MATCHES,
                    pattern="*Assets*Abstract*",
                    weight=8
                )
            ],
            context={'concept_index': index}
        )
    """

    @property
    def evaluator_type(self) -> str:
        return "hierarchy"

    def evaluate(
        self,
        concept: ConceptMetadata,
        rules: list[HierarchyRule],
        context: Optional[dict] = None
    ) -> EvaluationResult:
        """
        Evaluate hierarchy rules against concept position.

        Args:
            concept: Concept with hierarchy position info
            rules: List of HierarchyRule objects
            context: Must contain 'concept_index' for sibling lookups

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

            if rule.rule_type == HierarchyRuleType.PARENT_MATCHES:
                matched, match_details = self._check_parent_matches(
                    concept, rule.pattern
                )

            elif rule.rule_type == HierarchyRuleType.CHILD_OF_ROOT:
                matched, match_details = self._check_child_of_root(concept)

            elif rule.rule_type == HierarchyRuleType.HAS_SIBLINGS:
                matched, match_details = self._check_has_siblings(
                    concept, rule.pattern, concept_index
                )

            elif rule.rule_type == HierarchyRuleType.DEPTH_LEVEL:
                matched, match_details = self._check_depth_level(
                    concept, rule.pattern
                )

            elif rule.rule_type == HierarchyRuleType.POSITION_ORDINAL:
                matched, match_details = self._check_position_ordinal(
                    concept, rule.pattern, concept_index
                )

            if matched:
                total_score += rule.weight
                matched_rules.append({
                    'rule_type': rule.rule_type.value,
                    'pattern': rule.pattern,
                    'weight': rule.weight,
                    **match_details
                })

                self.logger.debug(
                    f"Hierarchy match: {rule.rule_type.value} for "
                    f"{concept.qname}, weight={rule.weight}"
                )

        return EvaluationResult(
            score=total_score,
            matched_rules=matched_rules,
            evaluator_type=self.evaluator_type
        )

    def _check_parent_matches(
        self,
        concept: ConceptMetadata,
        pattern: str
    ) -> tuple[bool, dict]:
        """Check if concept's parent matches pattern."""
        if not concept.presentation_parent:
            return False, {}

        parent = concept.presentation_parent

        # Extract local name from parent QName
        parent_local = parent.split(':')[-1] if ':' in parent else parent
        parent_local = parent_local.replace('_', ':').split(':')[-1]

        if self._pattern_matches(parent_local, pattern):
            return True, {
                'matched_parent': concept.presentation_parent,
                'parent_local_name': parent_local,
            }

        # Also try matching full QName
        if self._pattern_matches(parent, pattern):
            return True, {
                'matched_parent': concept.presentation_parent,
            }

        return False, {}

    def _check_child_of_root(
        self,
        concept: ConceptMetadata
    ) -> tuple[bool, dict]:
        """Check if concept is a direct child of root (level 1)."""
        if concept.presentation_level == 1:
            return True, {
                'level': concept.presentation_level,
            }
        return False, {}

    def _check_has_siblings(
        self,
        concept: ConceptMetadata,
        pattern: str,
        concept_index: Optional[ConceptIndex]
    ) -> tuple[bool, dict]:
        """Check if concept has siblings matching pattern."""
        siblings = concept.presentation_siblings or []

        if not siblings and concept_index and concept.presentation_parent:
            # Try to get siblings from parent's children
            parent_children = concept_index.find_children_of(
                concept.presentation_parent
            )
            siblings = [s for s in parent_children if s != concept.qname]

        for sibling in siblings:
            sibling_local = sibling.split(':')[-1] if ':' in sibling else sibling

            if self._pattern_matches(sibling_local, pattern):
                return True, {
                    'matched_sibling': sibling,
                    'pattern': pattern,
                }

        return False, {}

    def _check_depth_level(
        self,
        concept: ConceptMetadata,
        pattern: str
    ) -> tuple[bool, dict]:
        """
        Check if concept is at specific depth level.

        Pattern can be:
        - A number: exact level (e.g., "2")
        - "top": level 0 or 1
        - "bottom": typically level 3+
        """
        level = concept.presentation_level

        if pattern.isdigit():
            target_level = int(pattern)
            if level == target_level:
                return True, {'level': level}

        elif pattern == "top":
            if level <= 1:
                return True, {'level': level}

        elif pattern == "bottom":
            # Consider level 3+ as "bottom"
            if level >= 3:
                return True, {'level': level}

        return False, {}

    def _check_position_ordinal(
        self,
        concept: ConceptMetadata,
        pattern: str,
        concept_index: Optional[ConceptIndex]
    ) -> tuple[bool, dict]:
        """
        Check concept's ordinal position among siblings.

        Pattern can be:
        - "first": First among siblings
        - "last": Last among siblings
        - A number: Specific position (1-based)
        """
        # Get all siblings at same level under same parent
        siblings = []
        if concept_index and concept.presentation_parent:
            parent_children = concept_index.find_children_of(
                concept.presentation_parent
            )
            # Sort by presentation order
            sibling_concepts = [
                concept_index.get_concept(s)
                for s in parent_children
            ]
            sibling_concepts = [s for s in sibling_concepts if s]
            sibling_concepts.sort(key=lambda c: c.presentation_order)
            siblings = [s.qname for s in sibling_concepts]

        if not siblings:
            return False, {}

        try:
            position = siblings.index(concept.qname) + 1  # 1-based
        except ValueError:
            return False, {}

        if pattern == "first":
            if position == 1:
                return True, {'position': position, 'total_siblings': len(siblings)}

        elif pattern == "last":
            if position == len(siblings):
                return True, {'position': position, 'total_siblings': len(siblings)}

        elif pattern.isdigit():
            target_pos = int(pattern)
            if position == target_pos:
                return True, {'position': position, 'total_siblings': len(siblings)}

        return False, {}


__all__ = ['HierarchyEvaluator']
