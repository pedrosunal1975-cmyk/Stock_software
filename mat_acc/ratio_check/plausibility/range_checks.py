# Path: mat_acc/ratio_check/plausibility/range_checks.py
"""
Range Checks

Validates calculated ratios against expected ranges.
Uses market-specific norms when available, with declared values
from the company's own filing taking precedence.

Findings are purely interpretive - ratios are never modified.
"""

from typing import Dict, List, Optional

from .models import Finding, Severity, ExpectationSource
from .market_norms import get_ratio_range
from .declared_resolver import DeclaredResolver


def check_ranges(
    ratios: Dict[str, dict],
    market: str,
    declared: DeclaredResolver,
) -> List[Finding]:
    """
    Check all ratio values against expected ranges.

    Args:
        ratios: Dict of ratio_name -> {value, valid, ...}
        market: Market identifier for norm selection
        declared: DeclaredResolver with company-declared values

    Returns:
        List of Finding objects
    """
    findings = []

    for ratio_name, data in ratios.items():
        if not data.get('valid') or data.get('value') is None:
            continue
        value = data['value']

        # Check against declared value first, then normative
        finding = _check_declared(
            ratio_name, value, declared,
        )
        if finding:
            findings.append(finding)
            continue

        finding = _check_normative(
            ratio_name, value, market,
        )
        if finding:
            findings.append(finding)

    return findings


def _check_declared(
    ratio_name: str, value: float,
    declared: DeclaredResolver,
) -> Optional[Finding]:
    """Check ratio against company-declared value."""
    declared_val = declared.get_for_target(ratio_name)
    if declared_val is None:
        return None

    # Normalize: some declared rates are 0-100, ours are 0-1
    if abs(declared_val) > 1 and abs(value) <= 1:
        declared_val = declared_val / 100.0

    diff = abs(value - declared_val)
    tolerance = max(abs(declared_val) * 0.15, 0.02)

    if diff <= tolerance:
        return Finding(
            severity=Severity.INFO,
            category='range',
            target=ratio_name,
            message=(
                f"{ratio_name} = {value:.4f} matches "
                f"company-declared {declared_val:.4f}"
            ),
            actual_value=value,
            expectation_source=ExpectationSource.DECLARED,
            expectation_basis='company filing',
            declared_value=declared_val,
        )

    severity = Severity.WARNING if diff > tolerance * 3 else Severity.ADVISORY
    return Finding(
        severity=severity,
        category='range',
        target=ratio_name,
        message=(
            f"{ratio_name} = {value:.4f} differs from "
            f"company-declared {declared_val:.4f} "
            f"(diff: {diff:.4f})"
        ),
        actual_value=value,
        expectation_source=ExpectationSource.DECLARED,
        expectation_basis='company filing',
        declared_value=declared_val,
    )


def _check_normative(
    ratio_name: str, value: float, market: str,
) -> Optional[Finding]:
    """Check ratio against normative (hardcoded) range."""
    norm = get_ratio_range(ratio_name, market)
    if norm is None:
        return None

    warn_min, warn_max, basis = norm

    if warn_min is not None and value < warn_min:
        return _build_range_finding(
            ratio_name, value, warn_min, warn_max,
            basis, 'below',
        )

    if warn_max is not None and value > warn_max:
        return _build_range_finding(
            ratio_name, value, warn_min, warn_max,
            basis, 'above',
        )

    return None


def _build_range_finding(
    ratio_name: str, value: float,
    warn_min: Optional[float], warn_max: Optional[float],
    basis: str, direction: str,
) -> Finding:
    """Build a Finding for a range violation."""
    # Determine severity based on how far outside
    if direction == 'below' and warn_min is not None:
        excess = abs(value - warn_min)
        span = abs(warn_max - warn_min) if warn_max else 1.0
    else:
        excess = abs(value - warn_max) if warn_max else 0
        span = abs(warn_max - warn_min) if warn_min else 1.0

    if span > 0 and excess / span > 1.0:
        severity = Severity.WARNING
    else:
        severity = Severity.ADVISORY

    lo = f"{warn_min:.2f}" if warn_min is not None else 'N/A'
    hi = f"{warn_max:.2f}" if warn_max is not None else 'N/A'

    return Finding(
        severity=severity,
        category='range',
        target=ratio_name,
        message=(
            f"{ratio_name} = {value:.4f} is {direction} "
            f"expected range [{lo}, {hi}]"
        ),
        actual_value=value,
        expectation_source=ExpectationSource.NORMATIVE,
        expectation_basis=basis,
        expected_range=(warn_min, warn_max),
    )


__all__ = ['check_ranges']
