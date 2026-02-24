# Path: mat_acc/ratio_check/esef/esef_preprocessor.py
"""
ESEF Preprocessor

Runs AFTER value loading, BEFORE MIU and matching.
Fixes ESEF-specific data quality issues in mapped statements:

1. Context resolution: maps context_refs to actual periods
2. Period annotation: sets period_end/start on facts with nulls
3. Dimensional filtering: marks dimensional facts as non-primary
4. Primary period: re-determines after annotation

Uses iXBRL context definitions (authoritative) when available,
falls back to heuristic resolution from mapped data patterns.
"""
from pathlib import Path
from typing import Optional

from core.logger.ipo_logging import get_process_logger

from ..fact_value_lookup import FactValueLookup
from .context_resolver import resolve_contexts, ContextMap


logger = get_process_logger('esef_preprocessor')


def preprocess_esef(
    value_lookup: FactValueLookup,
    xbrl_dir: Optional[Path],
    parsed_json_path: Optional[Path] = None,
) -> int:
    """
    Preprocess ESEF data in the value lookup.

    Annotates FactValues with correct periods and dimensional
    flags. Returns count of facts annotated.
    """
    ctx_map = resolve_contexts(value_lookup, xbrl_dir, parsed_json_path)
    if not ctx_map:
        logger.warning("ESEF: no context resolution available")
        return 0

    annotated = _annotate_facts(value_lookup, ctx_map)
    if annotated:
        _redetermine_primary_period(value_lookup)
    logger.info(f"ESEF preprocessor: {annotated} facts annotated")
    return annotated


def _annotate_facts(
    value_lookup: FactValueLookup,
    ctx_map: ContextMap,
) -> int:
    """Annotate FactValues with period and dimensional info."""
    annotated = 0
    for concept_key, fact_list in value_lookup._value_index.items():
        for fv in fact_list:
            if not fv.context_ref:
                continue
            ctx = ctx_map.get(fv.context_ref)
            if not ctx:
                continue
            changed = False
            # Set period from context if missing
            if not fv.period_end and ctx.period_end:
                fv.period_end = ctx.period_end
                changed = True
            if not fv.period_start and ctx.period_start:
                fv.period_start = ctx.period_start
                changed = True
            # Mark dimensional facts as non-primary
            if ctx.has_dimensions and fv.is_primary:
                fv.is_primary = False
                changed = True
            if changed:
                annotated += 1
    return annotated


def _redetermine_primary_period(
    value_lookup: FactValueLookup,
) -> None:
    """Re-determine primary period after annotation."""
    periods = set()
    duration_periods = set()
    for fact_list in value_lookup._value_index.values():
        for fv in fact_list:
            if fv.period_end:
                periods.add(fv.period_end)
            if fv.period_start and fv.period_end:
                duration_periods.add(fv.period_end)

    value_lookup._available_periods = sorted(periods)
    value_lookup._duration_periods = duration_periods

    from ..values.fact_loading import determine_primary_period
    new_primary = determine_primary_period(
        value_lookup._available_periods,
        value_lookup._duration_periods,
    )
    if new_primary and new_primary != value_lookup._primary_period:
        old = value_lookup._primary_period
        value_lookup._primary_period = new_primary
        logger.info(
            f"ESEF: primary period updated: {old} -> {new_primary}"
        )


__all__ = ['preprocess_esef']
