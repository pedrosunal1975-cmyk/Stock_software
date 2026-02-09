# Path: mapping/orchestrator.py
"""
Mapping Orchestrator - Refactored

Coordinates the mapping workflow.
Delegates to specialized modules for clean separation of concerns.
"""

import logging
import json
import re
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..core.config_loader import ConfigLoader
from ..loaders.parser_output import ParserOutputDeserializer
from ..loaders.linkbase_locator import LinkbaseLocator
from ..loaders.xbrl_filings import XBRLFilingsLoader
from ..mapping.statement import StatementBuilder
from ..mapping.filing_extractor import FilingCharacteristicsExtractor
from ..mapping.output_manager import OutputManager
from ..output.statement_exporter import StatementSetExporter
from ..mapping.constants import (
    FILINGS_SUBDIRECTORY,
    PARSED_FOLDER_DELIMITER,
    IGNORE_DIRECTORY_PATTERNS,
    DEBUG_SEPARATOR,
)


def normalize_company_name(name: str) -> str:
    """
    Normalize company name for comparison.

    Handles variations like:
    - ELI_LILLY_&_Co vs Eli_Lilly_And_Company
    - CATERPILLAR_INC vs Caterpillar_Inc

    Returns lowercase alphanumeric-only version.
    """
    # Convert to lowercase
    normalized = name.lower()
    # Replace common variations
    normalized = normalized.replace('&', 'and')
    normalized = normalized.replace('_and_', '_')
    normalized = normalized.replace(' and ', ' ')
    # Remove non-alphanumeric (keep only letters and numbers)
    normalized = re.sub(r'[^a-z0-9]', '', normalized)
    return normalized


