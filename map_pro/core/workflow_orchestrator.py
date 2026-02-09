"""
Workflow Orchestrator - End-to-End Pipeline

Coordinates the complete Map Pro workflow:
1. Search   - Find filings via market APIs
2. Download - Retrieve and extract filing archives
3. Parse    - Extract XBRL facts and structure
4. Map      - Build financial statements

Architecture:
- Uses existing module orchestrators (SearchOrchestrator, DownloadCoordinator,
  XBRLParser, MappingOrchestrator)
- Tracks workflow state in database
- Provides progress updates and error handling
- Supports resume from failures
- Follows project standards (no hardcoding, market agnostic)

Example:
    orchestrator = WorkflowOrchestrator()

    results = await orchestrator.run_complete_workflow(
        market_id='sec',
        company_identifier='0000320193',  # Apple
        form_type='10-K',
        num_filings=1
    )
"""

import logging
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

# Database imports
from database import initialize_database, session_scope
from database.models import DownloadedFiling, Entity

# Module orchestrators
from searcher.engine.orchestrator import SearchOrchestrator
from downloader.engine.coordinator import DownloadCoordinator
from mapper.mapping.orchestrator import MappingOrchestrator

# Configuration
from database.core.config_loader import ConfigLoader as DatabaseConfig
from parser.core.config_loader import ConfigLoader as ParserConfig

# Workflow constants and helpers
from .constants import (
    PROGRESS_DATABASE_INIT,
    PROGRESS_SEARCH_START,
    PROGRESS_DOWNLOAD_START,
    PROGRESS_PARSE_START,
    PROGRESS_MAP_START,
    PROGRESS_COMPLETE,
    SEPARATOR_WIDTH,
    SEPARATOR_CHAR,
    PARSE_STATUS_PENDING,
    PARSE_STATUS_COMPLETED,
    PARSE_STATUS_FAILED,
    PARSED_JSON_FILENAME,
    GLOB_PATTERN_PARSED_FILES,
)
from .parse_helpers import (
    extract_form_type_from_path,
    create_output_directory,
    get_parser_output_directory,
    enrich_metadata,
    save_parsed_json,
)


