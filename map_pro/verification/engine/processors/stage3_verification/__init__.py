# Path: verification/engine/processors/stage3_verification/__init__.py
"""
Stage 3: Verification Processor

Performs verification checks on prepared data.
Produces final verification results and summary.

Components:
- VerificationProcessor: Main orchestrator
- HorizontalCheckRunner: Calculation linkbase verification
- VerticalCheckRunner: Cross-statement consistency checks
- SummaryBuilder: Score calculation and summary generation
"""

from .verification_processor import VerificationProcessor
from .horizontal_checks import HorizontalCheckRunner
from .vertical_checks import VerticalCheckRunner
from .summary_builder import SummaryBuilder

__all__ = [
    'VerificationProcessor',
    'HorizontalCheckRunner',
    'VerticalCheckRunner',
    'SummaryBuilder',
]
