# Path: mat_acc/process/matcher/engine/candidate_filter.py
"""
Candidate Filter

Standalone functions for candidate concept selection, type
validation, rejection pattern matching, and diagnostic logging.
Used by the AtomicMatcher during Phase 1 matching.
"""

from typing import Optional

from ..models.component_definition import (
    ComponentDefinition, RejectionCondition, MatchType,
)
from ..models.concept_metadata import ConceptMetadata, ConceptIndex


UNIVERSAL_EXCLUDE = [
    'textblock', 'schedule',
    'explanatory', 'disclosure', 'policy',
    'axis', 'member', 'domain',
]


def get_candidates(
    component: ComponentDefinition,
    concept_index: ConceptIndex,
    logger,
) -> list[ConceptMetadata]:
    """Get candidate concepts for a component."""
    label_patterns = []
    for rule in component.matching_rules.label_rules:
        label_patterns.extend(rule.patterns)

    local_name_patterns = []
    if component.matching_rules.local_name_rules:
        for rule in component.matching_rules.local_name_rules:
            local_name_patterns.extend(rule.patterns)

    balance_type = None
    period_type = None
    bt = component.characteristics.balance_type
    if bt and bt.value != 'none':
        balance_type = bt.value
    if component.characteristics.period_type:
        period_type = component.characteristics.period_type.value

    candidate_qnames = concept_index.get_candidates(
        label_patterns=label_patterns,
        local_name_patterns=local_name_patterns,
        balance_type=balance_type,
        period_type=period_type,
        exclude_abstract=(
            not component.characteristics.is_abstract
        ),
        max_candidates=100,
    )

    # Force-include exact local_name rule matches
    candidate_set = set(candidate_qnames)
    initial_count = len(candidate_set)
    if component.matching_rules.local_name_rules:
        for rule in component.matching_rules.local_name_rules:
            if rule.match_type != MatchType.EXACT:
                continue
            for pattern in rule.patterns:
                ensure_exact_candidate(
                    pattern, concept_index,
                    candidate_set, logger,
                )
    added = len(candidate_set) - initial_count
    if added > 0:
        logger.info(
            f"  [FORCE-INCLUDE] Added {added} exact "
            f"local_name concepts for "
            f"{component.component_id}"
        )
    candidate_qnames = list(candidate_set)

    # Apply universal filters and type validation
    candidates = []
    for qname in candidate_qnames:
        concept = concept_index.get_concept(qname)
        if not concept:
            continue
        # Structural exclusion (definition linkbase arcroles)
        if concept.is_dimensional:
            continue
        # Name-based exclusion (fallback for missing linkbase)
        local_lower = concept.local_name.lower()
        if any(
            excl in local_lower
            for excl in UNIVERSAL_EXCLUDE
        ):
            continue
        if concept.prefix == 'root':
            continue
        if not is_type_compatible(concept, component):
            continue
        candidates.append(concept)
    return candidates


def ensure_exact_candidate(
    local_name_pattern: str,
    concept_index: ConceptIndex,
    candidate_set: set[str],
    logger,
) -> None:
    """Ensure exact-named concept is in candidate set."""
    pattern_lower = local_name_pattern.lower()
    found = False
    for concept in concept_index.get_all_concepts():
        if concept.local_name.lower() == pattern_lower:
            found = True
            if concept.qname not in candidate_set:
                candidate_set.add(concept.qname)
                logger.debug(
                    f"  [FORCED] '{concept.qname}' added "
                    f"(local_name={concept.local_name}, "
                    f"balance={concept.balance_type}, "
                    f"period={concept.period_type})"
                )
    if not found:
        logger.warning(
            f"  [NOT IN INDEX] No concept with "
            f"local_name='{local_name_pattern}'"
        )


