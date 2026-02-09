# Path: output/csv_exporter.py
"""
CSV Exporter

Exports financial statements to CSV format with hierarchical folder structure.
"""

import logging
import csv
import json
from pathlib import Path
from typing import Callable

from ..loaders.parser_output import ParsedFiling
from ..mapping.statement.models import Statement, StatementSet
from ..mapping.constants import NetworkCategory


class CSVExporter:
    """
    Exports statements to CSV format.
    
    Creates folder structure:
    - core_statements/
    - details/
    - other/
    
    Each statement becomes a CSV file with columns:
    concept, value, context_ref, unit_ref, decimals, level, parent_concept, order
    """
    
    def __init__(self):
        """Initialize CSV exporter."""
        self.logger = logging.getLogger('output.csv_exporter')
    
    def export(
        self,
        statement_set: StatementSet,
        parsed_filing: ParsedFiling,
        output_folder: Path,
        filename_creator: Callable
    ) -> list[str]:
        """
        Export statements to CSV with folder structure.
        
        Args:
            statement_set: Set of statements to export
            parsed_filing: Parsed filing data
            output_folder: Base output folder
            filename_creator: Function to create filenames
            
        Returns:
            List of created CSV file paths
        """
        csv_paths = []
        
        # Create folder structure
        core_folder = output_folder / 'core_statements'
        details_folder = output_folder / 'details'
        other_folder = output_folder / 'other'
        
        core_folder.mkdir(parents=True, exist_ok=True)
        details_folder.mkdir(parents=True, exist_ok=True)
        other_folder.mkdir(parents=True, exist_ok=True)
        
        # Export each statement to CSV
        for statement in statement_set.statements:
            classification = statement.metadata.get('classification', {})
            category = classification.get('category', NetworkCategory.UNKNOWN)
            
            # Determine folder
            if category == NetworkCategory.CORE_STATEMENT:
                folder = core_folder
            elif category == NetworkCategory.DETAIL:
                folder = details_folder
            else:
                folder = other_folder
            
            # Create filename and export
            filename = filename_creator(statement)
            csv_path = self._export_file(statement, folder, filename)
            csv_paths.append(str(csv_path))
        
        self.logger.info(f"Exported {len(csv_paths)} CSV files")
        return csv_paths
    
    def _export_file(
        self,
        statement: Statement,
        output_folder: Path,
        filename: str
    ) -> Path:
        """
        Export single statement to CSV file.
        
        Args:
            statement: Statement to export
            output_folder: Folder to save to
            filename: Filename (without extension)
            
        Returns:
            Path to created file
        """
        csv_path = output_folder / f"{filename}.csv"
        
        # Write CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header - includes all fact attributes for complete export
            writer.writerow([
                'concept', 'value', 'display_value', 'formatted_value',
                'context_ref', 'unit_ref', 'decimals', 'scaling_factor',
                'level', 'parent_concept', 'order',
                # Period information (CRITICAL for calculation verification)
                'period_type', 'period_start', 'period_end',
                # Dimensional qualifiers (CRITICAL for grouping verification)
                'dimensions',
                # iXBRL-specific attributes
                'sign', 'scale', 'format', 'is_nil', 'fact_id'
            ])

            # Facts
            for fact in statement.facts:
                # Serialize dimensions dict as JSON string for CSV
                dimensions_str = json.dumps(fact.dimensions) if fact.dimensions else ''

                writer.writerow([
                    fact.concept,
                    fact.value,
                    fact.display_value or '',
                    fact.formatted_value or '',
                    fact.context_ref,
                    fact.unit_ref or '',
                    fact.decimals or '',
                    fact.scaling_factor or '',
                    fact.level,
                    fact.parent_concept or '',
                    fact.order or '',
                    # Period information
                    fact.period_type or '',
                    fact.period_start or '',
                    fact.period_end or '',
                    # Dimensional qualifiers
                    dimensions_str,
                    # iXBRL-specific attributes
                    fact.sign or '',
                    fact.scale or '',
                    fact.format or '',
                    'true' if fact.is_nil else '',
                    fact.fact_id or ''
                ])

        return csv_path