class WorkflowState:
    """Track workflow execution state."""

    def __init__(self):
        """Initialize workflow state."""
        self.phase = "initializing"
        self.progress = 0
        self.message = ""
        self.start_time = time.time()

        # Stage completion tracking
        self.search_complete = False
        self.download_complete = False
        self.parse_complete = False
        self.map_complete = False

        # Results tracking
        self.filings_found = 0
        self.filings_downloaded = 0
        self.filings_parsed = 0
        self.filings_mapped = 0

        # Error tracking
        self.errors: list[dict[str, any]] = []
        self.warnings: list[dict[str, any]] = []

    def update(self, phase: str, progress: int, message: str = ""):
        """Update workflow state."""
        self.phase = phase
        self.progress = progress
        self.message = message

    def add_error(self, stage: str, message: str, details: any = None):
        """Add error to tracking."""
        self.errors.append({
            'stage': stage,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

    def add_warning(self, stage: str, message: str):
        """Add warning to tracking."""
        self.warnings.append({
            'stage': stage,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

    def to_dict(self) -> dict[str, any]:
        """Convert state to dictionary."""
        return {
            'phase': self.phase,
            'progress': self.progress,
            'message': self.message,
            'elapsed_seconds': round(time.time() - self.start_time, 2),
            'stages': {
                'search': self.search_complete,
                'download': self.download_complete,
                'parse': self.parse_complete,
                'map': self.map_complete
            },
            'counts': {
                'found': self.filings_found,
                'downloaded': self.filings_downloaded,
                'parsed': self.filings_parsed,
                'mapped': self.filings_mapped
            },
            'errors': len(self.errors),
            'warnings': len(self.warnings)
        }


class WorkflowOrchestrator:
    """
    Orchestrates the complete Map Pro workflow.

    Coordinates all modules to provide end-to-end processing:
    Company Specs → Search → Download → Parse → Map → Financial Statements

    Features:
    - Automatic database initialization
    - Progress tracking and reporting
    - Error handling and recovery
    - State management for resume capability
    - Comprehensive logging

    Example:
        # Initialize orchestrator
        orchestrator = WorkflowOrchestrator()

        # Run complete workflow
        results = await orchestrator.run_complete_workflow(
            market_id='sec',
            company_identifier='AAPL',
            form_type='10-K',
            num_filings=1
        )

        # Access results
        print(f"Processed {results['summary']['filings_mapped']} filings")
        for path in results['output_paths']:
            print(f"Statements: {path}")
    """

    def __init__(
        self,
        db_config: Optional[DatabaseConfig] = None,
        parser_config: Optional[ParserConfig] = None
    ):
        """
        Initialize workflow orchestrator.

        Args:
            db_config: Optional database ConfigLoader instance
            parser_config: Optional parser ConfigLoader instance
        """
        self.db_config = db_config if db_config else DatabaseConfig()
        self.parser_config = parser_config if parser_config else ParserConfig()
        self.logger = logging.getLogger('workflow_orchestrator')

        # State tracking
        self.state = WorkflowState()

        # Initialize module orchestrators (lazy loaded)
        self._search_orchestrator = None
        self._download_coordinator = None
        self._parser = None
        self._mapper = None

        self.logger.info("WorkflowOrchestrator initialized")

    async def run_complete_workflow(
        self,
        market_id: str,
        company_identifier: str,
        form_type: str,
        num_filings: int = 1,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict[str, any]:
        """
        Run complete end-to-end workflow.

        Args:
            market_id: Market identifier (sec, esma, fca)
            company_identifier: Company identifier (CIK, LEI, company number)
            form_type: Filing form type (10-K, 10-Q, etc.)
            num_filings: Number of historical filings to process
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with complete workflow results and statistics

        Example:
            results = await orchestrator.run_complete_workflow(
                market_id='sec',
                company_identifier='0000320193',
                form_type='10-K',
                num_filings=2
            )
        """
        separator = SEPARATOR_CHAR * SEPARATOR_WIDTH

        self.logger.info(separator)
        self.logger.info("STARTING COMPLETE WORKFLOW")
        self.logger.info(separator)
        self.logger.info(f"Market: {market_id}")
        self.logger.info(f"Company: {company_identifier}")
        self.logger.info(f"Form Type: {form_type}")
        self.logger.info(f"Number of Filings: {num_filings}")
        self.logger.info(separator)

        # Reset state
        self.state = WorkflowState()

        try:
            # Phase 0: Database Initialization (0-5%)
            self.state.update("database_init", PROGRESS_DATABASE_INIT,
                              "Initializing database")
            self._initialize_database()

            # Phase 1: Search (5-20%)
            self.state.update("search", PROGRESS_SEARCH_START,
                              "Searching for filings")
            search_results = await self._phase_search(
                market_id, company_identifier, form_type,
                num_filings, start_date, end_date
            )

            if search_results['filings_saved'] == 0:
                self.state.add_warning("search", "No filings found")
                return self._build_results()

            # Phase 2: Download (20-50%)
            self.state.update("download", PROGRESS_DOWNLOAD_START,
                              "Downloading filings")
            download_results = await self._phase_download(num_filings)

            if download_results['succeeded'] == 0:
                self.state.add_error("download",
                                     "No filings downloaded successfully")
                return self._build_results()

            # Phase 3: Parse (50-75%)
            self.state.update("parse", PROGRESS_PARSE_START,
                              "Parsing XBRL filings")
            parse_results = await self._phase_parse(market_id, form_type)

            if parse_results['parsed_count'] == 0:
                # Check if parsing was skipped due to PDF-only format (expected, not an error)
                pdf_only_warnings = [w for w in self.state.warnings if 'PDF' in w or 'pdf' in w]
                if not pdf_only_warnings:
                    # Actual parsing failure - add error
                    self.state.add_error("parse",
                                         "No filings parsed successfully")
                # Return results (with warnings for PDF-only, or errors for actual failures)
                return self._build_results()

            # Phase 4: Map (75-100%)
            self.state.update("map", PROGRESS_MAP_START,
                              "Mapping to financial statements")
            map_results = await self._phase_map(market_id, form_type)

            # Complete
            self.state.update("complete", PROGRESS_COMPLETE,
                              "Workflow complete")

            self.logger.info(separator)
            self.logger.info("WORKFLOW COMPLETE")
            self.logger.info(separator)

            return self._build_results()

        except Exception as e:
            self.logger.error(f"Workflow failed: {e}", exc_info=True)
            self.state.add_error("workflow", str(e),
                                 {'exception': type(e).__name__})
            self.state.update("error", 0, f"Workflow failed: {e}")
            raise

    def _initialize_database(self):
        """Initialize database (Phase 0)."""
        self.logger.info("Phase 0: Database Initialization")

        try:
            initialize_database()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.state.add_error("database_init",
                                 f"Database initialization failed: {e}")
            raise

    async def _phase_search(
        self,
        market_id: str,
        company_identifier: str,
        form_type: str,
        num_filings: int,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> dict[str, any]:
        """
        Phase 1: Search for filings.

        Returns:
            Dictionary with search results
        """
        self.logger.info("Phase 1: Search")

        try:
            # Initialize search orchestrator
            if not self._search_orchestrator:
                self._search_orchestrator = SearchOrchestrator()

            # Execute search
            filings_saved = await self._search_orchestrator.search_and_save(
                market_id=market_id,
                identifier=company_identifier,
                form_type=form_type,
                max_results=num_filings,
                start_date=start_date,
                end_date=end_date
            )

            self.state.filings_found = filings_saved
            self.state.search_complete = True

            self.logger.info(
                f"Search complete: {filings_saved} filings found and "
                f"saved to database"
            )

            return {'filings_saved': filings_saved}

        except Exception as e:
            self.state.add_error("search", f"Search failed: {e}")
            raise

    async def _phase_download(self, limit: int) -> dict[str, any]:
        """
        Phase 2: Download filings.

        Args:
            limit: Maximum number of filings to download

        Returns:
            Dictionary with download statistics
        """
        self.logger.info("Phase 2: Download")

        try:
            # Initialize download coordinator
            if not self._download_coordinator:
                self._download_coordinator = DownloadCoordinator()

            # Process pending downloads
            stats = await self._download_coordinator.process_pending_downloads(
                limit=limit
            )

            self.state.filings_downloaded = stats['succeeded']
            self.state.download_complete = True

            self.logger.info(
                f"Download complete: {stats['succeeded']}/{stats['total']} "
                f"succeeded in {stats['duration']:.1f}s"
            )

            # Clean up
            await self._download_coordinator.close()

            return stats

        except Exception as e:
            self.state.add_error("download", f"Download failed: {e}")
            raise

    async def _phase_parse(
        self,
        market_id: str,
        form_type: str
    ) -> dict[str, any]:
        """
        Phase 3: Parse XBRL filings.

        Args:
            market_id: Market identifier
            form_type: Form type

        Returns:
            Dictionary with parsing statistics
        """
        self.logger.info("Phase 3: Parse")

        try:
            parsed_count = 0

            with session_scope() as session:
                # Get recently downloaded filings
                downloaded = session.query(DownloadedFiling, Entity).join(
                    Entity, DownloadedFiling.entity_id == Entity.entity_id
                ).filter(
                    DownloadedFiling.parse_status == PARSE_STATUS_PENDING
                ).order_by(
                    DownloadedFiling.created_at.desc()
                ).all()

                self.logger.info(
                    f"Found {len(downloaded)} filings ready for parsing"
                )

                # Initialize parser
                if not self._parser:
                    from parser.xbrl_parser.orchestrator import (
                        XBRLParser,
                        ParsingMode
                    )
                    self._parser = XBRLParser(mode=ParsingMode.FULL)

                # Get parser output directory
                parser_output = get_parser_output_directory(self.parser_config)

                # Parse each filing
                for downloaded_filing, entity in downloaded:
                    try:
                        parsed_count += self._parse_single_filing(
                            downloaded_filing,
                            entity,
                            market_id,
                            form_type,
                            parser_output
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Parse failed for {downloaded_filing.filing_id}: {e}"
                        )
                        self.state.add_warning("parse",
                                               f"Failed to parse filing: {e}")
                        downloaded_filing.parse_status = PARSE_STATUS_FAILED

                session.commit()

            self.state.filings_parsed = parsed_count
            self.state.parse_complete = True

            self.logger.info(f"Parse complete: {parsed_count} filings parsed")

            return {'parsed_count': parsed_count}

        except Exception as e:
            self.state.add_error("parse", f"Parse phase failed: {e}")
            raise

    def _parse_single_filing(
        self,
        downloaded_filing,
        entity,
        market_id: str,
        form_type: str,
        parser_output: Path
    ) -> int:
        """
        Parse a single filing.

        Args:
            downloaded_filing: DownloadedFiling database object
            entity: Entity database object
            market_id: Market identifier
            form_type: Form type (user input)
            parser_output: Parser output base directory

        Returns:
            1 if parsed successfully, 0 otherwise
        """
        filing_path = Path(downloaded_filing.download_directory)

        if not filing_path.exists():
            self.logger.warning(f"Filing directory not found: {filing_path}")
            return 0

        # Check if there are parseable XBRL files (not just PDFs)
        parseable_extensions = {'.xml', '.xbrl', '.xhtml', '.html', '.htm'}
        files_in_dir = list(filing_path.iterdir()) if filing_path.is_dir() else []
        parseable_files = [f for f in files_in_dir if f.suffix.lower() in parseable_extensions]
        pdf_files = [f for f in files_in_dir if f.suffix.lower() == '.pdf']

        if not parseable_files and pdf_files:
            # Only PDF files present - skip parsing gracefully
            self.logger.info(
                f"Skipping parse for {entity.company_name}: "
                f"Only PDF format available (not parseable as XBRL). "
                f"Downloaded: {', '.join(f.name for f in pdf_files)}"
            )
            downloaded_filing.parse_status = PARSE_STATUS_FAILED
            self.state.add_warning(
                "parse",
                f"{entity.company_name}: Only PDF available from source (iXBRL not filed)"
            )
            return 0

        self.logger.info(f"Parsing: {entity.company_name} - {filing_path}")

        # Parse filing
        parsed = self._parser.parse(filing_path)

        # Extract actual form type from physical directory structure
        actual_form_type = extract_form_type_from_path(
            filing_path,
            form_type
        )

        # Enrich metadata from database (only if parser didn't extract it)
        enrich_metadata(parsed, entity, downloaded_filing, actual_form_type)

        # Create output directory
        filing_date_str = None
        if downloaded_filing.filing_search and \
           downloaded_filing.filing_search.filing_date:
            filing_date_str = downloaded_filing.filing_search.filing_date \
                .strftime('%Y-%m-%d')

        output_dir = create_output_directory(
            parser_output,
            market_id,
            entity.company_name,
            actual_form_type,
            filing_date_str
        )

        # Save parsed.json
        json_file = save_parsed_json(parsed, output_dir)

        # Update database
        downloaded_filing.parse_status = PARSE_STATUS_COMPLETED
        downloaded_filing.parsed_output_path = str(json_file)

        self.logger.info(f"Parsed successfully: {json_file}")

        return 1

    async def _phase_map(
        self,
        market_id: str,
        form_type: str
    ) -> dict[str, any]:
        """
        Phase 4: Map to financial statements.

        Args:
            market_id: Market identifier
            form_type: Form type

        Returns:
            Dictionary with mapping statistics
        """
        self.logger.info("Phase 4: Map")

        try:
            # Initialize mapper
            if not self._mapper:
                self._mapper = MappingOrchestrator()

            # Get parser output directory
            parsed_base = get_parser_output_directory(self.parser_config)
            parsed_dir = parsed_base / market_id

            # Find ALL parsed.json files
            # Don't filter by user-input form_type
            # The actual form type is in the physical directory structure
            # Pattern: {market_id}/{company}/{form_type}/{date}/parsed.json
            parsed_files = list(parsed_dir.glob(GLOB_PATTERN_PARSED_FILES))

            self.logger.info(
                f"Found {len(parsed_files)} parsed files ready for mapping"
            )

            mapped_count = 0
            output_paths = []

            for parsed_file in parsed_files:
                try:
                    self.logger.info(f"Mapping: {parsed_file}")

                    # Run mapping
                    result = self._mapper.extract_and_export(parsed_file)

                    output_paths.append(result['output_folder'])
                    mapped_count += 1

                    self.logger.info(
                        f"Mapped successfully: {result['output_folder']}"
                    )
                    self.logger.info(
                        f"  Statements: {result['statistics']['total_statements']}, "
                        f"Facts: {result['statistics']['total_fact_placements']}"
                    )

                except Exception as e:
                    self.logger.error(f"Map failed for {parsed_file}: {e}", exc_info=True)
                    self.state.add_warning("map",
                                           f"Failed to map filing: {e}")

            self.state.filings_mapped = mapped_count
            self.state.map_complete = True

            self.logger.info(f"Map complete: {mapped_count} filings mapped")

            return {
                'mapped_count': mapped_count,
                'output_paths': output_paths
            }

        except Exception as e:
            self.state.add_error("map", f"Map phase failed: {e}")
            raise

    def _build_results(self) -> dict[str, any]:
        """Build final results dictionary."""
        return {
            'success': self.state.map_complete,
            'state': self.state.to_dict(),
            'summary': {
                'filings_found': self.state.filings_found,
                'filings_downloaded': self.state.filings_downloaded,
                'filings_parsed': self.state.filings_parsed,
                'filings_mapped': self.state.filings_mapped,
                'total_time_seconds': round(
                    time.time() - self.state.start_time, 2
                )
            },
            'errors': self.state.errors,
            'warnings': self.state.warnings
        }

    def get_state(self) -> dict[str, any]:
        """Get current workflow state."""
        return self.state.to_dict()


__all__ = ['WorkflowOrchestrator', 'WorkflowState']
