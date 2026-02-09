# Path: mat_acc/process/hierarchy/fact_merger.py
"""
Fact Merger - Merges fact data from parsed.json into hierarchy nodes.

This module provides utilities to:
1. Load facts from parsed.json
2. Index facts by concept for efficient lookup
3. Merge fact values and context_ref into hierarchy nodes

The merger enables mat_acc_id to include context_ref, making each
fact uniquely identifiable for ratio calculations.

Example:
    merger = FactMerger()
    merger.load_from_parsed_json(Path('/path/to/parsed.json'))

    # Get all facts for a concept
    facts = merger.get_facts_for_concept('us-gaap:Assets')
    # Returns: [FactInstance(context_ref='c4', value=1000000, ...), ...]
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any
from collections import defaultdict


@dataclass
class FactInstance:
    """
    A fact instance with its context and value.

    This represents a single fact occurrence for a concept
    in a specific context (period/dimension).

    Attributes:
        concept: Full concept name (e.g., 'us-gaap:Assets')
        context_ref: Context reference ID (e.g., 'c4', 'FD2024Q4')
        value: Numeric or text value
        unit: Unit of measure (e.g., 'USD', 'shares')
        decimals: Decimal precision
        period_type: 'instant' or 'duration'
        period_start: Period start date (for duration)
        period_end: Period end date or instant date
        dimensions: Dimensional qualifiers (axis/member pairs)
    """
    concept: str
    context_ref: str
    value: Any = None
    unit: Optional[str] = None
    decimals: Optional[int] = None
    period_type: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    dimensions: dict = field(default_factory=dict)

    @property
    def has_numeric_value(self) -> bool:
        """Check if this fact has a numeric value."""
        if self.value is None:
            return False
        try:
            float(str(self.value).replace(',', ''))
            return True
        except (ValueError, TypeError):
            return False

    @property
    def numeric_value(self) -> Optional[float]:
        """Get numeric value or None."""
        if not self.has_numeric_value:
            return None
        return float(str(self.value).replace(',', ''))


class FactMerger:
    """
    Merges fact data from parsed.json into hierarchy structures.

    Loads facts and indexes them by concept name for efficient lookup.
    Used by hierarchy builder to add context_ref to mat_acc_id.

    Example:
        merger = FactMerger()
        merger.load_from_parsed_json(parsed_json_path)

        # During hierarchy building:
        for node in hierarchy:
            facts = merger.get_facts_for_concept(node.concept)
            for fact in facts:
                # Create node instance with context_ref
                create_fact_node(node, fact.context_ref, fact.value)
    """

    def __init__(self):
        """Initialize the fact merger."""
        self.logger = logging.getLogger('hierarchy.fact_merger')

        # Index: concept -> list of FactInstance
        self._facts_by_concept: dict[str, list[FactInstance]] = defaultdict(list)

        # Index: normalized concept key -> list of FactInstance
        # This enables matching regardless of separator (: vs _)
        self._facts_by_key: dict[str, list[FactInstance]] = defaultdict(list)

        # Index: concept (local name only) -> list of FactInstance
        self._facts_by_local_name: dict[str, list[FactInstance]] = defaultdict(list)

        # All contexts from parsed.json
        self._contexts: dict[str, dict] = {}

        # All units from parsed.json
        self._units: dict[str, dict] = {}

        # Statistics
        self._total_facts = 0
        self._numeric_facts = 0

    def load_from_parsed_json(self, json_path: Path) -> bool:
        """
        Load facts from a parsed.json file.

        Args:
            json_path: Path to parsed.json file

        Returns:
            True if loading succeeded, False otherwise
        """
        if not json_path.exists():
            self.logger.warning(f"Parsed JSON not found: {json_path}")
            return False

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return self._load_from_data(data)

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error in {json_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error loading {json_path}: {e}")
            return False

    def _load_from_data(self, data: dict) -> bool:
        """Load facts from parsed data dictionary."""
        # Clear existing data
        self._facts_by_concept.clear()
        self._facts_by_key.clear()
        self._facts_by_local_name.clear()
        self._contexts.clear()
        self._units.clear()
        self._total_facts = 0
        self._numeric_facts = 0

        # Check for nested instance structure
        instance_data = data.get('instance', {})

        # Load contexts - check both top level and instance level
        contexts_data = data.get('contexts', {})
        if not contexts_data:
            contexts_data = instance_data.get('contexts', {})
        if isinstance(contexts_data, dict):
            self._contexts = contexts_data
        elif isinstance(contexts_data, list):
            for ctx in contexts_data:
                ctx_id = ctx.get('id', ctx.get('context_id'))
                if ctx_id:
                    self._contexts[ctx_id] = ctx

        # Load units - check both top level and instance level
        units_data = data.get('units', {})
        if not units_data:
            units_data = instance_data.get('units', {})
        if isinstance(units_data, dict):
            self._units = units_data
        elif isinstance(units_data, list):
            for unit in units_data:
                unit_id = unit.get('id', unit.get('unit_id'))
                if unit_id:
                    self._units[unit_id] = unit

        # Load facts - check multiple possible locations
        # Structure 1: data['facts'] (flat)
        # Structure 2: data['instance']['facts'] (nested under instance)
        facts_data = data.get('facts', [])
        if not facts_data:
            facts_data = instance_data.get('facts', [])

        for fact_data in facts_data:
            fact = self._parse_fact(fact_data)
            if fact and fact.context_ref:
                # Index by full concept name
                self._facts_by_concept[fact.concept].append(fact)

                # Index by normalized key (for separator-agnostic matching)
                concept_key = self._get_concept_key(fact.concept)
                self._facts_by_key[concept_key].append(fact)

                # Also index by local name (without prefix)
                local_name = self._get_local_name(fact.concept)
                self._facts_by_local_name[local_name].append(fact)

                self._total_facts += 1
                if fact.has_numeric_value:
                    self._numeric_facts += 1

        self.logger.info(
            f"Loaded {self._total_facts} facts ({self._numeric_facts} numeric) "
            f"for {len(self._facts_by_concept)} concepts"
        )

        return True

    def _parse_fact(self, data: dict) -> Optional[FactInstance]:
        """Parse a fact from JSON data."""
        try:
            concept = (
                data.get('concept') or
                data.get('name') or
                data.get('qname') or
                ''
            )

            if not concept:
                return None

            context_ref = data.get('context_ref', data.get('contextRef'))
            if not context_ref:
                return None

            # Get period info from context
            period_type = None
            period_start = None
            period_end = None

            if context_ref in self._contexts:
                ctx = self._contexts[context_ref]
                period = ctx.get('period', {})

                if 'instant' in period:
                    period_type = 'instant'
                    period_end = period['instant']
                elif 'startDate' in period or 'start_date' in period:
                    period_type = 'duration'
                    period_start = period.get('startDate', period.get('start_date'))
                    period_end = period.get('endDate', period.get('end_date'))

            # Also check fact-level period info
            if not period_type:
                period_type = data.get('period_type')
                period_start = data.get('period_start', data.get('startDate'))
                period_end = data.get('period_end', data.get('endDate', data.get('instant')))

            return FactInstance(
                concept=concept,
                context_ref=context_ref,
                value=data.get('value', data.get('fact_value')),
                unit=data.get('unit', data.get('unit_ref')),
                decimals=data.get('decimals'),
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                dimensions=data.get('dimensions', {})
            )

        except Exception as e:
            self.logger.warning(f"Error parsing fact: {e}")
            return None

    def _normalize_concept(self, concept: str) -> str:
        """
        Normalize concept name for matching.

        Handles different separator formats by converting to canonical form.
        The canonical form uses colon (:) as namespace separator.

        Examples:
            ifrs-full_Assets -> ifrs-full:Assets
            us-gaap:Revenue -> us-gaap:Revenue (unchanged)
            tescoplc_CustomConcept -> tescoplc:CustomConcept
        """
        if not concept:
            return concept

        # If already has colon, it's in canonical form
        if ':' in concept:
            return concept

        # Find the namespace separator (first underscore that separates prefix from local name)
        # Pattern: prefix_LocalName where LocalName starts with uppercase
        if '_' in concept:
            idx = concept.find('_')
            prefix = concept[:idx]
            local_name = concept[idx + 1:]

            # Validate: prefix should exist and local name should start with uppercase
            # or prefix should contain a hyphen (like ifrs-full, us-gaap)
            if prefix and local_name:
                return f"{prefix}:{local_name}"

        return concept

    def _get_concept_key(self, concept: str) -> str:
        """
        Get a normalized key for concept matching.

        Creates a key that will match regardless of separator used.
        Converts to lowercase and removes all separators for comparison.
        """
        if not concept:
            return ''

        # Remove all namespace separators and convert to lowercase
        key = concept.replace(':', '_').replace('-', '_').lower()
        return key

    def _get_local_name(self, concept: str) -> str:
        """Extract local name from QName (remove prefix)."""
        # Handle both : and _ as separators
        if ':' in concept:
            return concept.split(':', 1)[1]
        if '_' in concept:
            return concept.split('_', 1)[1]
        return concept

    def get_facts_for_concept(
        self,
        concept: str,
        include_local_name_match: bool = True
    ) -> list[FactInstance]:
        """
        Get all facts for a concept.

        Matches concepts regardless of separator format (: vs _).
        For example, 'ifrs-full_Assets' will match 'ifrs-full:Assets'.

        Args:
            concept: Concept name (e.g., 'us-gaap:Assets' or 'us-gaap_Assets')
            include_local_name_match: Also match by local name only

        Returns:
            List of FactInstance objects
        """
        results = []
        seen = set()  # Track (concept, context_ref) to avoid duplicates

        # Primary lookup: use normalized key for separator-agnostic matching
        concept_key = self._get_concept_key(concept)
        if concept_key in self._facts_by_key:
            for fact in self._facts_by_key[concept_key]:
                key = (fact.concept, fact.context_ref)
                if key not in seen:
                    results.append(fact)
                    seen.add(key)

        # Fallback: try local name match if no results and enabled
        if not results and include_local_name_match:
            local_name = self._get_local_name(concept)
            if local_name in self._facts_by_local_name:
                for fact in self._facts_by_local_name[local_name]:
                    key = (fact.concept, fact.context_ref)
                    if key not in seen:
                        results.append(fact)
                        seen.add(key)

        return results

    def get_numeric_facts_for_concept(self, concept: str) -> list[FactInstance]:
        """Get only numeric facts for a concept."""
        all_facts = self.get_facts_for_concept(concept)
        return [f for f in all_facts if f.has_numeric_value]

    def get_facts_for_context(self, context_ref: str) -> list[FactInstance]:
        """Get all facts for a specific context."""
        results = []
        for facts in self._facts_by_concept.values():
            for fact in facts:
                if fact.context_ref == context_ref:
                    results.append(fact)
        return results

    def get_available_contexts(self) -> list[str]:
        """Get list of all available context references."""
        contexts = set()
        for facts in self._facts_by_concept.values():
            for fact in facts:
                contexts.add(fact.context_ref)
        return sorted(contexts)

    def get_context_info(self, context_ref: str) -> Optional[dict]:
        """Get context details by reference."""
        return self._contexts.get(context_ref)

    @property
    def total_facts(self) -> int:
        """Total number of facts loaded."""
        return self._total_facts

    @property
    def numeric_facts_count(self) -> int:
        """Number of numeric facts."""
        return self._numeric_facts

    @property
    def concept_count(self) -> int:
        """Number of unique concepts."""
        return len(self._facts_by_concept)

    def clear(self):
        """Clear all loaded data."""
        self._facts_by_concept.clear()
        self._facts_by_key.clear()
        self._facts_by_local_name.clear()
        self._contexts.clear()
        self._units.clear()
        self._total_facts = 0
        self._numeric_facts = 0


__all__ = ['FactMerger', 'FactInstance']
