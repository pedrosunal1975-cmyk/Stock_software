# Path: mapping/statement/models.py
"""
Statement Data Models

Data classes representing statements and facts.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StatementFact:
    """
    A fact as it appears in a statement.

    Contains both raw XBRL values and calculated values for verification:
    - value: Raw XBRL value (e.g., "26755.7")
    - decimals: XBRL decimals attribute (e.g., "-5")
    - display_value: Scaled value for verification (e.g., "2675570000")
    - formatted_value: Human-readable (e.g., "$2,675,570,000")
    - scaling_factor: 10^(-decimals) for reference (e.g., 100000)

    Period information (critical for calculation verification):
    - period_type: 'instant' or 'duration'
    - period_start: Start date for duration periods (None for instant)
    - period_end: End date (for both instant and duration)
    """
    concept: str
    value: any
    context_ref: str
    unit_ref: Optional[str] = None
    decimals: Optional[str] = None
    precision: Optional[str] = None
    order: Optional[float] = None
    preferred_label: Optional[str] = None
    level: int = 0
    parent_concept: Optional[str] = None
    metadata: dict[str, any] = field(default_factory=dict)

    # Period information (from XBRL context)
    period_type: Optional[str] = None       # 'instant' or 'duration'
    period_start: Optional[str] = None      # Start date (duration only)
    period_end: Optional[str] = None        # End date (instant or duration end)

    # Calculated values (added by FactEnricher)
    display_value: Optional[str] = None      # Scaled value: value × 10^(-decimals)
    formatted_value: Optional[str] = None    # Human-readable: "$2,675,570,000"
    scaling_factor: Optional[int] = None     # 10^(-decimals) for reference

    # Dimensional qualifiers (from XBRL context segment/scenario)
    # Example: {"us-gaap:StatementEquityComponentsAxis": "us-gaap:RetainedEarningsMember"}
    dimensions: dict[str, str] = field(default_factory=dict)

    # iXBRL-specific attributes (from inline XBRL instance)
    sign: Optional[str] = None               # Sign attribute ("-" for negated values)
    scale: Optional[str] = None              # iXBRL scale (power of 10, e.g., "6" for millions)
    format: Optional[str] = None             # iXBRL format (e.g., "ixt:num-dot-decimal")
    is_nil: bool = False                     # Whether fact value is nil (xsi:nil="true")
    fact_id: Optional[str] = None            # Unique fact identifier from XBRL


@dataclass
class Statement:
    """A financial statement as declared by company."""
    role_uri: str
    role_definition: Optional[str] = None
    statement_type: Optional[str] = None
    facts: list[StatementFact] = field(default_factory=list)
    hierarchy: dict[str, any] = field(default_factory=dict)
    metadata: dict[str, any] = field(default_factory=dict)


@dataclass
class StatementSet:
    """Complete set of statements from a filing."""
    statements: list[Statement] = field(default_factory=list)
    role_uri_to_statement: dict[str, Statement] = field(default_factory=dict)
    concept_to_roles: dict[str, list[str]] = field(default_factory=dict)
    metadata: dict[str, any] = field(default_factory=dict)