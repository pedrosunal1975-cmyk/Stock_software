# Path: loaders/parser_output.py
"""
Parser Output Deserializer - NAMESPACE-AWARE VERSION

Uses namespace map from parsed.json to resolve prefixes to URIs, then detects taxonomy.
NO HARDCODED prefix assumptions - reads from actual namespace declarations.
"""

import logging
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path

from ..loaders.json_structure_reader import JSONStructureReader
from ..loaders.filing_analyzer import FilingAnalyzer
from ..loaders.constants import (
    NAMESPACE_CONTAINER_PATTERNS,
)


@dataclass
class FilingCharacteristics:
    """Discovered characteristics of filing."""
    filing_type: str = "UNKNOWN"
    market: str = "unknown"
    primary_taxonomy: str = "unknown"
    taxonomy_versions: dict[str, str] = field(default_factory=dict)
    company_extensions: list[str] = field(default_factory=list)
    fact_count: int = 0
    context_count: int = 0
    unit_count: int = 0
    parsing_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    has_dimensions: bool = False
    has_footnotes: bool = False
    dimension_count: int = 0
    statement_types: list[str] = field(default_factory=list)
    has_classical_statements: bool = False
    has_nonclassical_content: bool = False


@dataclass
class ParsedFiling:
    """Deserialized parsed filing with discovered structure."""
    characteristics: FilingCharacteristics
    raw_data: dict[str, any]
    discovered_structure: any
    extension_concepts: list[dict[str, any]] = field(default_factory=list)
    source_file: Optional[Path] = None
    
    @property
    def facts(self) -> list['Fact']:
        """Access facts from raw_data, converted to Fact objects."""
        from ..mapping.models.fact import Fact
        
        instance = self.raw_data.get('instance', {})
        fact_dicts = instance.get('facts', [])
        
        # Convert dict facts to Fact objects
        fact_objects = []
        for fact_dict in fact_dicts:
            fact_obj = Fact(
                name=fact_dict.get('concept', ''),
                value=fact_dict.get('value'),
                context_ref=fact_dict.get('context_ref', ''),
                unit_ref=fact_dict.get('unit_ref'),
                decimals=fact_dict.get('decimals'),
                precision=fact_dict.get('precision'),
                id=fact_dict.get('id'),
                footnote=fact_dict.get('footnote'),
                metadata={
                    k: v for k, v in fact_dict.items()
                    if k not in ['concept', 'value', 'context_ref', 'unit_ref', 
                               'decimals', 'precision', 'id', 'footnote']
                }
            )
            fact_objects.append(fact_obj)
        
        return fact_objects

    @property
    def contexts(self):
        """Access contexts - adaptive to dict or list structure, converted to Context objects."""
        from ..mapping.models.context import Context
        from datetime import datetime
        
        instance = self.raw_data.get('instance', {})
        contexts_raw = instance.get('contexts', {})
        
        # Helper to parse date strings
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return datetime.fromisoformat(str(date_str).replace('Z', '+00:00')).date()
            except:
                return None
        
        # Convert to list if dict
        if isinstance(contexts_raw, dict):
            contexts_list = contexts_raw.values()
        else:
            contexts_list = contexts_raw
        
        # Convert dicts to Context objects
        context_objects = []
        for ctx_dict in contexts_list:
            if not isinstance(ctx_dict, dict):
                continue
                
            # Extract entity
            entity_data = ctx_dict.get('entity', {})
            if isinstance(entity_data, dict):
                entity = entity_data.get('identifier', '')
            else:
                entity = str(entity_data)
            
            # Extract period info
            period = ctx_dict.get('period', {})
            period_type = period.get('type', 'instant')
            instant = parse_date(period.get('instant'))
            start_date = parse_date(period.get('start_date') or period.get('startDate'))
            end_date = parse_date(period.get('end_date') or period.get('endDate'))
            
            context_obj = Context(
                id=ctx_dict.get('id', ''),
                entity=entity,
                period_type=period_type,
                instant=instant,
                start_date=start_date,
                end_date=end_date,
                segment=ctx_dict.get('segment', {}),
                scenario=ctx_dict.get('scenario', {}),
                metadata={
                    k: v for k, v in ctx_dict.items()
                    if k not in ['id', 'entity', 'period', 'segment', 'scenario']
                }
            )
            context_objects.append(context_obj)
        
        return context_objects

    @property
    def units(self):
        """Access units - adaptive to dict or list structure, converted to Unit objects."""
        from ..mapping.models.unit import Unit
        
        instance = self.raw_data.get('instance', {})
        units_raw = instance.get('units', {})
        
        # Convert to list if dict
        if isinstance(units_raw, dict):
            units_list = units_raw.values()
        else:
            units_list = units_raw
        
        # Convert dicts to Unit objects
        unit_objects = []
        for unit_dict in units_list:
            if not isinstance(unit_dict, dict):
                continue
            
            unit_obj = Unit(
                id=unit_dict.get('id', ''),
                measures=unit_dict.get('measures', []),
                numerator=unit_dict.get('numerator', []),
                denominator=unit_dict.get('denominator', []),
                metadata={
                    k: v for k, v in unit_dict.items()
                    if k not in ['id', 'measures', 'numerator', 'denominator']
                }
            )
            unit_objects.append(unit_obj)
        
        return unit_objects


