# Path: mat_acc/ratio_check/fact_value_lookup.py
"""
Fact Value Lookup

Retrieves actual numeric values for matched concepts from
source files. The MISSING LINK between concept matching and
ratio calculation.

Value source: Mapped statements (company's declared presentation).
Sign corrections: Applied by MIU from iXBRL source truth.
Loading logic: Delegated to values/fact_loading.py.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple

from config_loader import ConfigLoader
from core.logger.ipo_logging import get_process_logger
from core.qname import parse_qname, alternate_qname

from loaders import MappedFilingEntry, MappedReader

from .values.fact_loading import (
    load_from_mapped,
    determine_primary_period,
)


logger = get_process_logger('fact_value_lookup')


@dataclass
class FactValue:
    """A fact value with its context."""
    concept: str
    value: float
    period_end: Optional[str] = None
    period_start: Optional[str] = None
    dimensions: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None
    source: str = ''
    is_primary: bool = True
    from_core_statement: bool = True
    context_ref: Optional[str] = None


class FactValueLookup:
    """
    Looks up fact values from mapped statement files.

    Strategy:
    1. Load facts from mapped statements (single clean source)
    2. Build lookup index by concept QName
    3. MIU applies sign corrections from iXBRL source truth
    4. For each concept, prefer: primary context, latest period
    5. Return numeric values for ratio calculations
    """

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.logger = get_process_logger('fact_value_lookup')
        self._mapped_reader = MappedReader()
        self._value_index: Dict[str, List[FactValue]] = {}
        self._available_periods: List[str] = []
        self._primary_period: Optional[str] = None
        self._duration_periods: set = set()
        self._normalized_index: Dict[Tuple[str, str], str] = {}

    def load_from_filing(
        self, mapped_entry: MappedFilingEntry,
    ) -> int:
        """Load fact values from mapped statement files."""
        self._value_index.clear()
        self._normalized_index.clear()
        self._available_periods = []
        self._duration_periods = set()

        mapped_count = load_from_mapped(
            self._mapped_reader, mapped_entry,
            self._value_index, self._normalized_index,
            self._available_periods, self._duration_periods,
            self.logger,
        )
        self.logger.info(
            f"Loaded {mapped_count} fact values from mapped"
        )

        self._primary_period = determine_primary_period(
            self._available_periods, self._duration_periods,
        )

        total = len(self._value_index)
        self.logger.info(
            f"Total: {total} concepts with values, "
            f"primary period: {self._primary_period}"
        )
        return total

    def get_value(
        self,
        concept: str,
        period_end: Optional[str] = None,
        prefer_primary: bool = True,
        core_only: bool = False,
    ) -> Optional[float]:
        """
        Get the value for a concept.

        Strategy:
        1. If period specified, use that period
        2. Otherwise, use primary period (most recent)
        3. Prefer primary context (no dimensions)
        4. If core_only, only return from primary statements
        """
        values = self._find_values(concept)
        if not values:
            return None

        if core_only:
            values = [v for v in values if v.from_core_statement]
            if not values:
                return None

        target_period = period_end or self._primary_period
        if target_period:
            period_vals = [
                v for v in values
                if v.period_end == target_period
            ]
            if period_vals:
                values = period_vals

        if prefer_primary:
            primary_vals = [v for v in values if v.is_primary]
            if primary_vals:
                values = primary_vals

        return values[0].value if values else None

    def _find_values(
        self, concept: str,
    ) -> Optional[List[FactValue]]:
        """Multi-tier namespace-aware value lookup."""
        # Tier 1: Exact match
        values = self._value_index.get(concept)
        if values:
            return values
        # Tier 2: Alternate format (colon <-> underscore)
        alt_key = alternate_qname(concept)
        if alt_key:
            values = self._value_index.get(alt_key)
            if values:
                return values
        # Tier 3: Namespace-aware normalized match
        return self._lookup_normalized(concept)

    def _lookup_normalized(
        self, concept: str,
    ) -> Optional[List[FactValue]]:
        """Namespace-aware normalized QName lookup."""
        ns, local = parse_qname(concept)
        if not local:
            return None

        if ns:
            norm_key = (ns.lower(), local)
            orig_key = self._normalized_index.get(norm_key)
            if orig_key:
                return self._value_index.get(orig_key)
            return None

        matches = [
            orig_key
            for (idx_ns, idx_local), orig_key
            in self._normalized_index.items()
            if idx_local == local
        ]

        if len(matches) == 1:
            self.logger.debug(
                f"Inferred namespace for '{concept}': "
                f"{matches[0]}"
            )
            return self._value_index.get(matches[0])

        if len(matches) > 1:
            self.logger.warning(
                f"Ambiguous concept '{concept}': found in "
                f"{len(matches)} namespaces, skipping"
            )
        return None

    def _find_best_fact(
        self, values: List[FactValue],
    ) -> Optional[FactValue]:
        """Find best fact for correction (soft filter)."""
        candidates = list(values)
        if self._primary_period:
            period_match = [
                v for v in candidates
                if v.period_end == self._primary_period
            ]
            if period_match:
                candidates = period_match
        primary_ctx = [v for v in candidates if v.is_primary]
        if primary_ctx:
            candidates = primary_ctx
        return candidates[0] if candidates else None

    def apply_corrections(
        self, corrections: Dict[str, float],
    ) -> int:
        """Apply MIU sign corrections to the value index."""
        corrected = 0
        for concept, correct_value in corrections.items():
            values = self._find_values(concept)
            if not values:
                continue
            target = self._find_best_fact(values)
            if target is None:
                continue
            if target.value != correct_value:
                self.logger.info(
                    f"MIU correction: {concept} "
                    f"{target.value:,.0f} -> "
                    f"{correct_value:,.0f}"
                )
                target.value = correct_value
                corrected += 1
        if corrected > 0:
            self.logger.info(
                f"Applied {corrected} sign corrections",
            )
        return corrected

    def get_all_values(self, concept: str) -> List[FactValue]:
        """Get all values for a concept."""
        return self._value_index.get(concept, [])

    def get_primary_period(self) -> Optional[str]:
        """Get the primary (most recent) period."""
        return self._primary_period

    def get_available_periods(self) -> List[str]:
        """Get list of available periods."""
        return sorted(self._available_periods, reverse=True)

    def get_concept_count(self) -> int:
        """Get number of concepts with values."""
        return len(self._value_index)

    def has_value(self, concept: str) -> bool:
        """Check if a concept has any value."""
        return (
            concept in self._value_index
            or self.get_value(concept) is not None
        )

    def get_value_summary(self) -> Dict[str, Any]:
        """Get summary of loaded values."""
        total_values = sum(
            len(v) for v in self._value_index.values()
        )
        primary_count = sum(
            1 for values in self._value_index.values()
            for v in values if v.is_primary
        )
        return {
            'concepts_with_values': len(self._value_index),
            'total_values': total_values,
            'primary_values': primary_count,
            'primary_period': self._primary_period,
            'available_periods': len(self._available_periods),
        }


__all__ = ['FactValueLookup', 'FactValue']
