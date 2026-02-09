# Path: mat_acc/process/matcher/evaluators/definition_evaluator.py
"""
Definition Evaluator

Evaluates definition matching rules by checking for keywords
in a concept's definition text from the taxonomy.
"""

from typing import Any, Optional

from .base_evaluator import BaseEvaluator, EvaluationResult
from ..models.concept_metadata import ConceptMetadata
from ..models.component_definition import DefinitionRule


class DefinitionEvaluator(BaseEvaluator):
    """
    Evaluates definition keyword rules.

    Checks if concept's definition text contains specified keywords.
    Can require all keywords or any of them.

    This evaluator typically has lower weight than label/hierarchy
    since definitions may not always be available or may vary.

    Example:
        evaluator = DefinitionEvaluator()
        result = evaluator.evaluate(
            concept=concept,
            rules=[
                DefinitionRule(
                    keywords=["one year", "operating cycle", "current"],
                    all_required=False,
                    weight=4
                )
            ]
        )
    """

    @property
    def evaluator_type(self) -> str:
        return "definition"

    def evaluate(
        self,
        concept: ConceptMetadata,
        rules: list[DefinitionRule],
        context: Optional[dict] = None
    ) -> EvaluationResult:
        """
        Evaluate definition rules against concept definition.

        Args:
            concept: Concept with definition text
            rules: List of DefinitionRule objects
            context: Optional additional context

        Returns:
            EvaluationResult with total score and matched rules
        """
        total_score = 0
        matched_rules = []

        definition = concept.definition or ""

        # Also check documentation label if available
        doc_label = concept.labels.get('documentation', '')
        full_text = f"{definition} {doc_label}".lower()

        if not full_text.strip():
            return EvaluationResult(
                score=0,
                matched_rules=[],
                evaluator_type=self.evaluator_type
            )

        for rule in rules:
            matched_keywords = []

            for keyword in rule.keywords:
                if keyword.lower() in full_text:
                    matched_keywords.append(keyword)

            # Check if matching criteria met
            matched = False
            if rule.all_required:
                # All keywords must be present
                if len(matched_keywords) == len(rule.keywords):
                    matched = True
            else:
                # At least one keyword must be present
                if len(matched_keywords) > 0:
                    matched = True

            if matched:
                total_score += rule.weight
                matched_rules.append({
                    'keywords': rule.keywords,
                    'all_required': rule.all_required,
                    'matched_keywords': matched_keywords,
                    'weight': rule.weight,
                })

                self.logger.debug(
                    f"Definition match: {matched_keywords} for "
                    f"{concept.qname}, weight={rule.weight}"
                )

        return EvaluationResult(
            score=total_score,
            matched_rules=matched_rules,
            evaluator_type=self.evaluator_type
        )


__all__ = ['DefinitionEvaluator']
