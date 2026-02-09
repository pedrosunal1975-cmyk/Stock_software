# Path: verification/engine/checks_v2/processors/pipeline_data.py
"""
Pipeline Data Structures for Verification Processing

Data containers passed between processing stages.
Each stage enriches the data and passes it to the next stage.

PIPELINE FLOW:
    Input Files -> Stage1 (Discovery) -> Stage2 (Preparation) -> Stage3 (Verification) -> Output

Each stage produces immutable output that the next stage consumes.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from pathlib import Path


# ==============================================================================
# STAGE 1 OUTPUT: Discovery Results
# ==============================================================================

@dataclass
class DiscoveredFact:
    """
    A fact discovered from the XBRL instance.

    Raw fact data before normalization and grouping.
    """
    concept: str                    # Original concept name
    value: Any                      # Raw value (may be string)
    context_id: str                 # Context reference
    unit_ref: Optional[str] = None  # Unit reference
    decimals: Optional[int] = None  # Decimal precision
    is_nil: bool = False            # xsi:nil attribute
    sign: Optional[str] = None      # iXBRL sign attribute
    format: Optional[str] = None    # iXBRL format attribute
    source_file: str = ""           # Source file path


@dataclass
class DiscoveredContext:
    """
    A context discovered from the XBRL instance.

    Raw context data before classification.
    """
    context_id: str
    period_type: str = ""           # 'instant' or 'duration'
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    instant_date: Optional[str] = None
    entity_id: str = ""
    dimensions: dict = field(default_factory=dict)  # dimension -> member


@dataclass
class DiscoveredUnit:
    """
    A unit discovered from the XBRL instance.
    """
    unit_id: str
    measure: str = ""               # e.g., 'iso4217:USD'
    numerator: Optional[str] = None # For divide units
    denominator: Optional[str] = None


@dataclass
class DiscoveredCalculation:
    """
    A calculation relationship discovered from linkbase.
    """
    parent_concept: str
    child_concept: str
    weight: float
    order: float = 0.0
    role: str = ""
    source: str = ""                # 'company' or 'taxonomy'


@dataclass
class DiscoveryResult:
    """
    Complete output of Stage 1 Discovery.

    Contains all raw discovered data from XBRL files.
    """
    # Filing identification
    filing_path: Path
    instance_file: Optional[Path] = None

    # Discovered elements
    facts: list[DiscoveredFact] = field(default_factory=list)
    contexts: list[DiscoveredContext] = field(default_factory=list)
    units: list[DiscoveredUnit] = field(default_factory=list)
    calculations: list[DiscoveredCalculation] = field(default_factory=list)

    # Metadata
    entry_point: Optional[str] = None
    taxonomy_refs: list[str] = field(default_factory=list)
    namespaces: dict[str, str] = field(default_factory=dict)

    # Discovery statistics
    stats: dict = field(default_factory=dict)

    # Errors encountered
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ==============================================================================
# STAGE 2 OUTPUT: Preparation Results
# ==============================================================================

@dataclass
class PreparedFact:
    """
    A fact after normalization and validation.

    Ready for verification with normalized concept name and parsed value.
    """
    concept: str                    # Normalized concept name (lowercase)
    original_concept: str           # Original concept name
    value: float                    # Parsed numeric value
    context_id: str
    unit: Optional[str] = None
    decimals: Optional[int] = None
    sign_correction: int = 1        # 1 or -1 from iXBRL sign
    is_dimensional: bool = False    # From dimensional context


@dataclass
class PreparedContext:
    """
    A context after classification.
    """
    context_id: str
    period_type: str                # 'instant' or 'duration'
    period_key: str                 # Normalized period identifier
    year: Optional[int] = None
    is_dimensional: bool = False
    dimensions: dict = field(default_factory=dict)


@dataclass
class PreparedCalculation:
    """
    A calculation tree ready for verification.
    """
    parent_concept: str             # Normalized
    original_parent: str            # Original
    children: list[tuple[str, float]] = field(default_factory=list)  # (concept, weight)
    role: str = ""
    source: str = ""


@dataclass
class FactGroup:
    """
    Facts grouped by context (C-Equal group).
    """
    context_id: str
    period_key: str
    is_dimensional: bool
    facts: dict[str, PreparedFact] = field(default_factory=dict)  # concept -> fact


@dataclass
class PreparationResult:
    """
    Complete output of Stage 2 Preparation.

    Contains organized, normalized data ready for verification.
    """
    # Source
    discovery: DiscoveryResult

    # Prepared data
    facts: list[PreparedFact] = field(default_factory=list)
    contexts: dict[str, PreparedContext] = field(default_factory=dict)
    calculations: list[PreparedCalculation] = field(default_factory=list)

    # Grouped data (for C-Equal verification)
    fact_groups: dict[str, FactGroup] = field(default_factory=dict)  # context_id -> group
    all_facts_by_concept: dict[str, list] = field(default_factory=dict)  # concept -> [(ctx, val, unit, dec)]

    # Sign corrections parsed from instance
    sign_corrections: dict[tuple[str, str], int] = field(default_factory=dict)  # (concept, ctx) -> correction

    # Duplicate detection results
    duplicates: dict[str, Any] = field(default_factory=dict)

    # Preparation statistics
    stats: dict = field(default_factory=dict)

    # Issues found during preparation
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ==============================================================================
# STAGE 3 OUTPUT: Verification Results
# ==============================================================================

@dataclass
class VerificationCheck:
    """
    Result of a single verification check.
    """
    check_name: str
    check_type: str                 # 'horizontal', 'vertical', 'library'
    passed: bool
    severity: str                   # 'critical', 'warning', 'info'
    message: str

    # Values
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    difference: Optional[float] = None

    # Context
    concept: str = ""
    context_id: str = ""
    role: str = ""

    # Details
    details: dict = field(default_factory=dict)


@dataclass
class VerificationSummary:
    """
    Summary statistics for verification.
    """
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    warnings: int = 0

    critical_issues: int = 0
    warning_issues: int = 0
    info_issues: int = 0

    score: float = 0.0              # Overall score (0-100)


@dataclass
class VerificationResult:
    """
    Complete output of Stage 3 Verification.

    Final verification results ready for output.
    """
    # Source
    preparation: PreparationResult

    # Verification results
    checks: list[VerificationCheck] = field(default_factory=list)

    # Summary
    summary: VerificationSummary = field(default_factory=VerificationSummary)

    # Categorized results
    horizontal_checks: list[VerificationCheck] = field(default_factory=list)
    vertical_checks: list[VerificationCheck] = field(default_factory=list)
    library_checks: list[VerificationCheck] = field(default_factory=list)

    # Output metadata
    verification_timestamp: str = ""
    processing_time_ms: float = 0.0


__all__ = [
    # Stage 1
    'DiscoveredFact',
    'DiscoveredContext',
    'DiscoveredUnit',
    'DiscoveredCalculation',
    'DiscoveryResult',
    # Stage 2
    'PreparedFact',
    'PreparedContext',
    'PreparedCalculation',
    'FactGroup',
    'PreparationResult',
    # Stage 3
    'VerificationCheck',
    'VerificationSummary',
    'VerificationResult',
]
