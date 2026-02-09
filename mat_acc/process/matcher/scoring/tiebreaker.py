# Path: mat_acc/process/matcher/scoring/tiebreaker.py
"""
Tiebreaker

Resolves ties when multiple concepts have equal scores.
"""

import logging
from typing import Optional

from ..models.match_result import ScoredMatch
from ..models.concept_metadata import ConceptMetadata, ConceptIndex
from ..models.component_definition import TiebreakerType


class Tiebreaker:
    """
    Resolves ties between equally-scored matches.

    Tiebreaker strategies:
    - HIGHEST_IN_HIERARCHY: Prefer concepts closer to root
    - MOST_CHILDREN: Prefer concepts with more calculation children
    - EXACT_LABEL_MATCH: Prefer exact label matches over partial
    - FIRST_IN_PRESENTATION: Prefer concepts appearing first

    Example:
        tiebreaker = Tiebreaker()
        best_match = tiebreaker.resolve(
            matches=[match1, match2, match3],
            strategy=TiebreakerType.HIGHEST_IN_HIERARCHY,
            concept_index=index
        )
    """

    def __init__(self):
        """Initialize tiebreaker."""
        self.logger = logging.getLogger('matcher.scoring.tiebreaker')

    def resolve(
        self,
        matches: list[ScoredMatch],
        strategy: TiebreakerType,
        concept_index: Optional[ConceptIndex] = None
    ) -> tuple[ScoredMatch, str]:
        """
        Resolve ties between matches.

        Args:
            matches: List of equally-scored matches
            strategy: Tiebreaker strategy to use
            concept_index: Index for looking up concept metadata

        Returns:
            Tuple of (best match, tiebreaker method used)
        """
        if len(matches) == 1:
            return matches[0], "single_match"

        if len(matches) == 0:
            raise ValueError("No matches to resolve")

        self.logger.debug(
            f"Resolving tie between {len(matches)} matches "
            f"using {strategy.value}"
        )

        if strategy == TiebreakerType.HIGHEST_IN_HIERARCHY:
            return self._resolve_by_hierarchy(matches, concept_index)

        elif strategy == TiebreakerType.MOST_CHILDREN:
            return self._resolve_by_children(matches, concept_index)

        elif strategy == TiebreakerType.EXACT_LABEL_MATCH:
            return self._resolve_by_exact_label(matches)

        elif strategy == TiebreakerType.FIRST_IN_PRESENTATION:
            return self._resolve_by_presentation_order(matches, concept_index)

        else:
            # Fallback: return first match
            self.logger.warning(
                f"Unknown tiebreaker strategy: {strategy}, using first match"
            )
            return matches[0], "fallback_first"

    def _resolve_by_hierarchy(
        self,
        matches: list[ScoredMatch],
        concept_index: Optional[ConceptIndex]
    ) -> tuple[ScoredMatch, str]:
        """Prefer concepts higher in hierarchy (lower level number)."""
        if not concept_index:
            return matches[0], "no_index_fallback"

        best_match = matches[0]
        best_level = float('inf')

        for match in matches:
            concept = concept_index.get_concept(match.concept)
            if concept:
                level = concept.presentation_level
                if level < best_level:
                    best_level = level
                    best_match = match

        return best_match, "highest_in_hierarchy"

    def _resolve_by_children(
        self,
        matches: list[ScoredMatch],
        concept_index: Optional[ConceptIndex]
    ) -> tuple[ScoredMatch, str]:
        """Prefer concepts with more calculation children."""
        if not concept_index:
            return matches[0], "no_index_fallback"

        best_match = matches[0]
        most_children = -1

        for match in matches:
            concept = concept_index.get_concept(match.concept)
            if concept:
                child_count = len(concept.calculation_children)
                if child_count > most_children:
                    most_children = child_count
                    best_match = match

        return best_match, "most_children"

    def _resolve_by_exact_label(
        self,
        matches: list[ScoredMatch]
    ) -> tuple[ScoredMatch, str]:
        """Prefer matches with exact label matches."""
        for match in matches:
            for rule_score in match.rule_scores:
                if rule_score.rule_type == 'label':
                    details = rule_score.details.get('matched_rules', [])
                    for rule in details:
                        if rule.get('match_type') == 'exact':
                            return match, "exact_label_match"

        # No exact match found, return first
        return matches[0], "no_exact_label_fallback"

    def _resolve_by_presentation_order(
        self,
        matches: list[ScoredMatch],
        concept_index: Optional[ConceptIndex]
    ) -> tuple[ScoredMatch, str]:
        """Prefer concepts appearing first in presentation."""
        if not concept_index:
            return matches[0], "no_index_fallback"

        best_match = matches[0]
        lowest_order = float('inf')

        for match in matches:
            concept = concept_index.get_concept(match.concept)
            if concept:
                order = concept.presentation_order
                if order < lowest_order:
                    lowest_order = order
                    best_match = match

        return best_match, "first_in_presentation"


__all__ = ['Tiebreaker']
