# Path: verification/engine/checks_v2/processors/__init__.py
"""
Verification Processors Module

3-stage pipeline for XBRL verification:
    Stage 1 (Discovery) -> Stage 2 (Preparation) -> Stage 3 (Verification)

Modules:
- pipeline_data: Data structures passed between stages
- orchestrator: Coordinates the 3-stage pipeline
- stage1_discovery: Extracts raw data from XBRL files
- stage2_preparation: Transforms and organizes data
- stage3_verification: Verifies and produces results

Usage:
    from verification.engine.checks_v2.processors import (
        PipelineOrchestrator,
        verify_filing,
    )

    # Quick verification
    result = verify_filing('/path/to/filing')
    print(f"Score: {result.summary.score}")

    # Detailed verification with configuration
    orchestrator = PipelineOrchestrator()
    orchestrator.configure(
        naming_strategy='local_name',
        binding_strategy='strict',
    )
    result = orchestrator.run('/path/to/filing')
"""

from .pipeline_data import (
    # Stage 1 output
    DiscoveredFact,
    DiscoveredContext,
    DiscoveredUnit,
    DiscoveredCalculation,
    DiscoveryResult,
    # Stage 2 output
    PreparedFact,
    PreparedContext,
    PreparedCalculation,
    FactGroup,
    PreparationResult,
    # Stage 3 output
    VerificationCheck,
    VerificationSummary,
    VerificationResult,
)

from .orchestrator import PipelineOrchestrator, verify_filing

from .stage1_discovery import DiscoveryProcessor
from .stage2_preparation import PreparationProcessor
from .stage3_verification import VerificationProcessor


__all__ = [
    # Orchestrator
    'PipelineOrchestrator',
    'verify_filing',
    # Stage processors
    'DiscoveryProcessor',
    'PreparationProcessor',
    'VerificationProcessor',
    # Data structures - Stage 1
    'DiscoveredFact',
    'DiscoveredContext',
    'DiscoveredUnit',
    'DiscoveredCalculation',
    'DiscoveryResult',
    # Data structures - Stage 2
    'PreparedFact',
    'PreparedContext',
    'PreparedCalculation',
    'FactGroup',
    'PreparationResult',
    # Data structures - Stage 3
    'VerificationCheck',
    'VerificationSummary',
    'VerificationResult',
]
