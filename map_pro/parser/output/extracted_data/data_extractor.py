# Path: xbrl_parser/output/extracted_data/data_extractor.py
"""
Data Extraction Utilities

Extract specific data from ParsedFiling into various formats (CSV, dict, lists).

This module provides utilities to extract facts, contexts, units, and other
XBRL data into structured formats suitable for analysis or export.
"""

import logging
import csv
from pathlib import Path
from datetime import date, datetime

from xbrl_parser.models.parsed_filing import ParsedFiling
from xbrl_parser.models.fact import Fact
from xbrl_parser.models.context import Context
from xbrl_parser.models.unit import Unit
from output.formats import CSV_FIELD_SIZE_LIMIT


class DataExtractor:
    """
    Extract data from ParsedFiling into structured formats.
    
    Provides methods to extract facts, contexts, units, and other data
    into dictionaries, lists, or CSV files for analysis.
    
    Example:
        extractor = DataExtractor()
        
        # Extract facts to list of dicts
        facts_data = extractor.extract_facts(filing)
        
        # Save facts to CSV
        extractor.save_facts_csv(filing, 'facts.csv')
        
        # Extract metadata
        metadata = extractor.extract_metadata(filing)
    """
    
    def __init__(self):
        """Initialize data extractor."""
        self.logger = logging.getLogger(__name__)
        
        # set CSV field size limit
        csv.field_size_limit(CSV_FIELD_SIZE_LIMIT)
    
    def extract_facts(self, filing: ParsedFiling) -> list[dict[str, any]]:
        """
        Extract facts to list of dictionaries.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of fact dictionaries
        """
        facts_data = []
        
        for fact in filing.instance.facts:
            fact_dict = {
                'concept': fact.concept,
                'value': fact.value,
                'context_ref': fact.context_ref,
                'unit_ref': fact.unit_ref,
                'decimals': fact.decimals,
                'precision': fact.precision,
                'fact_id': fact.id,
                'is_nil': fact.is_nil,
                'fact_type': fact.fact_type.value if fact.fact_type else None,
                'language': fact.language,
            }
            
            # Add context details if available
            if fact.context_ref and fact.context_ref in filing.instance.contexts:
                context = filing.instance.contexts[fact.context_ref]
                fact_dict.update(self._extract_context_details(context))
            
            # Add unit details - ALWAYS add field even if None
            fact_dict['unit_measures'] = None
            if fact.unit_ref and fact.unit_ref in filing.instance.units:
                unit = filing.instance.units[fact.unit_ref]
                fact_dict['unit_measures'] = ', '.join(unit.measures) if unit.measures else None
            
            facts_data.append(fact_dict)
        
        self.logger.debug(f"Extracted {len(facts_data)} facts")
        return facts_data
    
    def extract_contexts(self, filing: ParsedFiling) -> list[dict[str, any]]:
        """
        Extract contexts to list of dictionaries.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of context dictionaries
        """
        contexts_data = []
        
        for context_id, context in filing.instance.contexts.items():
            context_dict = {
                'context_id': context_id,
                'entity_scheme': context.entity.scheme,
                'entity_identifier': context.entity.value,
                'period_type': context.period.period_type.value.upper().upper(),
            }
            
            # Add period details
            if context.period.instant:
                context_dict['instant'] = str(context.period.instant)
            elif context.period.start_date and context.period.end_date:
                context_dict['start_date'] = str(context.period.start_date)
                context_dict['end_date'] = str(context.period.end_date)
            
            # Add dimensions if present
            if context.has_dimensions():
                dims = context.get_all_dimensions()
                context_dict['dimension_count'] = len(dims)
                context_dict['dimensions'] = ', '.join([
                    f"{d.dimension}={d.member}" for d in dims
                ])
            else:
                context_dict['dimension_count'] = 0
                context_dict['dimensions'] = None
            
            contexts_data.append(context_dict)
        
        self.logger.debug(f"Extracted {len(contexts_data)} contexts")
        return contexts_data
    
    def extract_units(self, filing: ParsedFiling) -> list[dict[str, any]]:
        """
        Extract units to list of dictionaries.
        
        Args:
            filing: Parsed filing
            
        Returns:
            list of unit dictionaries
        """
        units_data = []
        
        for unit_id, unit in filing.instance.units.items():
            unit_dict = {
                'unit_id': unit_id,
                'unit_type': unit.unit_type.value,
                'measures': ', '.join(unit.measures) if unit.measures else None,
            }
            
            # Add numerator/denominator for complex units
            if unit.numerator:
                unit_dict['numerator'] = ', '.join(unit.numerator)
            if unit.denominator:
                unit_dict['denominator'] = ', '.join(unit.denominator)
            
            units_data.append(unit_dict)
        
        self.logger.debug(f"Extracted {len(units_data)} units")
        return units_data
    
    def extract_metadata(self, filing: ParsedFiling) -> dict[str, any]:
        """
        Extract filing metadata.
        
        Args:
            filing: Parsed filing
            
        Returns:
            Metadata dictionary
        """
        metadata = filing.metadata
        
        return {
            'filing_id': metadata.filing_id,
            'document_type': metadata.document_type,
            'filing_date': str(metadata.filing_date) if metadata.filing_date else None,
            'period_end': str(metadata.period_end) if metadata.period_end else None,
            'entity_identifier': metadata.entity_identifier,
            'company_name': metadata.company_name,
            'market': metadata.market,
            'source_files_count': len(metadata.source_files),
            'fact_count': len(filing.instance.facts),
            'context_count': len(filing.instance.contexts),
            'unit_count': len(filing.instance.units),
            'error_count': len(filing.errors.errors),
            'quality_score': metadata.quality_score,
        }
    
    def save_facts_csv(
        self,
        filing: ParsedFiling,
        output_path: Path,
        include_context_details: bool = True
    ) -> None:
        """
        Save facts to CSV file.
        
        Args:
            filing: Parsed filing
            output_path: Output CSV file path
            include_context_details: Include context period details
        """
        facts_data = self.extract_facts(filing)
        
        if not facts_data:
            self.logger.warning("No facts to save")
            return
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get fieldnames from first fact
        fieldnames = list(facts_data[0].keys())
        
        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(facts_data)
        
        self.logger.info(f"Saved {len(facts_data)} facts to {output_path}")
    
    def save_contexts_csv(
        self,
        filing: ParsedFiling,
        output_path: Path
    ) -> None:
        """
        Save contexts to CSV file.
        
        Args:
            filing: Parsed filing
            output_path: Output CSV file path
        """
        contexts_data = self.extract_contexts(filing)
        
        if not contexts_data:
            self.logger.warning("No contexts to save")
            return
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        fieldnames = list(contexts_data[0].keys())
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(contexts_data)
        
        self.logger.info(f"Saved {len(contexts_data)} contexts to {output_path}")
    
    def save_units_csv(
        self,
        filing: ParsedFiling,
        output_path: Path
    ) -> None:
        """
        Save units to CSV file.
        
        Args:
            filing: Parsed filing
            output_path: Output CSV file path
        """
        units_data = self.extract_units(filing)
        
        if not units_data:
            self.logger.warning("No units to save")
            return
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        fieldnames = list(units_data[0].keys())
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(units_data)
        
        self.logger.info(f"Saved {len(units_data)} units to {output_path}")
    
    def _extract_context_details(self, context: Context) -> dict[str, any]:
        """
        Extract context details for fact enrichment.
        
        Args:
            context: Context object
            
        Returns:
            Dictionary of context details
        """
        details = {
            'entity_identifier': context.entity.value,
            'period_type': context.period.period_type.value.upper().upper(),
            'period_instant': None,
            'period_start': None,
            'period_end': None,
        }
        
        if context.period.instant:
            details['period_instant'] = str(context.period.instant)
        elif context.period.start_date and context.period.end_date:
            details['period_start'] = str(context.period.start_date)
            details['period_end'] = str(context.period.end_date)
        
        return details


__all__ = ['DataExtractor']