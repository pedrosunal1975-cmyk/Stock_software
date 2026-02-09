# Path: mat_acc/loaders/parsed_reader.py
"""
Parsed Filing Reader for mat_acc

Reads and interprets parsed.json files from parser output.
Works with paths provided by ParsedDataLoader.

RESPONSIBILITY: Load and parse parsed.json files
into structured data for financial analysis.

This provides access to the full parsed XBRL filing data
including facts, contexts, units, and taxonomy references.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

from .parsed_data import ParsedFilingEntry


@dataclass
class ParsedFact:
    """
    A single fact from a parsed filing.

    Attributes:
        concept: Concept QName (e.g., 'us-gaap:Assets')
        value: Fact value
        unit: Unit reference
        decimals: Decimal precision
        context_ref: Context reference ID
        period_type: 'instant' or 'duration'
        period_start: Period start date
        period_end: Period end date or instant date
        dimensions: Dimensional qualifiers
        is_nil: Whether fact is nil
    """
    concept: str
    value: Any
    unit: Optional[str] = None
    decimals: Optional[int] = None
    context_ref: Optional[str] = None
    period_type: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    dimensions: dict = field(default_factory=dict)
    is_nil: bool = False


@dataclass
class ParsedContext:
    """
    A context from a parsed filing.

    Attributes:
        context_id: Context identifier
        entity: Entity identifier
        period_type: 'instant' or 'duration'
        period_start: Period start date
        period_end: Period end date or instant
        dimensions: Dimensional qualifiers
    """
    context_id: str
    entity: Optional[str] = None
    period_type: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    dimensions: dict = field(default_factory=dict)


@dataclass
class ParsedUnit:
    """
    A unit from a parsed filing.

    Attributes:
        unit_id: Unit identifier
        measure: Unit measure (e.g., 'iso4217:USD')
        numerator: Numerator for divide units
        denominator: Denominator for divide units
    """
    unit_id: str
    measure: Optional[str] = None
    numerator: Optional[str] = None
    denominator: Optional[str] = None


@dataclass
class ParsedFiling:
    """
    Complete parsed filing data.

    Attributes:
        filing_info: Filing metadata
        facts: List of all facts
        contexts: Dictionary of contexts by ID
        units: Dictionary of units by ID
        namespaces: Namespace declarations
        taxonomy_refs: Referenced taxonomy schemas
        document_type: Type of document (10-K, 10-Q, etc.)
        entity_name: Company name
        fiscal_year_end: Fiscal year end date
    """
    filing_info: dict = field(default_factory=dict)
    facts: list[ParsedFact] = field(default_factory=list)
    contexts: dict[str, ParsedContext] = field(default_factory=dict)
    units: dict[str, ParsedUnit] = field(default_factory=dict)
    namespaces: dict = field(default_factory=dict)
    taxonomy_refs: list[str] = field(default_factory=list)
    document_type: Optional[str] = None
    entity_name: Optional[str] = None
    fiscal_year_end: Optional[str] = None


class ParsedReader:
    """
    Reads and interprets parsed.json files.

    Uses paths from ParsedDataLoader to load actual content.
    Converts JSON structure into typed dataclasses for analysis.

    Example:
        loader = ParsedDataLoader(config)
        reader = ParsedReader()

        filings = loader.discover_all_parsed_filings()
        for entry in filings:
            parsed = reader.read_parsed_filing(entry)
            print(f"Facts: {len(parsed.facts)}")
    """

    def __init__(self):
        """Initialize parsed reader."""
        self.logger = logging.getLogger('input.parsed_reader')

    def read_parsed_filing(self, filing: ParsedFilingEntry) -> Optional[ParsedFiling]:
        """
        Read parsed.json file for a filing.

        Args:
            filing: ParsedFilingEntry from ParsedDataLoader

        Returns:
            ParsedFiling object or None if reading fails
        """
        self.logger.info(f"Reading parsed filing for {filing.company}/{filing.form}/{filing.date}")

        json_path = filing.available_files.get('json')
        if not json_path or not json_path.exists():
            self.logger.warning(f"No parsed.json found in {filing.filing_folder}")
            return None

        return self.read_from_path(json_path)

    def read_from_path(self, json_path: Path) -> Optional[ParsedFiling]:
        """
        Read parsed filing from a specific path.

        Args:
            json_path: Path to parsed.json file

        Returns:
            ParsedFiling object or None if reading fails
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return self._parse_filing_data(data)

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error in {json_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading {json_path}: {e}")
            return None

    def _parse_filing_data(self, data: dict) -> ParsedFiling:
        """
        Parse the parsed.json data structure.

        Handles TWO structure formats:
        1. New format: facts/contexts/units inside 'instance' key
        2. Legacy format: facts/contexts/units at top level
        """
        result = ParsedFiling()

        # Extract filing info / metadata
        result.filing_info = data.get('filing_info', data.get('metadata', {}))
        result.document_type = result.filing_info.get('document_type',
                               result.filing_info.get('form_type'))
        result.entity_name = result.filing_info.get('entity_name',
                             result.filing_info.get('company_name'))
        result.fiscal_year_end = result.filing_info.get('fiscal_year_end')

        # Determine data source: 'instance' key (new format) or top-level (legacy)
        # New parser format puts facts/contexts/units inside 'instance'
        instance = data.get('instance', {})
        if instance and 'facts' in instance:
            # NEW FORMAT: facts are inside instance
            source = instance
            self.logger.debug("Using 'instance' structure for facts/contexts/units")
        else:
            # LEGACY FORMAT: facts at top level
            source = data
            self.logger.debug("Using top-level structure for facts/contexts/units")

        # Extract namespaces (check both locations)
        result.namespaces = instance.get('namespaces', data.get('namespaces', {}))

        # Extract taxonomy references
        result.taxonomy_refs = data.get('taxonomy_refs',
                               data.get('schema_refs', []))

        # Parse contexts from source
        contexts_data = source.get('contexts', {})
        if isinstance(contexts_data, dict):
            for ctx_id, ctx_data in contexts_data.items():
                ctx = self._parse_context(ctx_id, ctx_data)
                if ctx:
                    result.contexts[ctx_id] = ctx
        elif isinstance(contexts_data, list):
            for ctx_data in contexts_data:
                ctx_id = ctx_data.get('id', ctx_data.get('context_id'))
                if ctx_id:
                    ctx = self._parse_context(ctx_id, ctx_data)
                    if ctx:
                        result.contexts[ctx_id] = ctx

        # Parse units from source
        units_data = source.get('units', {})
        if isinstance(units_data, dict):
            for unit_id, unit_data in units_data.items():
                unit = self._parse_unit(unit_id, unit_data)
                if unit:
                    result.units[unit_id] = unit
        elif isinstance(units_data, list):
            for unit_data in units_data:
                unit_id = unit_data.get('id', unit_data.get('unit_id'))
                if unit_id:
                    unit = self._parse_unit(unit_id, unit_data)
                    if unit:
                        result.units[unit_id] = unit

        # Parse facts from source
        facts_data = source.get('facts', [])
        for fact_data in facts_data:
            fact = self._parse_fact(fact_data)
            if fact:
                result.facts.append(fact)

        self.logger.info(
            f"Parsed filing: {len(result.facts)} facts, "
            f"{len(result.contexts)} contexts, {len(result.units)} units"
        )

        return result

    def _parse_context(self, ctx_id: str, data: dict) -> Optional[ParsedContext]:
        """Parse a single context."""
        try:
            # Handle period data
            period = data.get('period', {})
            period_type = None
            period_start = None
            period_end = None

            if 'instant' in period:
                period_type = 'instant'
                period_end = period['instant']
            elif 'startDate' in period or 'start_date' in period:
                period_type = 'duration'
                period_start = period.get('startDate', period.get('start_date'))
                period_end = period.get('endDate', period.get('end_date'))

            # Handle entity
            entity = data.get('entity', {})
            entity_id = entity.get('identifier', entity) if isinstance(entity, dict) else entity

            # Handle dimensions
            dimensions = data.get('dimensions', data.get('segment', {}))

            return ParsedContext(
                context_id=ctx_id,
                entity=entity_id,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                dimensions=dimensions
            )

        except Exception as e:
            self.logger.warning(f"Error parsing context {ctx_id}: {e}")
            return None

    def _parse_unit(self, unit_id: str, data: dict) -> Optional[ParsedUnit]:
        """Parse a single unit."""
        try:
            if isinstance(data, str):
                return ParsedUnit(unit_id=unit_id, measure=data)

            return ParsedUnit(
                unit_id=unit_id,
                measure=data.get('measure', data.get('measures', [None])[0] if isinstance(data.get('measures'), list) else None),
                numerator=data.get('numerator'),
                denominator=data.get('denominator')
            )

        except Exception as e:
            self.logger.warning(f"Error parsing unit {unit_id}: {e}")
            return None

    def _parse_fact(self, data: dict) -> Optional[ParsedFact]:
        """Parse a single fact."""
        try:
            concept = (
                data.get('concept') or
                data.get('name') or
                data.get('qname') or
                ''
            )

            value = data.get('value', data.get('fact_value'))

            return ParsedFact(
                concept=concept,
                value=value,
                unit=data.get('unit', data.get('unit_ref')),
                decimals=data.get('decimals'),
                context_ref=data.get('context_ref', data.get('contextRef')),
                period_type=data.get('period_type'),
                period_start=data.get('period_start', data.get('startDate')),
                period_end=data.get('period_end', data.get('endDate', data.get('instant'))),
                dimensions=data.get('dimensions', {}),
                is_nil=data.get('is_nil', data.get('isNil', False))
            )

        except Exception as e:
            self.logger.warning(f"Error parsing fact: {e}")
            return None

    def get_facts_by_concept(
        self,
        filing: ParsedFiling,
        concept_pattern: str
    ) -> list[ParsedFact]:
        """
        Find facts matching a concept pattern.

        Args:
            filing: ParsedFiling object
            concept_pattern: Substring to match in concept name

        Returns:
            List of matching facts
        """
        matching = []
        pattern_lower = concept_pattern.lower()

        for fact in filing.facts:
            if pattern_lower in fact.concept.lower():
                matching.append(fact)

        return matching

    def get_facts_for_period(
        self,
        filing: ParsedFiling,
        period_end: str
    ) -> list[ParsedFact]:
        """
        Get facts for a specific period end date.

        Args:
            filing: ParsedFiling object
            period_end: Period end date to filter by

        Returns:
            List of matching facts
        """
        matching = []

        for fact in filing.facts:
            if fact.period_end and period_end in fact.period_end:
                matching.append(fact)
            elif fact.context_ref:
                ctx = filing.contexts.get(fact.context_ref)
                if ctx and ctx.period_end and period_end in ctx.period_end:
                    matching.append(fact)

        return matching

    def get_numeric_facts(self, filing: ParsedFiling) -> list[ParsedFact]:
        """
        Get only numeric facts.

        Args:
            filing: ParsedFiling object

        Returns:
            List of numeric facts
        """
        numeric = []

        for fact in filing.facts:
            if fact.unit is not None and fact.value is not None:
                try:
                    float(str(fact.value).replace(',', ''))
                    numeric.append(fact)
                except (ValueError, TypeError):
                    pass

        return numeric

    def get_available_periods(self, filing: ParsedFiling) -> list[str]:
        """
        Get list of available reporting periods.

        Args:
            filing: ParsedFiling object

        Returns:
            List of period end dates
        """
        periods = set()

        for ctx in filing.contexts.values():
            if ctx.period_end:
                periods.add(ctx.period_end)

        return sorted(periods, reverse=True)


__all__ = [
    'ParsedReader',
    'ParsedFiling',
    'ParsedFact',
    'ParsedContext',
    'ParsedUnit',
]
