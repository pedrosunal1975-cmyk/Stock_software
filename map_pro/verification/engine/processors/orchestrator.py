# Path: verification/engine/processors/orchestrator.py
"""
Pipeline Orchestrator for Verification Processing

Coordinates the 3-stage verification pipeline:
    Stage 1 (Discovery) -> Stage 2 (Preparation) -> Stage 3 (Verification)

Provides a single entry point for verification with configurable options.

DESIGN PRINCIPLES:
1. Each stage is independent and testable
2. Tools are picked up and dropped as needed by each stage
3. Data flows forward only - no backward dependencies
4. Errors are collected, not thrown (graceful degradation)

DATA SOURCES:
- Accepts MappedFilingEntry for production use (reads from XBRL via existing loaders)
- Accepts Path for testing use (reads from parsed.json fixtures)
"""

import logging
from pathlib import Path
from typing import Optional, Union

# Import MappedFilingEntry for type checking
from verification.loaders.mapped_data import MappedFilingEntry

from .pipeline_data import (
    DiscoveryResult,
    PreparationResult,
    VerificationResult,
)
from .stage1_discovery.discovery_processor import DiscoveryProcessor
from .stage2_preparation.preparation_processor import PreparationProcessor
from .stage3_verification.verification_processor import VerificationProcessor


