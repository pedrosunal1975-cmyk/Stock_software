# Path: verification/engine/processors/stage3_verification/verification_processor.py
"""
Stage 3: Verification Processor

Orchestrates verification checks on prepared data:
- Horizontal checks (calculation linkbase verification)
- Vertical checks (cross-statement consistency)

RESPONSIBILITY: Coordinate verification workflow and aggregate results.
Delegates actual check logic to specialized runners.

COMPONENTS:
- HorizontalCheckRunner: Calculation linkbase verification
- VerticalCheckRunner: Cross-statement consistency
- SummaryBuilder: Score and summary generation

OUTPUT: VerificationResult with all check results and summary
"""

import logging
from datetime import datetime

from ..pipeline_data import PreparationResult, VerificationResult

# Import check runners and summary builder
from .horizontal_checks import HorizontalCheckRunner
from .vertical_checks import VerticalCheckRunner
from .summary_builder import SummaryBuilder

# Import constants for default configuration
from ...constants.tolerances import (
    DEFAULT_CALCULATION_TOLERANCE,
    DEFAULT_ROUNDING_TOLERANCE,
    CROSS_STATEMENT_TOLERANCE,
)


class VerificationProcessor:
    """
    Stage 3: Verifies prepared data and produces results.

    Orchestrates verification using specialized runners:
    1. Horizontal checks - Verify calculation linkbase relationships
    2. Vertical checks - Verify cross-statement consistency

    Runners are configured based on filing characteristics.

    Usage:
        processor = VerificationProcessor()
        result = processor.verify(preparation_result)

        print(f"Score: {result.summary.score}")
        print(f"Critical issues: {result.summary.critical_issues}")
    """

    def __init__(self):
        self.logger = logging.getLogger('processors.stage3.verification')

        # Initialize check runners
        self._horizontal_runner = HorizontalCheckRunner()
        self._vertical_runner = VerticalCheckRunner()
        self._summary_builder = SummaryBuilder()

        # Configuration (can be modified via setters)
        self._calculation_tolerance = DEFAULT_CALCULATION_TOLERANCE
        self._rounding_tolerance = DEFAULT_ROUNDING_TOLERANCE
        self._cross_statement_tolerance = CROSS_STATEMENT_TOLERANCE

    def set_calculation_tolerance(self, tolerance: float) -> None:
        """Set calculation tolerance (percentage)."""
        self._calculation_tolerance = tolerance
        self._horizontal_runner.set_calculation_tolerance(tolerance)

    def set_rounding_tolerance(self, tolerance: float) -> None:
        """Set rounding tolerance (absolute value)."""
        self._rounding_tolerance = tolerance
        self._horizontal_runner.set_rounding_tolerance(tolerance)

    def set_cross_statement_tolerance(self, tolerance: float) -> None:
        """Set cross-statement tolerance (percentage)."""
        self._cross_statement_tolerance = tolerance
        self._vertical_runner.set_cross_statement_tolerance(tolerance)

    def set_binding_strategy(self, strategy: str) -> None:
        """
        Set binding strategy.

        Options: 'strict', 'fallback'
        """
        self._horizontal_runner.set_binding_strategy(strategy)

    def verify(self, preparation: PreparationResult) -> VerificationResult:
        """
        Verify prepared data.

        Args:
            preparation: PreparationResult from Stage 2

        Returns:
            VerificationResult with all checks
        """
        start_time = datetime.now()
        self.logger.info(
            f"Stage 3: Verifying {len(preparation.facts)} facts, "
            f"{len(preparation.calculations)} calculations"
        )

        result = VerificationResult(preparation=preparation)
        result.verification_timestamp = start_time.isoformat()

        # Set up sign lookup for horizontal checks
        self._horizontal_runner.setup_sign_lookup(preparation)

        # Step 1: Horizontal checks (calculation verification)
        self._horizontal_runner.run_checks(preparation, result)

        # Step 2: Vertical checks (cross-statement consistency)
        self._vertical_runner.run_checks(preparation, result)

        # Build summary
        self._summary_builder.build_summary(result)

        # Calculate processing time
        end_time = datetime.now()
        result.processing_time_ms = (end_time - start_time).total_seconds() * 1000

        self.logger.info(
            f"Stage 3 complete: {result.summary.total_checks} checks, "
            f"score {result.summary.score:.1f}/100"
        )

        return result


__all__ = ['VerificationProcessor']
