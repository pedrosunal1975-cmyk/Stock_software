# Path: mat_acc/ratio_check/plausibility/coherence_checks.py
"""
Coherence Checks

Internal consistency: do the numbers tell a coherent story?
Checks cross-component relationships that should logically hold
regardless of market or industry.
"""

from typing import Dict, List, Optional

from .models import Finding, Severity, ExpectationSource


def check_coherence(
    components: Dict[str, dict],
    ratios: Dict[str, dict],
) -> List[Finding]:
    """
    Run all coherence checks on components and ratios.

    Args:
        components: Dict of component_name -> {value, confidence, ...}
        ratios: Dict of ratio_name -> {value, valid, ...}

    Returns:
        List of Finding objects
    """
    findings = []
    findings.extend(_check_sign_coherence(components))
    findings.extend(_check_loss_profile(components))
    findings.extend(_check_balance_sheet(components))
    return findings


def _check_sign_coherence(
    components: Dict[str, dict],
) -> List[Finding]:
    """Check that related components have coherent signs."""
    findings = []

    # Revenue positive + Gross Profit positive + Operating Income negative
    # is coherent (high opex). But Revenue negative is always suspicious.
    rev = _get_val(components, 'revenue')
    if rev is not None and rev < 0:
        findings.append(Finding(
            severity=Severity.ALERT,
            category='coherence',
            target='revenue',
            message=(
                f"Revenue = {rev:,.0f} is negative. "
                f"Negative revenue is extremely unusual"
            ),
            actual_value=rev,
            expectation_source=ExpectationSource.NORMATIVE,
            expectation_basis='revenue should be non-negative',
        ))

    # COGS should generally be positive (cost)
    cogs = _get_val(components, 'cost_of_goods_sold')
    if cogs is not None and cogs < 0:
        findings.append(Finding(
            severity=Severity.WARNING,
            category='coherence',
            target='cost_of_goods_sold',
            message=(
                f"COGS = {cogs:,.0f} is negative. "
                f"Usually indicates a sign convention issue"
            ),
            actual_value=cogs,
            expectation_source=ExpectationSource.NORMATIVE,
            expectation_basis='COGS should be non-negative',
        ))

    return findings


def _check_loss_profile(
    components: Dict[str, dict],
) -> List[Finding]:
    """Annotate loss-making company profile for context."""
    findings = []

    ni = _get_val(components, 'net_income')
    gp = _get_val(components, 'gross_profit')
    oi = _get_val(components, 'operating_income')

    if ni is None:
        return findings

    if ni < 0 and gp is not None and gp < 0:
        findings.append(Finding(
            severity=Severity.INFO,
            category='coherence',
            target='net_income',
            message=(
                f"Loss-making company: negative gross profit "
                f"({gp:,.0f}) and net income ({ni:,.0f}). "
                f"Selling below cost"
            ),
            actual_value=ni,
            expectation_source=ExpectationSource.NORMATIVE,
            expectation_basis='loss profile annotation',
        ))
    elif ni < 0 and oi is not None and oi < 0:
        findings.append(Finding(
            severity=Severity.INFO,
            category='coherence',
            target='net_income',
            message=(
                f"Operating loss: negative operating income "
                f"({oi:,.0f}) and net income ({ni:,.0f})"
            ),
            actual_value=ni,
            expectation_source=ExpectationSource.NORMATIVE,
            expectation_basis='loss profile annotation',
        ))

    return findings


def _check_balance_sheet(
    components: Dict[str, dict],
) -> List[Finding]:
    """Check balance sheet coherence."""
    findings = []

    equity = _get_val(components, 'total_equity')
    retained = _get_val(components, 'retained_earnings')

    if equity is not None and equity < 0:
        findings.append(Finding(
            severity=Severity.INFO,
            category='coherence',
            target='total_equity',
            message=(
                f"Negative equity ({equity:,.0f}). "
                f"Accumulated losses exceed contributed capital"
            ),
            actual_value=equity,
            expectation_source=ExpectationSource.NORMATIVE,
            expectation_basis='negative equity annotation',
        ))

    # Retained earnings hugely negative vs equity positive = context
    if (
        retained is not None and equity is not None
        and retained < 0 and equity > 0
        and abs(retained) > equity * 2
    ):
        findings.append(Finding(
            severity=Severity.ADVISORY,
            category='coherence',
            target='retained_earnings',
            message=(
                f"Accumulated deficit ({retained:,.0f}) exceeds "
                f"2x total equity ({equity:,.0f}). Heavy reliance "
                f"on external capital"
            ),
            actual_value=retained,
            expectation_source=ExpectationSource.NORMATIVE,
            expectation_basis='capital structure observation',
        ))

    return findings


def _get_val(
    components: Dict[str, dict], name: str,
) -> Optional[float]:
    """Safely get a component value."""
    data = components.get(name)
    if data and data.get('value') is not None:
        return data['value']
    return None


__all__ = ['check_coherence']
