# Path: mat_acc_files/ratio_check/fact_value_lookup.py
"""
Fact Value Lookup

Retrieves actual numeric values for matched concepts from source files.
This is the MISSING LINK between concept matching and ratio calculation.

Sources (in priority order):
1. Mapped statements - preferred (company's declared presentation)
2. Parsed.json facts - comprehensive (all reported facts)

The loaders provide paths, this module reads actual values.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
from decimal import Decimal

from config_loader import ConfigLoader

# Import IPO logging
from core.logger.ipo_logging import get_process_logger

# Import loaders and readers
from loaders import (
    MappedDataLoader,
    ParsedDataLoader,
    MappedFilingEntry,
    ParsedFilingEntry,
    MappedReader,
    ParsedReader,
    MappedStatements,
    ParsedFiling,
    StatementFact,
    ParsedFact,
)


logger = get_process_logger('fact_value_lookup')


@dataclass
class FactValue:
    """
    A fact value with its context.

    Attributes:
        concept: Concept QName
        value: Numeric value
        period_end: Period end date
        period_start: Period start date (for duration)
        dimensions: Dimensional context
        unit: Unit of measurement
        source: Source of value ('mapped' or 'parsed')
        is_primary: True if this is the primary (non-dimensional) value
    """
    concept: str
    value: float
    period_end: Optional[str] = None
    period_start: Optional[str] = None
    dimensions: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None
    source: str = ''
    is_primary: bool = True


class FactValueLookup:
    """
    Looks up fact values from source files.

    This class bridges the gap between concept matching and ratio calculation
    by reading actual values from parsed.json and mapped statements.

    Strategy:
    1. Load facts from both mapped and parsed sources
    2. Build lookup index by concept QName
    3. For each concept, prefer: primary context (no dimensions), latest period
    4. Return numeric values for ratio calculations

    Example:
        lookup = FactValueLookup(config)
        lookup.load_from_filing(mapped_entry, parsed_entry)

        # Get value for a matched concept
        value = lookup.get_value('us-gaap:Assets')
        if value is not None:
            print(f"Assets: {value:,.0f}")
    """

    def __init__(self, config: ConfigLoader):
        """
        Initialize fact value lookup.

        Args:
            config: ConfigLoader instance
        """
        self.config = config
        self.logger = get_process_logger('fact_value_lookup')

        # Readers for loading content
        self._mapped_reader = MappedReader()
        self._parsed_reader = ParsedReader()

        # Value index: concept QName -> list of FactValue
        self._value_index: Dict[str, List[FactValue]] = {}

        # Track available periods for filtering
        self._available_periods: List[str] = []
        self._primary_period: Optional[str] = None

    def load_from_filing(
        self,
        mapped_entry: MappedFilingEntry,
        parsed_entry: Optional[ParsedFilingEntry] = None,
    ) -> int:
        """
        Load fact values from filing sources.

        Args:
            mapped_entry: Mapped filing entry (required)
            parsed_entry: Parsed filing entry (optional, recommended)

        Returns:
            Number of concepts with values loaded
        """
        self._value_index.clear()
        self._available_periods = []

        # 1. Load from parsed.json first (comprehensive source)
        if parsed_entry:
            parsed_count = self._load_from_parsed(parsed_entry)
            self.logger.info(f"Loaded {parsed_count} fact values from parsed.json")

        # 2. Load from mapped statements (may override/supplement)
        mapped_count = self._load_from_mapped(mapped_entry)
        self.logger.info(f"Loaded {mapped_count} fact values from mapped statements")

        # 3. Determine primary period
        self._determine_primary_period()

        total_concepts = len(self._value_index)
        self.logger.info(
            f"Total: {total_concepts} concepts with values, "
            f"primary period: {self._primary_period}"
        )

        return total_concepts

    def _load_from_parsed(self, parsed_entry: ParsedFilingEntry) -> int:
        """Load values from parsed.json."""
        count = 0

        try:
            parsed = self._parsed_reader.read_parsed_filing(parsed_entry)
            if not parsed:
                return 0

            # Track periods
            for ctx in parsed.contexts.values():
                if ctx.period_end:
                    if ctx.period_end not in self._available_periods:
                        self._available_periods.append(ctx.period_end)

            # Process facts
            for fact in parsed.facts:
                if self._add_fact_from_parsed(fact, parsed):
                    count += 1

        except Exception as e:
            self.logger.warning(f"Error loading from parsed.json: {e}")

        return count

    def _add_fact_from_parsed(
        self,
        fact: ParsedFact,
        parsed: ParsedFiling
    ) -> bool:
        """Add a single fact from parsed.json."""
        # Get numeric value
        value = self._parse_numeric_value(fact.value)
        if value is None:
            return False

        # Get period info from context
        period_end = fact.period_end
        period_start = fact.period_start
        dimensions = fact.dimensions or {}

        if fact.context_ref and not period_end:
            ctx = parsed.contexts.get(fact.context_ref)
            if ctx:
                period_end = ctx.period_end
                period_start = ctx.period_start
                if not dimensions:
                    dimensions = ctx.dimensions or {}

        # Determine if primary (no dimensional qualifiers)
        is_primary = len(dimensions) == 0

        fact_value = FactValue(
            concept=fact.concept,
            value=value,
            period_end=period_end,
            period_start=period_start,
            dimensions=dimensions,
            unit=fact.unit,
            source='parsed',
            is_primary=is_primary,
        )

        # Add to index
        if fact.concept not in self._value_index:
            self._value_index[fact.concept] = []
        self._value_index[fact.concept].append(fact_value)

        return True

    def _load_from_mapped(self, mapped_entry: MappedFilingEntry) -> int:
        """Load values from mapped statements."""
        count = 0

        try:
            statements = self._mapped_reader.read_statements(mapped_entry)
            if not statements:
                return 0

            # Process all statements
            for stmt in statements.statements:
                for fact in stmt.facts:
                    if self._add_fact_from_mapped(fact, stmt.name):
                        count += 1

        except Exception as e:
            self.logger.warning(f"Error loading from mapped statements: {e}")

        return count

    def _add_fact_from_mapped(
        self,
        fact: StatementFact,
        statement_name: str
    ) -> bool:
        """Add a single fact from mapped statement."""
        # Skip abstract items
        if fact.is_abstract:
            return False

        # Get numeric value
        value = self._parse_numeric_value(fact.value)
        if value is None:
            return False

        # Determine if primary (no dimensional qualifiers)
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
        )

        # Track period
        if fact.period_end and fact.period_end not in self._available_periods:
            self._available_periods.append(fact.period_end)

        # Add to index (mapped values supplement parsed)
        if fact.concept not in self._value_index:
            self._value_index[fact.concept] = []

        # Check if we already have this exact value
        existing = self._value_index[fact.concept]
        is_duplicate = any(
            v.period_end == fact_value.period_end and
            v.dimensions == fact_value.dimensions
            for v in existing
        )

        if not is_duplicate:
            self._value_index[fact.concept].append(fact_value)
            return True

        return False

    def _parse_numeric_value(self, value: Any) -> Optional[float]:
        """Parse a value to numeric, handling various formats."""
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, Decimal):
            return float(value)

        if isinstance(value, str):
            # Remove formatting
            cleaned = value.strip()
            if not cleaned:
                return None

            # Handle negative in parentheses
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]

            # Remove currency symbols and commas
            cleaned = cleaned.replace('$', '').replace(',', '').replace(' ', '')

            try:
                return float(cleaned)
            except ValueError:
                return None

        return None

    def _determine_primary_period(self) -> None:
        """Determine the primary (most recent) period."""
        if not self._available_periods:
            self._primary_period = None
            return

        # Sort periods descending (most recent first)
        sorted_periods = sorted(self._available_periods, reverse=True)
        self._primary_period = sorted_periods[0]

    def get_value(
        self,
        concept: str,
        period_end: Optional[str] = None,
        prefer_primary: bool = True,
    ) -> Optional[float]:
        """
        Get the value for a concept.

        Strategy:
        1. If period specified, use that period
        2. Otherwise, use primary period (most recent)
        3. Prefer primary context (no dimensions) over dimensional

        Args:
            concept: Concept QName (e.g., 'us-gaap:Assets')
            period_end: Specific period to retrieve (default: primary period)
            prefer_primary: Prefer non-dimensional values (default: True)

        Returns:
            Numeric value or None if not found
        """
        values = self._value_index.get(concept)
        if not values:
            # Try without prefix
            local_name = concept.split(':')[-1] if ':' in concept else concept
            for key in self._value_index:
                if key.endswith(':' + local_name) or key == local_name:
                    values = self._value_index[key]
                    break

        if not values:
            return None

        # Filter by period
        target_period = period_end or self._primary_period
        if target_period:
            period_values = [v for v in values if v.period_end == target_period]
            if period_values:
                values = period_values

        # Prefer primary context
        if prefer_primary:
            primary_values = [v for v in values if v.is_primary]
            if primary_values:
                values = primary_values

        # Return first matching value
        if values:
            return values[0].value

        return None

    def get_all_values(self, concept: str) -> List[FactValue]:
        """
        Get all values for a concept.

        Args:
            concept: Concept QName

        Returns:
            List of FactValue objects
        """
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
        return concept in self._value_index or self.get_value(concept) is not None

    def get_value_summary(self) -> Dict[str, Any]:
        """Get summary of loaded values."""
        total_values = sum(len(v) for v in self._value_index.values())
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
