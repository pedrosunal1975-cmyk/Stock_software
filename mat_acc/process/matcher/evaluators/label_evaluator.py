# Path: mat_acc/process/matcher/evaluators/label_evaluator.py
"""
Label Evaluator

Evaluates label matching rules against concept labels.
This is typically the highest-weighted evaluator as labels
are the most direct identifier of a concept's meaning.
"""

from typing import Any, Optional

from .base_evaluator import BaseEvaluator, EvaluationResult
from ..models.concept_metadata import ConceptMetadata
from ..models.component_definition import LabelRule, MatchType


class LabelEvaluator(BaseEvaluator):
    """
    Evaluates label matching rules.

    Matches patterns against all available labels for a concept:
    - standard: Primary label
    - terse: Short form label
    - verbose: Long form label
    - documentation: Detailed description
    - negated: Negated form labels

    Match types supported:
    - contains: Label contains pattern
    - starts_with: Label starts with pattern
    - ends_with: Label ends with pattern
    - exact: Exact match
    - regex: Regular expression

    Example:
        evaluator = LabelEvaluator()
        result = evaluator.evaluate(
            concept=concept,
            rules=[
                LabelRule(
                    patterns=["current assets", "assets, current"],
                    match_type=MatchType.CONTAINS,
                    weight=15
                )
            ]
        )
    """

    @property
    def evaluator_type(self) -> str:
        return "label"

    def evaluate(
        self,
        concept: ConceptMetadata,
        rules: list[LabelRule],
        context: Optional[dict] = None
    ) -> EvaluationResult:
        """
        Evaluate label rules against concept labels.

        Args:
            concept: Concept with labels to match
            rules: List of LabelRule objects
            context: Optional additional context

        Returns:
            EvaluationResult with total score and matched rules
        """
        total_score = 0
        matched_rules = []

        # Get all labels from concept
        labels = concept.labels
        if not labels:
            return EvaluationResult(
                score=0,
                matched_rules=[],
                evaluator_type=self.evaluator_type
            )

        for rule in rules:
            # Try to match against any label
            matched = False
            matched_label_type = None
            matched_label_text = None
            matched_pattern = None

            for label_type, label_text in labels.items():
                if not label_text:
                    continue

                for pattern in rule.patterns:
                    if self._matches_pattern(
                        label_text,
                        pattern,
                        rule.match_type,
                        rule.case_sensitive
                    ):
                        matched = True
                        matched_label_type = label_type
                        matched_label_text = label_text
                        matched_pattern = pattern
                        break

                if matched:
                    break

            if matched:
                total_score += rule.weight
                matched_rules.append({
                    'patterns': rule.patterns,
                    'match_type': rule.match_type.value,
                    'matched_pattern': matched_pattern,
                    'matched_label': matched_label_text,
                    'label_type': matched_label_type,
                    'weight': rule.weight,
                })

                self.logger.debug(
                    f"Label match: '{matched_pattern}' matched "
                    f"'{matched_label_text}' ({matched_label_type}) "
                    f"for {concept.qname}, weight={rule.weight}"
                )

        return EvaluationResult(
            score=total_score,
            matched_rules=matched_rules,
            evaluator_type=self.evaluator_type
        )

    def _matches_pattern(
        self,
        text: str,
        pattern: str,
        match_type: MatchType,
        case_sensitive: bool
    ) -> bool:
        """
        Check if text matches pattern according to match type.

        Args:
            text: Text to match against
            pattern: Pattern to match
            match_type: How to perform the match
            case_sensitive: Whether matching is case-sensitive

        Returns:
            True if pattern matches
        """
        if match_type == MatchType.CONTAINS:
            return self._text_contains(text, pattern, case_sensitive)

        elif match_type == MatchType.STARTS_WITH:
            return self._text_starts_with(text, pattern, case_sensitive)

        elif match_type == MatchType.ENDS_WITH:
            return self._text_ends_with(text, pattern, case_sensitive)

        elif match_type == MatchType.EXACT:
            # Normalize for comparison to handle punctuation variations
            norm_text = self._normalize_for_matching(text)
            norm_pattern = self._normalize_for_matching(pattern)
            if not case_sensitive:
                return norm_text.lower() == norm_pattern.lower()
            return norm_text == norm_pattern

        elif match_type == MatchType.REGEX:
            return self._regex_matches(text, pattern, case_sensitive)

        else:
            self.logger.warning(f"Unknown match type: {match_type}")
            return False


__all__ = ['LabelEvaluator']
