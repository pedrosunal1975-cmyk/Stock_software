# Path: mat_acc/process/matcher/engine/coordinator.py
"""
Matching Coordinator

The main orchestrator for dynamic concept matching.
This is the primary entry point for the matching engine.

Delegates atomic matching to AtomicMatcher, composite
resolution handled internally.
"""

from pathlib import Path
from typing import Optional

from core.logger.ipo_logging import get_process_logger

from .component_loader import ComponentLoader
from .atomic_matcher import AtomicMatcher
from ..models.component_definition import ComponentDefinition
from ..models.concept_metadata import ConceptMetadata, ConceptIndex
from ..models.match_result import MatchResult
from ..models.resolution_map import (
    ResolutionMap, CompositeResolution,
)
from ..evaluators import (
    LabelEvaluator, HierarchyEvaluator,
    CalculationEvaluator, DefinitionEvaluator,
    LocalNameEvaluator,
)
from ..scoring import ScoreAggregator, Tiebreaker


class MatchingCoordinator:
    """
    Main orchestrator for dynamic concept matching.

    Phase 1: Atomic matching (all components with rules)
    Phase 2: Formula computation (unresolved composites)
    """

    def __init__(
        self,
        dictionary_path: Optional[Path] = None,
        diagnostics: bool = True,
        market: Optional[str] = None,
    ):
        """Initialize matching coordinator."""
        self.logger = get_process_logger(
            'matcher.coordinator',
        )
        self.diagnostics = diagnostics

        # Load component definitions (market-aware)
        self.component_loader = ComponentLoader(
            dictionary_path,
        )
        if market:
            self.components = (
                self.component_loader.load_for_market(market)
            )
        else:
            self.components = self.component_loader.load_all()

        self.logger.info(
            f"Loaded {len(self.components)} "
            f"component definitions"
        )

        # Initialize evaluators
        evaluators = {
            'label': LabelEvaluator(),
            'local_name': LocalNameEvaluator(),
            'hierarchy': HierarchyEvaluator(),
            'calculation': CalculationEvaluator(),
            'definition': DefinitionEvaluator(),
        }

        # Create atomic matcher with shared components
        self._matcher = AtomicMatcher(
            evaluators=evaluators,
            score_aggregator=ScoreAggregator(),
            tiebreaker=Tiebreaker(),
            components=self.components,
            diagnostics=diagnostics,
        )

    def build_index(
        self, concepts: list[ConceptMetadata],
    ) -> ConceptIndex:
        """Build a concept index from a list of concepts."""
        index = ConceptIndex()
        for concept in concepts:
            index.add_concept(concept)
        self.logger.info(
            f"Built index with {len(index)} concepts",
        )
        return index

    def resolve_all(
        self, concept_index: ConceptIndex,
        filing_id: str = "unknown",
        required_components: Optional[list[str]] = None,
    ) -> ResolutionMap:
        """Resolve all components for a filing."""
        resolution = ResolutionMap(filing_id=filing_id)

        if required_components:
            to_resolve = {
                cid: self.components[cid]
                for cid in required_components
                if cid in self.components
            }
        else:
            to_resolve = self.components

        self.logger.info(
            f"Resolving {len(to_resolve)} components "
            f"for {filing_id}"
        )

        # Phase 1: Atomic matching for components with rules
        for cid, comp in to_resolve.items():
            has_rules = (
                comp.matching_rules.label_rules
                or comp.matching_rules.local_name_rules
            )
            if not has_rules:
                continue
            result = self._matcher.match(
                comp, concept_index,
            )
            resolution.add_match(cid, result)

        # Phase 2: Formula fallback for unresolved
        for cid, comp in to_resolve.items():
            if not comp.composition.formula:
                continue
            if resolution.is_resolved(cid):
                continue
            composite = self._resolve_composite(
                comp, resolution,
            )
            resolution.add_composite(cid, composite)

        self.logger.info(
            f"Resolution complete: "
            f"{len(resolution.resolved)}/"
            f"{len(to_resolve)} resolved, "
            f"{resolution.high_confidence_rate:.1f}% "
            f"high confidence"
        )
        return resolution

    def resolve_component(
        self, component_id: str,
        concept_index: ConceptIndex,
    ) -> MatchResult:
        """Resolve a single component."""
        if component_id not in self.components:
            return MatchResult.no_match(
                component_id,
                f"Unknown component: {component_id}",
            )

        component = self.components[component_id]
        if component.is_composite:
            self.logger.warning(
                f"resolve_component called for composite "
                f"{component_id}; use resolve_all"
            )
            return MatchResult.no_match(
                component_id,
                "Composite needs full resolution",
            )

        return self._matcher.match(
            component, concept_index,
        )

    def _resolve_composite(
        self, component: ComponentDefinition,
        resolution: ResolutionMap,
    ) -> CompositeResolution:
        """Resolve a composite via formula computation."""
        cid = component.component_id
        composition = component.composition

        missing = []
        component_concepts = {}
        for child_id in composition.components:
            if resolution.is_resolved(child_id):
                concept = resolution.get_concept(child_id)
                if concept:
                    component_concepts[child_id] = concept
            else:
                missing.append(child_id)

        if not missing:
            return CompositeResolution(
                component_id=cid,
                resolved=True,
                formula=composition.formula,
                component_concepts=component_concepts,
            )

        # Try alternatives
        for alt in composition.alternatives:
            alt_missing = []
            alt_concepts = {}
            for child_id in alt.components:
                if resolution.is_resolved(child_id):
                    concept = resolution.get_concept(child_id)
                    if concept:
                        alt_concepts[child_id] = concept
                else:
                    alt_missing.append(child_id)

            if not alt_missing:
                return CompositeResolution(
                    component_id=cid,
                    resolved=True,
                    formula=alt.formula,
                    component_concepts=alt_concepts,
                )

        return CompositeResolution(
            component_id=cid,
            resolved=False,
            formula=composition.formula,
            component_concepts=component_concepts,
            missing_components=missing,
        )

    def get_component(
        self, component_id: str,
    ) -> Optional[ComponentDefinition]:
        """Get a component definition by ID."""
        return self.components.get(component_id)

    def get_all_components(
        self,
    ) -> dict[str, ComponentDefinition]:
        """Get all loaded component definitions."""
        return self.components.copy()

    def reload_components(self) -> None:
        """Reload component definitions from disk."""
        self.component_loader.clear_cache()
        self.components = self.component_loader.load_all()
        self._matcher.components = self.components
        self.logger.info(
            f"Reloaded {len(self.components)} components",
        )

    def get_match_diagnostics(self) -> dict[str, dict]:
        """Get diagnostics for all match attempts."""
        return self._matcher.get_match_diagnostics()

    def print_diagnostics_summary(self) -> None:
        """Print human-readable match diagnostics."""
        self._matcher.print_diagnostics_summary()


__all__ = ['MatchingCoordinator']
