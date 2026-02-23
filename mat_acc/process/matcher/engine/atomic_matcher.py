# Path: mat_acc/process/matcher/engine/atomic_matcher.py
"""
Atomic Matcher

Core matching engine for individual component-to-concept matching.
Evaluates candidates, scores, and selects the best match.
"""

from core.logger.ipo_logging import get_process_logger

from ..models.component_definition import ComponentDefinition
from ..models.concept_metadata import ConceptIndex
from ..models.match_result import MatchResult

from .candidate_filter import (
    get_candidates,
    log_candidate_diagnostics,
    matches_rejection,
    print_diagnostics_summary,
)


# Negating qualifiers: concepts containing these are semantically
# different from what a component typically wants.
_NEGATING_QUALIFIERS = [
    'discontinued',
    'disposalgroup',
    'usefullife',
    'heldforsale',
    'antidilutive',
    'incometaxreconciliation',
]

_QUALIFIER_PENALTY = 25


class AtomicMatcher:
    """Matches individual components against concept candidates."""

    def __init__(
        self, evaluators, score_aggregator, tiebreaker,
        components, diagnostics=True,
    ):
        self.evaluators = evaluators
        self.score_aggregator = score_aggregator
        self.tiebreaker = tiebreaker
        self.components = components
        self.diagnostics = diagnostics
        self.logger = get_process_logger('matcher.atomic')
        self._match_diagnostics: dict[str, dict] = {}

    def match(
        self, component: ComponentDefinition,
        concept_index: ConceptIndex,
    ) -> MatchResult:
        """Match a single atomic component."""
        cid = component.component_id
        diag = self._init_diagnostics(component)

        candidates = get_candidates(
            component, concept_index, self.logger,
        )
        diag['candidates_found'] = len(candidates)

        if self.diagnostics:
            log_candidate_diagnostics(
                cid, candidates, concept_index,
                diag['search_patterns'],
                self.components, self.logger,
            )

        if not candidates:
            diag['failure_reason'] = 'NO_CANDIDATES'
            self._match_diagnostics[cid] = diag
            self.logger.info(
                f"[MATCH FAIL] {cid}: No candidates. "
                f"Patterns={diag['search_patterns']}, "
                f"filters={diag['filters']}"
            )
            return MatchResult.no_match(
                cid, "No candidates found",
            )

        self.logger.info(
            f"[MATCH] {cid}: Evaluating "
            f"{len(candidates)} candidates"
        )

        scored, rej_count, below_count = (
            self._evaluate_candidates(
                component, candidates, concept_index, diag,
            )
        )

        if self.diagnostics:
            self.logger.info(
                f"  [CANDIDATES] {cid}: "
                f"{len(candidates)} found, "
                f"{rej_count} rejected, "
                f"{below_count} below threshold, "
                f"{len(scored)} passed"
            )

        if not scored:
            return self._handle_no_match(
                cid, len(candidates), rej_count, diag, component,
            )

        return self._select_best(
            cid, scored, concept_index, diag,
            component.scoring.tiebreaker,
        )

    def _init_diagnostics(self, comp):
        """Initialize diagnostic dict for a component."""
        patterns = []
        for r in (comp.matching_rules.label_rules or []):
            patterns.extend(r.patterns)
        filters = {}
        if comp.characteristics.balance_type:
            filters['balance_type'] = comp.characteristics.balance_type.value
        if comp.characteristics.period_type:
            filters['period_type'] = comp.characteristics.period_type.value
        return {
            'component_id': comp.component_id,
            'search_patterns': patterns, 'filters': filters,
            'candidates_found': 0, 'rejections': [],
            'below_threshold': [], 'passed_threshold': [],
            'failure_reason': None,
        }

    def _evaluate_candidates(
        self, component, candidates, concept_index, diag,
    ):
        """Evaluate all candidates, return scored matches."""
        scored_matches = []
        rej_count = 0
        below_count = 0

        for concept in candidates:
            exempt = self._is_exact_name_match(
                concept, component,
            )
            rejection = self._check_rejection(
                concept, component,
            )
            if rejection and not exempt:
                rej_count += 1
                diag['rejections'].append({
                    'concept': concept.qname,
                    'reason': rejection,
                })
                continue

            scored = self._score_concept(
                concept, component, concept_index,
            )
            if scored is None:
                continue

            penalty = self._qualifier_penalty(concept)
            if penalty > 0:
                scored.total_score = max(
                    0, scored.total_score - penalty,
                )

            min_score = component.scoring.min_score
            if scored.total_score >= min_score:
                scored_matches.append(scored)
                diag['passed_threshold'].append({
                    'concept': concept.qname,
                    'score': scored.total_score,
                })
            else:
                below_count += 1
                diag['below_threshold'].append({
                    'concept': concept.qname,
                    'score': scored.total_score,
                    'min_required': min_score,
                })

        return scored_matches, rej_count, below_count

    def _score_concept(self, concept, component, ci):
        """Evaluate and score a single concept."""
        results = {}
        rules = component.matching_rules
        ctx = {'concept_index': ci}
        evaluations = [
            ('label', rules.label_rules, None),
            ('local_name', rules.local_name_rules, None),
            ('hierarchy', rules.hierarchy_rules, ctx),
            ('calculation', rules.calculation_rules, ctx),
            ('definition', rules.definition_rules, None),
        ]
        for name, rule_set, context in evaluations:
            if not rule_set:
                continue
            kwargs = {'concept': concept, 'rules': rule_set}
            if context:
                kwargs['context'] = context
            results[name] = self.evaluators[name].evaluate(
                **kwargs,
            )
        return self.score_aggregator.aggregate(
            concept_qname=concept.qname,
            evaluation_results=results,
            component=component,
            concept_balance_type=concept.balance_type,
        )

    def _handle_no_match(self, cid, n_cands, rej_count, diag, comp):
        """Handle case when no candidates pass threshold."""
        if rej_count == n_cands:
            diag['failure_reason'] = 'ALL_REJECTED'
            reason = f"All {n_cands} candidates rejected"
        else:
            diag['failure_reason'] = 'BELOW_THRESHOLD'
            reason = f"No candidates met min score ({comp.scoring.min_score})"
            for f in sorted(diag['below_threshold'], key=lambda x: x['score'], reverse=True)[:3]:
                self.logger.info(
                    f"  [NEAR MISS] {f['concept']}: score={f['score']:.2f} (needs {f['min_required']})"
                )
        self._match_diagnostics[cid] = diag
        return MatchResult.no_match(cid, reason)

    def _select_best(self, cid, scored_matches, ci, diag, strategy=None):
        """Select best match from scored candidates."""
        scored_matches.sort(key=lambda m: m.total_score, reverse=True)
        top = scored_matches[0].total_score
        ties = [m for m in scored_matches if m.total_score == top]
        if len(ties) > 1:
            best, _ = self.tiebreaker.resolve(
                matches=ties, strategy=strategy, concept_index=ci,
            )
            alts = [m for m in ties if m.concept != best.concept]
        else:
            best = scored_matches[0]
            alts = scored_matches[1:5]
        diag['failure_reason'] = None
        diag['matched_concept'] = best.concept
        diag['matched_score'] = best.total_score
        self._match_diagnostics[cid] = diag
        self.logger.info(
            f"  [MATCHED] {cid} -> {best.concept} "
            f"(score={best.total_score:.2f})"
        )
        return MatchResult.from_scored_match(
            component_id=cid, match=best, alternatives=alts,
        )

    def _is_exact_name_match(self, concept, component):
        """Check if concept is named in an EXACT rule."""
        if not component.matching_rules.local_name_rules:
            return False
        name_lower = concept.local_name.lower()
        for rule in component.matching_rules.local_name_rules:
            if rule.match_type.value != 'exact':
                continue
            for pattern in rule.patterns:
                if name_lower == pattern.lower():
                    return True
        return False

    def _check_rejection(self, concept, component):
        """Check if concept should be rejected."""
        for cond in component.scoring.reject_if:
            if matches_rejection(concept, cond):
                return cond.condition
        return None

    def _qualifier_penalty(self, concept) -> int:
        """Score penalty for negating qualifiers."""
        local_lower = concept.local_name.lower()
        for q in _NEGATING_QUALIFIERS:
            if q in local_lower:
                return _QUALIFIER_PENALTY
        return 0

    def get_match_diagnostics(self) -> dict[str, dict]:
        """Get diagnostics for all match attempts."""
        return self._match_diagnostics.copy()

    def print_diagnostics_summary(self) -> None:
        """Print human-readable match diagnostics."""
        print_diagnostics_summary(self._match_diagnostics)


__all__ = ['AtomicMatcher']
