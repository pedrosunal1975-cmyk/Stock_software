# Path: mat_acc/process/matcher/scoring/confidence.py
"""
Confidence Calculator

Determines confidence level based on score and rule breakdown.
"""

import logging
from typing import Optional

from ..models.match_result import RuleScore, Confidence
from ..models.component_definition import ConfidenceLevels


class ConfidenceCalculator:
    """
    Calculates confidence level from score and rule breakdown.

    Confidence is determined by:
    1. Raw score vs thresholds (primary)
    2. Number of evaluator types that matched (adjustment)
    3. Whether only labels matched (potential downgrade)

    Confidence levels:
    - HIGH: Strong evidence from multiple sources
    - MEDIUM: Good evidence but some uncertainty
    - LOW: Weak evidence, manual verification recommended
    - NONE: Score below minimum threshold
    """

    def __init__(self):
        """Initialize confidence calculator."""
        self.logger = logging.getLogger('matcher.scoring.confidence')

    def calculate(
        self,
        score: int,
        confidence_levels: ConfidenceLevels,
        rule_scores: list[RuleScore]
    ) -> Confidence:
        """
        Calculate confidence level.

        Args:
            score: Total score
            confidence_levels: Thresholds from component definition
            rule_scores: Breakdown of scores by rule type

        Returns:
            Confidence level
        """
        # Base confidence from thresholds
        if score >= confidence_levels.high:
            base_confidence = Confidence.HIGH
        elif score >= confidence_levels.medium:
            base_confidence = Confidence.MEDIUM
        elif score >= confidence_levels.low:
            base_confidence = Confidence.LOW
        else:
            return Confidence.NONE

        # Count evaluator types with matches
        evaluator_count = len([rs for rs in rule_scores if rs.score > 0])

        # Adjustments
        adjusted_confidence = base_confidence

        # Boost if multiple evaluator types matched
        if evaluator_count >= 4:
            adjusted_confidence = self._boost_confidence(base_confidence)
            self.logger.debug(
                f"Confidence boosted due to {evaluator_count} matching evaluators"
            )

        # Reduce if only label matched (could be false positive)
        if self._only_label_matched(rule_scores):
            adjusted_confidence = self._reduce_confidence(base_confidence)
            self.logger.debug(
                "Confidence reduced: only label rules matched"
            )

        return adjusted_confidence

    def _only_label_matched(self, rule_scores: list[RuleScore]) -> bool:
        """Check if only label evaluator produced a score."""
        matching_types = [
            rs.rule_type for rs in rule_scores if rs.score > 0
        ]

        return (
            len(matching_types) == 1 and
            matching_types[0] == 'label'
        )

    def _boost_confidence(self, current: Confidence) -> Confidence:
        """Boost confidence by one level."""
        if current == Confidence.LOW:
            return Confidence.MEDIUM
        elif current == Confidence.MEDIUM:
            return Confidence.HIGH
        return current  # Already HIGH

    def _reduce_confidence(self, current: Confidence) -> Confidence:
        """Reduce confidence by one level."""
        if current == Confidence.HIGH:
            return Confidence.MEDIUM
        elif current == Confidence.MEDIUM:
            return Confidence.LOW
        return current  # Already LOW


__all__ = ['ConfidenceCalculator']
