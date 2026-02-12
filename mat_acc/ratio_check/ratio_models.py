# Path: mat_acc/ratio_check/ratio_models.py
"""
Ratio Models

Data classes for ratio calculation results.
Used by RatioCalculator and consumed by display/reporting modules.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any


@dataclass
class ComponentMatch:
    """
    Result of matching a component.

    Attributes:
        component_name: Name of the component (e.g., 'current_assets')
        matched: Whether a match was found
        matched_concept: Matched concept QName if found
        confidence: Match confidence score (0-1)
        value: Numeric value if available
        label: Human-readable label
        rule_breakdown: Breakdown of rule scores
        fallback_formula: Composite formula to try if no value found
    """
    component_name: str
    matched: bool = False
    matched_concept: Optional[str] = None
    confidence: float = 0.0
    value: Optional[float] = None
    label: Optional[str] = None
    rule_breakdown: Dict[str, float] = field(default_factory=dict)
    fallback_formula: Optional[str] = None


@dataclass
class RatioResult:
    """
    Result of a ratio calculation.

    Attributes:
        ratio_name: Name of the ratio
        value: Calculated ratio value
        formula: Formula description
        numerator: Numerator component name
        denominator: Denominator component name
        numerator_value: Numerator value used
        denominator_value: Denominator value used
        valid: Whether calculation was successful
        error: Error message if calculation failed
    """
    ratio_name: str
    value: Optional[float] = None
    formula: str = ''
    numerator: str = ''
    denominator: str = ''
    numerator_value: Optional[float] = None
    denominator_value: Optional[float] = None
    valid: bool = False
    error: Optional[str] = None


@dataclass
class AnalysisResult:
    """
    Complete analysis result for a filing.

    Attributes:
        company: Company name
        market: Market identifier
        form: Form type
        date: Filing date
        component_matches: Matched components
        ratios: Calculated ratios
        summary: Summary statistics
    """
    company: str
    market: str
    form: str
    date: str
    component_matches: List[ComponentMatch] = field(default_factory=list)
    ratios: List[RatioResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


__all__ = ['ComponentMatch', 'RatioResult', 'AnalysisResult']
