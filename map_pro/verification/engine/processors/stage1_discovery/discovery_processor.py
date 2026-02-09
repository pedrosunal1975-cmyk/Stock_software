# Path: verification/engine/processors/stage1_discovery/discovery_processor.py
"""
Stage 1: Discovery Processor

Scans XBRL files to discover and extract raw data:
- Facts from mapped statements (via MappedReader)
- Calculations from XBRL linkbase (via XBRLReader)
- Sign attributes from iXBRL instance document

RESPONSIBILITY: Find and extract data. NO transformation or validation.
All data is passed as-is to Stage 2 for normalization.

DATA SOURCES (uses existing verification/ loaders):
- MappedReader: Reads facts from mapped statement JSON files
- XBRLReader: Reads calculation relationships from _cal.xml
- XBRLFilingsLoader: Finds XBRL filing directories

OUTPUT: DiscoveryResult with all raw discovered elements
"""

import json
import logging
from pathlib import Path
from typing import Optional, Union

# Import existing loaders from verification module
from verification.loaders.mapped_data import MappedDataLoader, MappedFilingEntry
from verification.loaders.mapped_reader import MappedReader, MappedStatements, StatementFact
from verification.loaders.xbrl_filings import XBRLFilingsLoader
from verification.loaders.xbrl_reader import XBRLReader, CalculationNetwork, CalculationArc

from ..pipeline_data import (
    DiscoveryResult,
    DiscoveredFact,
    DiscoveredContext,
    DiscoveredUnit,
    DiscoveredCalculation,
)


