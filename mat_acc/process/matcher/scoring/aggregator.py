# Path: mat_acc/process/matcher/scoring/aggregator.py
"""
Score Aggregator

Combines scores from multiple rule evaluators into a total score.
"""

import logging
from typing import Optional

from ..models.match_result import RuleScore, ScoredMatch, Confidence
from ..models.component_definition import ComponentDefinition
from ..evaluators.base_evaluator import EvaluationResult
from .confidence import ConfidenceCalculator


class ScoreAggregator:
    """
    Aggregates scores from multiple evaluators.

    Takes evaluation results from all evaluators and combines them
    into a final ScoredMatch with total score and breakdown.

    Example:
        aggregator = ScoreAggregator()
        scored_match = aggregator.aggregate(
            concept_qname="us-gaap:AssetsCurrent",
            evaluation_results={
                'label': label_result,
                'hierarchy': hierarchy_result,
                'calculation': calculation_result,
            },
            component=component_definition
        )
    """

    def __init__(self):
        """Initialize score aggregator."""
        self.logger = logging.getLogger('matcher.scoring.aggregator')
        self.confidence_calculator = ConfidenceCalculator()

    def aggregate(
        self,
        concept_qname: str,
        evaluation_results: dict[str, EvaluationResult],
        component: ComponentDefinition,
        rejection_reason: Optional[str] = None
    ) -> ScoredMatch:
        """
        Aggregate evaluation results into a scored match.

        Args:
            concept_qname: QName of the concept being scored
            evaluation_results: Results from each evaluator
            component: Component definition (for max score calculation)
            rejection_reason: If concept was rejected, the reason

        Returns:
            ScoredMatch with total score and breakdown
        """
        total_score = 0
        rule_scores = []
        has_exact_local_name = False

        for evaluator_type, result in evaluation_results.items():
            if result.score > 0:
                total_score += result.score
                rule_scores.append(RuleScore(
                    rule_type=evaluator_type,
                    score=result.score,
                    details={'matched_rules': result.matched_rules},
                ))
                if evaluator_type == 'local_name':
                    for mr in result.matched_rules:
                        if mr.get('match_type') == 'exact':
                            has_exact_local_name = True

        # Exact local_name match = dictionary explicitly names this
        # concept. Guarantee it clears min_score regardless of
        # whether hierarchy/calculation evaluators fired (they
        # depend on linkbase richness which varies by taxonomy).
        min_score = component.scoring.min_score
        if has_exact_local_name and total_score < min_score:
            total_score = min_score

        # Calculate confidence
        confidence = self.confidence_calculator.calculate(
            score=total_score,
            confidence_levels=component.scoring.confidence_levels,
            rule_scores=rule_scores
        )

        return ScoredMatch(
            concept=concept_qname,
            total_score=total_score,
            rule_scores=rule_scores,
            confidence=confidence,
            rejection_reason=rejection_reason,
        )

    def get_score_breakdown(
        self,
        evaluation_results: dict[str, EvaluationResult]
    ) -> dict[str, int]:
        """
        Get simple breakdown of scores by evaluator type.

        Args:
            evaluation_results: Results from each evaluator

        Returns:
            Dictionary mapping evaluator type to score
        """
        return {
            evaluator_type: result.score
            for evaluator_type, result in evaluation_results.items()
        }

    def count_matching_evaluators(
        self,
        evaluation_results: dict[str, EvaluationResult]
    ) -> int:
        """
        Count how many evaluator types produced matches.

        A higher count indicates more evidence for the match.

        Args:
            evaluation_results: Results from each evaluator

        Returns:
            Number of evaluators with score > 0
        """
        return sum(
            1 for result in evaluation_results.values()
            if result.score > 0
        )


__all__ = ['ScoreAggregator']
