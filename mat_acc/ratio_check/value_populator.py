# Path: mat_acc/ratio_check/value_populator.py
"""
Value Populator

Populates numeric values for matched components using a 4-pass strategy:
1. Atomic values from source files (direct lookup)
2. Alternative recovery (try alternative matches for unvalued)
3. Composite values from populated atomics (formula computation)
4. Fallback formula for remaining unvalued atomics

This module bridges matching (concept identification) and calculation
(ratio computation) by ensuring matched concepts have actual values.
"""

from typing import Optional, Dict, List, Any

from core.logger.ipo_logging import get_process_logger
from process.matcher.models.concept_metadata import ConceptIndex

from .ratio_models import ComponentMatch
from .fact_value_lookup import FactValueLookup


logger = get_process_logger('value_populator')


class ValuePopulator:
    """Populates values for matched components from source files."""

    def __init__(self):
        self.logger = get_process_logger('value_populator')

    def populate(
        self,
        matches: List[ComponentMatch],
        value_lookup: FactValueLookup,
        resolution=None,
        concept_index: Optional[ConceptIndex] = None,
    ) -> None:
        """
        Populate values for matched components.

        Four-pass strategy ensures maximum value coverage:
        Pass 1 - Atomic lookup from source files
        Pass 2 - Alternative recovery for unvalued atomics
        Pass 3 - Composite formula computation
        Pass 4 - Fallback formula for remaining unvalued

        Args:
            matches: ComponentMatch list with matched_concept set
            value_lookup: FactValueLookup with loaded values
            resolution: ResolutionMap with alternatives per component
            concept_index: ConceptIndex for label lookup
        """
        match_lookup = {m.component_name: m for m in matches}

        self._pass_atomic(matches, value_lookup)

        if resolution:
            self._pass_alternatives(
                matches, value_lookup, resolution, concept_index,
            )

        self._pass_composites(matches, match_lookup)
        self._pass_fallback(matches, match_lookup)

    def _pass_atomic(
        self,
        matches: List[ComponentMatch],
        value_lookup: FactValueLookup,
    ) -> None:
        """Pass 1: populate atomic values from source files."""
        for match in matches:
            if not match.matched or not match.matched_concept:
                continue
            if match.matched_concept.startswith('COMPOSITE:'):
                continue
            value = value_lookup.get_value(match.matched_concept)
            if value is not None:
                match.value = value

    def _pass_alternatives(
        self,
        matches: List[ComponentMatch],
        value_lookup: FactValueLookup,
        resolution,
        concept_index: Optional[ConceptIndex] = None,
    ) -> None:
        """
        Pass 2: try alternative matches for unvalued components.

        When the primary match has no value in reported facts,
        iterate through alternative matches (ranked by score)
        and use the first one that has a reported value.

        This is principle-based: any filing can have concepts in its
        presentation structure that lack reported fact values, while
        a lower-scoring alternative actually carries the data.
        """
        for match in matches:
            if match.value is not None:
                continue
            if not match.matched:
                continue
            if match.matched_concept.startswith('COMPOSITE:'):
                continue

            match_result = resolution.matches.get(match.component_name)
            if not match_result or not match_result.alternatives:
                continue

            self._try_alternatives(
                match, match_result.alternatives,
                value_lookup, concept_index,
            )

    def _try_alternatives(
        self,
        match: ComponentMatch,
        alternatives,
        value_lookup: FactValueLookup,
        concept_index: Optional[ConceptIndex],
    ) -> None:
        """Try each alternative until one has a value."""
        for alt in alternatives:
            if not alt.concept:
                continue
            value = value_lookup.get_value(alt.concept)
            if value is not None:
                old_concept = match.matched_concept
                match.matched_concept = alt.concept
                match.confidence = float(alt.total_score)
                match.value = value
                if concept_index:
                    alt_meta = concept_index.get_concept(alt.concept)
                    if alt_meta:
                        match.label = (
                            alt_meta.get_label('standard')
                            or alt_meta.get_label('taxonomy')
                        )
                self.logger.info(
                    f"[ALT RECOVERY] {match.component_name}: "
                    f"{old_concept} (no value) -> "
                    f"{alt.concept} (value={value:,.0f})"
                )
                break

    def _pass_composites(
        self,
        matches: List[ComponentMatch],
        match_lookup: Dict[str, ComponentMatch],
    ) -> None:
        """Pass 3: compute composite values from atomic values."""
        for match in matches:
            if not match.matched or not match.matched_concept:
                continue
            if not match.matched_concept.startswith('COMPOSITE:'):
                continue
            formula = match.matched_concept.replace('COMPOSITE:', '')
            match.value = evaluate_formula(formula, match_lookup)

    def _pass_fallback(
        self,
        matches: List[ComponentMatch],
        match_lookup: Dict[str, ComponentMatch],
    ) -> None:
        """Pass 4: fallback formula for atomic matches with no value."""
        for match in matches:
            if match.value is not None:
                continue
            if not match.matched or not match.fallback_formula:
                continue
            computed = evaluate_formula(
                match.fallback_formula, match_lookup
            )
            if computed is not None:
                match.value = computed


def evaluate_formula(
    formula: str,
    match_lookup: Dict[str, ComponentMatch],
) -> Optional[float]:
    """
    Evaluate a simple arithmetic formula using component values.

    Handles: a + b, a - b, a / b, a + b + c + d

    Args:
        formula: Formula string (e.g., "total_assets - total_equity")
        match_lookup: Component name to ComponentMatch mapping

    Returns:
        Computed value or None if any component missing
    """
    tokens = formula.replace('+', ' + ').replace(
        '-', ' - '
    ).replace('/', ' / ').split()

    result = None
    operator = '+'

    for token in tokens:
        if token in ('+', '-', '/'):
            operator = token
            continue

        component = match_lookup.get(token)
        if not component or component.value is None:
            return None

        val = component.value
        if result is None:
            result = val if operator == '+' else -val
        elif operator == '+':
            result += val
        elif operator == '-':
            result -= val
        elif operator == '/' and val != 0:
            result /= val
        else:
            return None

    return result


__all__ = ['ValuePopulator', 'evaluate_formula']
