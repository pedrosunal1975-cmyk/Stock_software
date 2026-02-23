# Path: mat_acc/ratio_check/values/value_populator.py
"""
Value Populator

Populates numeric values for matched components using a 6-pass strategy:
1. Atomic values from core financial statements only
2. Composite values from populated atomics (formula computation)
3. Fallback formula for remaining unvalued atomics
4. Alternative recovery with quality threshold (core statements only)
5. Supplementary recovery from detail/disclosure schedules
6. Recompute composites/fallback after all values loaded

Signs are preserved as-is from source data (iXBRL/MIU corrections).
Formula-convention cases (e.g. interest_expense in coverage ratios)
are handled via abs: prefix in ratio definitions, not here.

Composites and fallback formulas fire BEFORE alternatives so that
computed values (e.g. total_assets - current_assets) take priority
over low-confidence alternative matches from the candidate list.
Pass 6 recomputes any composites that failed in Pass 2 because
their dependencies were only available from supplementary sources.
"""

from typing import Optional, Dict, List, Any

from core.logger.ipo_logging import get_process_logger
from process.matcher.models.concept_metadata import ConceptIndex

from ..ratio_models import ComponentMatch
from ..fact_value_lookup import FactValueLookup


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

        Six-pass strategy with source priority:
        Pass 1 - Atomic lookup from core statements only
        Pass 2 - Composite formula computation
        Pass 3 - Fallback formula for remaining unvalued
        Pass 4 - Alternative recovery with quality threshold
        Pass 5 - Supplementary recovery from detail schedules
        Pass 6 - Recompute composites/fallback with all values

        Signs preserved as-is from source (MIU is authority).
        Composites and fallback formulas fire BEFORE alternatives
        so computed values take priority over weak alt matches.
        Pass 6 catches composites whose dependencies were only
        available from supplementary sources (e.g. interest_expense
        in detail schedules blocks EBITDA computation in Pass 2).

        Args:
            matches: ComponentMatch list with matched_concept set
            value_lookup: FactValueLookup with loaded values
            resolution: ResolutionMap with alternatives per component
            concept_index: ConceptIndex for label lookup
        """
        match_lookup = {m.component_name: m for m in matches}

        self._pass_atomic(matches, value_lookup, core_only=True)
        self._pass_composites(matches, match_lookup)
        self._pass_fallback(matches, match_lookup)

        if resolution:
            self._pass_alternatives(
                matches, value_lookup, resolution, concept_index,
                core_only=True,
            )

        self._pass_supplementary(matches, value_lookup)
        self._pass_recompute(matches, match_lookup)

    def _pass_atomic(
        self,
        matches: List[ComponentMatch],
        value_lookup: FactValueLookup,
        core_only: bool = False,
    ) -> None:
        """Pass 1: populate atomic values from source files."""
        for match in matches:
            if not match.matched or not match.matched_concept:
                continue
            if match.matched_concept.startswith('COMPOSITE:'):
                continue
            value = value_lookup.get_value(
                match.matched_concept, core_only=core_only,
            )
            if value is not None:
                match.value = value

    def _pass_alternatives(
        self,
        matches: List[ComponentMatch],
        value_lookup: FactValueLookup,
        resolution,
        concept_index: Optional[ConceptIndex] = None,
        core_only: bool = False,
    ) -> None:
        """
        Pass 4: try alternative matches for unvalued components.

        When the primary match has no value in reported facts,
        iterate through alternative matches (ranked by score)
        and use the first one that has a reported value.

        Alternatives must meet a quality threshold relative to the
        primary match score. This prevents garbage low-score matches
        from contaminating values when composites/fallback formulas
        have already been tried.
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
                core_only=core_only,
                primary_score=match_result.total_score,
            )

    def _try_alternatives(
        self,
        match: ComponentMatch,
        alternatives,
        value_lookup: FactValueLookup,
        concept_index: Optional[ConceptIndex],
        core_only: bool = False,
        primary_score: int = 0,
    ) -> None:
        """Try each alternative that meets quality threshold.

        Alternatives must score at least 50% of the primary match
        score (minimum 15 absolute) to prevent weak matches from
        contaminating values.
        """
        min_alt_score = max(15, primary_score * 0.5)

        for alt in alternatives:
            if not alt.concept:
                continue
            if alt.total_score < min_alt_score:
                self.logger.debug(
                    f"[ALT SKIP] {match.component_name}: "
                    f"{alt.concept} score={alt.total_score} < "
                    f"min={min_alt_score:.0f}"
                )
                continue
            value = value_lookup.get_value(
                alt.concept, core_only=core_only,
            )
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
                    f"{alt.concept} (value={value:,.0f}, "
                    f"score={alt.total_score})"
                )
                break

    def _pass_composites(
        self,
        matches: List[ComponentMatch],
        match_lookup: Dict[str, ComponentMatch],
    ) -> None:
        """Pass 2: compute composite values from atomic values."""
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
        """Pass 3: fallback formula for atomic matches with no value."""
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

    def _pass_supplementary(
        self,
        matches: List[ComponentMatch],
        value_lookup: FactValueLookup,
    ) -> None:
        """Pass 5: supplementary recovery from detail schedules.

        For components still without values after core lookups,
        composites, and fallback formulas, try detail/disclosure
        schedule values as last resort.
        """
        recovered = 0
        for match in matches:
            if match.value is not None:
                continue
            if not match.matched or not match.matched_concept:
                continue
            if match.matched_concept.startswith('COMPOSITE:'):
                continue
            value = value_lookup.get_value(match.matched_concept)
            if value is not None:
                match.value = value
                recovered += 1
        if recovered:
            self.logger.info(
                f"[SUPPLEMENTARY] Recovered {recovered} values "
                f"from detail/disclosure schedules"
            )

    def _pass_recompute(
        self,
        matches: List[ComponentMatch],
        match_lookup: Dict[str, ComponentMatch],
    ) -> None:
        """Pass 6: recompute composites/fallback after all values.

        Composites that failed in Pass 2 because dependencies had
        no value yet (e.g. interest_expense only in supplementary)
        can now compute with all values populated.
        """
        recomputed = 0
        for match in matches:
            if match.value is not None:
                continue
            if not match.matched or not match.matched_concept:
                continue
            if match.matched_concept.startswith('COMPOSITE:'):
                formula = match.matched_concept.replace(
                    'COMPOSITE:', ''
                )
                val = evaluate_formula(formula, match_lookup)
                if val is not None:
                    match.value = val
                    recomputed += 1
            elif match.fallback_formula:
                val = evaluate_formula(
                    match.fallback_formula, match_lookup
                )
                if val is not None:
                    match.value = val
                    recomputed += 1
        if recomputed:
            self.logger.info(
                f"[RECOMPUTE] {recomputed} composites/fallback "
                f"computed after all values loaded"
            )


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
