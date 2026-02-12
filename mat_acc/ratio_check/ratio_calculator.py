# Path: mat_acc_files/ratio_check/ratio_calculator.py
"""
Ratio Calculator

Runs the Dynamic Concept Matching Engine on enriched concepts
and calculates financial ratios from matched components.

Uses the dictionary component definitions to identify financial
statement items and compute standard ratios.

IMPORTANT: Values are retrieved from actual source files via FactValueLookup.
The matching engine matches concepts, the value lookup retrieves actual values.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from decimal import Decimal

from config_loader import ConfigLoader

# Import IPO logging (PROCESS layer for calculation work)
from core.logger.ipo_logging import get_process_logger

# Import matcher components
from process.matcher import (
    MatchingCoordinator,
    ConceptMetadata,
    ConceptIndex,
    MatchResult,
    MatchStatus,
)

# Import local modules
from .concept_builder import ConceptBuilder
from .filing_menu import FilingSelection
from .fact_value_lookup import FactValueLookup


# Use IPO-aware logger (PROCESS layer)
logger = get_process_logger('ratio_calculator')


@dataclass
class ComponentMatch:
    """
    Result of matching a component.

    Attributes:
        component_name: Name of the component (e.g., 'current_assets')
        matched: Whether a match was found
        matched_concept: Matched concept QName if found
        confidence: Match confidence score (0-1)
        value: Numeric value if available
        label: Human-readable label
        rule_breakdown: Breakdown of rule scores
    """
    component_name: str
    matched: bool = False
    matched_concept: Optional[str] = None
    confidence: float = 0.0
    value: Optional[float] = None
    label: Optional[str] = None
    rule_breakdown: Dict[str, float] = field(default_factory=dict)
    fallback_formula: Optional[str] = None


@dataclass
class RatioResult:
    """
    Result of a ratio calculation.

    Attributes:
        ratio_name: Name of the ratio
        value: Calculated ratio value
        formula: Formula description
        numerator: Numerator component name
        denominator: Denominator component name
        numerator_value: Numerator value used
        denominator_value: Denominator value used
        valid: Whether calculation was successful
        error: Error message if calculation failed
    """
    ratio_name: str
    value: Optional[float] = None
    formula: str = ''
    numerator: str = ''
    denominator: str = ''
    numerator_value: Optional[float] = None
    denominator_value: Optional[float] = None
    valid: bool = False
    error: Optional[str] = None


@dataclass
class AnalysisResult:
    """
    Complete analysis result for a filing.

    Attributes:
        company: Company name
        market: Market identifier
        form: Form type
        date: Filing date
        component_matches: Matched components
        ratios: Calculated ratios
        summary: Summary statistics
    """
    company: str
    market: str
    form: str
    date: str
    component_matches: List[ComponentMatch] = field(default_factory=list)
    ratios: List[RatioResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


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

        # Run analysis
        result = calculator.analyze(
            selection=filing_selection,
            concept_index=enriched_concepts,
        )

        # Display results
        for ratio in result.ratios:
            if ratio.valid:
                print(f"{ratio.ratio_name}: {ratio.value:.2f}")
    """

    # Standard financial ratios to calculate
    # Organized by category for traceability
    # Each ratio uses component IDs that match dictionary/components/ definitions
    STANDARD_RATIOS = [
        # =========================================================================
        # LIQUIDITY RATIOS - Measure ability to meet short-term obligations
        # =========================================================================
        {
            'name': 'Current Ratio',
            'category': 'liquidity',
            'formula': 'Current Assets / Current Liabilities',
            'numerator': 'current_assets',
            'denominator': 'current_liabilities',
        },
        {
            'name': 'Quick Ratio',
            'category': 'liquidity',
            'formula': '(Current Assets - Inventory) / Current Liabilities',
            'numerator': ['current_assets', '-inventory'],
            'denominator': 'current_liabilities',
        },
        {
            'name': 'Cash Ratio',
            'category': 'liquidity',
            'formula': 'Cash and Equivalents / Current Liabilities',
            'numerator': 'cash_and_equivalents',
            'denominator': 'current_liabilities',
        },
        # =========================================================================
        # LEVERAGE RATIOS - Measure financial leverage and debt capacity
        # =========================================================================
        {
            'name': 'Debt to Equity',
            'category': 'leverage',
            'formula': 'Total Liabilities / Total Equity',
            'numerator': 'total_liabilities',
            'denominator': 'total_equity',
        },
        {
            'name': 'Debt Ratio',
            'category': 'leverage',
            'formula': 'Total Liabilities / Total Assets',
            'numerator': 'total_liabilities',
            'denominator': 'total_assets',
        },
        {
            'name': 'Equity Multiplier',
            'category': 'leverage',
            'formula': 'Total Assets / Total Equity',
            'numerator': 'total_assets',
            'denominator': 'total_equity',
        },
        {
            'name': 'Interest Coverage',
            'category': 'leverage',
            'formula': 'Operating Income / Interest Expense',
            'numerator': 'operating_income',
            'denominator': 'interest_expense',
        },
        # =========================================================================
        # PROFITABILITY RATIOS - Measure ability to generate profits
        # =========================================================================
        {
            'name': 'Gross Margin',
            'category': 'profitability',
            'formula': 'Gross Profit / Revenue',
            'numerator': 'gross_profit',
            'denominator': 'revenue',
        },
        {
            'name': 'Operating Margin',
            'category': 'profitability',
            'formula': 'Operating Income / Revenue',
            'numerator': 'operating_income',
            'denominator': 'revenue',
        },
        {
            'name': 'Net Profit Margin',
            'category': 'profitability',
            'formula': 'Net Income / Revenue',
            'numerator': 'net_income',
            'denominator': 'revenue',
        },
        {
            'name': 'Return on Assets',
            'category': 'profitability',
            'formula': 'Net Income / Total Assets',
            'numerator': 'net_income',
            'denominator': 'total_assets',
        },
        {
            'name': 'Return on Equity',
            'category': 'profitability',
            'formula': 'Net Income / Total Equity',
            'numerator': 'net_income',
            'denominator': 'total_equity',
        },
        {
            'name': 'EBITDA Margin',
            'category': 'profitability',
            'formula': 'EBITDA / Revenue',
            'numerator': 'ebitda',
            'denominator': 'revenue',
        },
        # =========================================================================
        # EFFICIENCY RATIOS - Measure asset utilization and operational efficiency
        # =========================================================================
        {
            'name': 'Asset Turnover',
            'category': 'efficiency',
            'formula': 'Revenue / Total Assets',
            'numerator': 'revenue',
            'denominator': 'total_assets',
        },
        {
            'name': 'Inventory Turnover',
            'category': 'efficiency',
            'formula': 'Cost of Goods Sold / Inventory',
            'numerator': 'cost_of_goods_sold',
            'denominator': 'inventory',
        },
        {
            'name': 'Receivables Turnover',
            'category': 'efficiency',
            'formula': 'Revenue / Accounts Receivable',
            'numerator': 'revenue',
            'denominator': 'accounts_receivable',
        },
        {
            'name': 'Payables Turnover',
            'category': 'efficiency',
            'formula': 'Cost of Goods Sold / Accounts Payable',
            'numerator': 'cost_of_goods_sold',
            'denominator': 'accounts_payable',
        },
    ]

    def __init__(self, config: ConfigLoader, diagnostics: bool = True):
        """
        Initialize ratio calculator.

        Args:
            config: ConfigLoader instance
            diagnostics: Enable detailed diagnostic output (default True)
        """
        self.config = config
        self.logger = get_process_logger('ratio_calculator')
        self.diagnostics = diagnostics
        self._coordinator: Optional[MatchingCoordinator] = None
        self._last_resolution = None
        self._last_concept_index: Optional[ConceptIndex] = None

    def _get_coordinator(self) -> MatchingCoordinator:
        """Get or create matching coordinator."""
        if self._coordinator is None:
            self._coordinator = MatchingCoordinator(diagnostics=self.diagnostics)
            components = self._coordinator.get_all_components()
            self.logger.info(f"Loaded {len(components)} component definitions")
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

        # Match components
        component_matches = self.match_components(concept_index)

        # CRITICAL: Populate values from source files
        if value_lookup:
            self._populate_values(
                component_matches, value_lookup,
                self._last_resolution, concept_index,
            )
            self.logger.info(
                f"Populated values for {sum(1 for m in component_matches if m.value is not None)} "
                f"of {sum(1 for m in component_matches if m.matched)} matched components"
            )
        else:
            self.logger.warning("No value_lookup provided - ratios will not have values!")

        result.component_matches = component_matches

        # Calculate ratios
        ratios = self.calculate_ratios(component_matches)
        result.ratios = ratios

        # Build summary
        result.summary = self._build_summary(component_matches, ratios)

        return result

    def _populate_values(
        self,
        matches: List['ComponentMatch'],
        value_lookup: FactValueLookup,
        resolution=None,
        concept_index: Optional[ConceptIndex] = None,
    ) -> None:
        """
        Populate values for matched components from source files.

        Four passes:
        1. Atomic values from source files
        2. Alternative recovery: try alternative matches for unvalued
        3. Composite values from populated atomics
        4. Fallback formula for remaining unvalued atomics

        Args:
            matches: List of ComponentMatch with matched_concept set
            value_lookup: FactValueLookup with loaded values
            resolution: ResolutionMap with alternatives per component
            concept_index: ConceptIndex for label lookup
        """
        match_lookup = {m.component_name: m for m in matches}

        # Pass 1: populate atomic values from source files
        for match in matches:
            if not match.matched or not match.matched_concept:
                continue
            if match.matched_concept.startswith('COMPOSITE:'):
                continue

            value = value_lookup.get_value(match.matched_concept)
            if value is not None:
                match.value = value

        # Pass 2: alternative recovery for unvalued atomic matches
        # When the best-scoring concept has no reported value,
        # try alternative concepts from the scoring pipeline.
        # This handles cases where a concept exists in hierarchy
        # but not in reported facts (common across all filings).
        if resolution:
            self._try_alternative_values(
                matches, value_lookup, resolution, concept_index,
            )

        # Pass 3: compute composite values from atomic values
        for match in matches:
            if not match.matched or not match.matched_concept:
                continue
            if not match.matched_concept.startswith('COMPOSITE:'):
                continue

            formula = match.matched_concept.replace('COMPOSITE:', '')
            match.value = self._evaluate_formula(
                formula, match_lookup
            )

        # Pass 4: fallback formula for atomic matches with no value
        # If atomic match found a concept but no value exists for it,
        # try computing from the component's composite formula instead
        for match in matches:
            if match.value is not None:
                continue
            if not match.matched or not match.fallback_formula:
                continue

            computed = self._evaluate_formula(
                match.fallback_formula, match_lookup
            )
            if computed is not None:
                match.value = computed

    def _try_alternative_values(
        self,
        matches: List['ComponentMatch'],
        value_lookup: FactValueLookup,
        resolution,
        concept_index: Optional[ConceptIndex] = None,
    ) -> None:
        """
        Try alternative concept matches for unvalued components.

        When the primary match has no value in reported facts, iterate
        through alternative matches (ranked by score) and use the first
        one that has a reported value.

        This is principle-based: any filing can have concepts in its
        presentation structure that lack reported fact values, while
        a lower-scoring alternative actually carries the data.

        Args:
            matches: Component matches to check
            value_lookup: For looking up values
            resolution: ResolutionMap with alternatives
            concept_index: For updating labels
        """
        for match in matches:
            if match.value is not None:
                continue
            if not match.matched:
                continue
            if match.matched_concept.startswith('COMPOSITE:'):
                continue

            # Get the full match result with alternatives
            match_result = resolution.matches.get(match.component_name)
            if not match_result or not match_result.alternatives:
                continue

            for alt in match_result.alternatives:
                if not alt.concept:
                    continue
                value = value_lookup.get_value(alt.concept)
                if value is not None:
                    old_concept = match.matched_concept
                    match.matched_concept = alt.concept
                    match.confidence = float(alt.total_score)
                    match.value = value
                    # Update label from concept index
                    if concept_index:
                        alt_meta = concept_index.get_concept(
                            alt.concept
                        )
                        if alt_meta:
                            match.label = (
                                alt_meta.get_label('standard')
                                or alt_meta.get_label('taxonomy')
                            )
                    self.logger.info(
                        f"[ALT RECOVERY] {match.component_name}: "
                        f"{old_concept} (no value) -> "
                        f"{alt.concept} (value={value:,.0f})"
                    )
                    break

    def _evaluate_formula(
        self,
        formula: str,
        match_lookup: Dict[str, 'ComponentMatch'],
    ) -> Optional[float]:
        """
        Evaluate a simple arithmetic formula using component values.

        Handles: a + b, a - b, a / b, a + b + c + d

        Args:
            formula: Formula string (e.g., "total_assets - total_equity")
            match_lookup: Component name to ComponentMatch mapping

        Returns:
            Computed value or None if any component missing
        """
        tokens = formula.replace('+', ' + ').replace(
            '-', ' - '
        ).replace('/', ' / ').split()

        result = None
        operator = '+'

        for token in tokens:
            if token in ('+', '-', '/'):
                operator = token
                continue

            component = match_lookup.get(token)
            if not component or component.value is None:
                return None

            val = component.value
            if result is None:
                result = val if operator == '+' else -val
            elif operator == '+':
                result += val
            elif operator == '-':
                result -= val
            elif operator == '/' and val != 0:
                result /= val
            else:
                return None

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

        # Get all component definitions from coordinator
        components = coordinator.get_all_components()
        self.logger.info(
            f"Matching {len(components)} components "
            f"against {len(concept_index)} concepts"
        )

        # Use resolve_all for hybrid resolution (atomic + composite)
        resolution = coordinator.resolve_all(
            concept_index=concept_index,
            filing_id="current",
        )

        # Store for value population (alternative recovery)
        self._last_resolution = resolution
        self._last_concept_index = concept_index

        # Convert resolution map to ComponentMatch list
        for component_id in components:
            match = ComponentMatch(component_name=component_id)

            if resolution.is_resolved(component_id):
                resolved = resolution.resolved[component_id]
                match.matched = True

                if resolved.is_composite:
                    # Composite: store formula as concept marker
                    match.matched_concept = resolved.concept
                    match.confidence = float(resolved.score)
                    match.label = resolved.concept.replace(
                        'COMPOSITE:', ''
                    )
                else:
                    # Atomic: store matched concept
                    match.matched_concept = resolved.concept
                    match.confidence = float(resolved.score)
                    # Get label from concept index
                    concept = concept_index.get_concept(
                        resolved.concept
                    )
                    if concept:
                        match.label = (
                            concept.get_label('standard')
                            or concept.get_label('taxonomy')
                        )

            # Store fallback formula for composite-capable components
            comp_def = components.get(component_id)
            if comp_def and comp_def.composition.formula:
                match.fallback_formula = comp_def.composition.formula

            matches.append(match)

        # Log summary
        matched_count = sum(1 for m in matches if m.matched)
        self.logger.info(
            f"Matched {matched_count}/{len(matches)} components"
        )

        # Print diagnostics summary if enabled
        if self.diagnostics:
            coordinator.print_diagnostics_summary()

        return matches

    def _match_single_component(
        self,
        coordinator: MatchingCoordinator,
        component_id: str,
        concept_index: ConceptIndex,
    ) -> ComponentMatch:
        """
        Match a single component.

        Args:
            coordinator: Matching coordinator
            component_id: Component to match
            concept_index: Concepts to match against

        Returns:
            ComponentMatch result
        """
        match = ComponentMatch(component_name=component_id)

        try:
            # Run matching using coordinator
            result = coordinator.resolve_component(component_id, concept_index)

            if result and result.is_matched:
                match.matched = True
                match.matched_concept = result.matched_concept
                match.confidence = float(result.total_score)
                # Extract rule breakdown
                match.rule_breakdown = {
                    k: float(v.score) for k, v in result.rule_breakdown.items()
                }

                # Get label from matched concept
                if result.matched_concept:
                    concept = concept_index.get_concept(result.matched_concept)
                    if concept:
                        match.label = concept.get_label('standard') or concept.get_label('taxonomy')

        except Exception as e:
            self.logger.warning(f"Error matching {component_id}: {e}")

        return match

    def calculate_ratios(
        self,
        component_matches: List[ComponentMatch],
    ) -> List[RatioResult]:
        """
        Calculate financial ratios from matched components.

        Args:
            component_matches: List of matched components

        Returns:
            List of RatioResult
        """
        # Build lookup for matched components
        matched_lookup: Dict[str, ComponentMatch] = {
            m.component_name: m for m in component_matches if m.matched
        }

        ratios = []

        for ratio_def in self.STANDARD_RATIOS:
            ratio = self._calculate_single_ratio(ratio_def, matched_lookup)
            ratios.append(ratio)

        return ratios

    def _calculate_single_ratio(
        self,
        ratio_def: Dict[str, Any],
        matched_lookup: Dict[str, ComponentMatch],
    ) -> RatioResult:
        """
        Calculate a single ratio.

        Args:
            ratio_def: Ratio definition
            matched_lookup: Matched components lookup

        Returns:
            RatioResult
        """
        ratio = RatioResult(
            ratio_name=ratio_def['name'],
            formula=ratio_def['formula'],
        )

        # Get numerator
        numerator_def = ratio_def['numerator']
        numerator_result = self._resolve_component_value(numerator_def, matched_lookup)

        if numerator_result['error']:
            ratio.numerator = numerator_result['formula']
            ratio.error = numerator_result['error']
            return ratio

        ratio.numerator = numerator_result['formula']
        ratio.numerator_value = numerator_result['value']

        # Get denominator
        denominator_def = ratio_def['denominator']
        denominator_result = self._resolve_component_value(denominator_def, matched_lookup)

        if denominator_result['error']:
            ratio.denominator = denominator_result['formula']
            ratio.error = denominator_result['error']
            return ratio

        ratio.denominator = denominator_result['formula']
        ratio.denominator_value = denominator_result['value']

        # Calculate ratio if we have values
        if ratio.numerator_value is not None and ratio.denominator_value is not None:
            if ratio.denominator_value != 0:
                ratio.value = ratio.numerator_value / ratio.denominator_value
                ratio.valid = True
            else:
                ratio.error = "Division by zero"
        else:
            # Components matched but no values - still report as partially valid
            ratio.error = "Values not available for matched components"

        return ratio

    def _resolve_component_value(
        self,
        component_def: Any,
        matched_lookup: Dict[str, ComponentMatch],
    ) -> Dict[str, Any]:
        """
        Resolve a component definition to its numeric value.

        Handles both simple (string) and complex (list) component definitions.

        Simple: 'current_assets'
        Complex: ['current_assets', '-inventory'] means current_assets - inventory

        Args:
            component_def: Component definition (string or list)
            matched_lookup: Matched components lookup

        Returns:
            Dict with 'value', 'formula', and 'error' keys
        """
        if isinstance(component_def, str):
            # Simple case: single component
            if component_def in matched_lookup:
                match = matched_lookup[component_def]
                return {
                    'value': match.value,
                    'formula': component_def,
                    'error': None,
                }
            else:
                return {
                    'value': None,
                    'formula': component_def,
                    'error': f"Component '{component_def}' not matched",
                }

        elif isinstance(component_def, list):
            # Complex case: multiple components with operators
            # Format: ['current_assets', '-inventory'] = current_assets - inventory
            total_value = None
            formula_parts = []
            missing_components = []

            for item in component_def:
                # Parse operator and component name
                if item.startswith('-'):
                    operator = -1
                    component_name = item[1:]
                    formula_parts.append(f"- {component_name}")
                elif item.startswith('+'):
                    operator = 1
                    component_name = item[1:]
                    formula_parts.append(f"+ {component_name}")
                else:
                    operator = 1
                    component_name = item
                    if formula_parts:
                        formula_parts.append(f"+ {component_name}")
                    else:
                        formula_parts.append(component_name)

                # Get component value
                if component_name in matched_lookup:
                    match = matched_lookup[component_name]
                    if match.value is not None:
                        if total_value is None:
                            total_value = 0.0
                        total_value += operator * match.value
                    else:
                        # Component matched but no value
                        missing_components.append(f"{component_name} (no value)")
                else:
                    # Component not matched
                    missing_components.append(f"{component_name} (not matched)")

            formula = ' '.join(formula_parts)

            if missing_components:
                return {
                    'value': total_value,  # May be partial
                    'formula': formula,
                    'error': f"Missing: {', '.join(missing_components)}",
                }

            return {
                'value': total_value,
                'formula': formula,
                'error': None,
            }

        else:
            return {
                'value': None,
                'formula': str(component_def),
                'error': f"Invalid component definition type: {type(component_def)}",
            }

    def _build_summary(
        self,
        component_matches: List[ComponentMatch],
        ratios: List[RatioResult],
    ) -> Dict[str, Any]:
        """Build analysis summary."""
        total_components = len(component_matches)
        matched_components = sum(1 for m in component_matches if m.matched)

        total_ratios = len(ratios)
        valid_ratios = sum(1 for r in ratios if r.valid)
        partial_ratios = sum(1 for r in ratios if r.error and 'not matched' not in (r.error or ''))

        return {
            'total_components': total_components,
            'matched_components': matched_components,
            'match_rate': matched_components / total_components if total_components > 0 else 0,
            'total_ratios': total_ratios,
            'valid_ratios': valid_ratios,
            'partial_ratios': partial_ratios,
        }

    def display_results(self, result: AnalysisResult) -> None:
        """
        Display analysis results to console.

        Args:
            result: Analysis result to display
        """
        print()
        print("=" * 70)
        print(f"  RATIO ANALYSIS: {result.company}")
        print(f"  {result.market.upper()} | {result.form} | {result.date}")
        print("=" * 70)

        # Component matches
        print("\n  COMPONENT MATCHING:")
        print("-" * 70)

        matched = [m for m in result.component_matches if m.matched]
        unmatched = [m for m in result.component_matches if not m.matched]

        if matched:
            print(f"\n  Matched ({len(matched)}):")
            for m in matched:
                conf = f"{m.confidence:.2f}" if m.confidence else "N/A"
                label = m.label[:35] if m.label else m.matched_concept[:35] if m.matched_concept else ''
                # Show value if available
                if m.value is not None:
                    value_str = f"{m.value:>15,.0f}"
                else:
                    value_str = f"{'[no value]':>15}"
                print(f"    [OK] {m.component_name:22s} -> {label:35s} {value_str} ({conf})")

        if unmatched:
            print(f"\n  Unmatched ({len(unmatched)}):")
            for m in unmatched[:10]:  # Show first 10
                print(f"    [--] {m.component_name}")
            if len(unmatched) > 10:
                print(f"    ... and {len(unmatched) - 10} more")

        # Ratios
        print("\n  FINANCIAL RATIOS:")
        print("-" * 70)

        for ratio in result.ratios:
            if ratio.valid:
                print(f"    [OK] {ratio.ratio_name:25s} = {ratio.value:10.4f}")
                # Show the actual values used
                num_str = f"{ratio.numerator_value:,.0f}" if ratio.numerator_value else "N/A"
                den_str = f"{ratio.denominator_value:,.0f}" if ratio.denominator_value else "N/A"
                print(f"         {ratio.formula}")
                print(f"         ({num_str} / {den_str})")
            elif ratio.error:
                # Show partial info even on error
                if ratio.numerator_value is not None or ratio.denominator_value is not None:
                    num_str = f"{ratio.numerator_value:,.0f}" if ratio.numerator_value else "[missing]"
                    den_str = f"{ratio.denominator_value:,.0f}" if ratio.denominator_value else "[missing]"
                    print(f"    [--] {ratio.ratio_name:25s} - {ratio.error}")
                    print(f"         Values: {num_str} / {den_str}")
                else:
                    print(f"    [--] {ratio.ratio_name:25s} - {ratio.error}")

        # Summary
        print("\n  SUMMARY:")
        print("-" * 70)
        s = result.summary
        print(f"    Components: {s.get('matched_components', 0)}/{s.get('total_components', 0)} matched "
              f"({s.get('match_rate', 0)*100:.1f}%)")
        print(f"    Ratios: {s.get('valid_ratios', 0)}/{s.get('total_ratios', 0)} calculated")

        print()
        print("=" * 70)


__all__ = ['RatioCalculator', 'ComponentMatch', 'RatioResult', 'AnalysisResult']
