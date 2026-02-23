# Path: mat_acc/ratio_check/calculation/result_display.py
"""
Result Display

Console display functions for ratio analysis results.
Extracted from RatioCalculator to keep display logic separate
from calculation logic.
"""

from typing import Optional, Dict, List, Any

from ..ratio_models import (
    ComponentMatch, RatioResult, AnalysisResult,
)


def display_results(
    result: AnalysisResult,
    pmfv_corrections: list,
    normalizations: Optional[Dict] = None,
) -> None:
    """Display complete analysis results to console."""
    print()
    print("=" * 70)
    print(f"  RATIO ANALYSIS: {result.company}")
    print(
        f"  {result.market.upper()} | "
        f"{result.form} | {result.date}"
    )
    industry_name = result.summary.get('industry_display', '')
    if industry_name:
        print(f"  Industry: {industry_name}")
    print("=" * 70)

    display_pmfv_corrections(pmfv_corrections)
    display_components(result.component_matches)
    display_ratios(
        result.ratios,
        normalizations or result.normalizations,
    )
    display_summary(result.summary)


def display_pmfv_corrections(corrections: list) -> None:
    """Display PMFV corrections if any were made."""
    if not corrections:
        return
    print("\n  POST-MATCH VERIFICATION:")
    print("-" * 70)
    for c in corrections:
        old_name = c['old_concept'].split(':')[-1][:30]
        new_name = c['new_concept'].split(':')[-1][:30]
        old_v = (
            f"{c['old_value']:,.0f}" if c['old_value'] else '?'
        )
        new_v = (
            f"{c['new_value']:,.0f}" if c['new_value'] else '?'
        )
        print(
            f"    [FIX] {c['component']:22s} "
            f"{old_name} ({old_v}) -> {new_name} ({new_v})"
        )


def display_components(
    matches: List[ComponentMatch],
) -> None:
    """Display component matching section."""
    print("\n  COMPONENT MATCHING:")
    print("-" * 70)

    matched = [m for m in matches if m.matched]
    unmatched = [m for m in matches if not m.matched]

    if matched:
        print(f"\n  Matched ({len(matched)}):")
        for m in matched:
            _print_matched_component(m)

    if unmatched:
        print(f"\n  Unmatched ({len(unmatched)}):")
        for m in unmatched[:10]:
            print(f"    [--] {m.component_name}")
        if len(unmatched) > 10:
            print(f"    ... and {len(unmatched) - 10} more")


def _print_matched_component(m: ComponentMatch) -> None:
    """Print a single matched component line."""
    conf = f"{m.confidence:.2f}" if m.confidence else "N/A"
    label = m.label[:35] if m.label else ''
    if not label and m.matched_concept:
        label = m.matched_concept[:35]
    if m.value is not None:
        val = f"{m.value:>15,.0f}"
    else:
        val = f"{'[no value]':>15}"
    print(
        f"    [OK] {m.component_name:22s} -> "
        f"{label:35s} {val} ({conf})"
    )


def display_ratios(
    ratios: List[RatioResult],
    normalizations: Optional[Dict] = None,
) -> None:
    """Display financial ratios section with normalization."""
    print("\n  FINANCIAL RATIOS:")
    print("-" * 70)
    norms = normalizations or {}

    for r in ratios:
        if r.valid:
            _print_valid_ratio(r, norms)
        elif r.error:
            _print_invalid_ratio(r)


def _print_valid_ratio(r: RatioResult, norms: dict) -> None:
    """Print a valid ratio with optional normalization."""
    print(f"    [OK] {r.ratio_name:25s} = {r.value:10.4f}")
    num = (
        f"{r.numerator_value:,.0f}"
        if r.numerator_value else "N/A"
    )
    den = (
        f"{r.denominator_value:,.0f}"
        if r.denominator_value else "N/A"
    )
    print(f"         {r.formula}")
    print(f"         ({num} / {den})")
    ann = norms.get(r.ratio_name)
    if ann:
        print(
            f"         >> Normalized:"
            f" {ann.normalized_value:10.4f}"
            f"  ({ann.explanation})"
        )


def _print_invalid_ratio(r: RatioResult) -> None:
    """Print an invalid ratio with available info."""
    has_values = (
        r.numerator_value is not None
        or r.denominator_value is not None
    )
    if has_values:
        num = (
            f"{r.numerator_value:,.0f}"
            if r.numerator_value else "[missing]"
        )
        den = (
            f"{r.denominator_value:,.0f}"
            if r.denominator_value else "[missing]"
        )
        print(f"    [--] {r.ratio_name:25s} - {r.error}")
        print(f"         Values: {num} / {den}")
    else:
        print(f"    [--] {r.ratio_name:25s} - {r.error}")


def display_summary(s: Dict[str, Any]) -> None:
    """Display summary section with industry-aware counts."""
    print("\n  SUMMARY:")
    print("-" * 70)
    mc = s.get('matched_components', 0)
    ac = s.get(
        'applicable_components',
        s.get('total_components', 0),
    )
    na = s.get('not_applicable', 0)
    mr = s.get('match_rate', 0)
    print(f"    Components: {mc}/{ac} matched ({mr*100:.1f}%)")
    if na > 0:
        print(
            f"    Not applicable: {na} "
            f"(no matching concept in filing)"
        )
    vr = s.get('valid_ratios', 0)
    tr = s.get('total_ratios', 0)
    print(f"    Ratios: {vr}/{tr} calculated")
    print("\n" + "=" * 70)


__all__ = [
    'display_results',
    'display_components',
    'display_ratios',
    'display_summary',
]