def log_candidate_diagnostics(
    component_id: str,
    candidates: list[ConceptMetadata],
    concept_index: ConceptIndex,
    search_patterns: list[str],
    components: dict,
    logger,
) -> None:
    """Log diagnostic info about candidate selection."""
    if not candidates:
        return

    sample = [c.qname for c in candidates[:5]]
    logger.info(f"  [CANDIDATES SAMPLE] {sample}")

    expected_patterns = []
    component = components.get(component_id)
    if component and component.matching_rules.local_name_rules:
        for rule in component.matching_rules.local_name_rules:
            if rule.match_type == 'exact':
                expected_patterns.extend(rule.patterns[:3])

    candidate_qnames = {c.qname for c in candidates}
    all_concepts = concept_index.get_all_concepts()

    for pattern in expected_patterns:
        matching = [
            c for c in all_concepts
            if pattern.lower() in c.local_name.lower()
        ]
        if not matching:
            continue

        in_candidates = [
            c for c in matching
            if c.qname in candidate_qnames
        ]
        if not in_candidates:
            best = matching[0]
            labels = (
                list(best.labels.values())[:2]
                if best.labels else ['(no labels)']
            )
            logger.warning(
                f"  [MISSING FROM CANDIDATES] "
                f"'{best.qname}' "
                f"(local_name: {best.local_name}, "
                f"labels: {labels})"
            )
        else:
            logger.info(
                f"  [EXPECTED FOUND] "
                f"'{in_candidates[0].qname}' "
                f"is in candidates"
            )


def matches_rejection(
    concept: ConceptMetadata,
    condition: RejectionCondition,
) -> bool:
    """
    Check if concept matches a rejection condition.

    Patterns: abstract=true, label~keyword, name~pattern.
    """
    pattern = condition.pattern

    if pattern == "abstract=true":
        return concept.is_abstract

    if pattern.startswith("label~"):
        keyword = pattern[6:]
        for label in concept.get_all_labels():
            if keyword.lower() in label.lower():
                return True

    if pattern.startswith("name~"):
        keyword = pattern[5:]
        if keyword.lower() in concept.local_name.lower():
            return True

    return False


def is_type_compatible(
    concept: ConceptMetadata,
    component: ComponentDefinition,
) -> bool:
    """Check concept data type against component expectation."""
    if not concept.data_type:
        return True
    expected = component.characteristics.data_type
    if not expected:
        return True
    concept_cat = infer_data_category(concept.data_type)
    if not concept_cat:
        return True
    return concept_cat == expected.value


def infer_data_category(unit_str: str) -> Optional[str]:
    """Map XBRL unit string to DataType category."""
    lower = unit_str.lower()
    if '/' in lower:
        return 'per_share'
    if 'iso4217' in lower:
        return 'monetary'
    if 'shares' in lower:
        return 'shares'
    if 'pure' in lower:
        return 'pure'
    return None


def print_diagnostics_summary(diagnostics: dict) -> None:
    """Print human-readable match diagnostics."""
    print("\n" + "=" * 70)
    print("  MATCHING ENGINE DIAGNOSTICS")
    print("=" * 70)
    for cid, diag in diagnostics.items():
        if diag.get('matched_concept'):
            status = "[OK]"
            detail = (
                f"-> {diag['matched_concept']} "
                f"(score={diag['matched_score']:.2f})"
            )
        else:
            status = "[--]"
            detail = _format_failure(diag)
        print(f"  {status} {cid:30s} {detail}")
    print("=" * 70 + "\n")


def _format_failure(diag: dict) -> str:
    """Format failure reason for diagnostics."""
    reason = diag.get('failure_reason', 'UNKNOWN')
    if reason == 'NO_CANDIDATES':
        return (
            f"No candidates. "
            f"Patterns: {diag['search_patterns']}"
        )
    if reason == 'ALL_REJECTED':
        return (
            f"All {len(diag['rejections'])} "
            f"candidates rejected"
        )
    if reason == 'BELOW_THRESHOLD' and diag['below_threshold']:
        best = max(
            diag['below_threshold'],
            key=lambda x: x['score'],
        )
        return (
            f"Best score={best['score']:.2f} "
            f"(needs {best['min_required']})"
        )
    return reason


__all__ = [
    'get_candidates',
    'ensure_exact_candidate',
    'log_candidate_diagnostics',
    'matches_rejection',
    'is_type_compatible',
    'infer_data_category',
    'print_diagnostics_summary',
    'UNIVERSAL_EXCLUDE',
]