class MappingOrchestrator:
    """
    Orchestrates the extraction and mapping workflow.

    Workflow:
    1. Load parsed filing
    2. Extract filing characteristics
    3. Discover linkbases
    4. Build statements
    5. Create output structure
    6. Export to multiple formats
    """

    _logging_configured = False  # Class-level flag to configure logging once

    def __init__(self, config=None):
        """
        Initialize orchestrator.

        Args:
            config: Optional config (deprecated, uses ConfigLoader internally)
        """
        self.config = ConfigLoader()

        # Configure logging on first instantiation
        if not MappingOrchestrator._logging_configured:
            self._configure_logging()
            MappingOrchestrator._logging_configured = True

        self.logger = logging.getLogger('mapping.orchestrator')

        # Initialize components
        self.deserializer = ParserOutputDeserializer()
        self.xbrl_loader = XBRLFilingsLoader()
        self.linkbase_locator = LinkbaseLocator(self.xbrl_loader)
        self.statement_builder = StatementBuilder()
        self.statement_exporter = StatementSetExporter()

        # Initialize new modules
        self.filing_extractor = FilingCharacteristicsExtractor()
        self.output_manager = OutputManager(self.config.get('output_mapped_dir'))

        self.logger.info("MappingOrchestrator initialized (refactored)")

    def _configure_logging(self) -> None:
        """Configure IPO-based logging with file handlers."""
        from mapper.core.logger.ipo_logging import setup_ipo_logging

        log_dir = self.config.get('log_dir')
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)

            setup_ipo_logging(
                log_dir=log_dir,
                log_level=self.config.get('log_level', 'INFO'),
                console_output=True
            )
        else:
            # No log directory configured - console only
            import sys
            root_logger = logging.getLogger()
            root_logger.handlers.clear()
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            root_logger.addHandler(console_handler)
    
    def extract_and_export(self, parsed_json_path: Path) -> dict[str, any]:
        """
        Run complete extraction workflow.
        
        Args:
            parsed_json_path: Path to parsed.json file
            
        Returns:
            Results dictionary
        """
        start_time = datetime.now()
        
        # Step 1: Load parsed filing
        self.logger.info("Step 1: Loading parsed filing")
        with open(parsed_json_path, 'r') as f:
            parsed_data = json.load(f)
        parsed_filing = self.deserializer.deserialize(parsed_data, parsed_json_path)
        
        # Step 2: Extract filing characteristics
        self.logger.info("Step 2: Extracting filing characteristics")
        characteristics = self.filing_extractor.extract(parsed_filing)
        
        # Override entity_name with folder name if extraction failed
        # Extract company from path: .../company/form/date/parsed.json
        parts = parsed_json_path.parts
        if len(parts) >= 4:
            company_from_path = parts[-4]  # Company directory name
            
            # If extractor returned default/unknown, use folder name instead
            if characteristics.get('entity_name') in [None, 'unknown', 'Unknown_Company', '']:
                characteristics['entity_name'] = company_from_path
                self.logger.info(f"Using company name from folder: {company_from_path}")
        
        # DEBUG: Log what we extracted
        self.logger.warning(DEBUG_SEPARATOR)
        self.logger.warning("DEBUG: Extracted characteristics:")
        self.logger.warning(f"  entity_name: {characteristics.get('entity_name')}")
        self.logger.warning(f"  filing_type: {characteristics.get('filing_type')}")
        self.logger.warning(f"  period_end: {characteristics.get('period_end')}")
        self.logger.warning(f"  filing_date: {characteristics.get('filing_date')}")
        self.logger.warning(DEBUG_SEPARATOR)
        
        self.logger.info(
            f"Filing: {characteristics['entity_name']} - {characteristics['filing_type']} - "
            f"Period: {characteristics.get('period_end', 'unknown')}"
        )
        
        # Step 3: Find XBRL filing and discover linkbases
        self.logger.info("Step 3: Discovering linkbases")
        xbrl_filing_path = self._find_xbrl_filing(parsed_json_path)
        
        if not xbrl_filing_path:
            raise FileNotFoundError(f"No XBRL filing found for {parsed_json_path}")
        
        linkbase_set = self.linkbase_locator.discover_linkbases(str(xbrl_filing_path))
        self.logger.info(f"Discovered {len(linkbase_set.presentation_networks)} presentation networks")
        
        # Step 4: Build statements (pass XBRL path for direct dimension extraction)
        self.logger.info("Step 4: Building statements")
        statement_set = self.statement_builder.build_statements(
            linkbase_set, parsed_filing, xbrl_filing_path=xbrl_filing_path
        )
        self.logger.info(
            f"Built {len(statement_set.statements)} statements with "
            f"{sum(len(s.facts) for s in statement_set.statements)} fact placements"
        )
        
        # Step 5: Create output structure
        self.logger.info("Step 5: Creating output structure")
        output_folder = self.output_manager.create_output_structure(characteristics)
        
        # Step 6: Export statements
        self.logger.info("Step 6: Exporting statements")
        export_paths = self._export_statements(statement_set, parsed_filing, output_folder)
        
        # Calculate timing
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Build result
        result = {
            'export_paths': export_paths,
            'statistics': {
                'total_statements': len(statement_set.statements),
                'total_fact_placements': sum(len(s.facts) for s in statement_set.statements),
                'processing_time_seconds': elapsed
            },
            'filing_info': characteristics,
            'output_folder': str(output_folder)
        }
        
        # Log summary
        self._log_summary(result, elapsed)
        self.logger.info(f"Extraction complete in {elapsed:.2f}s")
        
        return result
    
    def _find_xbrl_filing(self, parsed_json_path: Path) -> Optional[Path]:
        """
        Find corresponding XBRL filing for a parsed filing.

        Extracts company name from parsed folder path structure.
        Expected path: .../company/form/date/parsed.json

        Uses flexible company name matching to handle variations like:
        - ELI_LILLY_&_Co vs Eli_Lilly_And_Company
        - Different capitalization and special characters

        Args:
            parsed_json_path: Path to parsed.json

        Returns:
            Path to XBRL filing directory, or None if not found
        """
        # Extract company/form/date from path structure
        # Path structure: .../company/form/date/parsed.json
        parts = parsed_json_path.parts
        if len(parts) < 4:
            self.logger.error(f"Invalid path structure: {parsed_json_path}")
            return None

        # Extract from path (parsed.json is the file, so parent directories are:)
        # parts[-1] = parsed.json (file)
        # parts[-2] = date directory
        # parts[-3] = form directory
        # parts[-4] = company directory
        company = parts[-4]
        form = parts[-3]
        date = parts[-2]

        self.logger.info(f"Searching for XBRL filing: {company}/{form}")

        # Normalize company name for fuzzy matching
        company_normalized = normalize_company_name(company)

        # Search across all market directories
        for market_dir in self.xbrl_loader.xbrl_path.iterdir():
            if not market_dir.is_dir() or market_dir.name.startswith('.'):
                continue

            # STRATEGY 1: Try exact company directory name match first
            company_dir = market_dir / company
            if company_dir.exists() and company_dir.is_dir():
                result = self._search_form_filing(company_dir, form)
                if result:
                    self.logger.info(f"Found XBRL filing (exact match): {result}")
                    return result

            # STRATEGY 2: Fuzzy matching - compare normalized names
            for candidate_dir in market_dir.iterdir():
                if not candidate_dir.is_dir() or candidate_dir.name.startswith('.'):
                    continue

                candidate_normalized = normalize_company_name(candidate_dir.name)

                # Check if normalized names match
                if candidate_normalized == company_normalized:
                    self.logger.info(
                        f"Company name match: '{company}' -> '{candidate_dir.name}'"
                    )
                    result = self._search_form_filing(candidate_dir, form)
                    if result:
                        self.logger.info(f"Found XBRL filing (fuzzy match): {result}")
                        return result

        self.logger.error(f"Could not find XBRL filing for {company}/{form}")
        return None

    def _search_form_filing(self, company_dir: Path, form: str) -> Optional[Path]:
        """
        Search for a form filing within a company directory.

        Args:
            company_dir: Company directory path
            form: Form type (e.g., '10-K')

        Returns:
            Path to filing directory, or None if not found
        """
        # Look for filings subdirectory
        filings_dir = company_dir / FILINGS_SUBDIRECTORY
        if not filings_dir.exists():
            return None

        # Look for form type directory
        form_dir = filings_dir / form
        if not form_dir.exists() or not form_dir.is_dir():
            return None

        # Get most recent filing in this form directory
        filings = sorted(
            [f for f in form_dir.iterdir() if f.is_dir()],
            reverse=True
        )

        if filings:
            return filings[0]

        return None
    
    def _export_statements(
        self,
        statement_set,
        parsed_filing,
        output_folder: Path
    ) -> dict[str, list]:
        """Export statements to all formats."""
        export_paths = {}
        
        # Export to json/
        json_folder = output_folder / 'json'
        json_paths = self.statement_exporter.export_json(
            statement_set,
            parsed_filing,
            json_folder
        )
        export_paths['json'] = json_paths
        self.logger.info(f"Exported {len(json_paths)} JSON files")
        
        # Export to csv/
        csv_folder = output_folder / 'csv'
        csv_paths = self.statement_exporter.export_csv(
            statement_set,
            parsed_filing,
            csv_folder
        )
        export_paths['csv'] = csv_paths
        self.logger.info(f"Exported {len(csv_paths)} CSV files")
        
        # Export to excel/
        try:
            excel_folder = output_folder / 'excel'
            excel_paths = self.statement_exporter.export_excel(
                statement_set,
                parsed_filing,
                excel_folder
            )
            if excel_paths:
                export_paths['excel'] = excel_paths
                self.logger.info(f"Exported {len(excel_paths)} Excel files")
        except Exception as e:
            self.logger.warning(f"Excel export failed: {e}")
        
        return export_paths
    
    def _log_summary(self, result: dict[str, any], elapsed: float):
        """Log extraction summary."""
        self.logger.info(DEBUG_SEPARATOR)
        self.logger.info("EXTRACTION SUMMARY")
        self.logger.info(DEBUG_SEPARATOR)
        
        stats = result['statistics']
        info = result['filing_info']
        
        self.logger.info(f"Total statements: {stats['total_statements']}")
        self.logger.info(f"Total fact placements: {stats['total_fact_placements']}")
        self.logger.info(f"Processing time: {elapsed:.2f}s")
        self.logger.info(f"Output folder: {result['output_folder']}")
        self.logger.info(DEBUG_SEPARATOR)


__all__ = ['MappingOrchestrator']