# Path: mat_acc/ratio_check/ratio_calculator.py
"""
Ratio Calculator

Orchestrates the matching engine and ratio calculation pipeline.
Delegates to specialized modules:
- ratio_models: Data classes
- value_populator: 4-pass value population
- match_verify: Post-Match Financial Verification (PMFV)
- ratio_engine: Ratio computation
- ratio_definitions: Standard ratio list
- industry_detector: Auto-detect industry from filing concepts
- industry_registry: Industry-specific ratio model configs
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
from .ratio_definitions import STANDARD_RATIOS
from .industry_detector import IndustryDetector
from .industry_registry import IndustryRegistry
from .match_verify import MatchVerifier


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
        self._coordinator_market: Optional[str] = None
        self._last_resolution = None
        self._last_concept_index: Optional[ConceptIndex] = None
        self._value_populator = ValuePopulator()
        self._match_verifier = MatchVerifier()
        self._industry_detector = IndustryDetector()
        self._industry_registry = IndustryRegistry()
        self._detected_industry: str = 'general'

    def _get_coordinator(
        self, market: Optional[str] = None
    ) -> MatchingCoordinator:
        """Get or create matching coordinator for market."""
        if (
            self._coordinator is None
            or market != self._coordinator_market
        ):
            self._coordinator = MatchingCoordinator(
                diagnostics=self.diagnostics,
                market=market,
            )
            self._coordinator_market = market
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

        # Set market for dictionary overlay selection
        self._current_market = selection.market

        # Detect industry from filing concepts
        self._detected_industry = self._industry_detector.detect(
            concept_index,
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

            # Post-Match Financial Verification (PMFV)
            self._match_verifier.verify(
                component_matches, self._last_resolution,
                concept_index, value_lookup,
            )
        else:
            self.logger.warning("No value_lookup - ratios will lack values")

        # Build filtered ratio list for this industry
        ratio_list = self._build_ratio_list(self._detected_industry)

        result.component_matches = component_matches
        result.ratios = calculate_ratios(component_matches, ratio_list)
        result.summary = self._build_summary(
            component_matches, result.ratios,
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
        market = getattr(self, '_current_market', None)
        coordinator = self._get_coordinator(market)
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

    def _build_ratio_list(self, industry: str) -> list[dict]:
        """
        Build filtered ratio list for the detected industry.

        Takes standard ratios, removes skipped ones, adds extras.

        Args:
            industry: Detected industry type

        Returns:
            List of ratio definitions to calculate
        """
        skip_ids = set(
            self._industry_registry.get_skip_ratio_ids(industry)
        )
        extras = self._industry_registry.get_extra_ratios(industry)

        # Filter standard ratios
        filtered = [
            r for r in STANDARD_RATIOS
            if r.get('ratio_id') not in skip_ids
        ]

        # Add industry-specific ratios
        filtered.extend(extras)

        skipped = len(STANDARD_RATIOS) - (len(filtered) - len(extras))
        if skipped > 0:
            self.logger.info(
                f"Industry '{industry}': skipped {skipped} ratios, "
                f"added {len(extras)} extras"
            )

        return filtered

    def _build_summary(
        self,
        component_matches: List[ComponentMatch],
        ratios: List[RatioResult],
    ) -> Dict[str, Any]:
        """Build analysis summary statistics."""
        total = len(component_matches)
        matched = sum(1 for m in component_matches if m.matched)
        valid = sum(1 for r in ratios if r.valid)

        # Classify unmatched as "not applicable" if zero candidates
        not_applicable = sum(
            1 for m in component_matches
            if not m.matched and m.confidence == 0
        )

        applicable = total - not_applicable
        industry = self._detected_industry
        display_name = self._industry_registry.get_display_name(industry)

        return {
            'total_components': total,
            'matched_components': matched,
            'match_rate': matched / applicable if applicable > 0 else 0,
            'applicable_components': applicable,
            'not_applicable': not_applicable,
            'total_ratios': len(ratios),
            'valid_ratios': valid,
            'industry': industry,
            'industry_display': display_name,
        }

    def display_results(self, result: AnalysisResult) -> None:
        """Display analysis results to console."""
        print()
        print("=" * 70)
        print(f"  RATIO ANALYSIS: {result.company}")
        print(f"  {result.market.upper()} | {result.form} | {result.date}")
        industry_name = result.summary.get('industry_display', '')
        if industry_name:
            print(f"  Industry: {industry_name}")
        print("=" * 70)

        self._display_pmfv_corrections()
        self._display_components(result.component_matches)
        self._display_ratios(result.ratios, result.normalizations)
        self._display_summary(result.summary)

    def _display_pmfv_corrections(self) -> None:
        """Display PMFV corrections if any were made."""
        corrections = self._match_verifier.get_corrections()
        if not corrections:
            return
        print("\n  POST-MATCH VERIFICATION:")
        print("-" * 70)
        for c in corrections:
            old_name = c['old_concept'].split(':')[-1][:30]
            new_name = c['new_concept'].split(':')[-1][:30]
            old_v = f"{c['old_value']:,.0f}" if c['old_value'] else '?'
            new_v = f"{c['new_value']:,.0f}" if c['new_value'] else '?'
            print(
                f"    [FIX] {c['component']:22s} "
                f"{old_name} ({old_v}) -> {new_name} ({new_v})"
            )

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

    def _display_ratios(
        self, ratios: List[RatioResult],
        normalizations: Optional[Dict] = None,
    ) -> None:
        """Display financial ratios section with normalization."""
        print("\n  FINANCIAL RATIOS:")
        print("-" * 70)
        norms = normalizations or {}

        for r in ratios:
            if r.valid:
                print(f"    [OK] {r.ratio_name:25s} = {r.value:10.4f}")
                num = f"{r.numerator_value:,.0f}" if r.numerator_value else "N/A"
                den = f"{r.denominator_value:,.0f}" if r.denominator_value else "N/A"
                print(f"         {r.formula}")
                print(f"         ({num} / {den})")
                ann = norms.get(r.ratio_name)
                if ann:
                    print(
                        f"         >> Normalized:"
                        f" {ann.normalized_value:10.4f}"
                        f"  ({ann.explanation})"
                    )
            elif r.error:
                if r.numerator_value is not None or r.denominator_value is not None:
                    num = f"{r.numerator_value:,.0f}" if r.numerator_value else "[missing]"
                    den = f"{r.denominator_value:,.0f}" if r.denominator_value else "[missing]"
                    print(f"    [--] {r.ratio_name:25s} - {r.error}")
                    print(f"         Values: {num} / {den}")
                else:
                    print(f"    [--] {r.ratio_name:25s} - {r.error}")

    def _display_summary(self, s: Dict[str, Any]) -> None:
        """Display summary section with industry-aware counts."""
        print("\n  SUMMARY:")
        print("-" * 70)
        mc = s.get('matched_components', 0)
        ac = s.get('applicable_components', s.get('total_components', 0))
        na = s.get('not_applicable', 0)
        mr = s.get('match_rate', 0)
        print(f"    Components: {mc}/{ac} matched ({mr*100:.1f}%)")
        if na > 0:
            print(f"    Not applicable: {na} (no matching concept in filing)")
        vr = s.get('valid_ratios', 0)
        tr = s.get('total_ratios', 0)
        print(f"    Ratios: {vr}/{tr} calculated")
        print("\n" + "=" * 70)


__all__ = ['RatioCalculator', 'ComponentMatch', 'RatioResult', 'AnalysisResult']
