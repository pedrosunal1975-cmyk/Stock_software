# Path: output/statement_exporter.py
"""
Statement Exporter with Network Classification Support

Exports statements organized by classification category.
Delegates to format-specific exporters for JSON, CSV, and Excel.
"""

import logging
from pathlib import Path

from ..loaders.parser_output import ParsedFiling
from ..mapping.statement.models import StatementSet, Statement
from ..output.catalog_generator import CatalogGenerator
from ..output.json_exporter import JSONExporter
from ..output.csv_exporter import CSVExporter
from ..output.excel_exporter import ExcelExporter
from ..mapping.constants import NetworkCategory


class StatementSetExporter:
    """
    Export statement sets with classification-based organization.
    """
    
    def __init__(self):
        self.logger = logging.getLogger('output.statement_exporter')
        self.catalog_generator = CatalogGenerator()
        
        # Initialize format-specific exporters
        self.json_exporter = JSONExporter(self._get_attr)
        self.csv_exporter = CSVExporter()
        self.excel_exporter = ExcelExporter()
    
    @staticmethod
    def _get_attr(data, attr, default=None):
        """
        Universal attribute getter - handles ANY data format.
        
        Supports:
        - Dictionary: data['attr'] or data.get('attr')
        - Object: data.attr or getattr(data, 'attr')
        - Nested: data.parent.child or data['parent']['child']
        - None/missing: returns default
        
        Args:
            data: Data in any format (dict, object, etc.)
            attr: Attribute name (supports dot notation for nested)
            default: Default value if not found
            
        Returns:
            Attribute value or default
        """
        if data is None:
            return default
        
        # Handle dot notation for nested attributes
        if '.' in attr:
            parts = attr.split('.')
            current = data
            for part in parts:
                current = StatementSetExporter._get_attr(current, part, None)
                if current is None:
                    return default
            return current
        
        # Try dictionary access first
        if isinstance(data, dict):
            return data.get(attr, default)
        
        # Try object attribute access
        if hasattr(data, attr):
            value = getattr(data, attr, default)
            # If we got back the default from getattr, that means attribute doesn't exist
            if value is default and not hasattr(data, attr):
                return default
            return value
        
        # Try dictionary-style access on object
        try:
            return data[attr]
        except (KeyError, TypeError, AttributeError):
            pass
        
        # Nothing worked, return default
        return default
    
    def export_all(
        self,
        statement_set: StatementSet,
        parsed_filing: ParsedFiling,
        output_folder: Path
    ) -> dict[str, any]:
        """
        Export statements in all formats with classification.
        """
        self.logger.info(f"Exporting statements with classification to: {output_folder}")
        
        # Create format directories
        json_folder = output_folder / 'json'
        csv_folder = output_folder / 'csv'
        excel_folder = output_folder / 'excel'
        
        json_folder.mkdir(parents=True, exist_ok=True)
        csv_folder.mkdir(parents=True, exist_ok=True)
        excel_folder.mkdir(parents=True, exist_ok=True)
        
        # Export to each format
        json_paths = self.export_json(statement_set, parsed_filing, json_folder)
        csv_paths = self.export_csv(statement_set, parsed_filing, csv_folder)
        excel_paths = self.export_excel(statement_set, parsed_filing, excel_folder)
        
        return {
            'json': json_paths,
            'csv': csv_paths,
            'excel': excel_paths
        }
    
    def export_json(
        self,
        statement_set: StatementSet,
        parsed_filing: ParsedFiling,
        output_folder: Path,
        pretty: bool = True
    ) -> list[Path]:
        """
        Export statements to JSON format.
        
        Delegates to JSONExporter for actual export logic.
        Also generates catalog file.
        
        Args:
            statement_set: Set of statements to export
            parsed_filing: Parsed filing data
            output_folder: Base output folder
            pretty: Whether to format JSON with indentation
            
        Returns:
            List of created JSON file paths
        """
        # Delegate to JSON exporter
        json_paths = self.json_exporter.export(
            statement_set,
            parsed_filing,
            output_folder,
            filename_creator=self._create_filename,
            pretty=pretty
        )
        
        # Generate catalog
        self._export_catalog(statement_set, parsed_filing, output_folder)
        
        return json_paths
    
    def _export_catalog(
        self,
        statement_set: StatementSet,
        parsed_filing: ParsedFiling,
        output_folder: Path
    ):
        """Generate and export catalog."""
        classifications = []
        filenames = {}
        
        for statement in statement_set.statements:
            classification_data = statement.metadata.get('classification', {})
            category = classification_data.get('category', NetworkCategory.UNKNOWN)
            
            # Determine folder
            if category == NetworkCategory.CORE_STATEMENT:
                folder = 'core_statements'
            elif category == NetworkCategory.DETAIL:
                folder = 'details'
            else:
                folder = 'other'
            
            filename = self._create_filename(statement)
            filenames[statement.role_uri] = f"{folder}/{filename}.json"
            
            # Reconstruct classification for catalog
            from ..mapping.network_classifier import NetworkClassification
            classifications.append(
                NetworkClassification(
                    category=classification_data.get('category', NetworkCategory.UNKNOWN),
                    statement_type=classification_data.get('statement_type', 'OTHER'),
                    is_primary=classification_data.get('is_primary', False),
                    confidence=classification_data.get('confidence', 'LOW'),
                    matched_patterns=classification_data.get('matched_patterns', []),
                    structural_signals=classification_data.get('structural_signals', {}),  # NEW: Required field
                    role_uri=statement.role_uri,
                    role_definition=statement.role_definition
                )
            )
        
        # Extract filing info flexibly
        entity_name = (
            self._get_attr(parsed_filing, 'entity_name') or
            self._get_attr(parsed_filing.raw_data, 'entity_name') or
            self._get_attr(parsed_filing.raw_data.get('instance', {}).get('entity', {}), 'name') or
            'Unknown'
        )
        
        filing_type = self._get_attr(parsed_filing.characteristics, 'filing_type', 'UNKNOWN')
        
        period_end = (
            self._get_attr(parsed_filing.characteristics, 'period_end') or
            self._get_attr(parsed_filing.raw_data, 'period_end') or
            self._get_attr(parsed_filing.raw_data.get('metadata', {}), 'period_end')
        )
        
        filing_info = {
            'entity_name': entity_name,
            'filing_type': filing_type,
            'period_end': period_end
        }
        
        catalog = self.catalog_generator.generate(
            classifications=classifications,
            filenames=filenames,
            filing_info=filing_info
        )
        
        self.catalog_generator.save_catalog(
            catalog,
            output_folder / '_catalog.json'
        )
    
    def _create_filename(self, statement: Statement) -> str:
        """
        Create unique filename from role definition or role URI.
        
        Uses role_definition if available, falls back to role_uri.
        Ensures uniqueness to prevent overwriting.
        
        Args:
            statement: Statement object
            
        Returns:
            Sanitized filename (without extension)
        """
        # Try role_definition first
        if statement.role_definition:
            filename = statement.role_definition.lower()
            filename = filename.replace(' - ', '_')
            filename = filename.replace(' ', '_')
            filename = filename.replace('(', '').replace(')', '')
            filename = filename.replace('[', '').replace(']', '')
            filename = filename.replace('/', '_').replace('\\', '_')
            filename = filename[:100]  # Limit length
        else:
            # Fallback: Use last part of role_uri
            role_uri = statement.role_uri or 'unknown'
            # Extract last part after final slash
            filename = role_uri.split('/')[-1] if '/' in role_uri else role_uri
            filename = filename.lower()
            filename = filename.replace('-', '_')
        
        # Ensure we have something
        if not filename or filename == '':
            filename = 'statement'
        
        # Pure XBRL approach - no hardcoded prefixes
        # Filename comes directly from company's role_definition
        return filename[:150]  # Final length limit
    
    def export_csv(self, statement_set, parsed_filing, output_folder):
        """
        Export statements to CSV format.
        
        Delegates to CSVExporter for actual export logic.
        
        Args:
            statement_set: Set of statements to export
            parsed_filing: Parsed filing data
            output_folder: Base output folder path
            
        Returns:
            List of created CSV file paths
        """
        return self.csv_exporter.export(
            statement_set,
            parsed_filing,
            output_folder,
            filename_creator=self._create_filename
        )
    
    def export_excel(self, statement_set, parsed_filing, output_folder):
        """
        Export statements to Excel format.
        
        Delegates to ExcelExporter for actual export logic.
        
        Args:
            statement_set: Set of statements to export
            parsed_filing: Parsed filing data
            output_folder: Base output folder path
            
        Returns:
            List of created Excel file paths
        """
        return self.excel_exporter.export(
            statement_set,
            parsed_filing,
            output_folder,
            filename_creator=self._create_filename
        )