# Path: verification/engine/checks_v2/processors/stage2_preparation/preparation_processor.py
"""
Stage 2: Preparation Processor

Transforms discovered data into verified, normalized form ready for verification:
- Normalizes concept names using naming tools
- Classifies contexts using context tools
- Parses and validates fact values using fact tools
- Groups facts by context (C-Equal)
- Parses sign corrections using sign tools
- Detects duplicates using duplicate handler

RESPONSIBILITY: Transform and organize. NO verification logic.
All data is prepared for Stage 3 to verify.

TOOLS USED:
- naming/: Normalizer for concept names
- context/: ContextClassifier, ContextGrouper for context handling
- period/: PeriodExtractor for period normalization
- fact/: ValueParser for value parsing, DuplicateHandler
- sign/: SignParser for sign correction extraction

OUTPUT: PreparationResult with normalized, grouped data
"""

import logging
from typing import Optional

from ..pipeline_data import (
    DiscoveryResult,
    PreparationResult,
    PreparedFact,
    PreparedContext,
    PreparedCalculation,
    FactGroup,
)

# Import tools
from ...tools.naming import Normalizer
from ...tools.context import ContextClassifier, ContextGrouper
from ...tools.period import PeriodExtractor
from ...tools.fact import ValueParser, DuplicateHandler
from ...tools.sign import SignParser


