# Path: output/json_exporter.py
"""
JSON Exporter

Exports financial statements to JSON format with hierarchical folder structure.
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Callable

from ..loaders.parser_output import ParsedFiling
from ..mapping.statement.models import Statement, StatementSet
from ..mapping.constants import NetworkCategory


class JSONExporter:
    """
    Exports statements to JSON format.
    
    Creates folder structure:
    - core_statements/
    - details/
    - other/
    
    Each statement becomes a JSON file with:
    - Role URI and definition
    - Classification metadata
    - Hierarchy structure
    - Complete fact list
    """
    
    def __init__(self, get_attr_func: Callable):
        """
        Initialize JSON exporter.
        
        Args:
            get_attr_func: Universal attribute getter function
        """
        self.logger = logging.getLogger('output.json_exporter')
        self._get_attr = get_attr_func
    
    def export(
        self,
        statement_set: StatementSet,
        parsed_filing: ParsedFiling,
        output_folder: Path,
        filename_creator: Callable,
        pretty: bool = True
    ) -> list[Path]:
        """
        Export statements to JSON with folder structure.
        
        Args:
            statement_set: Set of statements to export
            parsed_filing: Parsed filing data
            output_folder: Base output folder
            filename_creator: Function to create filenames
            pretty: Whether to format JSON with indentation
            
        Returns:
            List of created JSON file paths
        """
        # Track filenames to ensure uniqueness
        filename_counters = {}
        
        def get_unique_filename(base_filename: str) -> str:
            """Ensure filename is unique by adding counter if needed."""
            if base_filename not in filename_counters:
                filename_counters[base_filename] = 0
                return base_filename
            else:
                filename_counters[base_filename] += 1
                return f"{base_filename}_{filename_counters[base_filename]}"
        
        # Organize statements by classification
        core_statements = []
        detail_statements = []
        other_statements = []
        
        for statement in statement_set.statements:
            classification = statement.metadata.get('classification', {})
            category = classification.get('category', NetworkCategory.UNKNOWN)
            
            if category == NetworkCategory.CORE_STATEMENT:
                core_statements.append(statement)
            elif category == NetworkCategory.DETAIL:
                detail_statements.append(statement)
            else:
                other_statements.append(statement)
        
        self.logger.info(
            f"Classified statements: {len(core_statements)} core, "
            f"{len(detail_statements)} details, {len(other_statements)} other"
        )
        
        # Create folders
        core_folder = output_folder / 'core_statements'
        details_folder = output_folder / 'details'
        other_folder = output_folder / 'other'
        
        core_folder.mkdir(exist_ok=True)
        details_folder.mkdir(exist_ok=True)
        other_folder.mkdir(exist_ok=True)
        
        # Export core statements
        core_paths = []
        for statement in core_statements:
            base_filename = filename_creator(statement)
            filename = get_unique_filename(base_filename)
            path = self._export_file(statement, core_folder, filename)
            core_paths.append(path)
        
        # Export detail statements
        detail_paths = []
        for statement in detail_statements:
            base_filename = filename_creator(statement)
            filename = get_unique_filename(base_filename)
            path = self._export_file(statement, details_folder, filename)
            detail_paths.append(path)
        
        # Export other statements
        other_paths = []
        for statement in other_statements:
            base_filename = filename_creator(statement)
            filename = get_unique_filename(base_filename)
            path = self._export_file(statement, other_folder, filename)
            other_paths.append(path)
        
        # Export aggregated core statements
        if core_statements:
            self.export_aggregated_core(
                core_statements,
                parsed_filing,
                output_folder / 'MAIN_FINANCIAL_STATEMENTS.json'
            )
        
        all_paths = core_paths + detail_paths + other_paths
        self.logger.info(
            f"Exported {len(core_paths)} core, {len(detail_paths)} details, "
            f"{len(other_paths)} other JSON files"
        )
        
        return all_paths
    
    def _export_file(
        self,
        statement: Statement,
        output_folder: Path,
        filename: str
    ) -> Path:
        """
        Export single statement to JSON file.
        
        Args:
            statement: Statement to export
            output_folder: Folder to save to
            filename: Filename (without extension)
            
        Returns:
            Path to created file
        """
        output_path = output_folder / f"{filename}.json"

        # Log dimension statistics for this statement
        facts_with_dims = sum(1 for f in statement.facts if f.dimensions)
        if facts_with_dims > 0:
            self.logger.info(
                f"Exporting {statement.role_uri.split('/')[-1]}: "
                f"{facts_with_dims}/{len(statement.facts)} facts have dimensions"
            )

        data = {
            'role_uri': statement.role_uri,
            'role_definition': statement.role_definition,
            'statement_type': statement.statement_type,
            'classification': statement.metadata.get('classification', {}),
            'hierarchy': statement.hierarchy,
            'facts': [
                {
                    'concept': f.concept,
                    'value': str(f.value),
                    'context_ref': f.context_ref,
                    'unit_ref': f.unit_ref,
                    'decimals': f.decimals,
                    'level': f.level,
                    'order': f.order,
                    'parent_concept': f.parent_concept,
                    'metadata': f.metadata,
                    # Period information (CRITICAL for calculation verification)
                    'period_type': f.period_type,
                    'period_start': f.period_start,
                    'period_end': f.period_end,
                    # Dimensional qualifiers (CRITICAL for grouping verification)
                    'dimensions': f.dimensions,
                    # iXBRL-specific attributes (from inline XBRL instance)
                    'sign': f.sign,
                    'scale': f.scale,
                    'format': f.format,
                    'is_nil': f.is_nil,
                    'fact_id': f.fact_id,
                    # Calculated values for verification
                    'display_value': f.display_value,
                    'formatted_value': f.formatted_value,
                    'scaling_factor': f.scaling_factor
                }
                for f in statement.facts
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def export_aggregated_core(
        self,
        core_statements: list[Statement],
        parsed_filing: ParsedFiling,
        output_path: Path
    ):
        """
        Export all core statements in one file.
        
        Args:
            core_statements: List of core statements
            parsed_filing: Parsed filing data
            output_path: Path to save aggregated file
        """
        # Extract metadata flexibly
        filing_date = (
            self._get_attr(parsed_filing.characteristics, 'filing_date') or
            self._get_attr(parsed_filing.raw_data, 'filing_date') or
            None
        )
        
        entity_name = (
            self._get_attr(parsed_filing, 'entity_name') or
            self._get_attr(parsed_filing.raw_data, 'entity_name') or
            'Unknown'
        )
        
        filing_type = self._get_attr(parsed_filing.characteristics, 'filing_type', 'UNKNOWN')
        
        period_end = (
            self._get_attr(parsed_filing.characteristics, 'period_end') or
            self._get_attr(parsed_filing.raw_data, 'period_end')
        )
        
        aggregated = {
            'generated_at': datetime.now().isoformat(),
            'filing_info': {
                'entity_name': entity_name,
                'filing_type': filing_type,
                'period_end': str(period_end) if period_end else None,
                'filing_date': str(filing_date) if filing_date else None,
            },
            'core_statement_count': len(core_statements),
            'statements': []
        }
        
        # Add each core statement (log dimension stats)
        total_facts_with_dims = 0
        total_facts = 0
        for statement in core_statements:
            facts_with_dims = sum(1 for f in statement.facts if f.dimensions)
            total_facts_with_dims += facts_with_dims
            total_facts += len(statement.facts)

            classification = statement.metadata.get('classification', {})
            
            aggregated['statements'].append({
                'role_uri': statement.role_uri,
                'role_definition': statement.role_definition,
                'statement_type': classification.get('statement_type', 'OTHER'),
                'category': classification.get('category'),
                'is_primary': classification.get('is_primary'),
                'confidence': classification.get('confidence'),
                'total_facts': len(statement.facts),
                'hierarchy': statement.hierarchy,
                'facts': [
                    {
                        'concept': f.concept,
                        'value': str(f.value),
                        'context_ref': f.context_ref,
                        'unit_ref': f.unit_ref,
                        'decimals': f.decimals,
                        'level': f.level,
                        'order': f.order,
                        'parent_concept': f.parent_concept,
                        # Period information (CRITICAL for calculation verification)
                        'period_type': f.period_type,
                        'period_start': f.period_start,
                        'period_end': f.period_end,
                        # Dimensional qualifiers (CRITICAL for grouping verification)
                        'dimensions': f.dimensions,
                        # iXBRL-specific attributes (from inline XBRL instance)
                        'sign': f.sign,
                        'scale': f.scale,
                        'format': f.format,
                        'is_nil': f.is_nil,
                        'fact_id': f.fact_id,
                        # Calculated values for verification
                        'display_value': f.display_value,
                        'formatted_value': f.formatted_value,
                        'scaling_factor': f.scaling_factor
                    }
                    for f in statement.facts
                ]
            })
        
        # Log dimension statistics for aggregated export
        self.logger.info(
            f"Aggregated export: {total_facts_with_dims}/{total_facts} facts have dimensions"
        )

        # Sample a fact with dimensions for verification
        for statement in core_statements:
            for f in statement.facts:
                if f.dimensions:
                    self.logger.info(
                        f"Sample dimensional fact: concept={f.concept}, "
                        f"dims={f.dimensions}"
                    )
                    break
            else:
                continue
            break

        # Save aggregated file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(aggregated, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Exported aggregated core statements to: {output_path}")