class DiscoveryProcessor:
    """
    Stage 1: Discovers raw data from XBRL filing.

    Uses existing verification module loaders:
    - MappedReader for facts from mapped statements
    - XBRLReader for calculation relationships from linkbase

    Usage:
        processor = DiscoveryProcessor()

        # Discovery from MappedFilingEntry (preferred)
        result = processor.discover_from_filing(filing_entry)

        # Discovery from path (for testing with parsed.json)
        result = processor.discover(filing_path)

        # Result contains all raw discovered data
        print(f"Found {len(result.facts)} facts")
        print(f"Found {len(result.calculations)} calculations")
    """

    def __init__(self, config=None):
        """
        Initialize discovery processor.

        Args:
            config: Optional ConfigLoader instance for loaders
        """
        self.logger = logging.getLogger('processors.stage1.discovery')
        self.config = config

        # Initialize loaders
        self._mapped_reader = MappedReader()
        self._xbrl_reader = XBRLReader(config)
        self._xbrl_loader = XBRLFilingsLoader(config) if config else None

    def discover(self, source: Union[Path, str, MappedFilingEntry]) -> DiscoveryResult:
        """
        Discover all data from a filing.

        Args:
            source: Path to filing/parsed.json, or MappedFilingEntry

        Returns:
            DiscoveryResult with all discovered elements
        """
        # Handle MappedFilingEntry - route to production method
        if isinstance(source, MappedFilingEntry):
            return self.discover_from_filing(source)

        # Handle path
        filing_path = Path(source)
        self.logger.info(f"Stage 1: Discovering data from {filing_path}")

        result = DiscoveryResult(filing_path=filing_path)

        # Try parsed.json first (for testing/fixture compatibility)
        parsed_json = self._find_parsed_json(filing_path)
        if parsed_json:
            self._discover_from_parsed_json(parsed_json, result)
        else:
            result.errors.append(f"No parsed.json found in {filing_path}")
            self.logger.warning(f"No parsed.json found in {filing_path}")

        # Build statistics
        result.stats = self._build_stats(result)

        self.logger.info(
            f"Stage 1 complete: {result.stats['facts_discovered']} facts, "
            f"{result.stats['contexts_discovered']} contexts, "
            f"{result.stats['calculations_discovered']} calculations"
        )

        return result

    def discover_from_filing(self, filing: MappedFilingEntry) -> DiscoveryResult:
        """
        Discover data from a MappedFilingEntry using existing loaders.

        This is the primary method for production use.
        Uses EXACTLY the same approach as verification/ module:
        - MappedReader.read_statements(filing) for facts
        - XBRLReader for calculation relationships from linkbase

        Args:
            filing: MappedFilingEntry from MappedDataLoader

        Returns:
            DiscoveryResult with all discovered elements
        """
        filing_id = f"{filing.market}/{filing.company}/{filing.form}/{filing.date}"
        self.logger.info(f"Stage 1: Discovering data for {filing_id}")

        result = DiscoveryResult(filing_path=filing.filing_folder)

        try:
            # Step 1: Read facts from mapped statements (SAME as verification/ module)
            # This is EXACTLY what verification/engine/coordinator.py does
            self.logger.info(f"Reading mapped statements")
            statements = self._mapped_reader.read_statements(filing)

            if statements and statements.statements:
                self._extract_facts_from_statements(statements, result)
                self._extract_contexts_from_statements(statements, result)
                self.logger.info(f"Found {len(result.facts)} facts from mapped statements")
            else:
                self.logger.warning(f"No statements found for {filing_id}")
                result.warnings.append(f"No statements found for {filing_id}")

            # Step 2: Read calculations from XBRL linkbase
            if self._xbrl_loader:
                self.logger.info(f"Reading XBRL calculation linkbase")
                xbrl_path = self._xbrl_loader.find_filing_for_company(
                    filing.market,
                    filing.company,
                    filing.form,
                    filing.date
                )

                if xbrl_path:
                    calc_networks = self._xbrl_reader.read_calculation_linkbase(xbrl_path)
                    self._extract_calculations_from_networks(calc_networks, result)
                    self.logger.info(f"Found {len(result.calculations)} calculations")
                else:
                    result.warnings.append(f"No XBRL filing found for {filing_id}")
            else:
                result.warnings.append("XBRLFilingsLoader not initialized - no calculations loaded")

        except Exception as e:
            result.errors.append(f"Error discovering from filing: {e}")
            self.logger.error(f"Discovery error: {e}")

        # Build statistics
        result.stats = self._build_stats(result)

        self.logger.info(
            f"Stage 1 complete: {result.stats['facts_discovered']} facts, "
            f"{result.stats['calculations_discovered']} calculations"
        )

        return result

    def _extract_facts_from_statements(
        self,
        statements: MappedStatements,
        result: DiscoveryResult
    ) -> None:
        """Extract facts from mapped statements."""
        for statement in statements.statements:
            for fact in statement.facts:
                discovered = DiscoveredFact(
                    concept=fact.concept,
                    value=fact.value,
                    context_id=fact.context_id or '',
                    unit_ref=fact.unit,
                    decimals=fact.decimals,
                    is_nil=fact.value is None,
                    sign=None,  # Will be extracted from instance document
                    source_file=statement.source_file or '',
                )
                result.facts.append(discovered)

    def _extract_contexts_from_statements(
        self,
        statements: MappedStatements,
        result: DiscoveryResult
    ) -> None:
        """Extract contexts from mapped statements."""
        # Build unique contexts from facts
        seen_contexts = set()
        for statement in statements.statements:
            for fact in statement.facts:
                ctx_id = fact.context_id
                if ctx_id and ctx_id not in seen_contexts:
                    seen_contexts.add(ctx_id)

                    # Determine period type
                    if fact.period_start and fact.period_end:
                        period_type = 'duration'
                    elif fact.period_end:
                        period_type = 'instant'
                    else:
                        period_type = 'unknown'

                    result.contexts.append(DiscoveredContext(
                        context_id=ctx_id,
                        period_type=period_type,
                        start_date=fact.period_start,
                        end_date=fact.period_end,
                        instant_date=fact.period_end if period_type == 'instant' else None,
                        entity_id='',
                        dimensions=fact.dimensions or {},
                    ))

    def _extract_calculations_from_networks(
        self,
        networks: list[CalculationNetwork],
        result: DiscoveryResult
    ) -> None:
        """Extract calculations from XBRL calculation networks."""
        for network in networks:
            for arc in network.arcs:
                result.calculations.append(DiscoveredCalculation(
                    parent_concept=arc.parent_concept,
                    child_concept=arc.child_concept,
                    weight=arc.weight,
                    order=arc.order,
                    role=network.role,
                    source='company',
                ))

    def _build_stats(self, result: DiscoveryResult) -> dict:
        """Build statistics dictionary."""
        return {
            'facts_discovered': len(result.facts),
            'contexts_discovered': len(result.contexts),
            'units_discovered': len(result.units),
            'calculations_discovered': len(result.calculations),
            'errors_count': len(result.errors),
            'warnings_count': len(result.warnings),
        }

    # =========================================================================
    # PARSED.JSON METHODS (for testing/fixture compatibility)
    # =========================================================================

    def _find_parsed_json(self, filing_path: Path) -> Optional[Path]:
        """Find parsed.json in filing directory."""
        if filing_path.is_file() and filing_path.name == 'parsed.json':
            return filing_path

        if filing_path.is_dir():
            parsed = filing_path / 'parsed.json'
            if parsed.exists():
                return parsed

        return None

    def _discover_from_parsed_json(self, parsed_json: Path, result: DiscoveryResult) -> None:
        """Extract data from parsed.json (for testing)."""
        try:
            with open(parsed_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            result.instance_file = parsed_json

            # Extract metadata
            metadata = data.get('metadata', {})
            result.entry_point = metadata.get('entry_point')
            result.taxonomy_refs = metadata.get('taxonomy_references', [])

            # Extract namespaces
            result.namespaces = data.get('namespaces', {})

            # Discover facts
            self._discover_facts_from_json(data, result)

            # Discover contexts
            self._discover_contexts_from_json(data, result)

            # Discover units
            self._discover_units_from_json(data, result)

            # Discover calculations
            self._discover_calculations_from_json(data, result)

        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid JSON in {parsed_json}: {e}")
        except Exception as e:
            result.errors.append(f"Error reading {parsed_json}: {e}")

    def _discover_facts_from_json(self, data: dict, result: DiscoveryResult) -> None:
        """Discover facts from parsed.json data."""
        facts_data = data.get('facts', [])

        if isinstance(facts_data, list):
            for fact in facts_data:
                discovered = self._parse_fact_entry(fact)
                if discovered:
                    result.facts.append(discovered)

        elif isinstance(facts_data, dict):
            for concept, fact_list in facts_data.items():
                if isinstance(fact_list, list):
                    for fact in fact_list:
                        fact['concept'] = concept
                        discovered = self._parse_fact_entry(fact)
                        if discovered:
                            result.facts.append(discovered)

        # Also check statements for facts
        statements = data.get('statements', {})
        for stmt_name, stmt_data in statements.items():
            if isinstance(stmt_data, dict):
                line_items = stmt_data.get('line_items', [])
                for item in line_items:
                    facts = self._extract_facts_from_line_item(item, stmt_name)
                    result.facts.extend(facts)

    def _parse_fact_entry(self, fact: dict) -> Optional[DiscoveredFact]:
        """Parse a single fact entry."""
        concept = fact.get('concept') or fact.get('name')
        if not concept:
            return None

        return DiscoveredFact(
            concept=concept,
            value=fact.get('value'),
            context_id=fact.get('context_id') or fact.get('contextRef', ''),
            unit_ref=fact.get('unit_ref') or fact.get('unitRef'),
            decimals=self._parse_decimals(fact.get('decimals')),
            is_nil=fact.get('is_nil', False) or fact.get('nil', False),
            sign=fact.get('sign'),
            format=fact.get('format'),
            source_file=str(fact.get('source', '')),
        )

    def _extract_facts_from_line_item(self, item: dict, statement: str) -> list[DiscoveredFact]:
        """Extract facts from statement line item."""
        facts = []
        concept = item.get('concept') or item.get('name')
        if not concept:
            return facts

        values = item.get('values', {})
        if isinstance(values, dict):
            for context_id, value_data in values.items():
                if isinstance(value_data, dict):
                    facts.append(DiscoveredFact(
                        concept=concept,
                        value=value_data.get('value'),
                        context_id=context_id,
                        unit_ref=value_data.get('unit'),
                        decimals=self._parse_decimals(value_data.get('decimals')),
                        is_nil=value_data.get('is_nil', False),
                        sign=value_data.get('sign'),
                    ))
                else:
                    facts.append(DiscoveredFact(
                        concept=concept,
                        value=value_data,
                        context_id=context_id,
                    ))

        return facts

    def _discover_contexts_from_json(self, data: dict, result: DiscoveryResult) -> None:
        """Discover contexts from parsed.json data."""
        contexts_data = data.get('contexts', {})

        if isinstance(contexts_data, dict):
            for ctx_id, ctx_data in contexts_data.items():
                if isinstance(ctx_data, dict):
                    discovered = DiscoveredContext(
                        context_id=ctx_id,
                        period_type=ctx_data.get('period_type', ''),
                        start_date=ctx_data.get('start_date'),
                        end_date=ctx_data.get('end_date'),
                        instant_date=ctx_data.get('instant'),
                        entity_id=ctx_data.get('entity', ''),
                        dimensions=ctx_data.get('dimensions', {}),
                    )
                    result.contexts.append(discovered)

    def _discover_units_from_json(self, data: dict, result: DiscoveryResult) -> None:
        """Discover units from parsed.json data."""
        units_data = data.get('units', {})

        if isinstance(units_data, dict):
            for unit_id, unit_data in units_data.items():
                if isinstance(unit_data, dict):
                    discovered = DiscoveredUnit(
                        unit_id=unit_id,
                        measure=unit_data.get('measure', ''),
                        numerator=unit_data.get('numerator'),
                        denominator=unit_data.get('denominator'),
                    )
                elif isinstance(unit_data, str):
                    discovered = DiscoveredUnit(
                        unit_id=unit_id,
                        measure=unit_data,
                    )
                else:
                    continue
                result.units.append(discovered)

    def _discover_calculations_from_json(self, data: dict, result: DiscoveryResult) -> None:
        """Discover calculations from parsed.json data."""
        calc_data = data.get('calculations', {})

        if isinstance(calc_data, dict):
            for role, role_data in calc_data.items():
                if isinstance(role_data, dict):
                    trees = role_data.get('trees', [])
                    for tree in trees:
                        self._extract_calculation_tree(tree, role, 'company', result)

        taxonomy_calc = data.get('taxonomy_calculations', {})
        if isinstance(taxonomy_calc, dict):
            for role, role_data in taxonomy_calc.items():
                if isinstance(role_data, dict):
                    trees = role_data.get('trees', [])
                    for tree in trees:
                        self._extract_calculation_tree(tree, role, 'taxonomy', result)

    def _extract_calculation_tree(
        self,
        tree: dict,
        role: str,
        source: str,
        result: DiscoveryResult
    ) -> None:
        """Extract calculation relationships from a tree structure."""
        parent = tree.get('concept') or tree.get('parent')
        if not parent:
            return

        children = tree.get('children', [])
        for child in children:
            if isinstance(child, dict):
                child_concept = child.get('concept') or child.get('name')
                weight = child.get('weight', 1.0)
                order = child.get('order', 0.0)

                if child_concept:
                    result.calculations.append(DiscoveredCalculation(
                        parent_concept=parent,
                        child_concept=child_concept,
                        weight=float(weight),
                        order=float(order),
                        role=role,
                        source=source,
                    ))

                if child.get('children'):
                    self._extract_calculation_tree(child, role, source, result)

    def _parse_decimals(self, value) -> Optional[int]:
        """Parse decimals value."""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            if value.upper() == 'INF':
                return None
            try:
                return int(value)
            except ValueError:
                return None
        return None


__all__ = ['DiscoveryProcessor']