class ParserOutputDeserializer:
    """
    Namespace-aware deserializer.
    
    Uses namespace map to resolve prefixes (ns0, us-gaap, etc.) to URIs,
    then detects taxonomy from URIs - NO hardcoded prefix expectations.
    """
    
    def __init__(self):
        """Initialize deserializer."""
        self.logger = logging.getLogger('input.parser_output')
        self.structure_reader = JSONStructureReader()
        self.analyzer = FilingAnalyzer(self.structure_reader)
        self.logger.info("ParserOutputDeserializer initialized")
    
    def deserialize(
        self,
        parsed_data: dict[str, any],
        source_file: Path
    ) -> ParsedFiling:
        """
        Deserialize by discovering structure and using namespace map.
        
        Args:
            parsed_data: Raw JSON data
            source_file: Path to source file
            
        Returns:
            ParsedFiling with characteristics
        """
        self.logger.info(f"Deserializing: {source_file}")
        
        # Step 1: Discover complete structure
        structure = self.structure_reader.discover_structure(parsed_data)
        
        # Step 2: Extract namespace map
        namespace_map = self._extract_namespace_map(parsed_data, structure)
        
        # Step 3: Extract characteristics using analyzer
        characteristics = self.analyzer.extract_characteristics(
            parsed_data, structure, namespace_map
        )
        
        # Step 4: Extract extensions using analyzer
        extensions = self.analyzer.extract_extensions(
            parsed_data, structure, namespace_map
        )
        
        filing = ParsedFiling(
            characteristics=characteristics,
            raw_data=parsed_data,
            discovered_structure=structure,
            extension_concepts=extensions,
            source_file=source_file
        )
        
        self.logger.info(
            f"Deserialized: {characteristics.filing_type} | "
            f"{characteristics.primary_taxonomy} | "
            f"{characteristics.fact_count} facts | "
            f"{len(extensions)} extensions"
        )
        
        return filing
    
    def _extract_namespace_map(
        self,
        data: dict[str, any],
        structure: any
    ) -> dict[str, str]:
        """
        Extract namespace prefix → URI map from JSON using patterns from constants.
        
        Returns:
            Dictionary mapping prefixes to URIs
        """
        # Try configured namespace paths
        for path in NAMESPACE_CONTAINER_PATTERNS:
            namespaces = self.structure_reader.get_value_by_path(data, path, {})
            if namespaces:
                self.logger.debug(f"Found {len(namespaces)} namespace declarations at {path}")
                return namespaces
        
        # Fallback: search for any path containing 'namespace'
        for path in structure.all_paths:
            if 'namespace' in path.lower():
                namespaces = self.structure_reader.get_value_by_path(data, path, {})
                if namespaces and isinstance(namespaces, dict):
                    self.logger.debug(f"Found {len(namespaces)} namespace declarations at {path}")
                    return namespaces
        
        self.logger.warning("No namespace map found in JSON")
        return {}


__all__ = ['ParserOutputDeserializer', 'ParsedFiling', 'FilingCharacteristics']