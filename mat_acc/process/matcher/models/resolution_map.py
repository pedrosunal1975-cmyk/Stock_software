# Path: mat_acc/process/matcher/models/resolution_map.py
"""
Resolution Map Models

The resolution map is the primary output of the matching engine.
It maps component IDs to matched concepts for a specific filing.
"""

from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from .match_result import MatchResult, Confidence, MatchStatus


@dataclass
class ResolvedComponent:
    """
    A successfully resolved component with its matched concept.

    Attributes:
        component_id: The component identifier
        concept: The matched XBRL concept QName
        confidence: Confidence level of the match
        score: Total match score
        is_composite: Whether this is a calculated component
    """
    component_id: str
    concept: str
    confidence: Confidence
    score: int
    is_composite: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'component_id': self.component_id,
            'concept': self.concept,
            'confidence': self.confidence.value,
            'score': self.score,
            'is_composite': self.is_composite,
        }


@dataclass
class CompositeResolution:
    """
    Resolution for a composite (calculated) component.

    Attributes:
        component_id: The composite component ID
        resolved: Whether all child components are available
        formula: The formula to calculate this component
        component_concepts: Mapping of child component IDs to concepts
        missing_components: Component IDs that couldn't be resolved
    """
    component_id: str
    resolved: bool
    formula: Optional[str] = None
    component_concepts: dict[str, str] = field(default_factory=dict)
    missing_components: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'component_id': self.component_id,
            'resolved': self.resolved,
            'formula': self.formula,
            'component_concepts': self.component_concepts,
            'missing_components': self.missing_components,
        }


@dataclass
class ResolutionMap:
    """
    Complete mapping of components to concepts for a filing.

    This is the primary output of the matching engine. It contains
    all resolved components (atomic and composite) and can be used
    to extract values and calculate ratios.

    Attributes:
        filing_id: Identifier for the filing
        resolved_at: When the resolution was performed
        engine_version: Version of the matching engine
        matches: All match results (including failures)
        resolved: Successfully resolved components
        composites: Composite component resolutions
        unresolved: Components that couldn't be resolved
    """
    filing_id: str
    resolved_at: datetime = field(default_factory=datetime.utcnow)
    engine_version: str = "1.0.0"
    matches: dict[str, MatchResult] = field(default_factory=dict)
    resolved: dict[str, ResolvedComponent] = field(default_factory=dict)
    composites: dict[str, CompositeResolution] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)

    def add_match(self, component_id: str, result: MatchResult) -> None:
        """
        Add a match result to the resolution map.

        Args:
            component_id: Component that was matched
            result: The match result
        """
        self.matches[component_id] = result

        if result.is_matched:
            self.resolved[component_id] = ResolvedComponent(
                component_id=component_id,
                concept=result.matched_concept,
                confidence=result.confidence,
                score=result.total_score,
                is_composite=False,
            )
        else:
            if component_id not in self.unresolved:
                self.unresolved.append(component_id)

    def add_composite(
        self,
        component_id: str,
        resolution: CompositeResolution
    ) -> None:
        """
        Add a composite component resolution.

        Args:
            component_id: Composite component ID
            resolution: The composite resolution
        """
        self.composites[component_id] = resolution

        if resolution.resolved:
            # Add to resolved with a marker for composite
            self.resolved[component_id] = ResolvedComponent(
                component_id=component_id,
                concept=f"COMPOSITE:{resolution.formula}",
                confidence=Confidence.HIGH,
                score=100,  # Composites have perfect score if resolved
                is_composite=True,
            )
        else:
            if component_id not in self.unresolved:
                self.unresolved.append(component_id)

    def get_concept(self, component_id: str) -> Optional[str]:
        """
        Get the matched concept for a component.

        Args:
            component_id: Component to look up

        Returns:
            Matched concept QName or None
        """
        if component_id in self.resolved:
            resolved = self.resolved[component_id]
            if not resolved.is_composite:
                return resolved.concept
        return None

    def get_composite(self, component_id: str) -> Optional[CompositeResolution]:
        """
        Get composite resolution for a component.

        Args:
            component_id: Component to look up

        Returns:
            CompositeResolution or None
        """
        return self.composites.get(component_id)

    def is_resolved(self, component_id: str) -> bool:
        """Check if a component is resolved."""
        return component_id in self.resolved

    def get_confidence(self, component_id: str) -> Confidence:
        """Get confidence level for a component."""
        if component_id in self.resolved:
            return self.resolved[component_id].confidence
        return Confidence.NONE

    @property
    def resolution_rate(self) -> float:
        """Calculate percentage of components resolved."""
        total = len(self.matches) + len(self.composites)
        if total == 0:
            return 0.0
        resolved_count = len(self.resolved)
        return (resolved_count / total) * 100

    @property
    def high_confidence_rate(self) -> float:
        """Calculate percentage with high confidence."""
        if len(self.resolved) == 0:
            return 0.0
        high_count = sum(
            1 for r in self.resolved.values()
            if r.confidence == Confidence.HIGH
        )
        return (high_count / len(self.resolved)) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'filing_id': self.filing_id,
            'resolved_at': self.resolved_at.isoformat(),
            'engine_version': self.engine_version,
            'summary': {
                'total_components': len(self.matches) + len(self.composites),
                'resolved': len(self.resolved),
                'unresolved': len(self.unresolved),
                'resolution_rate': self.resolution_rate,
                'high_confidence_rate': self.high_confidence_rate,
            },
            'matches': {
                k: v.to_dict() for k, v in self.matches.items()
            },
            'resolved': {
                k: v.to_dict() for k, v in self.resolved.items()
            },
            'composites': {
                k: v.to_dict() for k, v in self.composites.items()
            },
            'unresolved': self.unresolved,
        }

    def to_simple_map(self) -> dict[str, str]:
        """
        Get simple component_id -> concept mapping.

        This is the primary output for value extraction.
        Composites are not included (they need special handling).

        Returns:
            Dictionary mapping component IDs to concept QNames
        """
        return {
            component_id: resolved.concept
            for component_id, resolved in self.resolved.items()
            if not resolved.is_composite
        }


__all__ = [
    'ResolvedComponent',
    'CompositeResolution',
    'ResolutionMap',
]
