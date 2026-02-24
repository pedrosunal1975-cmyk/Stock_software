# Path: mat_acc/ratio_check/calculation/result_display.py
"""
Result Display

Console display functions for ratio analysis results.
Extracted from RatioCalculator to keep display logic separate
from calculation logic. Includes plausibility annotations.
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

    # Build inline annotation lookup from plausibility
    p_index = _build_plausibility_index(result.plausibility)

    display_pmfv_corrections(pmfv_corrections)
    display_components(result.component_matches, p_index)
    display_ratios(
        result.ratios,
        normalizations or result.normalizations,
        p_index,
    )
    display_plausibility(result.plausibility)
    display_summary(result.summary, result.plausibility)


def _build_plausibility_index(
    plausibility,
) -> Dict[str, list]:
    """Build target -> findings lookup for inline display."""
    index: Dict[str, list] = {}
    if not plausibility:
        return index
    for f in plausibility.findings:
        index.setdefault(f.target, []).append(f)
    return index


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
    p_index: Optional[Dict] = None,
) -> None:
    """Display component matching section."""
    print("\n  COMPONENT MATCHING:")
    print("-" * 70)
    p_index = p_index or {}

    matched = [m for m in matches if m.matched]
    unmatched = [m for m in matches if not m.matched]

    confident = [m for m in matched if m.match_quality != 'uncertain']
    uncertain = [m for m in matched if m.match_quality == 'uncertain']

    if confident:
        print(f"\n  Matched ({len(confident)}):")
        for m in confident:
            _print_matched_component(m, p_index)

    if uncertain:
        print(f"\n  Uncertain ({len(uncertain)}):")
        for m in uncertain:
            _print_uncertain_component(m)

    if unmatched:
        print(f"\n  Unmatched ({len(unmatched)}):")
        for m in unmatched[:10]:
            print(f"    [--] {m.component_name}")
        if len(unmatched) > 10:
            print(f"    ... and {len(unmatched) - 10} more")


def _print_matched_component(
    m: ComponentMatch, p_index: Dict,
) -> None:
    """Print a single matched component line with annotation."""
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
    # Inline plausibility annotation (warnings only)
    findings = p_index.get(m.component_name, [])
    for f in findings:
        if f.severity.value in ('warning', 'alert'):
            print(
                f"         {f.severity_tag} {f.message}"
            )


def _print_uncertain_component(m: ComponentMatch) -> None:
    """Print an uncertain match (blocked from value loading)."""
    label = m.label[:35] if m.label else ''
    if not label and m.matched_concept:
        label = m.matched_concept[:35]
    print(
        f"    [??] {m.component_name:22s} -> "
        f"{label:35s} [uncertain match]"
    )


def display_ratios(
    ratios: List[RatioResult],
    normalizations: Optional[Dict] = None,
    p_index: Optional[Dict] = None,
) -> None:
    """Display financial ratios section with normalization."""
    print("\n  FINANCIAL RATIOS:")
    print("-" * 70)
    norms = normalizations or {}
    p_index = p_index or {}

    for r in ratios:
        if r.valid:
            _print_valid_ratio(r, norms, p_index)
        elif r.error:
            _print_invalid_ratio(r)


def _print_valid_ratio(
    r: RatioResult, norms: dict, p_index: Dict,
) -> None:
    """Print a valid ratio with optional annotations."""
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
    # Inline plausibility (warnings/advisories)
    findings = p_index.get(r.ratio_name, [])
    for f in findings:
        if f.severity.value in ('warning', 'alert', 'advisory'):
            print(
                f"         {f.severity_tag} {f.message}"
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


def display_plausibility(plausibility) -> None:
    """Display plausibility audit summary section."""
    if not plausibility or not plausibility.findings:
        return

    counts = plausibility.summary_counts
    w = counts.get('warning', 0) + counts.get('alert', 0)
    a = counts.get('advisory', 0)
    i = counts.get('info', 0)

    print("\n  PLAUSIBILITY AUDIT:")
    print("-" * 70)
    print(
        f"    Findings: {len(plausibility.findings)} "
        f"({w} warning, {a} advisory, {i} info)"
    )

    for f in plausibility.findings:
        src = f"[{f.source_tag}]"
        print(f"    {f.severity_tag} {f.target:25s} {src}")
        print(f"        {f.message}")


def display_summary(
    s: Dict[str, Any], plausibility=None,
) -> None:
    """Display summary section with industry-aware counts."""
    print("\n  SUMMARY:")
    print("-" * 70)
    mc = s.get('matched_components', 0)
    ac = s.get(
        'applicable_components',
        s.get('total_components', 0),
    )
    na = s.get('not_applicable', 0)
    uc = s.get('uncertain_components', 0)
    mr = s.get('match_rate', 0)
    print(f"    Components: {mc}/{ac} matched ({mr*100:.1f}%)")
    if uc > 0:
        print(f"    Uncertain: {uc} (value blocked)")
    if na > 0:
        print(
            f"    Not applicable: {na} "
            f"(no matching concept in filing)"
        )
    vr = s.get('valid_ratios', 0)
    tr = s.get('total_ratios', 0)
    print(f"    Ratios: {vr}/{tr} calculated")
    if plausibility and plausibility.findings:
        w = len(plausibility.warnings)
        a = len(plausibility.advisories)
        print(
            f"    Plausibility: {w} warnings, {a} advisories"
        )
    print("\n" + "=" * 70)


__all__ = [
    'display_results',
    'display_components',
    'display_ratios',
    'display_plausibility',
    'display_summary',
]
