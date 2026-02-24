# Path: mat_acc/ratio_check/plausibility/proportion_checks.py
"""
Proportion Checks

Cross-component proportionality: verifies that pairs of components
have values in a reasonable ratio to each other.

Example: SBC should be 0.5-50% of SG&A. If SBC = 70 and SG&A = 376,110
that is 0.02% - flagged as WARNING.

Also detects scale anomalies: values suspiciously small relative to
company size (revenue) combined with low match confidence.
"""

from typing import Dict, List, Optional

from .models import Finding, Severity, ExpectationSource
from .market_norms import (
    PROPORTION_NORMS,
    SCALE_ANOMALY_THRESHOLD,
    SCALE_LOW_CONFIDENCE_CUTOFF,
)


def check_proportions(
    components: Dict[str, dict],
    market: str,
) -> List[Finding]:
    """
    Run all proportion checks on component values.

    Args:
        components: Dict of component_name -> {value, confidence, ...}
        market: Market identifier for context

    Returns:
        List of Finding objects
    """
    findings = []
    findings.extend(_check_pairs(components))
    findings.extend(_check_scale_anomalies(components))
    return findings


def _check_pairs(components: Dict[str, dict]) -> List[Finding]:
    """Check component-pair proportionality from PROPORTION_NORMS."""
    findings = []

    for comp, ref, min_pct, max_pct, basis in PROPORTION_NORMS:
        c_data = components.get(comp)
        r_data = components.get(ref)
        if not c_data or not r_data:
            continue

        c_val = c_data.get('value')
        r_val = r_data.get('value')
        if c_val is None or r_val is None or r_val == 0:
            continue

        ratio = abs(c_val) / abs(r_val)

        if ratio < min_pct or ratio > max_pct:
            finding = _build_proportion_finding(
                comp, ref, c_val, r_val, ratio,
                min_pct, max_pct, basis, c_data,
            )
            findings.append(finding)

    return findings


def _build_proportion_finding(
    comp: str, ref: str,
    c_val: float, r_val: float, ratio: float,
    min_pct: float, max_pct: float,
    basis: str, c_data: dict,
) -> Finding:
    """Build a Finding for a proportion anomaly."""
    pct_str = f"{ratio*100:.2f}%"
    conf = c_data.get('confidence', 100)

    if conf < SCALE_LOW_CONFIDENCE_CUTOFF and ratio < min_pct:
        severity = Severity.WARNING
    elif ratio < min_pct * 0.1 or ratio > max_pct * 2:
        severity = Severity.WARNING
    else:
        severity = Severity.ADVISORY

    msg = (
        f"{comp} = {c_val:,.0f} is {pct_str} of "
        f"{ref} = {r_val:,.0f}. "
        f"Expected: {min_pct*100:.1f}-{max_pct*100:.1f}%"
    )
    if conf < SCALE_LOW_CONFIDENCE_CUTOFF:
        msg += f". Low match confidence ({conf:.0f})"

    return Finding(
        severity=severity,
        category='proportion',
        target=comp,
        message=msg,
        actual_value=ratio,
        expectation_source=ExpectationSource.NORMATIVE,
        expectation_basis=basis,
        expected_range=(min_pct, max_pct),
    )


def _check_scale_anomalies(
    components: Dict[str, dict],
) -> List[Finding]:
    """Flag components with suspiciously small values."""
    findings = []
    rev_data = components.get('revenue')
    if not rev_data or not rev_data.get('value'):
        return findings

    revenue = abs(rev_data['value'])
    if revenue == 0:
        return findings

    for comp_name, data in components.items():
        if comp_name == 'revenue':
            continue
        finding = _check_single_scale(
            comp_name, data, revenue,
        )
        if finding:
            findings.append(finding)

    return findings


def _check_single_scale(
    comp_name: str, data: dict, revenue: float,
) -> Optional[Finding]:
    """Check a single component for scale anomaly."""
    val = data.get('value')
    conf = data.get('confidence', 100)
    if val is None or conf >= SCALE_LOW_CONFIDENCE_CUTOFF:
        return None

    ratio = abs(val) / revenue
    if ratio >= SCALE_ANOMALY_THRESHOLD:
        return None

    pct = f"{ratio*100:.4f}%"
    return Finding(
        severity=Severity.WARNING,
        category='scale',
        target=comp_name,
        message=(
            f"{comp_name} = {val:,.0f} is {pct} of revenue "
            f"({revenue:,.0f}). Match confidence: {conf:.0f}. "
            f"Possible detail/disclosure value"
        ),
        actual_value=val,
        expectation_source=ExpectationSource.NORMATIVE,
        expectation_basis='value too small for company size + low confidence',
    )


__all__ = ['check_proportions']
