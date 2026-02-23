# Path: mat_acc/ratio_check/dim_awareness/dim_extractor.py
"""
Dimension Extractor

Extracts dimensional structure from XBRL definition linkbase.
Identifies concepts serving dimensional roles (axes, members,
domains, hypercubes) so they can be excluded from primary
financial statement matching.
"""

from dataclasses import dataclass, field
from typing import Optional

from core.logger.ipo_logging import get_process_logger
from loaders.xbrl_reader import DefinitionNetwork, DefinitionArc


logger = get_process_logger('dim_extractor')


# Standard XBRL dimensional arcroles
_ARCROLE_ALL = (
    'http://xbrl.org/int/dim/arcrole/all'
)
_ARCROLE_NOT_ALL = (
    'http://xbrl.org/int/dim/arcrole/notAll'
)
_ARCROLE_HYPERCUBE_DIM = (
    'http://xbrl.org/int/dim/arcrole/hypercube-dimension'
)
_ARCROLE_DIM_DOMAIN = (
    'http://xbrl.org/int/dim/arcrole/dimension-domain'
)
_ARCROLE_DOMAIN_MEMBER = (
    'http://xbrl.org/int/dim/arcrole/domain-member'
)
_ARCROLE_DIM_DEFAULT = (
    'http://xbrl.org/int/dim/arcrole/dimension-default'
)


@dataclass
class DimensionIndex:
    """Index of dimensional concepts from definition linkbase."""
    hypercubes: set[str] = field(default_factory=set)
    axes: set[str] = field(default_factory=set)
    domains: set[str] = field(default_factory=set)
    members: set[str] = field(default_factory=set)

    def is_dimensional(self, qname: str) -> bool:
        """Check if concept serves a dimensional role."""
        return (
            qname in self.hypercubes
            or qname in self.axes
            or qname in self.domains
            or qname in self.members
        )

    def get_role(self, qname: str) -> Optional[str]:
        """Get dimensional role for a concept."""
        if qname in self.hypercubes:
            return 'hypercube'
        if qname in self.axes:
            return 'axis'
        if qname in self.domains:
            return 'domain'
        if qname in self.members:
            return 'member'
        return None

    def total_count(self) -> int:
        """Total unique dimensional concepts."""
        all_concepts = (
            self.hypercubes | self.axes
            | self.domains | self.members
        )
        return len(all_concepts)


def extract_dimensions(
    def_networks: list[DefinitionNetwork],
) -> DimensionIndex:
    """
    Build DimensionIndex from definition linkbase networks.

    Classifies concepts by arcrole relationships:
    - hypercube-dimension parent -> hypercube
    - hypercube-dimension child -> axis
    - dimension-domain child -> domain
    - domain-member child -> member
    """
    index = DimensionIndex()

    for network in def_networks:
        for arc in network.arcs:
            _classify_arc(arc, index)

    logger.info(
        f"Dimension index: {len(index.hypercubes)} hypercubes, "
        f"{len(index.axes)} axes, {len(index.domains)} domains, "
        f"{len(index.members)} members"
    )
    return index


def _classify_arc(
    arc: DefinitionArc, index: DimensionIndex,
) -> None:
    """Classify a definition arc into dimensional roles."""
    role = arc.arcrole or ''

    if role == _ARCROLE_HYPERCUBE_DIM:
        index.hypercubes.add(arc.parent_concept)
        index.axes.add(arc.child_concept)

    elif role == _ARCROLE_DIM_DOMAIN:
        index.axes.add(arc.parent_concept)
        index.domains.add(arc.child_concept)

    elif role == _ARCROLE_DOMAIN_MEMBER:
        index.domains.add(arc.parent_concept)
        index.members.add(arc.child_concept)

    elif role in (_ARCROLE_ALL, _ARCROLE_NOT_ALL):
        index.hypercubes.add(arc.child_concept)

    elif role == _ARCROLE_DIM_DEFAULT:
        index.axes.add(arc.parent_concept)


__all__ = ['DimensionIndex', 'extract_dimensions']
