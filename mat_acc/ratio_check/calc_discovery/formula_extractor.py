# Path: mat_acc/ratio_check/calc_discovery/formula_extractor.py
"""
Formula Extractor

Extracts company-declared financial formulas from the XBRL
calculation linkbase. Transforms raw calculation arcs into
structured formula objects.

Each DeclaredFormula represents a parent concept and its
children with arithmetic weights (+1 = add, -1 = subtract).

Example from linkbase:
    GrossProfit = Revenue(+1) + CostOfRevenue(-1)
    means: GrossProfit = Revenue - CostOfRevenue
"""

from dataclasses import dataclass, field

from core.logger.ipo_logging import get_process_logger
from loaders.xbrl_reader import CalculationNetwork, CalculationArc


logger = get_process_logger('formula_extractor')


@dataclass
class FormulaChild:
    """A child term in a declared formula."""
    concept: str          # Full QName: "us-gaap:Revenues"
    local_name: str       # "Revenues"
    weight: float         # +1.0 (add) or -1.0 (subtract)
    order: float = 0.0


@dataclass
class DeclaredFormula:
    """A company-declared calculation relationship."""
    parent_concept: str              # Full QName
    parent_local_name: str           # Local name only
    children: list[FormulaChild] = field(default_factory=list)
    role: str = ''                   # Statement role URI

    def formula_display(self) -> str:
        """Human-readable formula string."""
        parts = []
        for child in sorted(self.children, key=lambda c: c.order):
            sign = '+' if child.weight > 0 else '-'
            parts.append(f"{sign}{child.local_name}")
        return f"{self.parent_local_name} = {' '.join(parts)}"


def extract_formulas(
    calc_networks: list[CalculationNetwork],
) -> list[DeclaredFormula]:
    """
    Extract structured formulas from calculation networks.

    Groups arcs by parent concept, deduplicates across roles,
    and builds DeclaredFormula objects.

    Args:
        calc_networks: CalculationNetwork list from XBRLReader

    Returns:
        List of DeclaredFormula objects
    """
    formulas = []
    formula_by_key: dict[str, DeclaredFormula] = {}

    for network in calc_networks:
        parent_groups = _group_by_parent(network.arcs)

        for parent_concept, arcs in parent_groups.items():
            parent_local = _extract_local_name(parent_concept)
            key = parent_local.lower()

            children = _build_children(arcs)
            if not children:
                continue

            if key in formula_by_key:
                _merge_children(formula_by_key[key], children)
            else:
                formula = DeclaredFormula(
                    parent_concept=parent_concept,
                    parent_local_name=parent_local,
                    children=children,
                    role=network.role,
                )
                formula_by_key[key] = formula
                formulas.append(formula)

    logger.info(
        f"Extracted {len(formulas)} declared formulas "
        f"from {len(calc_networks)} networks"
    )
    return formulas


def _build_children(
    arcs: list[CalculationArc],
) -> list[FormulaChild]:
    """Build FormulaChild list from arcs, sorted by order."""
    children = []
    for arc in sorted(arcs, key=lambda a: a.order):
        # Only handle standard weights (+1 or -1)
        if abs(arc.weight) != 1.0:
            continue
        child_local = _extract_local_name(arc.child_concept)
        children.append(FormulaChild(
            concept=arc.child_concept,
            local_name=child_local,
            weight=arc.weight,
            order=arc.order,
        ))
    return children


def _merge_children(
    formula: DeclaredFormula,
    new_children: list[FormulaChild],
) -> None:
    """Merge new children into existing formula, skip duplicates."""
    known = {c.local_name.lower() for c in formula.children}
    for child in new_children:
        if child.local_name.lower() not in known:
            formula.children.append(child)
            known.add(child.local_name.lower())


def _group_by_parent(
    arcs: list[CalculationArc],
) -> dict[str, list[CalculationArc]]:
    """Group calculation arcs by parent concept."""
    groups: dict[str, list[CalculationArc]] = {}
    for arc in arcs:
        parent = arc.parent_concept
        if parent not in groups:
            groups[parent] = []
        groups[parent].append(arc)
    return groups


def _extract_local_name(concept: str) -> str:
    """Extract local name from QName."""
    if ':' in concept:
        return concept.split(':', 1)[1]
    if '_' in concept:
        return concept.split('_', 1)[1]
    return concept


__all__ = [
    'FormulaChild',
    'DeclaredFormula',
    'extract_formulas',
]