class PipelineOrchestrator:
    """
    Orchestrates the 3-stage verification pipeline.

    Coordinates:
    - Stage 1: Discovery - Extract raw data from XBRL files
    - Stage 2: Preparation - Normalize and organize data
    - Stage 3: Verification - Verify and produce results

    Each stage uses specialized tools that can be configured
    based on filing characteristics.

    Usage:
        orchestrator = PipelineOrchestrator()

        # Run full pipeline
        result = orchestrator.run(filing_path)
        print(f"Score: {result.summary.score}")

        # Or run individual stages
        discovery = orchestrator.run_discovery(filing_path)
        preparation = orchestrator.run_preparation(discovery)
        verification = orchestrator.run_verification(preparation)

        # Configure before running
        orchestrator.configure(
            naming_strategy='local_name',
            binding_strategy='strict',
            calculation_tolerance=0.02,
        )
        result = orchestrator.run(filing_path)
    """

    def __init__(self, config=None):
        """
        Initialize the pipeline orchestrator.

        Args:
            config: Optional ConfigLoader instance for loaders
        """
        self.logger = logging.getLogger('processors.orchestrator')
        self.config = config

        # Initialize processors
        self._discovery = DiscoveryProcessor(config)
        self._preparation = PreparationProcessor()
        self._verification = VerificationProcessor()

        # Pipeline state
        self._last_discovery: Optional[DiscoveryResult] = None
        self._last_preparation: Optional[PreparationResult] = None
        self._last_verification: Optional[VerificationResult] = None

    def configure(
        self,
        naming_strategy: str = None,
        context_strategy: str = None,
        binding_strategy: str = None,
        calculation_tolerance: float = None,
        rounding_tolerance: float = None,
    ) -> 'PipelineOrchestrator':
        """
        Configure pipeline options.

        Args:
            naming_strategy: 'canonical', 'local_name', 'full_qualified', 'auto'
            context_strategy: 'default', 'strict'
            binding_strategy: 'strict', 'fallback'
            calculation_tolerance: Percentage tolerance (e.g., 0.01 for 1%)
            rounding_tolerance: Absolute tolerance (e.g., 1.0 for $1)

        Returns:
            Self for chaining
        """
        if naming_strategy:
            self._preparation.set_naming_strategy(naming_strategy)

        if context_strategy:
            self._preparation.set_context_strategy(context_strategy)

        if binding_strategy:
            self._verification.set_binding_strategy(binding_strategy)

        if calculation_tolerance is not None:
            self._verification.set_calculation_tolerance(calculation_tolerance)

        if rounding_tolerance is not None:
            self._verification.set_rounding_tolerance(rounding_tolerance)

        return self

    def run(self, source: Union[Path, str, MappedFilingEntry]) -> VerificationResult:
        """
        Run the complete verification pipeline.

        Args:
            source: Path to filing/parsed.json, or MappedFilingEntry

        Returns:
            VerificationResult with all checks and summary
        """
        if isinstance(source, MappedFilingEntry):
            filing_id = f"{source.market}/{source.company}/{source.form}/{source.date}"
            self.logger.info(f"Starting verification pipeline for {filing_id}")
        else:
            self.logger.info(f"Starting verification pipeline for {source}")

        # Stage 1: Discovery
        self._last_discovery = self.run_discovery(source)

        # Log if no facts found but continue (same behavior as verification/ module)
        if not self._last_discovery.facts:
            self.logger.warning("Discovery found no facts - continuing with verification")

        # Stage 2: Preparation
        self._last_preparation = self.run_preparation(self._last_discovery)

        # Log if no facts after preparation but continue (same behavior as verification/ module)
        if not self._last_preparation.facts:
            self.logger.warning("Preparation produced no facts - continuing with verification")

        # Stage 3: Verification
        self._last_verification = self.run_verification(self._last_preparation)

        return self._last_verification

    def run_discovery(self, source: Union[Path, str, MappedFilingEntry]) -> DiscoveryResult:
        """
        Run Stage 1: Discovery.

        Args:
            source: Path to filing/parsed.json, or MappedFilingEntry

        Returns:
            DiscoveryResult with raw discovered data
        """
        return self._discovery.discover(source)

    def run_preparation(self, discovery: DiscoveryResult) -> PreparationResult:
        """
        Run Stage 2: Preparation.

        Args:
            discovery: DiscoveryResult from Stage 1

        Returns:
            PreparationResult with normalized, grouped data
        """
        return self._preparation.prepare(discovery)

    def run_verification(self, preparation: PreparationResult) -> VerificationResult:
        """
        Run Stage 3: Verification.

        Args:
            preparation: PreparationResult from Stage 2

        Returns:
            VerificationResult with all checks
        """
        return self._verification.verify(preparation)

    def _create_empty_result(
        self,
        discovery: DiscoveryResult,
        preparation: PreparationResult = None
    ) -> VerificationResult:
        """Create an empty result when pipeline cannot complete."""
        from .pipeline_data import VerificationSummary

        if preparation is None:
            preparation = PreparationResult(discovery=discovery)

        result = VerificationResult(
            preparation=preparation,
            summary=VerificationSummary(score=0.0),
        )

        # Add error as a check
        from .pipeline_data import VerificationCheck
        result.checks.append(VerificationCheck(
            check_name='pipeline_error',
            check_type='system',
            passed=False,
            severity='critical',
            message='Pipeline could not complete due to missing data',
            details={
                'discovery_errors': discovery.errors,
                'discovery_facts': len(discovery.facts),
            }
        ))

        return result

    # Accessors for last run results
    @property
    def last_discovery(self) -> Optional[DiscoveryResult]:
        """Get last discovery result."""
        return self._last_discovery

    @property
    def last_preparation(self) -> Optional[PreparationResult]:
        """Get last preparation result."""
        return self._last_preparation

    @property
    def last_verification(self) -> Optional[VerificationResult]:
        """Get last verification result."""
        return self._last_verification


# Convenience function for quick verification
def verify_filing(
    filing_path: Path | str,
    naming_strategy: str = 'canonical',
    binding_strategy: str = 'fallback',
    calculation_tolerance: float = 0.01,
) -> VerificationResult:
    """
    Quick verification of a filing.

    Args:
        filing_path: Path to filing directory or parsed.json
        naming_strategy: Concept naming strategy
        binding_strategy: Calculation binding strategy
        calculation_tolerance: Calculation tolerance

    Returns:
        VerificationResult
    """
    orchestrator = PipelineOrchestrator()
    orchestrator.configure(
        naming_strategy=naming_strategy,
        binding_strategy=binding_strategy,
        calculation_tolerance=calculation_tolerance,
    )
    return orchestrator.run(filing_path)


__all__ = ['PipelineOrchestrator', 'verify_filing']
