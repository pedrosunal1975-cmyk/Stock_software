# Path: mat_acc/ratio_check/match_verify/confidence_gate.py
"""
Confidence Gate

Assesses match quality BEFORE value population to prevent wrong
values from silently corrupting ratios.

Two checks:
1. Confidence floor: LOW confidence matches are always uncertain
2. Name specificity: MEDIUM confidence matches whose concept name
   has excessive qualifiers beyond the expected stem are uncertain

HIGH confidence and composite matches always pass.
Uncertain matches are blocked from value loading - the system
reports 'uncertain' rather than risk a wrong value.
"""

from core.logger.ipo_logging import get_process_logger

logger = get_process_logger('confidence_gate')


def assess_quality(comp_id, confidence_value, is_composite, local_name):
    """Assess match quality: 'confident' or 'uncertain'.

    Args:
        comp_id: Component identifier (e.g. 'interest_expense')
        confidence_value: Confidence enum value string ('high', 'medium', 'low')
        is_composite: Whether this is a composite resolution
        local_name: Matched concept's local name (or None)

    Returns:
        'confident' or 'uncertain'
    """
    if is_composite:
        return 'confident'
    if confidence_value == 'low':
        logger.info(
            f"  [UNCERTAIN] {comp_id}: LOW confidence"
        )
        return 'uncertain'
    if confidence_value == 'medium' and local_name:
        if _is_name_excessive(comp_id, local_name):
            logger.info(
                f"  [UNCERTAIN] {comp_id}: overly specific "
                f"'{local_name}'"
            )
            return 'uncertain'
    return 'confident'


def _is_name_excessive(comp_id, local_name):
    """Check if concept name has excessive qualifiers.

    Derives an expected stem from the component_id
    (e.g. interest_expense -> InterestExpense) and checks
    if the concept name contains significantly more than that.

    Threshold: excess characters > max(stem_length, 15).
    This means the concept must be roughly 2x the stem length
    to trigger, with a floor of 15 extra chars for short stems.
    """
    stem = ''.join(w.capitalize() for w in comp_id.split('_'))
    idx = local_name.lower().find(stem.lower())
    if idx == -1:
        return False
    excess = len(local_name) - len(stem)
    return excess > max(len(stem), 15)


__all__ = ['assess_quality']
