# Path: mat_acc/ratio_check/esef/context_resolver.py
"""
ESEF Context Resolver

Resolves opaque context_ref identifiers (c-1, c-7, etc.) to
actual period and dimensional information for ESEF filings.

Two resolution strategies:
1. iXBRL authoritative: reads xbrli:context from iXBRL HTML
2. Heuristic fallback: infers periods from mapped data patterns

ESEF mapped data often has null periods for income/cash flow
statements. This module fixes that by reading the authoritative
source (the iXBRL document) or inferring from available data.
"""
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
) -> ContextMap:
    """
    Resolve context_refs to periods and dimensions.

    Three strategies in priority order:
    1. iXBRL authoritative (reads xbrli:context from HTML)
    2. parsed.json via FactMerger (pre-parsed contexts)
    3. Heuristic from mapped data patterns (last resort)
    """
    ctx_map = _resolve_from_ixbrl(xbrl_dir)
    if ctx_map:
        logger.info(f"Resolved {len(ctx_map)} contexts from iXBRL")
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
    return ctx_map


def _resolve_from_ixbrl(
    xbrl_dir: Optional[Path],
) -> ContextMap:
    """Read xbrli:context definitions from iXBRL HTML."""
    if not xbrl_dir:
        return {}

    ixbrl_file = _find_ixbrl_file(xbrl_dir)
    if not ixbrl_file:
        return {}

    content = _read_file(ixbrl_file)
    if not content:
        return {}

    ctx_filter = ContextFilter()
    parsed = ctx_filter.parse_contexts(content)
    if not parsed:
        return {}

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
    """
    Resolve contexts from parsed.json via FactMerger.

    Conservative use: only reads context METADATA (period/dimensions)
    from parsed.json. Never reads fact values (parsed.json is known
    to have value issues). Context definitions are structural metadata
    and safe to use as secondary confirmation.
    """
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
    """
    Heuristic context resolution from mapped data patterns.

    Strategy: facts WITH periods (balance sheet) anchor the
    context resolution. Facts WITHOUT periods inherit the
    primary period from the balance sheet anchor.
    """
    ctx_map: ContextMap = {}
    known_periods: Dict[str, str] = {}
    null_period_refs: set = set()

    # Pass 1: collect context_refs with known periods
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

    # Determine primary period from known periods
    primary = value_lookup.get_primary_period()
    if not primary and known_periods:
        primary = sorted(known_periods.values(), reverse=True)[0]

    if not primary:
        logger.warning("ESEF heuristic: no primary period")
        return {}

    # Pass 2: for null-period contexts, assign primary period
    # Heuristic: count facts per context to identify primary
    ctx_fact_count: Dict[str, int] = {}
    for fact_list in value_lookup._value_index.values():
        for fv in fact_list:
            ref = fv.context_ref
            if ref and ref in null_period_refs:
                ctx_fact_count[ref] = ctx_fact_count.get(ref, 0) + 1

    # The context with most facts is likely the current-year total
    if ctx_fact_count:
        sorted_ctxs = sorted(
            ctx_fact_count.items(),
            key=lambda x: (-x[1], x[0]),
        )
        # Top context = current year primary
        primary_ctx_id = sorted_ctxs[0][0]
        logger.info(
            f"ESEF heuristic: primary context={primary_ctx_id} "
            f"({sorted_ctxs[0][1]} facts)"
        )

    # Build resolved contexts
    for ref in known_periods:
        ctx_map[ref] = ResolvedContext(
            context_id=ref,
            period_end=known_periods[ref],
        )

    for ref in null_period_refs:
        ctx_map[ref] = ResolvedContext(
            context_id=ref,
            period_end=primary,
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
        for ext in ('**/*.htm', '**/*.html', '**/*.xhtml'):
            candidates.extend(filing_dir.glob(ext))

    # Filter by size (iXBRL files are large) and content
    for f in sorted(candidates, key=lambda p: p.stat().st_size,
                    reverse=True):
        if f.stat().st_size < 50_000:
            continue
        try:
            head = f.read_text(encoding='utf-8', errors='ignore')
            head = head[:50_000]
            if 'ix:nonfraction' in head.lower():
                return f
        except Exception:
            continue
    return None


def _read_file(path: Path) -> str:
    """Read file with encoding fallback."""
    for enc in ('utf-8', 'latin-1', 'cp1252'):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return ''


__all__ = ['resolve_contexts', 'ContextMap', 'ResolvedContext']
