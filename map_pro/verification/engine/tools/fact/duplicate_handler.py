# Path: verification/engine/checks_v2/tools/fact/duplicate_handler.py
"""
Duplicate Handler for XBRL Verification

Handles detection and classification of duplicate facts per XBRL Duplicates Guidance.

Techniques consolidated from:
- checks/context/duplicate_detection.py

DUPLICATE TYPES (per XBRL spec):
- COMPLETE: Same value, same precision - ignore, use one
- CONSISTENT: Same value (within tolerance), different precision - use most precise
- INCONSISTENT: Different values - error, skip calculation

DESIGN: Stateless tool for analyzing duplicate facts.
Uses DecimalTolerance from tolerance/ tools for value comparison.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ..tolerance.decimal_tolerance import DecimalTolerance
from .value_parser import ValueParser
from .fact_entry import FactEntry
from ...constants.tolerances import DUPLICATE_PERCENTAGE_TOLERANCE
from ...constants.enums import DuplicateType, DuplicateSource


@dataclass
class DuplicateInfo:
    """
    Information about duplicate facts for a concept in a context.

    Attributes:
        concept: Normalized concept name
        context_id: The context these duplicates belong to
        entries: List of all FactEntry objects for this concept
        duplicate_type: Type of duplicate (complete/consistent/inconsistent)
        duplicate_source: Likely source/reason for the duplicate
        selected_value: The value to use (most precise for consistent)
        selected_decimals: The decimals of selected value
        is_dimensional: Whether the context is dimensional
        value_range: (min_value, max_value) of the duplicate values
        precision_range: (min_decimals, max_decimals) of precision levels
        diagnostics: Additional diagnostic information
    """
    concept: str
    context_id: str = ""
    entries: list[FactEntry] = field(default_factory=list)
    duplicate_type: Optional[DuplicateType] = None
    duplicate_source: Optional[DuplicateSource] = None
    selected_value: Optional[float] = None
    selected_decimals: Optional[int] = None
    is_dimensional: bool = False
    value_range: tuple = (None, None)
    precision_range: tuple = (None, None)
    diagnostics: dict = field(default_factory=dict)

    def has_duplicates(self) -> bool:
        """Check if there are duplicate entries."""
        return len(self.entries) > 1

    def is_usable(self) -> bool:
        """Check if the value can be used (not inconsistent)."""
        return self.duplicate_type != DuplicateType.INCONSISTENT

    def get_summary(self) -> str:
        """Get human-readable summary of the duplicate situation."""
        if not self.has_duplicates():
            return "No duplicates"

        parts = [
            f"{len(self.entries)} entries",
            f"type={self.duplicate_type.value if self.duplicate_type else 'unknown'}",
        ]

        if self.duplicate_source:
            parts.append(f"source={self.duplicate_source.value}")

        if self.value_range[0] is not None:
            parts.append(f"values={self.value_range[0]:,.0f}-{self.value_range[1]:,.0f}")

        if self.is_dimensional:
            parts.append("dimensional")

        return ", ".join(parts)


class DuplicateHandler:
    """
    Handles detection and classification of duplicate facts.

    Per XBRL Duplicates Guidance, duplicates are classified as:
    - COMPLETE: Same value, same precision
    - CONSISTENT: Same value, different precision (use most precise)
    - INCONSISTENT: Different values (error condition)

    This is a STATELESS tool - can be reused across all processing stages.

    Strategies:
    - 'decimal': Use decimal tolerance for comparison (default)
    - 'percentage': Use percentage tolerance as fallback
    - 'both': Try decimal first, then percentage

    Usage:
        handler = DuplicateHandler()

        # Analyze duplicates
        entries = [entry1, entry2, entry3]  # Same concept, same context
        info = handler.analyze(entries)

        if info.duplicate_type == DuplicateType.INCONSISTENT:
            print("Error: inconsistent duplicates")
        else:
            print(f"Selected value: {info.selected_value}")
    """

    def __init__(self, strategy: str = 'both'):
        """
        Initialize the duplicate handler.

        Args:
            strategy: Comparison strategy ('decimal', 'percentage', or 'both')
        """
        self.logger = logging.getLogger('tools.fact.duplicate_handler')
        self._strategy = strategy
        self._decimal_tolerance = DecimalTolerance()
        self._value_parser = ValueParser()

    def set_strategy(self, strategy: str) -> None:
        """
        Set the comparison strategy.

        Args:
            strategy: 'decimal', 'percentage', or 'both'
        """
        if strategy not in ('decimal', 'percentage', 'both'):
            raise ValueError(f"Unknown strategy: {strategy}")
        self._strategy = strategy

    def analyze(self, entries: list[FactEntry], context_id: str = "") -> DuplicateInfo:
        """
        Analyze a list of fact entries for duplicates.

        Args:
            entries: List of FactEntry objects (same concept, same context)
            context_id: Optional context ID for diagnostic info

        Returns:
            DuplicateInfo with classification, source identification, and diagnostics
        """
        if not entries:
            return DuplicateInfo(concept="")

        concept = entries[0].concept
        ctx_id = context_id or (entries[0].context_id if entries else "")

        # Check if any entry is from a dimensional context
        is_dimensional = any(
            getattr(e, 'is_dimensional', False) for e in entries
        )

        info = DuplicateInfo(
            concept=concept,
            context_id=ctx_id,
            entries=entries,
            is_dimensional=is_dimensional,
        )

        if len(entries) <= 1:
            # No duplicates
            info.duplicate_type = None
            if entries:
                info.selected_value = entries[0].value
                info.selected_decimals = self._normalize_decimals(entries[0].decimals)
            return info

        # Calculate value and precision ranges for diagnostics
        values = [e.value for e in entries]
        # Normalize decimals and filter out None values
        decimals_list = [
            d for d in (self._normalize_decimals(e.decimals) for e in entries)
            if d is not None
        ]

        info.value_range = (min(values), max(values))
        if decimals_list:
            info.precision_range = (min(decimals_list), max(decimals_list))

        # Multiple entries - classify duplicate type
        all_equal = self._are_values_equal(entries)

        if all_equal:
            # Check if same precision (COMPLETE) or different (CONSISTENT)
            if len(set(decimals_list)) <= 1:
                info.duplicate_type = DuplicateType.COMPLETE
                info.duplicate_source = DuplicateSource.IXBRL_DISPLAY
            else:
                info.duplicate_type = DuplicateType.CONSISTENT
                info.duplicate_source = DuplicateSource.PRECISION_VARIANT

            # Select most precise value
            self._select_most_precise(info)
        else:
            # Different values - INCONSISTENT
            info.duplicate_type = DuplicateType.INCONSISTENT
            info.selected_value = None
            info.selected_decimals = None

            # Try to identify the source of inconsistency
            info.duplicate_source = self._identify_inconsistency_source(entries)

        # Build diagnostics
        info.diagnostics = self._build_diagnostics(entries, info)

        return info

    def _identify_inconsistency_source(
        self,
        entries: list[FactEntry]
    ) -> DuplicateSource:
        """
        Try to identify why duplicate values are inconsistent.

        Uses heuristics to determine the likely source of the difference.

        Args:
            entries: List of FactEntry with different values

        Returns:
            DuplicateSource indicating likely reason for inconsistency
        """
        values = [e.value for e in entries]
        min_val = min(values)
        max_val = max(values)

        if max_val == 0:
            return DuplicateSource.UNKNOWN

        # Check if difference is just rounding
        diff_pct = abs(max_val - min_val) / max(abs(max_val), abs(min_val))

        if diff_pct <= 0.001:  # 0.1% difference
            return DuplicateSource.ROUNDING_DIFF

        # Check if this might be a restatement (significant difference)
        if diff_pct > 0.05:  # >5% difference
            return DuplicateSource.RESTATEMENT

        # Default to value conflict
        return DuplicateSource.VALUE_CONFLICT

    def _build_diagnostics(
        self,
        entries: list[FactEntry],
        info: DuplicateInfo
    ) -> dict:
        """
        Build diagnostic information for duplicate analysis.

        Args:
            entries: List of FactEntry objects
            info: DuplicateInfo being built

        Returns:
            Dictionary with diagnostic details
        """
        # Get unique precisions, filtering out None after normalization
        normalized_decimals = [
            d for d in (self._normalize_decimals(e.decimals) for e in entries)
            if d is not None
        ]
        diagnostics = {
            'entry_count': len(entries),
            'unique_values': len(set(e.value for e in entries)),
            'unique_precisions': len(set(normalized_decimals)),
        }

        # Add value details
        diagnostics['values'] = [
            {
                'value': e.value,
                'decimals': self._normalize_decimals(e.decimals),
                'fact_id': getattr(e, 'fact_id', None),
                'source': getattr(e, 'source', None),
            }
            for e in entries
        ]

        # If inconsistent, add difference analysis
        if info.duplicate_type == DuplicateType.INCONSISTENT:
            values = [e.value for e in entries]
            min_val = min(values)
            max_val = max(values)
            diagnostics['value_difference'] = max_val - min_val
            if max(abs(max_val), abs(min_val)) > 0:
                diagnostics['difference_pct'] = (
                    abs(max_val - min_val) / max(abs(max_val), abs(min_val))
                )

        return diagnostics

    def _are_values_equal(self, entries: list[FactEntry]) -> bool:
        """Check if all entries have equal values."""
        if len(entries) <= 1:
            return True

        if self._strategy in ('decimal', 'both'):
            if self._are_equal_decimal(entries):
                return True

        if self._strategy in ('percentage', 'both'):
            if self._are_equal_percentage(entries):
                return True

        return False

    def _are_equal_decimal(self, entries: list[FactEntry]) -> bool:
        """Check equality using decimal tolerance."""
        reference = entries[0]
        ref_decimals = self._normalize_decimals(reference.decimals)

        for entry in entries[1:]:
            entry_decimals = self._normalize_decimals(entry.decimals)
            result = self._decimal_tolerance.compare(
                reference.value,
                entry.value,
                ref_decimals,
                entry_decimals
            )
            if not result.values_equal:
                return False

        return True

    def _are_equal_percentage(
        self,
        entries: list[FactEntry],
        tolerance: float = DUPLICATE_PERCENTAGE_TOLERANCE
    ) -> bool:
        """Check equality using percentage tolerance."""
        values = [abs(e.value) for e in entries]
        max_val = max(values)
        min_val = min(values)

        if max_val == 0:
            return all(v == 0 for v in values)

        pct_diff = abs(max_val - min_val) / max_val
        return pct_diff <= tolerance

    def _select_most_precise(self, info: DuplicateInfo) -> None:
        """Select the value with highest precision."""
        if not info.entries:
            return

        best_idx = 0
        best_decimals = self._normalize_decimals(info.entries[0].decimals)
        if best_decimals is None:
            best_decimals = float('-inf')

        for i in range(1, len(info.entries)):
            entry_decimals = self._normalize_decimals(info.entries[i].decimals)
            if entry_decimals is None:
                continue

            # Higher decimals = more precise (e.g., -3 is more precise than -6)
            if entry_decimals > best_decimals:
                best_decimals = entry_decimals
                best_idx = i

        info.selected_value = info.entries[best_idx].value
        info.selected_decimals = self._normalize_decimals(info.entries[best_idx].decimals)

    def _normalize_decimals(self, decimals) -> Optional[int]:
        """Normalize decimals value to int."""
        return self._value_parser.parse_decimals(decimals)

    def classify_type(self, entries: list[FactEntry]) -> Optional[DuplicateType]:
        """
        Classify the duplicate type without full analysis.

        Args:
            entries: List of FactEntry objects

        Returns:
            DuplicateType or None if no duplicates
        """
        info = self.analyze(entries)
        return info.duplicate_type


__all__ = ['DuplicateHandler', 'DuplicateInfo']
