# Path: verification/__init__.py
"""
Verification Module v2

Validates mapped financial statements for quality assessment.
Determines whether company-provided XBRL filings are consistent,
accurate, and suitable for financial analysis.

Key Principle: We do NOT correct company data. We detect and
report inconsistencies in what companies have declared.

Architecture:
- INPUT: loaders/ - Data access from mapper, parser, XBRL files
- PROCESS: engine/ - 3-stage verification pipeline (discovery -> preparation -> verification)
- OUTPUT: output/ - Reports, summaries

Usage:
    from verification.engine import PipelineOrchestrator, verify_filing

    # Quick verification
    result = verify_filing('/path/to/parsed.json')
    print(f"Score: {result.summary.score}")

    # Detailed verification
    orchestrator = PipelineOrchestrator()
    orchestrator.configure(naming_strategy='local_name')
    result = orchestrator.run('/path/to/filing')
"""

__version__ = '2.0.0'
__author__ = 'MAP PRO'

# Core exports for convenient access
from .engine import (
    PipelineOrchestrator,
    verify_filing,
    VerificationResult,
    VerificationCheck,
    VerificationSummary,
)

__all__ = [
    '__version__',
    '__author__',
    'PipelineOrchestrator',
    'verify_filing',
    'VerificationResult',
    'VerificationCheck',
    'VerificationSummary',
]
