# Path: mat_acc/ratio_check/ratio_calculator.py
"""
Ratio Calculator

Orchestrates the matching engine and ratio calculation pipeline.
Delegates to specialized modules:
- ratio_models: Data classes
- value_populator: 6-pass value population
- calc_discovery: Dynamic formulas from calculation linkbase
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

from .input.filing_menu import FilingSelection
from .fact_value_lookup import FactValueLookup
from .ratio_models import ComponentMatch, RatioResult, AnalysisResult
from .values.value_populator import ValuePopulator
from .calculation.ratio_engine import calculate_ratios
from .calculation.ratio_definitions import STANDARD_RATIOS
from .industry.detector import IndustryDetector
from .industry.registry import IndustryRegistry
from .match_verify import MatchVerifier


logger = get_process_logger('ratio_calculator')


class RatioCalculator:
    """Calculates financial ratios using the matching engine."""

    def __init__(
        self, config: ConfigLoader, diagnostics: bool = True,
    ):
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
        self, selection: FilingSelection,
        concept_index: ConceptIndex,
        value_lookup: Optional[FactValueLookup] = None,
        calc_networks: Optional[list] = None,
    ) -> AnalysisResult:
        """Run complete analysis on a filing."""
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

        # Calculation Discovery: enhance matches using
        # company-declared formulas from calculation linkbase
        if calc_networks:
            self._run_calc_discovery(
                calc_networks, component_matches, concept_index,
            )

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
        self, concept_index: ConceptIndex,
    ) -> List[ComponentMatch]:
        """Match all components using hybrid resolution."""
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
        if comp_def and hasattr(comp_def, 'validation'):
            sign = comp_def.validation.expected_sign
            match.expected_sign = sign.value if sign else None

        return match

    def _build_ratio_list(self, industry: str) -> list[dict]:
        """Build filtered ratio list for the detected industry."""
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

    def _run_calc_discovery(
        self, calc_networks, matches, concept_index,
    ) -> None:
        """Use company's calculation linkbase to enhance matches."""
        from .calc_discovery import extract_formulas, enhance_matches
        formulas = extract_formulas(calc_networks)
        if formulas:
            enhanced = enhance_matches(
                formulas, matches, concept_index,
            )
            if enhanced:
                self.logger.info(
                    f"Calc discovery: {enhanced} enhancements"
                )

    def display_results(self, result: AnalysisResult) -> None:
        """Display analysis results to console."""
        from .calculation.result_display import display_results
        corrections = self._match_verifier.get_corrections()
        display_results(result, corrections)


__all__ = ['RatioCalculator', 'ComponentMatch', 'RatioResult', 'AnalysisResult']
