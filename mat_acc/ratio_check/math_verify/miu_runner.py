# Path: mat_acc/ratio_check/math_verify/miu_runner.py
"""
MIU Runner

Integrates Mathematical Integrity Unit layers into the analysis
pipeline. Provides standalone functions called by the orchestrator.

Layer 1: iXBRL fact extraction with sign/scale analysis
Layer 2: Reconciliation against mapped values
Layer 3: Mathematical identity validation (post-matching)
Scale: Post-ratio normalization from iXBRL scale metadata
"""

from core.logger.ipo_logging import get_process_logger


logger = get_process_logger('miu_runner')


def run_math_verify(
    extractor, reconciler, sign_analyzer,
    xbrl_dir, value_lookup, market='sec',
) -> tuple:
    """
    Run MIU Layers 1-2 on loaded values.

    Layer 1: Extract numeric truth from iXBRL source
    Layer 2: Reconcile against parsed/mapped values

    Returns:
        Tuple of (corrections_applied, ixbrl_facts)
    """
    ixbrl_facts = extractor.extract_from_directory(xbrl_dir)
    if not ixbrl_facts:
        logger.warning("MIU: No facts extracted from iXBRL")
        return 0, []

    print(
        f"  MIU Layer 1: Extracted {len(ixbrl_facts)} "
        f"primary facts from iXBRL"
    )

    sign_checks = sign_analyzer.analyze(ixbrl_facts)
    sign_summary = sign_analyzer.summarize(sign_checks)
    _print_sign_summary(sign_summary)

    loaded_values = _build_loaded_values(
        ixbrl_facts, extractor.get_context_filter(),
        value_lookup,
    )

    results = reconciler.reconcile(
        ixbrl_facts=ixbrl_facts,
        parsed_values=loaded_values,
    )
    corrections = reconciler.get_corrections(results)
    summary = reconciler.get_summary(results)

    print(
        f"  MIU Layer 2: {summary['sign_corrections']} sign "
        f"corrections, {summary['scale_diffs']} scale diffs "
        f"(expected), {summary['value_matches']} matched"
    )

    if corrections and market.lower() != 'esef':
        corrected = value_lookup.apply_corrections(corrections)
        print(f"  MIU: Applied {corrected} sign corrections")
        for concept, val in list(corrections.items())[:3]:
            local = (
                concept.split(':')[-1]
                if ':' in concept else concept
            )
            print(f"    - {local}: corrected to {val:,.0f}")
        return corrected, ixbrl_facts

    if corrections:
        print(
            f"  MIU: Skipped {len(corrections)} sign "
            f"corrections (ESEF uses business convention)"
        )
    return 0, ixbrl_facts


def _print_sign_summary(sign_summary: dict) -> None:
    """Print sign analysis results."""
    if sign_summary['anomalies'] > 0:
        print(
            f"  MIU Sign Check: "
            f"{sign_summary['anomalies']} anomalies detected"
        )
        for concept, value, note in (
            sign_summary['anomaly_concepts'][:3]
        ):
            local = (
                concept.split(':')[-1]
                if ':' in concept else concept
            )
            print(f"    - {local}: {value:,.0f} ({note})")
    else:
        print(
            f"  MIU Sign Check: "
            f"{sign_summary['consistent']} facts consistent"
        )


def _build_loaded_values(
    ixbrl_facts, ctx_filter, value_lookup,
) -> dict:
    """Build loaded values map for reconciliation."""
    loaded_values = {}
    for fact in ixbrl_facts:
        period_end = None
        ctx = ctx_filter.get_context(fact.context_ref)
        if ctx:
            if ctx.period_type == 'instant':
                period_end = ctx.instant_date
            elif ctx.period_type == 'duration':
                period_end = ctx.end_date
        existing = value_lookup.get_value(
            fact.concept, period_end=period_end,
        )
        if existing is not None:
            loaded_values[fact.concept] = existing
    return loaded_values


def run_identity_checks(validator, component_matches) -> None:
    """
    Run Layer 3 identity validation after matching.

    Args:
        validator: IdentityValidator instance
        component_matches: List of ComponentMatch with values
    """
    values = {}
    for match in component_matches:
        if match.value is not None:
            values[match.component_name] = match.value

    checks = validator.validate(values)

    print("\n  MIU Layer 3: Mathematical Identity Checks")
    print("  " + "-" * 50)
    for check in checks:
        if check.skipped:
            continue
        status = '[OK]' if check.passed else '[FAIL]'
        print(f"    {status} {check.identity}")
        if not check.passed and check.lhs_value is not None:
            print(
                f"          LHS: {check.lhs_value:,.0f}  "
                f"RHS: {check.rhs_value:,.0f}  "
                f"diff: {check.difference:,.0f}"
            )


def run_scale_normalization(
    extractor, ratios, component_matches,
    ixbrl_facts, standard_ratios,
) -> dict:
    """
    Run scale normalization on calculated ratios.

    Uses ALL extracted iXBRL facts for scale metadata lookup,
    since scale attributes are the same regardless of context.

    Returns:
        Dict of ratio_name -> ScaleAnnotation
    """
    from ..calculation.scale_normalizer import ScaleNormalizer

    all_facts = extractor.get_all_extracted()
    scale_facts = all_facts if all_facts else ixbrl_facts

    normalizer = ScaleNormalizer()
    annotations = normalizer.normalize(
        ratios, component_matches,
        scale_facts, standard_ratios,
    )
    if annotations:
        print(
            f"\n  Scale Normalizer: {len(annotations)} "
            f"ratios normalized from iXBRL scale metadata"
        )
        for name, ann in annotations.items():
            print(
                f"    {name}: {ann.raw_value:.4f} "
                f"-> {ann.normalized_value:.4f} "
                f"({ann.explanation})"
            )
    return annotations


__all__ = [
    'run_math_verify',
    'run_identity_checks',
    'run_scale_normalization',
]
