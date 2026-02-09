# Path: verification/engine/checks_v2/tools/context/grouper.py
"""
Context Grouper for XBRL Verification

Groups facts by context_id for C-Equal verification.

Techniques consolidated from:
- checks/context/context_grouping.py

DESIGN: Stateful container that accumulates facts grouped by context.
Used during discovery/preparation stages to organize facts for verification.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Iterator

from ...constants.tolerances import SAMPLE_CONCEPTS_LIMIT, SAMPLE_CONTEXTS_LIMIT


@dataclass
class ContextGroup:
    """
    Facts grouped by context_id.

    All facts in a group are c-equal and can be compared in calculations.
    Tracks units and decimals for u-equal and tolerance checks.

    Attributes:
        context_id: XBRL context identifier (e.g., "c-4")
        facts: Dictionary mapping normalized concept -> fact info
    """
    context_id: str
    facts: dict[str, dict] = field(default_factory=dict)

    def add_fact(
        self,
        concept: str,
        value: float,
        original_concept: str = None,
        unit: Optional[str] = None,
        decimals: Optional[int] = None,
        is_nil: bool = False
    ) -> None:
        """
        Add a fact entry to this context group.

        Args:
            concept: Normalized concept name
            value: Numeric value
            original_concept: Original concept name as reported
            unit: Unit of measurement
            decimals: Decimal precision
            is_nil: Whether fact is nil-valued
        """
        if concept not in self.facts:
            self.facts[concept] = {
                'concept': concept,
                'original_concept': original_concept or concept,
                'entries': []
            }

        self.facts[concept]['entries'].append({
            'value': value,
            'unit': unit,
            'decimals': decimals,
            'is_nil': is_nil,
        })

    def get_value(self, concept: str) -> Optional[float]:
        """
        Get the value for a concept.

        Returns None if concept doesn't exist.
        If multiple entries, returns the first (most entries are single).

        Args:
            concept: Normalized concept name

        Returns:
            Float value or None
        """
        info = self.facts.get(concept)
        if not info or not info['entries']:
            return None
        return info['entries'][0]['value']

    def get_unit(self, concept: str) -> Optional[str]:
        """Get the unit for a concept."""
        info = self.facts.get(concept)
        if not info or not info['entries']:
            return None
        return info['entries'][0]['unit']

    def get_decimals(self, concept: str) -> Optional[int]:
        """Get the decimals for a concept."""
        info = self.facts.get(concept)
        if not info or not info['entries']:
            return None
        return info['entries'][0]['decimals']

    def get_original_name(self, concept: str) -> Optional[str]:
        """Get the original concept name."""
        info = self.facts.get(concept)
        if not info:
            return None
        return info.get('original_concept', concept)

    def get_all_values(self, concept: str) -> list[float]:
        """Get all values for a concept (handles duplicates)."""
        info = self.facts.get(concept)
        if not info:
            return []
        return [e['value'] for e in info['entries']]

    def has(self, concept: str) -> bool:
        """Check if concept exists in this context."""
        return concept in self.facts

    def has_duplicates(self, concept: str) -> bool:
        """Check if concept has multiple entries (duplicates)."""
        info = self.facts.get(concept)
        if not info:
            return False
        return len(info['entries']) > 1

    def __len__(self) -> int:
        return len(self.facts)


class ContextGrouper:
    """
    Container for facts grouped by context_id.

    Provides access to facts organized by their XBRL context.
    This is the primary data structure for c-equal verification.

    Usage:
        grouper = ContextGrouper()

        # Add facts
        grouper.add_fact('assets', 1000000, context_id='c-1', unit='USD')
        grouper.add_fact('liabilities', 500000, context_id='c-1', unit='USD')

        # Get facts for a context
        context = grouper.get_context('c-1')
        assets = context.get_value('assets')  # -> 1000000

        # Iterate over contexts
        for context in grouper.iter_groups():
            print(f"{context.context_id}: {len(context)} facts")
    """

    def __init__(self):
        self._groups: dict[str, ContextGroup] = {}
        self.logger = logging.getLogger('tools.context.grouper')

    def add_fact(
        self,
        concept: str,
        value: float,
        context_id: str,
        original_concept: str = None,
        unit: Optional[str] = None,
        decimals: Optional[int] = None,
        is_nil: bool = False
    ) -> None:
        """
        Add a fact to the appropriate context group.

        Args:
            concept: Normalized concept name
            value: Numeric value
            context_id: XBRL context identifier
            original_concept: Original concept name
            unit: Unit of measurement
            decimals: Decimal precision
            is_nil: Whether fact is nil-valued
        """
        if context_id not in self._groups:
            self._groups[context_id] = ContextGroup(context_id=context_id)

        self._groups[context_id].add_fact(
            concept=concept,
            value=value,
            original_concept=original_concept,
            unit=unit,
            decimals=decimals,
            is_nil=is_nil,
        )

    def get_context(self, context_id: str) -> Optional[ContextGroup]:
        """Get the fact group for a specific context."""
        return self._groups.get(context_id)

    def get_contexts(self) -> list[str]:
        """Get all context IDs."""
        return list(self._groups.keys())

    def get_contexts_with_concept(self, concept: str) -> list[str]:
        """Get all context IDs that contain a specific concept."""
        return [
            ctx_id for ctx_id, group in self._groups.items()
            if concept in group.facts
        ]

    def iter_groups(self) -> Iterator[ContextGroup]:
        """Iterate over all context groups."""
        yield from self._groups.values()

    def get_all_facts_by_concept(self) -> dict[str, list[tuple[str, float, Optional[str], Optional[int]]]]:
        """
        Get all facts indexed by concept for cross-context lookups.

        Returns a dictionary where:
        - Key: normalized concept name
        - Value: list of (context_id, value, unit, decimals) tuples

        This is used for dimensional fallback lookups when
        facts are reported with dimensional qualifiers.
        """
        result = {}
        for ctx_id, group in self._groups.items():
            for concept, info in group.facts.items():
                if concept not in result:
                    result[concept] = []
                for entry in info['entries']:
                    result[concept].append((
                        ctx_id,
                        entry['value'],
                        entry['unit'],
                        entry['decimals']
                    ))
        return result

    def get_diagnostic_summary(self) -> dict:
        """
        Get diagnostic summary of what facts are in the groups.

        Returns dict with:
        - total_contexts: number of contexts
        - total_concepts: number of unique concepts (normalized)
        - sample_concepts: sample concept names for inspection
        - contexts_sample: sample of context_id -> concept count
        """
        all_concepts = set()
        context_concept_counts = {}

        for ctx_id, group in self._groups.items():
            context_concept_counts[ctx_id] = len(group.facts)
            all_concepts.update(group.facts.keys())

        return {
            'total_contexts': len(self._groups),
            'total_concepts': len(all_concepts),
            'sample_concepts': sorted(list(all_concepts))[:SAMPLE_CONCEPTS_LIMIT],
            'contexts_sample': dict(list(context_concept_counts.items())[:SAMPLE_CONTEXTS_LIMIT]),
        }

    @property
    def total_facts(self) -> int:
        """Total number of unique concept entries across all contexts."""
        return sum(len(g) for g in self._groups.values())

    @property
    def context_count(self) -> int:
        """Number of unique contexts."""
        return len(self._groups)

    def __len__(self) -> int:
        return len(self._groups)


__all__ = ['ContextGroup', 'ContextGrouper']
