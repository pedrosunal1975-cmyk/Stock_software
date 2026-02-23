# Path: mat_acc/ratio_check/calc_discovery/formula_mapper.py
"""
Formula Mapper

Maps company-declared formulas to mat_acc components.
Two modes: dynamic fallback for matched components without
YAML formulas, and dynamic composites for unmatched components
when linkbase reveals a formula with all children matched.
"""

from typing import Optional, Dict, List

from core.logger.ipo_logging import get_process_logger
from process.matcher.models.concept_metadata import ConceptIndex

from ..ratio_models import ComponentMatch
from .formula_extractor import DeclaredFormula, FormulaChild


logger = get_process_logger('formula_mapper')


def enhance_matches(
    formulas: list[DeclaredFormula],
    matches: List[ComponentMatch],
    concept_index: ConceptIndex,
) -> int:
    """
    Use company-declared formulas to enhance match results.

    For each formula, finds the corresponding mat_acc component
    (via matched concept or name heuristic), maps children to
    other components, and enhances the match when possible.

    Args:
        formulas: Extracted DeclaredFormula list
        matches: Component matches (modified in-place)
        concept_index: ConceptIndex for metadata lookup

    Returns:
        Number of components enhanced
    """
    concept_to_comp = _build_concept_lookup(matches)
    local_to_comp = _build_localname_lookup(
        matches, concept_index,
    )
    match_lookup = {m.component_name: m for m in matches}
    enhanced = 0

    for formula in formulas:
        comp_id = _resolve_formula_parent(
            formula, concept_to_comp, local_to_comp,
            match_lookup,
        )
        if not comp_id:
            continue

        match = match_lookup.get(comp_id)
        if not match:
            continue

        result = _try_enhance(
            match, formula, concept_to_comp, local_to_comp,
        )
        if result:
            enhanced += 1

    if enhanced:
        logger.info(
            f"Calc discovery enhanced {enhanced} components"
        )
    return enhanced


def _resolve_formula_parent(
    formula: DeclaredFormula,
    concept_to_comp: Dict[str, str],
    local_to_comp: Dict[str, str],
    match_lookup: Dict[str, ComponentMatch],
) -> Optional[str]:
    """Find which component a formula's parent maps to."""
    # Try exact concept match first
    comp = _find_comp_for_concept(
        formula.parent_concept,
        concept_to_comp, local_to_comp,
    )
    if comp:
        return comp

    # For unmatched components, try name heuristic
    return _find_unmatched_by_name(
        formula.parent_local_name, match_lookup,
    )


def _try_enhance(
    match: ComponentMatch,
    formula: DeclaredFormula,
    concept_to_comp: Dict[str, str],
    local_to_comp: Dict[str, str],
) -> bool:
    """
    Try to enhance a single component match using a formula.

    Returns True if the match was enhanced.
    """
    # Map all children to component IDs
    child_map = _map_children(
        formula.children, concept_to_comp, local_to_comp,
    )
    if not child_map:
        return False

    # Build formula string
    formula_str = _build_formula_string(
        formula.children, child_map,
    )
    if not formula_str:
        return False

    # Mode 1: Dynamic fallback for matched atomic components
    if match.matched and not _is_composite(match):
        if not match.fallback_formula:
            match.fallback_formula = formula_str
            logger.info(
                f"[CALC DISCOVERY] {match.component_name}: "
                f"dynamic fallback = {formula_str}"
            )
            return True
        # Already has fallback - log validation
        _log_validation(match, formula_str)
        return False

    # Mode 2: Dynamic composite for unmatched components
    if not match.matched:
        match.matched = True
        match.matched_concept = f"COMPOSITE:{formula_str}"
        match.label = formula_str
        match.confidence = 0.0
        logger.info(
            f"[CALC DISCOVERY] {match.component_name}: "
            f"new composite = {formula_str}"
        )
        return True

    return False


