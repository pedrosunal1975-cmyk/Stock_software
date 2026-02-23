# Path: mat_acc/ratio_check/dim_awareness/dim_tagger.py
"""
Dimension Tagger

Tags concepts in ConceptIndex with dimensional metadata from
the definition linkbase. Tagged concepts are excluded from
primary matching by the candidate filter.

Complements the name-based UNIVERSAL_EXCLUDE (axis, member,
domain substrings) with structural certainty from arcroles.
"""

from core.logger.ipo_logging import get_process_logger
from process.matcher.models.concept_metadata import ConceptIndex

from .dim_extractor import DimensionIndex


logger = get_process_logger('dim_tagger')


def tag_concepts(
    dim_index: DimensionIndex,
    concept_index: ConceptIndex,
) -> int:
    """
    Tag dimensional concepts in a ConceptIndex.

    Sets is_dimensional=True on concepts identified as axes,
    members, domains, or hypercubes by the definition linkbase.

    Args:
        dim_index: DimensionIndex from definition linkbase
        concept_index: ConceptIndex to tag (modified in-place)

    Returns:
        Number of concepts tagged
    """
    tagged = 0

    for concept in concept_index.get_all_concepts():
        if dim_index.is_dimensional(concept.qname):
            concept.is_dimensional = True
            tagged += 1

    if tagged:
        logger.info(
            f"Tagged {tagged} concepts as dimensional"
        )
    return tagged


__all__ = ['tag_concepts']
