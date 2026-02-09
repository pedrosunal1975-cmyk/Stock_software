# Path: verification/engine/scoring/score_calculator.py
"""
Score Calculator for Verification Module

Aggregates check results into scores.
Calculates per-category and overall verification scores.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ..checks import CheckResult
from .constants import (
    DEFAULT_HORIZONTAL_WEIGHT,
    DEFAULT_VERTICAL_WEIGHT,
    DEFAULT_LIBRARY_WEIGHT,
    CRITICAL_PENALTY,
    WARNING_PENALTY,
    INFO_PENALTY,
    SCORE_MIN,
    SCORE_MAX,
    HORIZONTAL_WEIGHTS,
    VERTICAL_WEIGHTS,
    LIBRARY_WEIGHTS,
    AGGREGATE_CHECKS,
)
from ...constants import (
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    SEVERITY_INFO,
    CHECK_TYPE_HORIZONTAL,
    CHECK_TYPE_VERTICAL,
    CHECK_TYPE_LIBRARY,
)


@dataclass
class VerificationScores:
    """
    Verification scores for a filing.

    Attributes:
        horizontal_score: Score for within-statement checks (0-100)
        vertical_score: Score for cross-statement checks (0-100)
        library_score: Score for taxonomy conformance (0-100)
        overall_score: Weighted average score (0-100)
        horizontal_checks: Number of horizontal checks run
        vertical_checks: Number of vertical checks run
        library_checks: Number of library checks run
        critical_issues: Count of critical issues
        warning_issues: Count of warning issues
        info_issues: Count of info issues
    """
    horizontal_score: float = 100.0
    vertical_score: float = 100.0
    library_score: float = 100.0
    overall_score: float = 100.0
    horizontal_checks: int = 0
    vertical_checks: int = 0
    library_checks: int = 0
    critical_issues: int = 0
    warning_issues: int = 0
    info_issues: int = 0


class ScoreCalculator:
    """
    Calculates verification scores from check results.

    Aggregates individual check results into category scores
    and an overall weighted score.

    Example:
        calculator = ScoreCalculator()
        scores = calculator.calculate_scores(check_results)
        print(f"Overall score: {scores.overall_score}")
    """

    def __init__(
        self,
        horizontal_weight: float = DEFAULT_HORIZONTAL_WEIGHT,
        vertical_weight: float = DEFAULT_VERTICAL_WEIGHT,
        library_weight: float = DEFAULT_LIBRARY_WEIGHT
    ):
        """
        Initialize score calculator.

        Args:
            horizontal_weight: Weight for horizontal score in overall (0-1)
            vertical_weight: Weight for vertical score in overall (0-1)
            library_weight: Weight for library score in overall (0-1)
        """
        self.horizontal_weight = horizontal_weight
        self.vertical_weight = vertical_weight
        self.library_weight = library_weight
        self.logger = logging.getLogger('process.score_calculator')

        # Normalize weights to sum to 1
        total_weight = horizontal_weight + vertical_weight + library_weight
        if total_weight > 0:
            self.horizontal_weight /= total_weight
            self.vertical_weight /= total_weight
            self.library_weight /= total_weight

    def calculate_scores(self, check_results: list[CheckResult]) -> VerificationScores:
        """
        Calculate all scores from check results.

        Args:
            check_results: List of CheckResult from all checkers

        Returns:
            VerificationScores with all calculated scores
        """
        self.logger.info(f"Calculating scores from {len(check_results)} check results")

        # Separate results by type
        horizontal_results = [r for r in check_results if r.check_type == CHECK_TYPE_HORIZONTAL]
        vertical_results = [r for r in check_results if r.check_type == CHECK_TYPE_VERTICAL]
        library_results = [r for r in check_results if r.check_type == CHECK_TYPE_LIBRARY]

        # Calculate category scores
        horizontal_score = self._calculate_category_score(horizontal_results, HORIZONTAL_WEIGHTS)
        vertical_score = self._calculate_category_score(vertical_results, VERTICAL_WEIGHTS)
        library_score = self._calculate_category_score(library_results, LIBRARY_WEIGHTS)

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            horizontal_score,
            vertical_score,
            library_score
        )

        # Count issues by severity
        critical, warnings, info = self._count_issues(check_results)

        scores = VerificationScores(
            horizontal_score=horizontal_score,
            vertical_score=vertical_score,
            library_score=library_score,
            overall_score=overall_score,
            horizontal_checks=len(horizontal_results),
            vertical_checks=len(vertical_results),
            library_checks=len(library_results),
            critical_issues=critical,
            warning_issues=warnings,
            info_issues=info,
        )

        self.logger.info(
            f"Scores calculated: H={horizontal_score:.1f}, V={vertical_score:.1f}, "
            f"L={library_score:.1f}, Overall={overall_score:.1f}"
        )

        return scores

    def _calculate_category_score(
        self,
        results: list[CheckResult],
        check_weights: dict[str, float]
    ) -> float:
        """
        Calculate score for a single category.

        For AGGREGATE checks (xbrl_calculation_company, xbrl_calculation_taxonomy):
        - Uses pass-rate based scoring: score = pass_rate * weight * 100
        - Many results are expected, so we use percentage instead of penalties

        For STANDARD checks:
        - Starts at 100, deducts points based on failures and severity
        - Each failure deducts penalty * weight

        Args:
            results: List of CheckResult for this category
            check_weights: Weights for each check type within category

        Returns:
            Category score (0-100)
        """
        if not results:
            return SCORE_MAX  # No checks = perfect score (nothing to fail)

        # Group results by check name
        results_by_check: dict[str, list[CheckResult]] = {}
        for result in results:
            if result.check_name not in results_by_check:
                results_by_check[result.check_name] = []
            results_by_check[result.check_name].append(result)

        # Calculate weighted score contributions
        total_weight = 0.0
        weighted_score = 0.0

        for check_name, check_results in results_by_check.items():
            # Get weight for this check type
            weight = check_weights.get(check_name, 1.0 / len(results_by_check))
            total_weight += weight

            # Use pass-rate scoring for aggregate checks
            if check_name in AGGREGATE_CHECKS:
                # Calculate pass rate
                total = len(check_results)
                passed = sum(1 for r in check_results if r.passed)

                if total > 0:
                    pass_rate = passed / total
                    # Contribute weighted score based on pass rate
                    # 100% pass rate = full weight contribution
                    weighted_score += pass_rate * weight * SCORE_MAX
                else:
                    # No results = full score for this check
                    weighted_score += weight * SCORE_MAX
            else:
                # Standard penalty-based scoring for non-aggregate checks
                check_penalty = 0.0
                for result in check_results:
                    if not result.passed:
                        check_penalty += self._get_severity_penalty(result.severity)

                # Calculate score contribution (max = weight * 100)
                check_score = max(0, SCORE_MAX - check_penalty)
                weighted_score += check_score * weight

        # Normalize to 0-100 scale
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = SCORE_MAX

        return max(SCORE_MIN, min(SCORE_MAX, final_score))

    def _calculate_overall_score(
        self,
        horizontal_score: float,
        vertical_score: float,
        library_score: float
    ) -> float:
        """
        Calculate overall weighted score.

        Args:
            horizontal_score: Horizontal check score
            vertical_score: Vertical check score
            library_score: Library check score

        Returns:
            Overall score (0-100)
        """
        overall = (
            horizontal_score * self.horizontal_weight +
            vertical_score * self.vertical_weight +
            library_score * self.library_weight
        )

        return max(SCORE_MIN, min(SCORE_MAX, overall))

    def _get_severity_penalty(self, severity: str) -> float:
        """Get penalty points for a severity level."""
        penalties = {
            SEVERITY_CRITICAL: CRITICAL_PENALTY,
            SEVERITY_WARNING: WARNING_PENALTY,
            SEVERITY_INFO: INFO_PENALTY,
        }
        return penalties.get(severity, INFO_PENALTY)

    def _count_issues(self, results: list[CheckResult]) -> tuple[int, int, int]:
        """
        Count issues by severity.

        Args:
            results: All check results

        Returns:
            Tuple of (critical, warnings, info) counts
        """
        critical = 0
        warnings = 0
        info = 0

        for result in results:
            if not result.passed:
                if result.severity == SEVERITY_CRITICAL:
                    critical += 1
                elif result.severity == SEVERITY_WARNING:
                    warnings += 1
                else:
                    info += 1

        return critical, warnings, info


__all__ = ['ScoreCalculator', 'VerificationScores']
