# Path: mat_acc/ratio_check/dim_awareness/__init__.py
"""
Dimensional Awareness

Extracts and applies dimensional metadata from the XBRL
definition linkbase. Tags concepts serving dimensional roles
(axes, members, domains, hypercubes) so they are excluded
from primary financial statement matching.

Integration point: after concept building, before matching.
"""

from .dim_extractor import DimensionIndex, extract_dimensions
from .dim_tagger import tag_concepts


__all__ = [
    'DimensionIndex',
    'extract_dimensions',
    'tag_concepts',
]
