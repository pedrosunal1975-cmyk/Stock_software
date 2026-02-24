# Path: mat_acc/ratio_check/esef/context_resolver.py
"""ESEF Context Resolver - maps context_refs to periods and dimensions."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict

from core.logger.ipo_logging import get_process_logger

from ..fact_value_lookup import FactValueLookup
from ..math_verify.context_filter import ContextFilter


logger = get_process_logger('esef.context_resolver')


@dataclass
class ResolvedContext:
    """Resolved context with period and dimensional info."""
    context_id: str
    period_end: Optional[str] = None
    period_start: Optional[str] = None
    has_dimensions: bool = False

    @property
    def is_duration(self) -> bool:
        return bool(self.period_start and self.period_end)


ContextMap = Dict[str, ResolvedContext]


def resolve_contexts(
    value_lookup: FactValueLookup,
    xbrl_dir: Optional[Path],
    parsed_json_path: Optional[Path] = None,
    context_filter: Optional[ContextFilter] = None,
) -> ContextMap:
    """
    Resolve context_refs to periods and dimensions.

    Four strategies in priority order:
    0. Pre-parsed ContextFilter from MIU (most reliable)
    1. iXBRL authoritative (reads xbrli:context from HTML)
    2. parsed.json via FactMerger (pre-parsed contexts)
    3. Heuristic from mapped data patterns (last resort)
    """
    if context_filter:
        ctx_map = _resolve_from_filter(context_filter)
        if ctx_map:
            dim_count = sum(
                1 for c in ctx_map.values() if c.has_dimensions
            )
            logger.info(
                f"Resolved {len(ctx_map)} contexts from MIU "
                f"ContextFilter ({dim_count} dimensional)"
            )
            return ctx_map
        logger.warning("MIU ContextFilter had 0 parsed contexts")

    ctx_map = _resolve_from_ixbrl(xbrl_dir)
    if ctx_map:
        dim_count = sum(
            1 for c in ctx_map.values() if c.has_dimensions
        )
        logger.info(
            f"Resolved {len(ctx_map)} from iXBRL "
            f"({dim_count} dimensional)"
        )
        return ctx_map

    ctx_map = _resolve_from_parsed(parsed_json_path)
    if ctx_map:
        logger.info(
            f"Resolved {len(ctx_map)} contexts from parsed.json"
        )
        return ctx_map

    ctx_map = _resolve_from_mapped(value_lookup)
    if ctx_map:
        logger.info(
            f"Resolved {len(ctx_map)} contexts via heuristic"
        )
    else:
        logger.error("All context resolution strategies failed")
    return ctx_map


def _resolve_from_filter(
    ctx_filter: ContextFilter,
) -> ContextMap:
    """Convert pre-parsed ContextFilter to ContextMap."""
    parsed = ctx_filter._contexts
    if not parsed:
        return {}
    return _convert_context_infos(parsed)


def _resolve_from_ixbrl(
    xbrl_dir: Optional[Path],
) -> ContextMap:
    """Read xbrli:context definitions from iXBRL HTML."""
    if not xbrl_dir:
        logger.debug("iXBRL strategy: no xbrl_dir provided")
        return {}

    ixbrl_file = _find_ixbrl_file(xbrl_dir)
    if not ixbrl_file:
        logger.info(f"iXBRL strategy: no file found in {xbrl_dir}")
        return {}

    logger.info(f"iXBRL strategy: reading {ixbrl_file.name}")
    content = _read_file(ixbrl_file)
    if not content:
        logger.warning(f"iXBRL strategy: empty content {ixbrl_file}")
        return {}

    ctx_filter = ContextFilter()
    parsed = ctx_filter.parse_contexts(content)
    if not parsed:
        logger.warning("iXBRL strategy: parse_contexts returned empty")
        return {}

    return _convert_context_infos(parsed)


def _convert_context_infos(parsed: dict) -> ContextMap:
    """Convert ContextInfo dict to ContextMap."""
    ctx_map: ContextMap = {}
    for ctx_id, ctx_info in parsed.items():
        rc = ResolvedContext(context_id=ctx_id)
        if ctx_info.period_type == 'instant':
            rc.period_end = ctx_info.instant_date
        elif ctx_info.period_type == 'duration':
            rc.period_start = ctx_info.start_date
            rc.period_end = ctx_info.end_date
        rc.has_dimensions = ctx_info.has_dimensions
        ctx_map[ctx_id] = rc
    return ctx_map


def _resolve_from_parsed(
    parsed_json_path: Optional[Path],
) -> ContextMap:
    """Resolve contexts from parsed.json via FactMerger."""
    if not parsed_json_path or not parsed_json_path.exists():
        return {}

    try:
        from mat_acc.process.hierarchy.fact_merger import FactMerger
    except ImportError:
        return {}

    merger = FactMerger()
    if not merger.load_from_parsed_json(parsed_json_path):
        return {}

    if not merger._contexts:
        return {}

    ctx_map: ContextMap = {}
    for ctx_id, ctx_info in merger._contexts.items():
        rc = ResolvedContext(context_id=ctx_id)
        period = ctx_info.get('period', {})
        if 'instant' in period:
            rc.period_end = period['instant']
        elif 'startDate' in period or 'start_date' in period:
            rc.period_start = period.get(
                'startDate', period.get('start_date'))
            rc.period_end = period.get(
                'endDate', period.get('end_date'))
        dims = ctx_info.get('dimensions', {})
        if not dims:
            dims = ctx_info.get('entity', {}).get('segment', {})
        rc.has_dimensions = bool(dims)
        ctx_map[ctx_id] = rc

    return ctx_map


def _resolve_from_mapped(
    value_lookup: FactValueLookup,
) -> ContextMap:
    """Heuristic context resolution from mapped data patterns."""
    ctx_map: ContextMap = {}
    known_periods: Dict[str, str] = {}
    null_period_refs: set = set()

    for fact_list in value_lookup._value_index.values():
        for fv in fact_list:
            if not fv.context_ref:
                continue
            if fv.period_end:
                known_periods[fv.context_ref] = fv.period_end
            else:
                null_period_refs.add(fv.context_ref)

    if not null_period_refs:
        return {}

    primary = value_lookup.get_primary_period()
    if not primary and known_periods:
        primary = sorted(known_periods.values(), reverse=True)[0]
    if not primary:
        logger.warning("Heuristic: no primary period available")
        return {}

    # Build resolved contexts
    for ref in known_periods:
        ctx_map[ref] = ResolvedContext(
            context_id=ref, period_end=known_periods[ref],
        )
    for ref in null_period_refs:
        ctx_map[ref] = ResolvedContext(
            context_id=ref, period_end=primary,
        )

    return ctx_map


def _find_ixbrl_file(filing_dir: Path) -> Optional[Path]:
    """Find the main iXBRL file in a filing directory."""
    if not filing_dir or not filing_dir.is_dir():
        return None

    candidates = []
    for ext in ('*.htm', '*.html', '*.xhtml', '*.xml'):
        candidates.extend(filing_dir.glob(ext))
    if not candidates:
        for ext in (
            '**/*.htm', '**/*.html',
            '**/*.xhtml', '**/*.xml',
        ):
            candidates.extend(filing_dir.glob(ext))

    if not candidates:
        logger.debug(f"No HTML/XML files found in {filing_dir}")
        return None

    # Sort by size descending - main filing is usually largest
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)

    for f in candidates:
        try:
            head = f.read_text(
                encoding='utf-8', errors='ignore',
            )[:50_000]
            if 'ix:nonfraction' in head.lower():
                return f
        except Exception:
            continue

    # Fallback: return largest file
    return candidates[0] if candidates else None


def _read_file(path: Path) -> str:
    """Read file with encoding fallback."""
    for enc in ('utf-8', 'latin-1', 'cp1252'):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return ''


__all__ = ['resolve_contexts', 'ContextMap', 'ResolvedContext']
