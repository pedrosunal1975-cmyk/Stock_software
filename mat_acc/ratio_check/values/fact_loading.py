# Path: mat_acc/ratio_check/values/fact_loading.py
"""
Fact Loading - Loads numeric values from mapped statements.

Standalone functions that populate the FactValueLookup indices.
Separated from the lookup/query API for single-responsibility.

Two-tier loading: primary financial statements load first
so their values take priority. Supplementary fill gaps only.
"""
from decimal import Decimal
from typing import Optional, Dict, List, Any, Tuple

from core.qname import parse_qname
from loaders import MappedFilingEntry, MappedReader, StatementFact


# XBRL taxonomy-defined root concepts for primary statements.
# Intrinsic to FASB (US-GAAP) and IASB (IFRS) taxonomies.
_PRIMARY_STATEMENT_ROOTS = {
    # US-GAAP (FASB taxonomy)
    'StatementOfFinancialPositionAbstract',
    'IncomeStatementAbstract',
    'StatementOfIncomeAndComprehensiveIncomeAbstract',
    'StatementOfCashFlowsAbstract',
    'StatementOfStockholdersEquityAbstract',
    # IFRS (IASB taxonomy)
    'StatementOfChangesInEquityAbstract',
    'StatementOfComprehensiveIncomeAbstract',
}


def is_primary_statement(stmt) -> bool:
    """Check if statement is a primary financial statement.

    Uses XBRL taxonomy-defined root abstract concepts from
    hierarchy.roots. Works for any taxonomy.
    """
    metadata = getattr(stmt, 'metadata', None)
    if not isinstance(metadata, dict):
        return False
    hierarchy = metadata.get('hierarchy', {})
    if not isinstance(hierarchy, dict):
        return False
    roots = hierarchy.get('roots', [])
    for root in roots:
        _, local_name = parse_qname(str(root))
        if local_name in _PRIMARY_STATEMENT_ROOTS:
            return True
    return False


def load_from_mapped(
    mapped_reader: MappedReader,
    mapped_entry: MappedFilingEntry,
    value_index: Dict[str, list],
    normalized_index: Dict[Tuple[str, str], str],
    available_periods: List[str],
    duration_periods: set,
    logger,
) -> int:
    """Load values from mapped statements into indices.

    Two-tier: primary statements first, supplementary fill gaps.
    Returns count of facts loaded.
    """
    count = 0
    try:
        statements = mapped_reader.read_statements(mapped_entry)
        if not statements:
            return 0

        primary = []
        supplementary = []
        for stmt in statements.statements:
            if is_primary_statement(stmt):
                primary.append(stmt)
            else:
                supplementary.append(stmt)

        logger.info(
            f"Statement priority: {len(primary)} primary, "
            f"{len(supplementary)} supplementary"
        )

        for stmt in primary:
            for fact in stmt.facts:
                if _add_fact(
                    fact, value_index, normalized_index,
                    available_periods, duration_periods,
                    is_core=True,
                ):
                    count += 1

        for stmt in supplementary:
            for fact in stmt.facts:
                if _add_fact(
                    fact, value_index, normalized_index,
                    available_periods, duration_periods,
                    is_core=False,
                ):
                    count += 1

    except Exception as e:
        logger.warning(
            f"Error loading from mapped statements: {e}",
        )
    return count


def _add_fact(
    fact: StatementFact,
    value_index: Dict[str, list],
    normalized_index: Dict[Tuple[str, str], str],
    available_periods: List[str],
    duration_periods: set,
    is_core: bool = True,
) -> bool:
    """Add a single fact from mapped statement to indices."""
    if fact.is_abstract:
        return False

    value = parse_numeric_value(fact.value)
    if value is None:
        return False

    # Import here to avoid circular - FactValue is in parent
    from ..fact_value_lookup import FactValue

    dimensions = fact.dimensions or {}
    is_primary = len(dimensions) == 0

    fact_value = FactValue(
        concept=fact.concept,
        value=value,
        period_end=fact.period_end,
        period_start=fact.period_start,
        dimensions=dimensions,
        unit=fact.unit,
        source='mapped',
        is_primary=is_primary,
        from_core_statement=is_core,
    )

    if fact.period_end:
        if fact.period_end not in available_periods:
            available_periods.append(fact.period_end)
    if fact.period_start and fact.period_end:
        duration_periods.add(fact.period_end)

    if fact.concept not in value_index:
        value_index[fact.concept] = []

    existing = value_index[fact.concept]
    is_duplicate = any(
        v.period_end == fact_value.period_end
        and v.dimensions == fact_value.dimensions
        for v in existing
    )

    if not is_duplicate:
        value_index[fact.concept].append(fact_value)
        ns, local = parse_qname(fact.concept)
        if local:
            norm_key = (ns.lower(), local)
            if norm_key not in normalized_index:
                normalized_index[norm_key] = fact.concept
        return True
    return False


def parse_numeric_value(value: Any) -> Optional[float]:
    """Parse a value to numeric, handling various formats."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        cleaned = (
            cleaned.replace('$', '')
            .replace(',', '')
            .replace(' ', '')
        )
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def determine_primary_period(
    available_periods: List[str],
    duration_periods: set,
) -> Optional[str]:
    """Determine the primary (most recent) period.

    Filing dates only appear as instant contexts (no duration
    facts). Fiscal year-end always has duration facts (IS, CF).
    Prefer the latest period with duration facts.
    """
    if not available_periods:
        return None
    if duration_periods:
        sorted_dur = sorted(duration_periods, reverse=True)
        return sorted_dur[0]
    sorted_all = sorted(available_periods, reverse=True)
    return sorted_all[0]


__all__ = [
    'load_from_mapped',
    'determine_primary_period',
    'parse_numeric_value',
    'is_primary_statement',
]
