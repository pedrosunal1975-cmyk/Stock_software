# Path: verification/engine/__init__.py
"""
Verification Engine for MAP PRO

Main verification engine with three-tier architecture:

1. CONSTANTS - All configuration values, no hardcoding in working files
   - tolerances: Numeric thresholds
   - patterns: Regex patterns for extraction
   - xbrl: XBRL specification constants
   - naming: Concept name handling constants
   - check_names: Standard check identifiers
   - enums: Type-safe enumerations

2. TOOLS - Specialized, reusable skill modules
   - naming: Concept name normalization
   - period: Period extraction and comparison
   - sign: Sign correction parsing and lookup
   - context: Context classification and grouping
   - fact: Fact finding and parsing
   - dimension: Dimensional structure handling
   - hierarchy: Parent/child relationships
   - calculation: Calculation weights and sums
   - tolerance: Decimal tolerance and comparisons

3. PROCESSORS - Multi-stage verification pipeline
   - stage1_discovery: Structure scanning, identification
   - stage2_preparation: Organization, preparation for verification
   - stage3_verification: Final verification and output

Design Principles:
- Tools are stateless and reusable across all processing stages
- Processors pick the right tool/technique for each situation
- Constants configure, tools do work, processors orchestrate
"""

__version__ = '2.0.0'
__author__ = 'MAP PRO Team'

# Main entry points
from .processors import (
    PipelineOrchestrator,
    verify_filing,
    VerificationResult,
    VerificationCheck,
    VerificationSummary,
)

__all__ = [
    # Pipeline
    'PipelineOrchestrator',
    'verify_filing',
    'VerificationResult',
    'VerificationCheck',
    'VerificationSummary',
]