class PreparationProcessor:
    """
    Stage 2: Prepares discovered data for verification.

    Transforms raw discovered data using specialized tools:
    1. Normalize concept names (multiple strategies available)
    2. Classify contexts as dimensional or default
    3. Parse fact values to numeric form
    4. Group facts by context (C-Equal principle)
    5. Extract sign corrections from iXBRL
    6. Detect duplicate facts

    Tools are configurable - different strategies can be selected
    for different filing types.

    Usage:
        processor = PreparationProcessor()

        # Use default tools
        result = processor.prepare(discovery_result)

        # Or configure tools
        processor.set_naming_strategy('local_name')
        result = processor.prepare(discovery_result)
    """

    def __init__(self):
        self.logger = logging.getLogger('processors.stage2.preparation')

        # Initialize tools with defaults
        self._normalizer = Normalizer()
        self._classifier = ContextClassifier()
        self._period_extractor = PeriodExtractor()
        self._value_parser = ValueParser()
        self._duplicate_handler = DuplicateHandler()
        self._sign_parser = SignParser()

        # Configuration
        self._naming_strategy = 'canonical'
        self._context_strategy = 'default'

    def set_naming_strategy(self, strategy: str) -> None:
        """
        Set the naming normalization strategy.

        Options: 'canonical', 'local_name', 'full_qualified', 'auto'
        """
        self._naming_strategy = strategy
        self.logger.info(f"Naming strategy set to: {strategy}")

    def set_context_strategy(self, strategy: str) -> None:
        """
        Set the context classification strategy.

        Options: 'default', 'strict'
        """
        self._context_strategy = strategy
        self._classifier.set_strategy(strategy)
        self.logger.info(f"Context strategy set to: {strategy}")

    def prepare(self, discovery: DiscoveryResult) -> PreparationResult:
        """
        Prepare discovered data for verification.

        Args:
            discovery: DiscoveryResult from Stage 1

        Returns:
            PreparationResult ready for Stage 3
        """
        self.logger.info(f"Stage 2: Preparing {len(discovery.facts)} facts")

        result = PreparationResult(discovery=discovery)

        # Step 1: Prepare contexts first (needed for fact classification)
        self._prepare_contexts(discovery, result)

        # Step 2: Parse sign corrections from discovered facts
        self._extract_sign_corrections(discovery, result)

        # Step 3: Prepare and normalize facts
        self._prepare_facts(discovery, result)

        # Step 4: Group facts by context (C-Equal)
        self._group_facts(result)

        # Step 5: Build cross-context lookup
        self._build_concept_lookup(result)

        # Step 6: Detect duplicates
        self._detect_duplicates(result)

        # Step 7: Prepare calculations
        self._prepare_calculations(discovery, result)

        # Build statistics
        result.stats = {
            'facts_prepared': len(result.facts),
            'contexts_prepared': len(result.contexts),
            'fact_groups': len(result.fact_groups),
            'calculations_prepared': len(result.calculations),
            'sign_corrections': len(result.sign_corrections),
            'duplicates_found': len(result.duplicates),
            'errors_count': len(result.errors),
            'warnings_count': len(result.warnings),
        }

        self.logger.info(
            f"Stage 2 complete: {result.stats['facts_prepared']} facts in "
            f"{result.stats['fact_groups']} groups, "
            f"{result.stats['calculations_prepared']} calculations"
        )

        return result

    def _prepare_contexts(self, discovery: DiscoveryResult, result: PreparationResult) -> None:
        """Prepare contexts using context tools."""
        for ctx in discovery.contexts:
            # Classify as dimensional or default
            is_dimensional = self._classifier.is_dimensional(ctx.context_id)

            # Determine period type from discovered context
            period_type = ctx.period_type or 'unknown'

            # Build period_key from actual dates (not from context_id string)
            period_key = self._build_period_key(ctx)

            # Extract year from dates
            year = self._extract_year_from_context(ctx)

            prepared = PreparedContext(
                context_id=ctx.context_id,
                period_type=period_type,
                period_key=period_key,
                year=year,
                is_dimensional=is_dimensional or bool(ctx.dimensions),
                dimensions=ctx.dimensions,
            )

            result.contexts[ctx.context_id] = prepared

    def _build_period_key(self, ctx) -> str:
        """
        Build period_key from actual context dates.

        Period key format:
        - Duration: d_YYYY-MM-DD_YYYY-MM-DD (start_to_end)
        - Instant: i_YYYY-MM-DD (as of date)
        - Year only: y_YYYY (fallback)
        - Context ID: ctx.context_id (last resort fallback)

        Args:
            ctx: DiscoveredContext with date fields

        Returns:
            Normalized period key string
        """
        if ctx.period_type == 'duration':
            if ctx.start_date and ctx.end_date:
                return f"d_{ctx.start_date}_{ctx.end_date}"
        elif ctx.period_type == 'instant':
            date = ctx.instant_date or ctx.end_date
            if date:
                return f"i_{date}"

        # Fallback: try to extract year from any available date
        year = self._extract_year_from_context(ctx)
        if year:
            return f"y_{year}"

        # Last resort: use context_id
        return ctx.context_id

    def _extract_year_from_context(self, ctx) -> Optional[int]:
        """Extract year from context dates."""
        # Try end_date first (most common)
        for date_str in [ctx.end_date, ctx.instant_date, ctx.start_date]:
            if date_str:
                try:
                    # Parse YYYY-MM-DD or YYYY format
                    year_str = date_str[:4]
                    return int(year_str)
                except (ValueError, IndexError):
                    continue
        return None

    def _extract_sign_corrections(self, discovery: DiscoveryResult, result: PreparationResult) -> None:
        """Extract sign corrections from facts with sign attributes."""
        for fact in discovery.facts:
            if fact.sign:
                # Parse sign attribute
                correction = self._sign_parser.parse_sign_attribute(fact.sign)
                if correction != 1:
                    # Normalize concept for lookup
                    normalized = self._normalizer.normalize(
                        fact.concept, strategy=self._naming_strategy
                    )
                    key = (normalized, fact.context_id)
                    result.sign_corrections[key] = correction

                    self.logger.debug(
                        f"Sign correction for {fact.concept} in {fact.context_id}: {correction}"
                    )

    def _prepare_facts(self, discovery: DiscoveryResult, result: PreparationResult) -> None:
        """Prepare facts using fact and naming tools."""
        for fact in discovery.facts:
            # Skip nil facts
            if fact.is_nil:
                continue

            # Parse value
            value = self._value_parser.parse_value(fact.value)
            if value is None:
                # Skip unparseable values
                continue

            # Normalize concept name
            normalized = self._normalizer.normalize(
                fact.concept, strategy=self._naming_strategy
            )

            # Register in normalizer for bidirectional lookup
            self._normalizer.register(fact.concept, 'discovery')

            # Get context classification
            ctx_info = result.contexts.get(fact.context_id)
            is_dimensional = ctx_info.is_dimensional if ctx_info else False

            # Get sign correction
            sign_key = (normalized, fact.context_id)
            sign_correction = result.sign_corrections.get(sign_key, 1)

            prepared = PreparedFact(
                concept=normalized,
                original_concept=fact.concept,
                value=value,
                context_id=fact.context_id,
                unit=fact.unit_ref,
                decimals=fact.decimals,
                sign_correction=sign_correction,
                is_dimensional=is_dimensional,
            )

            result.facts.append(prepared)

    def _group_facts(self, result: PreparationResult) -> None:
        """Group facts by context using C-Equal principle."""
        grouper = ContextGrouper()

        for fact in result.facts:
            grouper.add_fact(
                concept=fact.concept,
                value=fact.value,
                context_id=fact.context_id,
                unit=fact.unit,
                decimals=fact.decimals,
                original_concept=fact.original_concept,
            )

        # Convert grouper output to FactGroup structures
        for context_id in grouper.get_contexts():
            ctx_group = grouper.get_context(context_id)
            if ctx_group:
                ctx_info = result.contexts.get(context_id)

                fact_group = FactGroup(
                    context_id=context_id,
                    period_key=ctx_info.period_key if ctx_info else context_id,
                    is_dimensional=ctx_info.is_dimensional if ctx_info else False,
                    facts={},
                )

                # Copy facts from grouper to fact_group
                for concept in ctx_group.facts.keys():
                    # Find matching prepared fact
                    for pf in result.facts:
                        if pf.concept == concept and pf.context_id == context_id:
                            fact_group.facts[concept] = pf
                            break

                result.fact_groups[context_id] = fact_group

    def _build_concept_lookup(self, result: PreparationResult) -> None:
        """
        Build cross-context concept lookup for dimensional fallback.

        The tuple includes all data needed for proper fact matching:
        (context_id, value, unit, decimals, is_dimensional, period_key)

        By including period_key from the actual filing data, FactFinder can
        compare periods directly without parsing context_id strings.
        This eliminates hardcoded pattern matching for period detection.
        """
        for fact in result.facts:
            if fact.concept not in result.all_facts_by_concept:
                result.all_facts_by_concept[fact.concept] = []

            # Get context info for dimensional status and period_key
            ctx_info = result.contexts.get(fact.context_id)
            is_dimensional = ctx_info.is_dimensional if ctx_info else False
            period_key = ctx_info.period_key if ctx_info else ''

            result.all_facts_by_concept[fact.concept].append((
                fact.context_id,
                fact.value,
                fact.unit,
                fact.decimals,
                is_dimensional,
                period_key,  # Added: actual period from filing data
            ))

    def _detect_duplicates(self, result: PreparationResult) -> None:
        """Detect duplicate facts using duplicate handler."""
        # Build fact entries for duplicate detection
        from ...tools.fact import FactEntry

        entries_by_concept = {}
        for fact in result.facts:
            if fact.concept not in entries_by_concept:
                entries_by_concept[fact.concept] = []

            # Get context info for dimensional status
            ctx_info = result.contexts.get(fact.context_id)
            is_dimensional = ctx_info.is_dimensional if ctx_info else False
            dimensions = ctx_info.dimensions if ctx_info else None

            entries_by_concept[fact.concept].append(FactEntry(
                concept=fact.concept,
                original_concept=fact.original_concept,
                value=fact.value,
                unit=fact.unit,
                decimals=fact.decimals,
                context_id=fact.context_id,
                is_dimensional=is_dimensional,
                dimensions=dimensions,
            ))

        # Check each concept for duplicates
        for concept, entries in entries_by_concept.items():
            if len(entries) > 1:
                # Group by context to find true duplicates
                by_context = {}
                for entry in entries:
                    if entry.context_id not in by_context:
                        by_context[entry.context_id] = []
                    by_context[entry.context_id].append(entry)

                for context_id, ctx_entries in by_context.items():
                    if len(ctx_entries) > 1:
                        # Pass context_id for diagnostic info
                        info = self._duplicate_handler.analyze(ctx_entries, context_id)
                        if info.has_duplicates():
                            key = f"{concept}:{context_id}"
                            result.duplicates[key] = info

    def _prepare_calculations(self, discovery: DiscoveryResult, result: PreparationResult) -> None:
        """Prepare calculation trees."""
        # Group calculations by parent
        calc_trees = {}

        for calc in discovery.calculations:
            # Normalize parent
            parent_norm = self._normalizer.normalize(
                calc.parent_concept, strategy=self._naming_strategy
            )

            key = (parent_norm, calc.role, calc.source)
            if key not in calc_trees:
                calc_trees[key] = {
                    'parent': parent_norm,
                    'original_parent': calc.parent_concept,
                    'children': [],
                    'role': calc.role,
                    'source': calc.source,
                }

            # Normalize child
            child_norm = self._normalizer.normalize(
                calc.child_concept, strategy=self._naming_strategy
            )

            calc_trees[key]['children'].append((child_norm, calc.weight))

        # Convert to PreparedCalculation
        for key, tree in calc_trees.items():
            result.calculations.append(PreparedCalculation(
                parent_concept=tree['parent'],
                original_parent=tree['original_parent'],
                children=tree['children'],
                role=tree['role'],
                source=tree['source'],
            ))


__all__ = ['PreparationProcessor']
