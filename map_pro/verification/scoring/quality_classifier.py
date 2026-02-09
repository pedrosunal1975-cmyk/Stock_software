# Path: verification/engine/scoring/quality_classifier.py
"""
Quality Classifier for Verification Module

Classifies overall quality level based on verification scores.
Provides recommendations based on quality classification.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .score_calculator import VerificationScores
from .constants import (
    DEFAULT_EXCELLENT_THRESHOLD,
    DEFAULT_GOOD_THRESHOLD,
    DEFAULT_FAIR_THRESHOLD,
    DEFAULT_POOR_THRESHOLD,
    QUALITY_DESCRIPTIONS,
    QUALITY_RECOMMENDATIONS,
)
from ...constants import (
    QUALITY_EXCELLENT,
    QUALITY_GOOD,
    QUALITY_FAIR,
    QUALITY_POOR,
    QUALITY_UNUSABLE,
)


@dataclass
class QualityClassification:
    """
    Quality classification result.

    Attributes:
        level: Quality level (EXCELLENT, GOOD, FAIR, POOR, UNUSABLE)
        description: Human-readable description
        recommendation: Recommended action
        confidence: Confidence in classification (0-1)
        factors: Factors that influenced classification
    """
    level: str
    description: str
    recommendation: str
    confidence: float = 1.0
    factors: dict = None

    def __post_init__(self):
        if self.factors is None:
            self.factors = {}


class QualityClassifier:
    """
    Classifies filing quality based on verification scores.

    Based on scores, classifies filing as:
    - EXCELLENT (90-100): Fully consistent, ready for analysis
    - GOOD (75-89): Minor issues, usable with caution
    - FAIR (50-74): Notable issues, limited analysis value
    - POOR (25-49): Significant issues, use at own risk
    - UNUSABLE (0-24): Major inconsistencies, not recommended

    Example:
        classifier = QualityClassifier()
        classification = classifier.classify(scores)
        print(f"Quality: {classification.level}")
        print(f"Recommendation: {classification.recommendation}")
    """

    def __init__(
        self,
        excellent_threshold: int = DEFAULT_EXCELLENT_THRESHOLD,
        good_threshold: int = DEFAULT_GOOD_THRESHOLD,
        fair_threshold: int = DEFAULT_FAIR_THRESHOLD,
        poor_threshold: int = DEFAULT_POOR_THRESHOLD
    ):
        """
        Initialize quality classifier.

        Args:
            excellent_threshold: Minimum score for EXCELLENT (default 90)
            good_threshold: Minimum score for GOOD (default 75)
            fair_threshold: Minimum score for FAIR (default 50)
            poor_threshold: Minimum score for POOR (default 25)
        """
        self.excellent_threshold = excellent_threshold
        self.good_threshold = good_threshold
        self.fair_threshold = fair_threshold
        self.poor_threshold = poor_threshold
        self.logger = logging.getLogger('process.quality_classifier')

    def classify(self, scores: VerificationScores) -> QualityClassification:
        """
        Determine quality level from scores.

        Args:
            scores: VerificationScores from ScoreCalculator

        Returns:
            QualityClassification with level, description, recommendation
        """
        overall = scores.overall_score

        self.logger.info(f"Classifying quality for score: {overall:.1f}")

        # Determine base level from overall score
        if overall >= self.excellent_threshold:
            level = QUALITY_EXCELLENT
        elif overall >= self.good_threshold:
            level = QUALITY_GOOD
        elif overall >= self.fair_threshold:
            level = QUALITY_FAIR
        elif overall >= self.poor_threshold:
            level = QUALITY_POOR
        else:
            level = QUALITY_UNUSABLE

        # Check for critical issues that might downgrade
        level = self._adjust_for_critical_issues(level, scores)

        # Get descriptions and recommendations
        description = QUALITY_DESCRIPTIONS.get(level, '')
        recommendation = QUALITY_RECOMMENDATIONS.get(level, '')

        # Calculate confidence
        confidence = self._calculate_confidence(scores, level)

        # Collect classification factors
        factors = self._collect_factors(scores, level)

        classification = QualityClassification(
            level=level,
            description=description,
            recommendation=recommendation,
            confidence=confidence,
            factors=factors,
        )

        self.logger.info(f"Quality classification: {level} (confidence: {confidence:.2f})")

        return classification

    def _adjust_for_critical_issues(
        self,
        level: str,
        scores: VerificationScores
    ) -> str:
        """
        Adjust quality level based on critical issues.

        Critical issues may downgrade the classification even if
        overall score is high.

        Args:
            level: Initial quality level
            scores: Verification scores

        Returns:
            Adjusted quality level
        """
        # Critical issues can downgrade quality
        if scores.critical_issues > 0:
            if level == QUALITY_EXCELLENT:
                level = QUALITY_GOOD
                self.logger.info(f"Downgraded from EXCELLENT due to {scores.critical_issues} critical issues")
            elif level == QUALITY_GOOD and scores.critical_issues >= 2:
                level = QUALITY_FAIR
                self.logger.info(f"Downgraded from GOOD due to {scores.critical_issues} critical issues")

        # Balance sheet equation failure is always critical
        if scores.horizontal_score < 50 or scores.vertical_score < 50:
            if level in [QUALITY_EXCELLENT, QUALITY_GOOD]:
                level = QUALITY_FAIR
                self.logger.info("Downgraded due to low horizontal/vertical scores")

        return level

    def _calculate_confidence(
        self,
        scores: VerificationScores,
        level: str
    ) -> float:
        """
        Calculate confidence in the classification.

        Confidence is higher when:
        - Score is clearly within a band (not on borderline)
        - Multiple check categories agree
        - Sufficient checks were performed

        Args:
            scores: Verification scores
            level: Classified level

        Returns:
            Confidence value (0-1)
        """
        confidence = 1.0
        overall = scores.overall_score

        # Check if score is on borderline
        thresholds = [
            self.excellent_threshold,
            self.good_threshold,
            self.fair_threshold,
            self.poor_threshold,
        ]

        for threshold in thresholds:
            distance = abs(overall - threshold)
            if distance < 5:
                confidence -= 0.15  # Reduce confidence for borderline scores

        # Check category agreement
        category_scores = [
            scores.horizontal_score,
            scores.vertical_score,
            scores.library_score,
        ]

        variance = self._calculate_variance(category_scores)
        if variance > 400:  # High variance between categories
            confidence -= 0.2

        # Check if sufficient checks were performed
        total_checks = (
            scores.horizontal_checks +
            scores.vertical_checks +
            scores.library_checks
        )

        if total_checks < 5:
            confidence -= 0.15

        return max(0.0, min(1.0, confidence))

    def _calculate_variance(self, values: list[float]) -> float:
        """Calculate variance of a list of values."""
        if not values:
            return 0.0

        mean = sum(values) / len(values)
        squared_diffs = [(v - mean) ** 2 for v in values]
        return sum(squared_diffs) / len(values)

    def _collect_factors(
        self,
        scores: VerificationScores,
        level: str
    ) -> dict:
        """
        Collect factors that influenced classification.

        Args:
            scores: Verification scores
            level: Final quality level

        Returns:
            Dictionary of factors
        """
        factors = {
            'overall_score': scores.overall_score,
            'horizontal_score': scores.horizontal_score,
            'vertical_score': scores.vertical_score,
            'library_score': scores.library_score,
            'critical_issues': scores.critical_issues,
            'warning_issues': scores.warning_issues,
            'total_checks': (
                scores.horizontal_checks +
                scores.vertical_checks +
                scores.library_checks
            ),
        }

        # Add specific concerns
        concerns = []

        if scores.horizontal_score < 70:
            concerns.append('Low horizontal (calculation) score')

        if scores.vertical_score < 70:
            concerns.append('Low vertical (cross-statement) score')

        if scores.critical_issues > 0:
            concerns.append(f'{scores.critical_issues} critical issue(s) found')

        factors['concerns'] = concerns

        return factors

    def get_threshold_info(self) -> dict:
        """
        Get information about classification thresholds.

        Returns:
            Dictionary with threshold information
        """
        return {
            QUALITY_EXCELLENT: {
                'min_score': self.excellent_threshold,
                'max_score': 100,
                'description': QUALITY_DESCRIPTIONS.get(QUALITY_EXCELLENT, ''),
            },
            QUALITY_GOOD: {
                'min_score': self.good_threshold,
                'max_score': self.excellent_threshold - 1,
                'description': QUALITY_DESCRIPTIONS.get(QUALITY_GOOD, ''),
            },
            QUALITY_FAIR: {
                'min_score': self.fair_threshold,
                'max_score': self.good_threshold - 1,
                'description': QUALITY_DESCRIPTIONS.get(QUALITY_FAIR, ''),
            },
            QUALITY_POOR: {
                'min_score': self.poor_threshold,
                'max_score': self.fair_threshold - 1,
                'description': QUALITY_DESCRIPTIONS.get(QUALITY_POOR, ''),
            },
            QUALITY_UNUSABLE: {
                'min_score': 0,
                'max_score': self.poor_threshold - 1,
                'description': QUALITY_DESCRIPTIONS.get(QUALITY_UNUSABLE, ''),
            },
        }


__all__ = ['QualityClassifier', 'QualityClassification']
