# Path: mat_acc/ratio_check/match_verify/match_verifier.py
"""
Match Verifier (PMFV - Post-Match Financial Verification)

Validates matched components and promotes alternatives when
the original match fails verification. Three strategies:
1. Qualifier rules: semantic name qualifiers (Current vs Noncurrent)
2. Plausibility: cross-component value relationships
3. Alternative promotion: try next-best when match fails

Runs AFTER value population, BEFORE ratio calculation.
"""

from typing import Optional, List

from core.logger.ipo_logging import get_process_logger
from process.matcher.models.concept_metadata import ConceptIndex

from ..ratio_models import ComponentMatch
from ..fact_value_lookup import FactValueLookup
from .qualifier_rules import check_qualifier
from .plausibility_checks import check_plausibility


logger = get_process_logger('match_verifier')

# Only scrutinize matches below this score for plausibility.
VERIFY_THRESHOLD = 55.0
MAX_ALTERNATIVES = 5


class MatchVerifier:
    """Post-match verification engine with alternative promotion."""

    def __init__(self):
        self.logger = get_process_logger('match_verifier')
        self._corrections: list[dict] = []

    def verify(
        self,
        matches: List[ComponentMatch],
        resolution,
        concept_index: ConceptIndex,
        value_lookup: FactValueLookup,
    ) -> List[ComponentMatch]:
        """Verify matches and promote alternatives for flagged ones."""
        self._corrections.clear()

        # Phase 1: qualifier checks (name-based)
        qual_flags = self._run_qualifier_checks(matches, concept_index)

        # Phase 2: plausibility checks (value-based)
        plaus_flags = self._run_plausibility_checks(matches)

        all_flags = {**qual_flags, **plaus_flags}
        if not all_flags:
            self.logger.info("PMFV: all matches verified OK")
            return matches

        self.logger.info(
            f"PMFV: {len(all_flags)} matches flagged for review"
        )

        # Phase 3: promote alternatives for flagged matches
        match_lookup = {m.component_name: m for m in matches}
        changed = self._promote_alternatives(
            all_flags, match_lookup, resolution,
            concept_index, value_lookup,
        )

        # Phase 4: re-run plausibility if anything changed
        if changed:
            self._recheck_plausibility(matches, changed)

        count = len(self._corrections)
        self.logger.info(
            f"PMFV: {count} corrections applied"
            if count else "PMFV: no corrections needed"
        )
        return matches

    def get_corrections(self) -> list[dict]:
        """Return corrections made during verification."""
        return list(self._corrections)

    def _run_qualifier_checks(
        self, matches: List[ComponentMatch], concept_index: ConceptIndex,
    ) -> dict[str, str]:
        """Run qualifier checks on all matched components."""
        flags = {}
        for match in matches:
            if not match.matched or match.matched_concept is None:
                continue
            if match.confidence >= 100:
                continue
            local_name = self._get_local_name(
                match.matched_concept, concept_index,
            )
            if not local_name:
                continue
            result = check_qualifier(match.component_name, local_name)
            if not result['valid']:
                flags[match.component_name] = result['reason']
                self.logger.info(f"  PMFV qualifier: {result['reason']}")
        return flags

    def _run_plausibility_checks(
        self, matches: List[ComponentMatch],
    ) -> dict[str, str]:
        """Run plausibility checks on low-confidence matches."""
        flags = {}
        all_values = {
            m.component_name: m.value
            for m in matches if m.matched
        }
        for match in matches:
            if not match.matched or match.value is None:
                continue
            if match.confidence > VERIFY_THRESHOLD:
                continue
            if match.confidence >= 100:
                continue
            result = check_plausibility(
                match.component_name, match.value, all_values,
            )
            if not result['valid']:
                flags[match.component_name] = result['reason']
                self.logger.info(f"  PMFV plausibility: {result['reason']}")
        return flags

    def _promote_alternatives(
        self, flags, match_lookup, resolution,
        concept_index, value_lookup,
    ) -> set[str]:
        """Try alternative candidates for flagged matches."""
        changed = set()
        for component_id in flags:
            match = match_lookup.get(component_id)
            if not match:
                continue
            match_result = getattr(resolution, 'matches', {}).get(
                component_id,
            )
            if not match_result or not match_result.alternatives:
                self.logger.info(
                    f"  PMFV: {component_id} - no alternatives"
                )
                continue
            if self._try_alternatives(
                component_id, match, match_result.alternatives,
                concept_index, value_lookup, match_lookup,
            ):
                changed.add(component_id)
        return changed

    def _try_alternatives(
        self, component_id, current_match, alternatives,
        concept_index, value_lookup, match_lookup,
    ) -> bool:
        """Try alternatives for a flagged component. True if promoted."""
        old_concept = current_match.matched_concept
        old_value = current_match.value
        all_values = {
            m.component_name: m.value
            for m in match_lookup.values() if m.matched
        }
        tried = 0
        for alt in alternatives:
            if tried >= MAX_ALTERNATIVES:
                break
            if alt.is_rejected or alt.concept == old_concept:
                continue
            tried += 1

            local_name = self._get_local_name(
                alt.concept, concept_index,
            )
            if not local_name:
                continue
            if not check_qualifier(component_id, local_name)['valid']:
                continue

            alt_value = value_lookup.get_value(alt.concept)
            if alt_value is None:
                continue

            test_values = dict(all_values)
            test_values[component_id] = alt_value
            plaus = check_plausibility(
                component_id, alt_value, test_values,
            )
            if not plaus['valid']:
                continue

            # Promote this alternative
            self._apply_promotion(
                current_match, alt, alt_value,
                concept_index, old_concept, old_value,
            )
            return True

        self.logger.info(
            f"  PMFV: {component_id} - no valid alternative, "
            f"keeping original"
        )
        return False

    def _apply_promotion(
        self, match, alt, alt_value, concept_index,
        old_concept, old_value,
    ) -> None:
        """Apply a verified alternative promotion."""
        match.matched_concept = alt.concept
        match.confidence = float(alt.total_score)
        match.value = alt_value
        concept = concept_index.get_concept(alt.concept)
        if concept:
            match.label = (
                concept.get_label('standard')
                or concept.get_label('taxonomy')
            )
        old_short = (old_concept or '?').split(':')[-1]
        new_short = (alt.concept or '?').split(':')[-1]
        self._corrections.append({
            'component': match.component_name,
            'old_concept': old_concept,
            'old_value': old_value,
            'new_concept': alt.concept,
            'new_value': alt_value,
        })
        fmt_old = f"{old_value:,.0f}" if old_value else '?'
        fmt_new = f"{alt_value:,.0f}"
        self.logger.info(
            f"  PMFV PROMOTED: {match.component_name}: "
            f"{old_short} ({fmt_old}) -> {new_short} ({fmt_new})"
        )

    def _recheck_plausibility(self, matches, changed) -> None:
        """Re-run plausibility for non-changed components."""
        all_values = {
            m.component_name: m.value
            for m in matches if m.matched
        }
        for match in matches:
            if not match.matched or match.value is None:
                continue
            if match.component_name in changed:
                continue
            result = check_plausibility(
                match.component_name, match.value, all_values,
            )
            if not result['valid']:
                self.logger.info(
                    f"  PMFV recheck: {result['reason']}"
                )

    def _get_local_name(self, concept_qname, concept_index) -> str:
        """Extract local name from a concept qname."""
        concept = concept_index.get_concept(concept_qname)
        if concept and concept.local_name:
            return concept.local_name
        if ':' in concept_qname:
            return concept_qname.split(':')[-1]
        if '_' in concept_qname:
            parts = concept_qname.split('_', 1)
            if len(parts) == 2:
                return parts[1]
        return concept_qname


__all__ = ['MatchVerifier']
