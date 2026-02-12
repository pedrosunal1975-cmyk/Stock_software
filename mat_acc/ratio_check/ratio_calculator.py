# Path: mat_acc/ratio_check/ratio_calculator.py
"""
Ratio Calculator

Orchestrates the matching engine and ratio calculation pipeline.
Delegates to specialized modules:
- ratio_models: Data classes
- value_populator: 4-pass value population
- ratio_engine: Ratio computation
- ratio_definitions: Standard ratio list
"""

from typing import Optional, Dict, List, Any

from config_loader import ConfigLoader
from core.logger.ipo_logging import get_process_logger

from process.matcher import MatchingCoordinator, ConceptIndex

from .filing_menu import FilingSelection
from .fact_value_lookup import FactValueLookup
from .ratio_models import ComponentMatch, RatioResult, AnalysisResult
from .value_populator import ValuePopulator
from .ratio_engine import calculate_ratios


logger = get_process_logger('ratio_calculator')


class RatioCalculator:
    """
    Calculates financial ratios using the matching engine.

    Workflow:
    1. Load component definitions from dictionary
    2. Match components against filing concepts
    3. Extract values for matched components
    4. Calculate financial ratios

    Example:
        calculator = RatioCalculator(config)
        result = calculator.analyze(
            selection=filing_selection,
            concept_index=enriched_concepts,
        )
        for ratio in result.ratios:
            if ratio.valid:
                print(f"{ratio.ratio_name}: {ratio.value:.2f}")
    """

    def __init__(self, config: ConfigLoader, diagnostics: bool = True):
        """
        Initialize ratio calculator.

        Args:
            config: ConfigLoader instance
            diagnostics: Enable detailed diagnostic output
        """
        self.config = config
        self.logger = get_process_logger('ratio_calculator')
        self.diagnostics = diagnostics
        self._coordinator: Optional[MatchingCoordinator] = None
        self._last_resolution = None
        self._last_concept_index: Optional[ConceptIndex] = None
        self._value_populator = ValuePopulator()

    def _get_coordinator(self) -> MatchingCoordinator:
        """Get or create matching coordinator."""
        if self._coordinator is None:
            self._coordinator = MatchingCoordinator(
                diagnostics=self.diagnostics
            )
        return self._coordinator

    def analyze(
        self,
        selection: FilingSelection,
        concept_index: ConceptIndex,
        value_lookup: Optional[FactValueLookup] = None,
    ) -> AnalysisResult:
        """
        Run complete analysis on a filing.

        Args:
            selection: Selected filing
            concept_index: Enriched concept index
            value_lookup: FactValueLookup for retrieving actual values

        Returns:
            AnalysisResult with matches and ratios
        """
        result = AnalysisResult(
            company=selection.company,
            market=selection.market,
            form=selection.form,
            date=selection.date,
        )

        component_matches = self.match_components(concept_index)

        if value_lookup:
            self._value_populator.populate(
                component_matches, value_lookup,
                self._last_resolution, concept_index,
            )
            valued = sum(1 for m in component_matches if m.value is not None)
            matched = sum(1 for m in component_matches if m.matched)
            self.logger.info(
                f"Populated values for {valued} of {matched} matched"
            )
        else:
            self.logger.warning("No value_lookup - ratios will lack values")

        result.component_matches = component_matches
        result.ratios = calculate_ratios(component_matches)
        result.summary = self._build_summary(
            component_matches, result.ratios
        )

        return result

    def match_components(
        self,
        concept_index: ConceptIndex,
    ) -> List[ComponentMatch]:
        """
        Match all components against concepts using hybrid resolution.

        Uses resolve_all() which tries atomic matching first for ALL
        components, then formula computation for unresolved composites.

        Args:
            concept_index: Index of concepts to match against

        Returns:
            List of ComponentMatch results
        """
        coordinator = self._get_coordinator()
        matches = []

        components = coordinator.get_all_components()
        self.logger.info(
            f"Matching {len(components)} components "
            f"against {len(concept_index)} concepts"
        )

        resolution = coordinator.resolve_all(
            concept_index=concept_index,
            filing_id="current",
        )

        self._last_resolution = resolution
        self._last_concept_index = concept_index

        for component_id in components:
            match = self._build_component_match(
                component_id, resolution, concept_index, components,
            )
            matches.append(match)

        matched_count = sum(1 for m in matches if m.matched)
        self.logger.info(
            f"Matched {matched_count}/{len(matches)} components"
        )

        if self.diagnostics:
            coordinator.print_diagnostics_summary()

        return matches

    def _build_component_match(
        self,
        component_id: str,
        resolution,
        concept_index: ConceptIndex,
        components: dict,
    ) -> ComponentMatch:
        """Build a ComponentMatch from resolution data."""
        match = ComponentMatch(component_name=component_id)

        if resolution.is_resolved(component_id):
            resolved = resolution.resolved[component_id]
            match.matched = True
            match.matched_concept = resolved.concept
            match.confidence = float(resolved.score)

            if resolved.is_composite:
                match.label = resolved.concept.replace(
                    'COMPOSITE:', ''
                )
            else:
                concept = concept_index.get_concept(resolved.concept)
                if concept:
                    match.label = (
                        concept.get_label('standard')
                        or concept.get_label('taxonomy')
                    )

        comp_def = components.get(component_id)
        if comp_def and comp_def.composition.formula:
            match.fallback_formula = comp_def.composition.formula

        return match

    def _build_summary(
        self,
        component_matches: List[ComponentMatch],
        ratios: List[RatioResult],
    ) -> Dict[str, Any]:
        """Build analysis summary statistics."""
        total = len(component_matches)
        matched = sum(1 for m in component_matches if m.matched)
        valid = sum(1 for r in ratios if r.valid)

        return {
            'total_components': total,
            'matched_components': matched,
            'match_rate': matched / total if total > 0 else 0,
            'total_ratios': len(ratios),
            'valid_ratios': valid,
        }

    def display_results(self, result: AnalysisResult) -> None:
        """Display analysis results to console."""
        print()
        print("=" * 70)
        print(f"  RATIO ANALYSIS: {result.company}")
        print(f"  {result.market.upper()} | {result.form} | {result.date}")
        print("=" * 70)

        self._display_components(result.component_matches)
        self._display_ratios(result.ratios)
        self._display_summary(result.summary)

    def _display_components(self, matches: List[ComponentMatch]) -> None:
        """Display component matching section."""
        print("\n  COMPONENT MATCHING:")
        print("-" * 70)

        matched = [m for m in matches if m.matched]
        unmatched = [m for m in matches if not m.matched]

        if matched:
            print(f"\n  Matched ({len(matched)}):")
            for m in matched:
                conf = f"{m.confidence:.2f}" if m.confidence else "N/A"
                label = m.label[:35] if m.label else ''
                if not label and m.matched_concept:
                    label = m.matched_concept[:35]
                if m.value is not None:
                    val = f"{m.value:>15,.0f}"
                else:
                    val = f"{'[no value]':>15}"
                print(f"    [OK] {m.component_name:22s} -> {label:35s} {val} ({conf})")

        if unmatched:
            print(f"\n  Unmatched ({len(unmatched)}):")
            for m in unmatched[:10]:
                print(f"    [--] {m.component_name}")
            if len(unmatched) > 10:
                print(f"    ... and {len(unmatched) - 10} more")

    def _display_ratios(self, ratios: List[RatioResult]) -> None:
        """Display financial ratios section."""
        print("\n  FINANCIAL RATIOS:")
        print("-" * 70)

        for r in ratios:
            if r.valid:
                print(f"    [OK] {r.ratio_name:25s} = {r.value:10.4f}")
                num = f"{r.numerator_value:,.0f}" if r.numerator_value else "N/A"
                den = f"{r.denominator_value:,.0f}" if r.denominator_value else "N/A"
                print(f"         {r.formula}")
                print(f"         ({num} / {den})")
            elif r.error:
                if r.numerator_value is not None or r.denominator_value is not None:
                    num = f"{r.numerator_value:,.0f}" if r.numerator_value else "[missing]"
                    den = f"{r.denominator_value:,.0f}" if r.denominator_value else "[missing]"
                    print(f"    [--] {r.ratio_name:25s} - {r.error}")
                    print(f"         Values: {num} / {den}")
                else:
                    print(f"    [--] {r.ratio_name:25s} - {r.error}")

    def _display_summary(self, s: Dict[str, Any]) -> None:
        """Display summary section."""
        print("\n  SUMMARY:")
        print("-" * 70)
        mc, tc = s.get('matched_components', 0), s.get('total_components', 0)
        mr = s.get('match_rate', 0)
        print(f"    Components: {mc}/{tc} matched ({mr*100:.1f}%)")
        print(f"    Ratios: {s.get('valid_ratios', 0)}/{s.get('total_ratios', 0)} calculated")
        print("\n" + "=" * 70)


__all__ = ['RatioCalculator', 'ComponentMatch', 'RatioResult', 'AnalysisResult']