def _map_children(
    children: list[FormulaChild],
    concept_to_comp: Dict[str, str],
    local_to_comp: Dict[str, str],
) -> Dict[str, str]:
    """Map formula children to component IDs.

    Returns mapping only if ALL children map successfully.
    """
    child_map: Dict[str, str] = {}
    for child in children:
        comp = _find_comp_for_concept(
            child.concept, concept_to_comp, local_to_comp,
        )
        if not comp:
            return {}
        child_map[child.concept] = comp
    return child_map


def _build_formula_string(
    children: list[FormulaChild],
    child_map: Dict[str, str],
) -> Optional[str]:
    """Build mat_acc formula string from mapped children.

    Converts linkbase: Revenue(+1) + CostOfRevenue(-1)
    To formula: "revenue - cost_of_goods_sold"
    """
    parts: list[str] = []
    for child in sorted(children, key=lambda c: c.order):
        comp_id = child_map.get(child.concept)
        if not comp_id:
            return None
        if not parts:
            if child.weight < 0:
                parts.append(f"-{comp_id}")
            else:
                parts.append(comp_id)
        else:
            op = '+' if child.weight > 0 else '-'
            parts.append(f"{op} {comp_id}")
    if not parts:
        return None
    return ' '.join(parts)


def _find_comp_for_concept(
    concept: str,
    concept_lookup: Dict[str, str],
    local_lookup: Dict[str, str],
) -> Optional[str]:
    """Find component ID for a concept via exact or local name."""
    if concept in concept_lookup:
        return concept_lookup[concept]
    local = concept.split(':')[-1] if ':' in concept else concept
    key = local.lower()
    if key in local_lookup:
        return local_lookup[key]
    return None


def _find_unmatched_by_name(
    parent_local_name: str,
    match_lookup: Dict[str, ComponentMatch],
) -> Optional[str]:
    """Find unmatched component by name heuristic.

    Normalizes both component ID and formula parent to lowercase
    without separators, then checks startswith both directions.
    Also strips 'total' prefix from component IDs since taxonomy
    concepts often omit it (Assets vs total_assets).
    """
    norm_parent = parent_local_name.lower()

    for comp_id, match in match_lookup.items():
        if match.matched:
            continue
        norm_comp = comp_id.replace('_', '')
        variants = [norm_comp]
        if norm_comp.startswith('total'):
            variants.append(norm_comp[5:])

        for variant in variants:
            if not variant:
                continue
            if (norm_parent.startswith(variant)
                    or variant.startswith(norm_parent)):
                return comp_id
    return None


def _is_composite(match: ComponentMatch) -> bool:
    """Check if a match is already a composite."""
    if not match.matched_concept:
        return False
    return match.matched_concept.startswith('COMPOSITE:')


def _log_validation(
    match: ComponentMatch, linkbase_formula: str,
) -> None:
    """Log whether YAML fallback matches linkbase formula."""
    yaml_fb = match.fallback_formula or ''
    if yaml_fb == linkbase_formula:
        logger.debug(
            f"[CALC VALIDATED] {match.component_name}: "
            f"YAML matches linkbase ({linkbase_formula})"
        )
    else:
        logger.debug(
            f"[CALC DIFFERS] {match.component_name}: "
            f"YAML='{yaml_fb}' vs linkbase='{linkbase_formula}'"
        )


def _build_concept_lookup(
    matches: List[ComponentMatch],
) -> Dict[str, str]:
    """Build concept QName -> component_id reverse lookup."""
    lookup: Dict[str, str] = {}
    for m in matches:
        if m.matched and m.matched_concept:
            if not _is_composite(m):
                lookup[m.matched_concept] = m.component_name
    return lookup


def _build_localname_lookup(
    matches: List[ComponentMatch],
    concept_index: ConceptIndex,
) -> Dict[str, str]:
    """Build local_name (lowercase) -> component_id lookup."""
    lookup: Dict[str, str] = {}
    for m in matches:
        if not m.matched or not m.matched_concept:
            continue
        if _is_composite(m):
            continue
        concept = concept_index.get_concept(m.matched_concept)
        if concept and concept.local_name:
            key = concept.local_name.lower()
            lookup[key] = m.component_name
    return lookup


__all__ = ['enhance_matches']
