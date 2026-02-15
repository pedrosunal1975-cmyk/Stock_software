# Path: mat_acc/ratio_check/match_verify/match_verifier.py
"""
Match Verifier (PMFV - Post-Match Financial Verification)

Validates matched components and promotes alternatives when
the original match fails verification. Three strategies:
1. Qualifier rules: semantic name qualifiers (Current vs Noncurrent)
2. Plausibility: cross-component value relationships
3. Alternative promotion: try next-best when match fails
   (from matcher alternatives, then fallback concept scan)

Runs AFTER value population, BEFORE ratio calculation.
"""

from typing import List

from core.logger.ipo_logging import get_process_logger
from process.matcher.models.concept_metadata import ConceptIndex

from ..ratio_models import ComponentMatch
from ..fact_value_lookup import FactValueLookup
from .qualifier_rules import check_qualifier
from .plausibility_checks import check_plausibility
from .fallback_patterns import FALLBACK_PATTERNS


logger = get_process_logger('match_verifier')

MAX_ALTERNATIVES = 5
MAX_FALLBACK = 10


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
        qual_flags = self._run_qualifier_checks(matches, concept_index)
        plaus_flags = self._run_plausibility_checks(matches)
        all_flags = {**qual_flags, **plaus_flags}
        if not all_flags:
            self.logger.info("PMFV: all matches verified OK")
            return matches
        self.logger.info(
            f"PMFV: {len(all_flags)} matches flagged for review"
        )
        match_lookup = {m.component_name: m for m in matches}
        changed = self._promote_alternatives(
            all_flags, match_lookup, resolution,
            concept_index, value_lookup,
        )
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

    def _run_qualifier_checks(self, matches, concept_index):
        """Run qualifier checks on all matched components."""
        flags = {}
        for match in matches:
            if not match.matched or match.matched_concept is None:
                continue
            if match.confidence >= 100:
                continue
            local = self._get_local_name(
                match.matched_concept, concept_index,
            )
            if not local:
                continue
            result = check_qualifier(match.component_name, local)
            if not result['valid']:
                flags[match.component_name] = result['reason']
                self.logger.info(
                    f"  PMFV qualifier: {result['reason']}"
                )
        return flags

    def _run_plausibility_checks(self, matches):
        """Run plausibility checks on ALL matched components."""
        flags = {}
        all_vals = {
            m.component_name: m.value
            for m in matches if m.matched
        }
        for match in matches:
            if not match.matched or match.value is None:
                continue
            if match.confidence >= 100:
                continue
            result = check_plausibility(
                match.component_name, match.value, all_vals,
            )
            if not result['valid']:
                flags[match.component_name] = result['reason']
                self.logger.info(
                    f"  PMFV plausibility: {result['reason']}"
                )
        return flags

    def _promote_alternatives(
        self, flags, match_lookup, resolution,
        concept_index, value_lookup,
    ):
        """Try alternatives, then fallback scan for flagged matches."""
        changed = set()
        for comp_id in flags:
            match = match_lookup.get(comp_id)
            if not match:
                continue
            mr = getattr(resolution, 'matches', {}).get(comp_id)
            alts = mr.alternatives if mr else []
            if self._try_alternatives(
                comp_id, match, alts,
                concept_index, value_lookup, match_lookup,
            ):
                changed.add(comp_id)
                continue
            if self._try_fallback_scan(
                comp_id, match, concept_index,
                value_lookup, match_lookup,
            ):
                changed.add(comp_id)
        return changed

    def _try_alternatives(
        self, comp_id, current, alternatives,
        concept_index, value_lookup, match_lookup,
    ):
        """Try matcher alternatives for a flagged component."""
        if not alternatives:
            return False
        old = current.matched_concept
        vals = self._collect_values(match_lookup)
        tried = 0
        for alt in alternatives:
            if tried >= MAX_ALTERNATIVES:
                break
            if alt.is_rejected or alt.concept == old:
                continue
            tried += 1
            if self._check_and_promote(
                comp_id, current, alt.concept,
                float(alt.total_score), concept_index,
                value_lookup, vals,
            ):
                return True
        return False

    def _try_fallback_scan(
        self, comp_id, current, concept_index,
        value_lookup, match_lookup,
    ):
        """Scan concept index for valid replacements."""
        patterns = FALLBACK_PATTERNS.get(comp_id)
        if not patterns:
            self.logger.info(
                f"  PMFV: {comp_id} - no fallback patterns"
            )
            return False
        old = current.matched_concept
        vals = self._collect_values(match_lookup)
        candidates = set()
        for pattern in patterns:
            candidates.update(
                concept_index.find_by_local_name(pattern)
            )
        candidates.discard(old)
        tried = 0
        for qname in sorted(candidates):
            if tried >= MAX_FALLBACK:
                break
            tried += 1
            if self._check_and_promote(
                comp_id, current, qname, 0.0,
                concept_index, value_lookup, vals,
            ):
                return True
        self.logger.info(
            f"  PMFV: {comp_id} - no valid alternative "
            f"(checked {tried} fallback candidates)"
        )
        return False

    def _check_and_promote(
        self, comp_id, current, qname, score,
        concept_index, value_lookup, all_vals,
    ):
        """Check one candidate and promote if valid."""
        local = self._get_local_name(qname, concept_index)
        if not local:
            return False
        if not check_qualifier(comp_id, local)['valid']:
            return False
        val = value_lookup.get_value(qname)
        if val is None:
            return False
        test = dict(all_vals)
        test[comp_id] = val
        if not check_plausibility(comp_id, val, test)['valid']:
            return False
        self._apply_promotion(
            current, qname, score, val, concept_index,
        )
        return True

    def _apply_promotion(
        self, match, new_qname, new_score, new_value,
        concept_index,
    ):
        """Apply a verified alternative promotion."""
        old_concept = match.matched_concept
        old_value = match.value
        match.matched_concept = new_qname
        match.confidence = new_score
        match.value = new_value
        concept = concept_index.get_concept(new_qname)
        if concept:
            match.label = (
                concept.get_label('standard')
                or concept.get_label('taxonomy')
            )
        old_short = (old_concept or '?').split(':')[-1]
        new_short = (new_qname or '?').split(':')[-1]
        self._corrections.append({
            'component': match.component_name,
            'old_concept': old_concept, 'old_value': old_value,
            'new_concept': new_qname, 'new_value': new_value,
        })
        fmt_old = f"{old_value:,.0f}" if old_value else '?'
        fmt_new = f"{new_value:,.0f}"
        self.logger.info(
            f"  PMFV PROMOTED: {match.component_name}: "
            f"{old_short} ({fmt_old}) -> {new_short} ({fmt_new})"
        )

    def _recheck_plausibility(self, matches, changed):
        """Re-run plausibility for non-changed components."""
        all_vals = {
            m.component_name: m.value
            for m in matches if m.matched
        }
        for match in matches:
            if not match.matched or match.value is None:
                continue
            if match.component_name in changed:
                continue
            result = check_plausibility(
                match.component_name, match.value, all_vals,
            )
            if not result['valid']:
                self.logger.info(
                    f"  PMFV recheck: {result['reason']}"
                )

    def _collect_values(self, match_lookup):
        """Collect all current component values."""
        return {
            m.component_name: m.value
            for m in match_lookup.values() if m.matched
        }

    def _get_local_name(self, concept_qname, concept_index):
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
