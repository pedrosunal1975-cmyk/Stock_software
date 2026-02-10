# Path: mat_acc/process/matcher/engine/coordinator.py
"""
Matching Coordinator

The main orchestrator for dynamic concept matching.
This is the primary entry point for the matching engine.
"""

import logging
from pathlib import Path
from typing import Optional, Any

# Import IPO logging (PROCESS layer for matching engine)
from core.logger.ipo_logging import get_process_logger

from .component_loader import ComponentLoader
from ..models.component_definition import ComponentDefinition, RejectionCondition
from ..models.concept_metadata import ConceptMetadata, ConceptIndex
from ..models.match_result import MatchResult, ScoredMatch, Confidence
from ..models.resolution_map import ResolutionMap, CompositeResolution
from ..evaluators import (
    LabelEvaluator,
    HierarchyEvaluator,
    CalculationEvaluator,
    DefinitionEvaluator,
    LocalNameEvaluator,
)
from ..scoring import ScoreAggregator, Tiebreaker


class MatchingCoordinator:
    """
    Main orchestrator for dynamic concept matching.

    The MatchingCoordinator:
    1. Loads component definitions from the dictionary
    2. Indexes filing concepts for fast lookup
    3. Evaluates matching rules for each component
    4. Scores and selects the best matches
    5. Produces a ResolutionMap for value extraction

    Example:
        coordinator = MatchingCoordinator()

        # Build concept index from filing data
        concept_index = coordinator.build_index(concepts)

        # Resolve all components
        resolution = coordinator.resolve_all(
            concept_index=concept_index,
            required_components=['current_assets', 'current_liabilities']
        )

        # Get matched concept
        concept = resolution.get_concept('current_assets')
        # Returns: "us-gaap:AssetsCurrent"
    """

    def __init__(self, dictionary_path: Optional[Path] = None, diagnostics: bool = True):
        """
        Initialize matching coordinator.

        Args:
            dictionary_path: Path to dictionary directory.
                           Defaults to mat_acc_files/dictionary/
            diagnostics: Enable detailed diagnostic logging (default True)
        """
        self.logger = get_process_logger('matcher.coordinator')
        self.diagnostics = diagnostics
        self._match_diagnostics: dict[str, dict] = {}  # Store diagnostics per component

        # Load component definitions
        self.component_loader = ComponentLoader(dictionary_path)
        self.components = self.component_loader.load_all()

        self.logger.info(
            f"Loaded {len(self.components)} component definitions"
        )

        # Initialize evaluators
        self.evaluators = {
            'label': LabelEvaluator(),
            'local_name': LocalNameEvaluator(),
            'hierarchy': HierarchyEvaluator(),
            'calculation': CalculationEvaluator(),
            'definition': DefinitionEvaluator(),
        }

        # Initialize scoring components
        self.score_aggregator = ScoreAggregator()
        self.tiebreaker = Tiebreaker()

    def build_index(
        self,
        concepts: list[ConceptMetadata]
    ) -> ConceptIndex:
        """
        Build a concept index from a list of concepts.

        Args:
            concepts: List of concept metadata objects

        Returns:
            ConceptIndex for fast lookup
        """
        index = ConceptIndex()

        for concept in concepts:
            index.add_concept(concept)

        self.logger.info(f"Built index with {len(index)} concepts")
        return index

    def resolve_all(
        self,
        concept_index: ConceptIndex,
        filing_id: str = "unknown",
        required_components: Optional[list[str]] = None
    ) -> ResolutionMap:
        """
        Resolve all components for a filing.

        Args:
            concept_index: Index of concepts from the filing
            filing_id: Identifier for the filing
            required_components: Optional list of component IDs to resolve.
                               If None, resolves all components.

        Returns:
            ResolutionMap with matched concepts
        """
        resolution = ResolutionMap(filing_id=filing_id)

        # Determine which components to resolve
        if required_components:
            components_to_resolve = {
                cid: self.components[cid]
                for cid in required_components
                if cid in self.components
            }
        else:
            components_to_resolve = self.components

        self.logger.info(
            f"Resolving {len(components_to_resolve)} components for {filing_id}"
        )

        # Phase 1: Try atomic matching for ALL components with rules
        # This includes composites - they may match directly (e.g.,
        # us-gaap:GrossProfit) which is more reliable than computing
        for component_id, component in components_to_resolve.items():
            has_rules = (
                component.matching_rules.label_rules
                or component.matching_rules.local_name_rules
            )
            if not has_rules:
                continue

            result = self._match_component(component, concept_index)
            resolution.add_match(component_id, result)

        # Phase 2: Formula computation for unresolved components
        # Any component with a formula (composite or atomic with
        # fallback) gets a chance at computation from resolved parts
        for component_id, component in components_to_resolve.items():
            if not component.composition.formula:
                continue
            if resolution.is_resolved(component_id):
                continue  # Already matched atomically

            composite_result = self._resolve_composite(
                component, resolution
            )
            resolution.add_composite(component_id, composite_result)

        # Log summary
        self.logger.info(
            f"Resolution complete: {len(resolution.resolved)}/{len(components_to_resolve)} "
            f"resolved, {resolution.high_confidence_rate:.1f}% high confidence"
        )

        return resolution

    def resolve_component(
        self,
        component_id: str,
        concept_index: ConceptIndex
    ) -> MatchResult:
        """
        Resolve a single component.

        Args:
            component_id: Component to resolve
            concept_index: Index of concepts

        Returns:
            MatchResult for the component
        """
        if component_id not in self.components:
            return MatchResult.no_match(
                component_id,
                f"Unknown component: {component_id}"
            )

        component = self.components[component_id]

        if component.is_composite:
            # For composites, we need a full resolution map
            self.logger.warning(
                f"resolve_component called for composite {component_id}; "
                f"use resolve_all for composites"
            )
            return MatchResult.no_match(
                component_id,
                "Composite components require full resolution"
            )

        return self._match_component(component, concept_index)

    def _match_component(
        self,
        component: ComponentDefinition,
        concept_index: ConceptIndex
    ) -> MatchResult:
        """
        Match a single atomic component.

        Args:
            component: Component definition
            concept_index: Concept index

        Returns:
            MatchResult
        """
        component_id = component.component_id

        # Initialize diagnostics for this component
        diag = {
            'component_id': component_id,
            'search_patterns': [],
            'filters': {},
            'candidates_found': 0,
            'rejections': [],
            'below_threshold': [],
            'passed_threshold': [],
            'failure_reason': None,
        }

        # Extract search criteria for diagnostics
        if component.matching_rules.label_rules:
            for rule in component.matching_rules.label_rules:
                diag['search_patterns'].extend(rule.patterns)

        if component.characteristics.balance_type:
            diag['filters']['balance_type'] = component.characteristics.balance_type.value
        if component.characteristics.period_type:
            diag['filters']['period_type'] = component.characteristics.period_type.value

        # Get candidate concepts
        candidates = self._get_candidates(component, concept_index)
        diag['candidates_found'] = len(candidates)

        # Diagnostic: Check for expected concepts and why they might be missing
        if self.diagnostics:
            self._log_candidate_diagnostics(
                component_id, candidates, concept_index, diag['search_patterns']
            )

        if not candidates:
            diag['failure_reason'] = 'NO_CANDIDATES'
            self._match_diagnostics[component_id] = diag

            self.logger.info(
                f"[MATCH FAIL] {component_id}: No candidates found. "
                f"Searched for patterns={diag['search_patterns']}, "
                f"filters={diag['filters']}"
            )
            return MatchResult.no_match(component_id, "No candidates found")

        self.logger.info(
            f"[MATCH] {component_id}: Evaluating {len(candidates)} candidates"
        )

        # Evaluate each candidate
        scored_matches = []
        rejection_count = 0
        below_threshold_count = 0

        for concept in candidates:
            # Check rejection conditions first
            rejection = self._check_rejection(concept, component)
            if rejection:
                rejection_count += 1
                diag['rejections'].append({
                    'concept': concept.qname,
                    'reason': rejection
                })
                if self.diagnostics and rejection_count <= 3:
                    self.logger.debug(
                        f"  [REJECTED] {concept.qname}: {rejection}"
                    )
                continue

            # Evaluate all rules
            evaluation_results = {}

            # Label rules
            if component.matching_rules.label_rules:
                result = self.evaluators['label'].evaluate(
                    concept=concept,
                    rules=component.matching_rules.label_rules
                )
                evaluation_results['label'] = result

            # Local name rules
            if component.matching_rules.local_name_rules:
                result = self.evaluators['local_name'].evaluate(
                    concept=concept,
                    rules=component.matching_rules.local_name_rules
                )
                evaluation_results['local_name'] = result

            # Hierarchy rules
            if component.matching_rules.hierarchy_rules:
                result = self.evaluators['hierarchy'].evaluate(
                    concept=concept,
                    rules=component.matching_rules.hierarchy_rules,
                    context={'concept_index': concept_index}
                )
                evaluation_results['hierarchy'] = result

            # Calculation rules
            if component.matching_rules.calculation_rules:
                result = self.evaluators['calculation'].evaluate(
                    concept=concept,
                    rules=component.matching_rules.calculation_rules,
                    context={'concept_index': concept_index}
                )
                evaluation_results['calculation'] = result

            # Definition rules
            if component.matching_rules.definition_rules:
                result = self.evaluators['definition'].evaluate(
                    concept=concept,
                    rules=component.matching_rules.definition_rules
                )
                evaluation_results['definition'] = result

            # Aggregate scores
            scored_match = self.score_aggregator.aggregate(
                concept_qname=concept.qname,
                evaluation_results=evaluation_results,
                component=component
            )

            # Check minimum score
            min_score = component.scoring.min_score
            if scored_match.total_score >= min_score:
                scored_matches.append(scored_match)
                diag['passed_threshold'].append({
                    'concept': concept.qname,
                    'score': scored_match.total_score,
                })
            else:
                below_threshold_count += 1
                diag['below_threshold'].append({
                    'concept': concept.qname,
                    'score': scored_match.total_score,
                    'min_required': min_score,
                })

        # Log diagnostic summary
        if self.diagnostics:
            self.logger.info(
                f"  [CANDIDATES] {component_id}: "
                f"{len(candidates)} found, "
                f"{rejection_count} rejected, "
                f"{below_threshold_count} below threshold, "
                f"{len(scored_matches)} passed"
            )

        # Handle results
        if not scored_matches:
            if rejection_count == len(candidates):
                diag['failure_reason'] = 'ALL_REJECTED'
                reason = f"All {len(candidates)} candidates rejected"
            else:
                diag['failure_reason'] = 'BELOW_THRESHOLD'
                reason = f"No candidates met min score ({component.scoring.min_score})"

                # Show top failing candidates
                if diag['below_threshold']:
                    top_failures = sorted(
                        diag['below_threshold'],
                        key=lambda x: x['score'],
                        reverse=True
                    )[:3]
                    for f in top_failures:
                        self.logger.info(
                            f"  [NEAR MISS] {f['concept']}: "
                            f"score={f['score']:.2f} (needs {f['min_required']})"
                        )

            self._match_diagnostics[component_id] = diag
            return MatchResult.no_match(component_id, reason)

        # Sort by score (descending)
        scored_matches.sort(key=lambda m: m.total_score, reverse=True)

        # Check for ties
        top_score = scored_matches[0].total_score
        ties = [m for m in scored_matches if m.total_score == top_score]

        if len(ties) > 1:
            # Apply tiebreaker
            best_match, tiebreaker_used = self.tiebreaker.resolve(
                matches=ties,
                strategy=component.scoring.tiebreaker,
                concept_index=concept_index
            )
            alternatives = [m for m in ties if m.concept != best_match.concept]
        else:
            best_match = scored_matches[0]
            tiebreaker_used = None
            alternatives = scored_matches[1:5]  # Keep top 5 alternatives

        # Log successful match
        diag['failure_reason'] = None
        diag['matched_concept'] = best_match.concept
        diag['matched_score'] = best_match.total_score
        self._match_diagnostics[component_id] = diag

        self.logger.info(
            f"  [MATCHED] {component_id} -> {best_match.concept} "
            f"(score={best_match.total_score:.2f})"
        )

        return MatchResult.from_scored_match(
            component_id=component_id,
            match=best_match,
            alternatives=alternatives,
            tiebreaker_used=tiebreaker_used
        )

    def _get_candidates(
        self,
        component: ComponentDefinition,
        concept_index: ConceptIndex
    ) -> list[ConceptMetadata]:
        """
        Get candidate concepts for matching.

        Uses the concept index for fast pre-filtering.

        Args:
            component: Component definition
            concept_index: Concept index

        Returns:
            List of candidate concepts
        """
        # Extract search terms from label rules
        label_patterns = []
        for rule in component.matching_rules.label_rules:
            label_patterns.extend(rule.patterns)

        # Extract local name patterns for candidate search
        local_name_patterns = []
        if component.matching_rules.local_name_rules:
            for rule in component.matching_rules.local_name_rules:
                local_name_patterns.extend(rule.patterns)

        # Get characteristic filters
        balance_type = None
        period_type = None

        if component.characteristics.balance_type:
            balance_type = component.characteristics.balance_type.value

        if component.characteristics.period_type:
            period_type = component.characteristics.period_type.value

        # Query index (labels + local names)
        candidate_qnames = concept_index.get_candidates(
            label_patterns=label_patterns,
            local_name_patterns=local_name_patterns,
            balance_type=balance_type,
            period_type=period_type,
            exclude_abstract=not component.characteristics.is_abstract,
            max_candidates=100
        )

        # Convert to concept metadata objects and apply universal filters
        # These patterns indicate non-value concepts (text blocks, disclosures)
        # that should never match monetary components
        universal_exclude = [
            'textblock', 'table', 'schedule',
            'explanatory', 'disclosure', 'policy',
        ]

        candidates = []
        for qname in candidate_qnames:
            concept = concept_index.get_concept(qname)
            if concept:
                local_lower = concept.local_name.lower()
                if any(excl in local_lower for excl in universal_exclude):
                    continue
                candidates.append(concept)

        return candidates

    def _log_candidate_diagnostics(
        self,
        component_id: str,
        candidates: list[ConceptMetadata],
        concept_index: ConceptIndex,
        search_patterns: list[str]
    ) -> None:
        """
        Log diagnostic info about candidate selection.

        Shows:
        - Sample of candidate QNames
        - Check if expected concepts exist but are missing from candidates
        - Sample labels from candidates
        """
        if not candidates:
            return

        # Sample candidate QNames
        sample = [c.qname for c in candidates[:5]]
        self.logger.info(f"  [CANDIDATES SAMPLE] {sample}")

        # Expected concept patterns based on component_id
        expected_map = {
            'current_assets': ['AssetsCurrent'],
            'total_assets': ['Assets'],
            'current_liabilities': ['LiabilitiesCurrent'],
            'total_liabilities': ['Liabilities'],
            'total_equity': ['StockholdersEquity', 'Equity'],
            'net_income': ['NetIncomeLoss', 'ProfitLoss'],
            'revenue': ['Revenues', 'Revenue', 'SalesRevenueNet'],
        }

        expected_patterns = expected_map.get(component_id, [])
        candidate_qnames = {c.qname for c in candidates}
        all_concepts = concept_index.get_all_concepts()

        for pattern in expected_patterns:
            # Find concepts matching this pattern in the FULL index
            matching = [c for c in all_concepts
                       if pattern.lower() in c.local_name.lower()]

            if matching:
                # Check if any of them are in our candidates
                in_candidates = [c for c in matching if c.qname in candidate_qnames]

                if not in_candidates:
                    # Expected concept exists but NOT in candidates
                    best_match = matching[0]
                    labels = list(best_match.labels.values())[:2] if best_match.labels else ['(no labels)']
                    self.logger.warning(
                        f"  [MISSING FROM CANDIDATES] '{best_match.qname}' "
                        f"(local_name: {best_match.local_name}, labels: {labels})"
                    )
                else:
                    # It's in candidates - will be evaluated
                    self.logger.info(
                        f"  [EXPECTED FOUND] '{in_candidates[0].qname}' is in candidates"
                    )

    def _check_rejection(
        self,
        concept: ConceptMetadata,
        component: ComponentDefinition
    ) -> Optional[str]:
        """
        Check if concept should be rejected.

        Args:
            concept: Concept to check
            component: Component with rejection conditions

        Returns:
            Rejection reason or None if not rejected
        """
        for condition in component.scoring.reject_if:
            if self._matches_rejection(concept, condition):
                return condition.condition

        return None

    def _matches_rejection(
        self,
        concept: ConceptMetadata,
        condition: RejectionCondition
    ) -> bool:
        """
        Check if concept matches a rejection condition.

        Supported patterns:
        - "abstract=true": Concept is abstract
        - "label~keyword": Label contains keyword
        - "name~pattern": Local name contains pattern

        Args:
            concept: Concept to check
            condition: Rejection condition

        Returns:
            True if concept should be rejected
        """
        pattern = condition.pattern

        if pattern == "abstract=true":
            return concept.is_abstract

        if pattern.startswith("label~"):
            keyword = pattern[6:]  # Remove "label~"
            for label in concept.get_all_labels():
                if keyword.lower() in label.lower():
                    return True

        if pattern.startswith("name~"):
            keyword = pattern[5:]  # Remove "name~"
            if keyword.lower() in concept.local_name.lower():
                return True

        return False

    def _resolve_composite(
        self,
        component: ComponentDefinition,
        resolution: ResolutionMap
    ) -> CompositeResolution:
        """
        Resolve a composite component.

        Args:
            component: Composite component definition
            resolution: Current resolution map with atomic matches

        Returns:
            CompositeResolution
        """
        component_id = component.component_id
        composition = component.composition

        # Check primary formula
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
            # Primary formula satisfied
            return CompositeResolution(
                component_id=component_id,
                resolved=True,
                formula=composition.formula,
                component_concepts=component_concepts
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
                # Alternative satisfied
                return CompositeResolution(
                    component_id=component_id,
                    resolved=True,
                    formula=alt.formula,
                    component_concepts=alt_concepts
                )

        # No formula satisfied
        return CompositeResolution(
            component_id=component_id,
            resolved=False,
            formula=composition.formula,
            component_concepts=component_concepts,
            missing_components=missing
        )

    def get_component(self, component_id: str) -> Optional[ComponentDefinition]:
        """Get a component definition by ID."""
        return self.components.get(component_id)

    def get_all_components(self) -> dict[str, ComponentDefinition]:
        """Get all loaded component definitions."""
        return self.components.copy()

    def reload_components(self) -> None:
        """Reload component definitions from disk."""
        self.component_loader.clear_cache()
        self.components = self.component_loader.load_all()
        self.logger.info(f"Reloaded {len(self.components)} components")

    def get_match_diagnostics(self) -> dict[str, dict]:
        """
        Get detailed diagnostics for all match attempts.

        Returns:
            Dictionary mapping component_id to diagnostic info including:
            - search_patterns: Patterns used to find candidates
            - filters: Balance/period type filters applied
            - candidates_found: Number of candidates found
            - rejections: List of rejected candidates with reasons
            - below_threshold: Candidates that scored below minimum
            - passed_threshold: Candidates that passed
            - failure_reason: Why matching failed (if it did)
            - matched_concept: The matched concept (if successful)
            - matched_score: The match score (if successful)
        """
        return self._match_diagnostics.copy()

    def print_diagnostics_summary(self) -> None:
        """Print a human-readable summary of match diagnostics."""
        print("\n" + "=" * 70)
        print("  MATCHING ENGINE DIAGNOSTICS")
        print("=" * 70)

        for comp_id, diag in self._match_diagnostics.items():
            if diag.get('matched_concept'):
                status = "[OK]"
                detail = f"-> {diag['matched_concept']} (score={diag['matched_score']:.2f})"
            else:
                status = "[--]"
                reason = diag.get('failure_reason', 'UNKNOWN')
                if reason == 'NO_CANDIDATES':
                    detail = f"No candidates. Patterns: {diag['search_patterns']}"
                elif reason == 'ALL_REJECTED':
                    detail = f"All {len(diag['rejections'])} candidates rejected"
                elif reason == 'BELOW_THRESHOLD':
                    if diag['below_threshold']:
                        best = max(diag['below_threshold'], key=lambda x: x['score'])
                        detail = (
                            f"Best score={best['score']:.2f} "
                            f"(needs {best['min_required']})"
                        )
                    else:
                        detail = "Below threshold"
                else:
                    detail = reason

            print(f"  {status} {comp_id:30s} {detail}")

        print("=" * 70 + "\n")


__all__ = ['MatchingCoordinator']
