# Path: verification/engine/processors/stage3_verification/summary_builder.py
"""
Summary Builder - Builds verification summary and calculates score

Aggregates verification check results into a summary with:
- Pass/fail counts by check type
- Severity breakdown (critical, warning, info)
- Overall verification score

RESPONSIBILITY: Build summary from check results.
Score calculation is based on pass rate with penalties for issues.
"""

import logging

from ..pipeline_data import VerificationResult, VerificationSummary

# Import constants
from ...constants.tolerances import (
    CRITICAL_PENALTY_WEIGHT,
    WARNING_PENALTY_WEIGHT,
    MIN_SCORE,
    MAX_SCORE,
    DEFAULT_NO_CHECKS_SCORE,
    SCORE_PERCENTAGE_MULTIPLIER,
)


class SummaryBuilder:
    """
    Builds verification summary from check results.

    Aggregates checks by type and severity, then calculates
    an overall verification score.

    Usage:
        builder = SummaryBuilder()
        builder.build_summary(result)

        print(f"Score: {result.summary.score}")
        print(f"Critical: {result.summary.critical_issues}")
    """

    def __init__(self):
        self.logger = logging.getLogger('processors.stage3.summary')

    def build_summary(self, result: VerificationResult) -> None:
        """
        Build verification summary from checks.

        Args:
            result: VerificationResult containing all checks
        """
        summary = VerificationSummary()

        for check in result.checks:
            summary.total_checks += 1

            if check.passed:
                summary.passed += 1
                # Passed checks don't count as issues
            elif check.severity == 'info' and 'skipped' in check.message.lower():
                summary.skipped += 1
            else:
                # Only count issues for FAILED checks
                summary.failed += 1

                if check.severity == 'critical':
                    summary.critical_issues += 1
                elif check.severity == 'warning':
                    summary.warning_issues += 1
                    summary.warnings += 1
                elif check.severity == 'info':
                    summary.info_issues += 1

        # Calculate score
        summary.score = self._calculate_score(summary)

        result.summary = summary

        self.logger.info(
            f"Summary built: {summary.total_checks} checks, "
            f"{summary.passed} passed, {summary.failed} failed, "
            f"score {summary.score:.1f}"
        )

    def _calculate_score(self, summary: VerificationSummary) -> float:
        """
        Calculate verification score using pass rate approach.

        Score calculation:
        1. Base score from pass rate (passed + skipped) / total
        2. Apply penalty for critical and warning issues
        3. Clamp result to valid range

        Args:
            summary: VerificationSummary with counts

        Returns:
            Score from 0 to 100
        """
        if summary.total_checks == 0:
            return DEFAULT_NO_CHECKS_SCORE

        # Base score on pass rate
        pass_rate = (summary.passed + summary.skipped) / summary.total_checks
        raw_score = pass_rate * SCORE_PERCENTAGE_MULTIPLIER

        # Apply penalty only for failed checks
        # Critical failures have heavy impact, warnings less so
        if summary.failed > 0:
            # Penalty as percentage of total checks (proportional)
            critical_penalty = (
                (summary.critical_issues / summary.total_checks)
                * CRITICAL_PENALTY_WEIGHT
            )
            warning_penalty = (
                (summary.warning_issues / summary.total_checks)
                * WARNING_PENALTY_WEIGHT
            )
            penalty = critical_penalty + warning_penalty
            score = raw_score - penalty
        else:
            score = raw_score

        # Clamp to valid range
        return max(MIN_SCORE, min(MAX_SCORE, score))


__all__ = ['SummaryBuilder']
