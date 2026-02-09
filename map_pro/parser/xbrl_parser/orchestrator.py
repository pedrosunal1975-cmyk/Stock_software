# Path: xbrl_parser/orchestrator.py
"""
XBRL Parser Orchestrator - PROPER VERSION

Uses loaders for file access (no duplicate recursive search):
- loaders.XBRLFilingsLoader for XBRL filing file access
- loaders.TaxonomyLoader for taxonomy file access
- Orchestrator decides WHAT files to use (instance vs linkbase)
- Loaders provide file access (HOW to get files)

FIXED:
- Uses XBRLFilingsLoader instead of doing rglob() itself
- Much shorter _find_entry_point() - delegates to loader
- Lines 464, 508, 545: .add() not .add_error()
"""

import logging
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
import time

from .parser_modes import ParsingMode, get_mode_config
from .models.parsed_filing import ParsedFiling, FilingMetadata
from .models.error import ErrorSeverity
from .entry_point_detector import EntryPointDetector
from ..core.config_loader import ConfigLoader
from ..loaders import XBRLFilingsLoader, TaxonomyLoader


class ParsingProgress:
    """Track parsing progress across phases."""
    
    def __init__(self):
        self.phase = "initializing"
        self.progress = 0
        self.message = "Starting..."
        self.errors_count = 0
        self.warnings_count = 0
        self.start_time = time.time()
    
    def update(self, phase: str, progress: int, message: str = "",
               add_errors: int = 0, add_warnings: int = 0) -> None:
        self.phase = phase
        self.progress = progress
        self.message = message
        self.errors_count += add_errors
        self.warnings_count += add_warnings
    
    def to_dict(self) -> dict[str, any]:
        elapsed = time.time() - self.start_time
        return {
            'phase': self.phase,
            'progress': self.progress,
            'message': self.message,
            'errors': self.errors_count,
            'warnings': self.warnings_count,
            'elapsed_seconds': round(elapsed, 2)
        }


class XBRLParser:
    """Main XBRL parser orchestrator - uses loaders for file access."""

    _logging_configured = False  # Class-level flag to configure logging once

    def __init__(self, mode: ParsingMode = ParsingMode.FULL,
                 config: Optional[ConfigLoader] = None):
        self.config = config or ConfigLoader()

        # Configure logging on first instantiation
        if not XBRLParser._logging_configured:
            self._configure_logging()
            XBRLParser._logging_configured = True

        self.logger = logging.getLogger(__name__)
        self.mode = mode
        self.mode_config = get_mode_config(mode)

        # Loaders (file access layer)
        self._filings_loader = None

        # Components (lazy loaded)
        self._taxonomy_service = None
        self._instance_parser = None
        self._ixbrl_parser = None
        self._validation_registry = None
        self._market_registry = None
        self._serializer = None
        self._metrics = None
        self._profiler = None

        # Progress tracking
        self.progress = ParsingProgress()

        self.logger.info(f"XBRLParser initialized in {mode.value} mode")
        self.logger.info(f"Config: {self.mode_config.description}")

    def _configure_logging(self) -> None:
        """Configure logging with file handlers."""
        from parser.core.logger.logger import setup_logging

        log_dir = self.config.get('log_dir')
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)

            # Main log file
            log_file = log_dir / self.config.get('main_log', 'parser.log')

            setup_logging(
                log_level=self.config.get('log_level', 'INFO'),
                log_file=log_file,
                config=self.config
            )
        else:
            # No log directory configured - console only
            setup_logging(
                log_level=self.config.get('log_level', 'INFO'),
                log_file=None
            )
    
    def parse(self, filing_path: Path, output_path: Optional[Path] = None,
              progress_callback: Optional[Callable[[dict[str, any]], None]] = None) -> ParsedFiling:
        """Parse an XBRL filing - main entry point."""
        filing_path = Path(filing_path)
        
        if not filing_path.exists():
            raise FileNotFoundError(f"Filing not found: {filing_path}")
        
        self.logger.info(f"Starting parse: {filing_path}")
        self.logger.info(f"Mode: {self.mode.value}")
        
        # Initialize progress
        self.progress = ParsingProgress()
        self._notify_progress(progress_callback)
        
        # Initialize metrics if enabled
        if self.mode_config.enable_metrics:
            self._init_metrics()
            self._metrics.increment('parse_started')
        
        try:
            # Start profiling if enabled
            if self.mode_config.enable_profiling:
                self._start_profiling()
            
            # Phase 1: Discovery (0-15%)
            entry_point = self._phase_discovery(filing_path, progress_callback)
            
            # Phase 2: Taxonomy Loading (15-35%)
            taxonomy = None
            if self.mode_config.load_taxonomy:
                taxonomy = self._phase_taxonomy(entry_point, progress_callback)
            
            # Phase 3: Instance Parsing (35-60%)
            parsed_filing = self._phase_extraction(entry_point, taxonomy, progress_callback)
            
            # Phase 4: Core Validation (60-75%)
            if self.mode_config.validate_structure:
                self._phase_validation(parsed_filing, progress_callback)
            
            # Phase 5: Market Validation (75-85%)
            if self.mode_config.market_validation:
                self._phase_market_validation(parsed_filing, progress_callback)
            
            # Phase 6: Serialization (85-100%)
            if self.mode_config.serialize_output:
                self._phase_serialization(parsed_filing, output_path, progress_callback)
            
            # Stop profiling
            if self.mode_config.enable_profiling:
                self._stop_profiling(parsed_filing)
            
            # Final progress
            self.progress.update("complete", 100, "Parsing complete")
            self._notify_progress(progress_callback)
            
            # Metrics
            if self.mode_config.enable_metrics:
                self._metrics.increment('parse_completed')
                self._metrics.timer('parse_duration', time.time() - self.progress.start_time)
                self._metrics.gauge('facts_extracted', len(parsed_filing.instance.facts))
                
                # ErrorCollection uses count_by_severity() method, not properties
                counts = parsed_filing.errors.count_by_severity()
                self._metrics.gauge('errors_found', counts[ErrorSeverity.ERROR])
            
            self.logger.info(f"Parsing complete: {parsed_filing.metadata.filing_id}")
            
            # ErrorCollection uses count_by_severity() method
            counts = parsed_filing.errors.count_by_severity()
            self.logger.info(f"Facts: {len(parsed_filing.instance.facts)}, " +
                           f"Errors: {counts[ErrorSeverity.ERROR]}, " +
                           f"Warnings: {counts[ErrorSeverity.WARNING]}")
            
            return parsed_filing
            
        except Exception as e:
            self.logger.error(f"Parsing failed: {e}", exc_info=True)
            self.progress.update("error", 0, f"Error: {str(e)}", add_errors=1)
            self._notify_progress(progress_callback)
            
            if self.mode_config.enable_metrics:
                self._metrics.increment('parse_failed')
            
            raise
    
    def _phase_discovery(self, filing_path: Path, progress_callback: Optional[Callable]) -> Path:
        """Phase 1: Discovery - Find entry point file."""
        self.progress.update("discovery", 5, "Discovering entry point")
        self._notify_progress(progress_callback)
        
        self.logger.info("Phase 1: Discovery")
        
        # If it's a file, use it directly
        if filing_path.is_file():
            self.logger.info(f"Entry point: {filing_path.name}")
            return filing_path
        
        # If it's a directory, find entry point using loader
        if filing_path.is_dir():
            entry_point = self._find_entry_point(filing_path)
            self.logger.info(f"Entry point found: {entry_point.name}")
            return entry_point
        
        raise ValueError(f"Invalid filing path: {filing_path}")
    
    def _find_entry_point(self, directory: Path) -> Path:
        """
        Find entry point in directory - USES LOADER for file access.
        
        Orchestrator's job: Coordinate detection
        Loader's job: Provide file access
        Detector's job: Identify which file is the instance
        """
        # Lazy load filings loader
        if not self._filings_loader:
            self._filings_loader = XBRLFilingsLoader(config=self.config)
        
        # Get all files in this directory using loader
        try:
            # Calculate relative path from XBRL filings root
            xbrl_root = Path(self.config.get('xbrl_filings_path'))
            relative_path = directory.relative_to(xbrl_root)
            
            # Ask loader for files
            all_files = self._filings_loader.discover_all_files(subdirectory=str(relative_path))
        except ValueError:
            # directory is not relative to xbrl_root, might be absolute
            # Try direct discovery
            all_files = list(directory.rglob('*.*'))
        
        if not all_files:
            raise FileNotFoundError(f"No files found in {directory}")
        
        self.logger.debug(f"Loader found {len(all_files)} files")
        
        # Use EntryPointDetector to identify instance file
        detector = EntryPointDetector()
        instance_file = detector.detect(all_files)
        
        if not instance_file:
            self.logger.error(f"No instance file identified among {len(all_files)} files")
            raise FileNotFoundError(f"No XBRL instance file found in {directory}")
        
        return instance_file
    
    
    def _phase_taxonomy(self, entry_point: Path, progress_callback: Optional[Callable]) -> any:
        """Phase 2: Taxonomy Loading."""
        self.progress.update("taxonomy", 20, "Loading taxonomy")
        self._notify_progress(progress_callback)
        
        self.logger.info("Phase 2: Taxonomy Loading")
        
        # Lazy load taxonomy service (handles taxonomy loading internally)
        if not self._taxonomy_service:
            from .taxonomy.service import TaxonomyService
            self._taxonomy_service = TaxonomyService(config=self.config)
        
        # Load taxonomy
        try:
            taxonomy = self._taxonomy_service.load_from_instance(entry_point)
            self.logger.info(f"Taxonomy loaded: {len(taxonomy.concepts) if hasattr(taxonomy, 'concepts') else 0} concepts")
            return taxonomy
        except Exception as e:
            self.logger.warning(f"Taxonomy loading failed: {e}")
            from .models.parsed_filing import TaxonomyData
            return TaxonomyData()
    
    def _phase_extraction(self, entry_point: Path, taxonomy: any,
                          progress_callback: Optional[Callable]) -> ParsedFiling:
        """Phase 3: Instance Parsing - Extract facts and data."""
        self.progress.update("extraction", 40, "Parsing instance")
        self._notify_progress(progress_callback)
        
        self.logger.info("Phase 3: Instance Parsing")
        
        # Determine if inline XBRL
        is_inline = entry_point.suffix.lower() in ['.xhtml', '.html', '.htm']
        
        if is_inline:
            self.logger.info("Detected inline XBRL format")
            if not self._ixbrl_parser:
                from .ixbrl.ixbrl_parser import IXBRLParser
                self._ixbrl_parser = IXBRLParser(config=self.config)
            
            ixbrl_result = self._ixbrl_parser.parse_ixbrl(entry_point)
            
            # iXBRL returns transformed XML - parse with instance parser
            if ixbrl_result.xbrl_document:
                if not self._instance_parser:
                    from .instance.instance_parser import InstanceParser
                    self._instance_parser = InstanceParser(config=self.config)
                
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp:
                    tmp.write(ixbrl_result.xbrl_document)
                    tmp_path = Path(tmp.name)
                
                try:
                    result = self._instance_parser.parse_instance(tmp_path)
                finally:
                    tmp_path.unlink()
                
                result.errors.extend(ixbrl_result.errors)
            else:
                from .instance.instance_parser import InstanceParseResult
                result = InstanceParseResult()
                result.errors = ixbrl_result.errors
        else:
            self.logger.info("Detected standard XBRL format")
            if not self._instance_parser:
                from .instance.instance_parser import InstanceParser
                self._instance_parser = InstanceParser(config=self.config)
            
            result = self._instance_parser.parse_instance(entry_point)
        
        # Create ParsedFiling
        from .models.parsed_filing import InstanceData
        parsed_filing = ParsedFiling()
        
        # set basic metadata
        parsed_filing.metadata.filing_id = entry_point.stem
        parsed_filing.metadata.entry_point = entry_point
        parsed_filing.metadata.source_files = [entry_point]

        # Extract metadata from DEI facts (Document and Entity Information)
        # This populates document_type, company_name, entity_identifier, dates, etc.
        # Also extracts period_end_date from contexts if not in facts
        from .metadata_extractor import MetadataExtractor
        metadata_extractor = MetadataExtractor()
        extracted_metadata = metadata_extractor.extract(
            facts=result.facts,
            contexts=result.contexts,
            entry_point=entry_point,
            filing_id=entry_point.stem
        )

        # Merge extracted metadata (preserve any existing values)
        if not parsed_filing.metadata.document_type and extracted_metadata.document_type:
            parsed_filing.metadata.document_type = extracted_metadata.document_type
        if not parsed_filing.metadata.company_name and extracted_metadata.company_name:
            parsed_filing.metadata.company_name = extracted_metadata.company_name
        if not parsed_filing.metadata.entity_identifier and extracted_metadata.entity_identifier:
            parsed_filing.metadata.entity_identifier = extracted_metadata.entity_identifier
        if not parsed_filing.metadata.period_end_date and extracted_metadata.period_end_date:
            parsed_filing.metadata.period_end_date = extracted_metadata.period_end_date
        if not parsed_filing.metadata.filing_date and extracted_metadata.filing_date:
            parsed_filing.metadata.filing_date = extracted_metadata.filing_date
        if not parsed_filing.metadata.market and extracted_metadata.market:
            parsed_filing.metadata.market = extracted_metadata.market
        if not parsed_filing.metadata.regulatory_authority and extracted_metadata.regulatory_authority:
            parsed_filing.metadata.regulatory_authority = extracted_metadata.regulatory_authority

        # Create InstanceData
        instance_data = InstanceData(
            facts=result.facts,
            contexts=result.contexts,
            units=result.units,
            namespaces=result.namespaces if hasattr(result, 'namespaces') else {},
            footnotes={fn_id: fn.content for fn_id, fn in result.footnotes.items()} if result.footnotes else {}
        )
        
        parsed_filing.instance = instance_data
        parsed_filing.taxonomy = taxonomy
        
        # FIXED: .add() not .add_error()
        for error in result.errors:
            parsed_filing.errors.add(error)
        
        self.logger.info(f"Extraction complete: {len(result.facts)} facts, " +
                        f"{len(result.contexts)} contexts, {len(result.units)} units")
        
        return parsed_filing
    
    def _phase_validation(self, filing: ParsedFiling, progress_callback: Optional[Callable]) -> None:
        """Phase 4: Core Validation."""
        self.progress.update("validation", 65, "Validating structure")
        self._notify_progress(progress_callback)
        
        self.logger.info("Phase 4: Core Validation")
        
        if not self._validation_registry:
            from .validation.registry import ValidationRegistry
            self._validation_registry = ValidationRegistry(config=self.config)
        
        validation_summary = self._validation_registry.validate_filing(filing)
        
        all_errors = []
        for result in validation_summary.results:
            all_errors.extend(result.errors)
            all_errors.extend(result.warnings)
        
        # FIXED: .add() not .add_error()
        for error in all_errors:
            filing.errors.add(error)
        
        self.logger.info(f"Validation complete: {validation_summary.total_errors} errors, {validation_summary.total_warnings} warnings")
    
    def _phase_market_validation(self, filing: ParsedFiling, progress_callback: Optional[Callable]) -> None:
        """Phase 5: Market Validation."""
        self.progress.update("market_validation", 78, "Market validation")
        self._notify_progress(progress_callback)
        
        self.logger.info("Phase 5: Market Validation")
        
        if not self._market_registry:
            from .market.registry import MarketRegistry
            self._market_registry = MarketRegistry()
        
        errors = self._market_registry.validate(filing)
        
        # FIXED: .add() not .add_error()
        for error in errors:
            filing.errors.add(error)
        
        self.logger.info(f"Market validation complete: {len(errors)} issues")
    
    def _phase_serialization(self, filing: ParsedFiling, output_path: Optional[Path],
                             progress_callback: Optional[Callable]) -> None:
        """Phase 6: Serialization (output handled by parser.py main workflow)."""
        self.progress.update("serialization", 90, "Serialization complete")
        self._notify_progress(progress_callback)
        
        self.logger.info("Phase 6: Serialization")
        
        # Note: JSON output is handled by parser.py main workflow
        # This phase kept for progress tracking compatibility
        # orchestrator no longer saves duplicate JSON files
        
        self.logger.info("Serialization phase complete (output handled by parser.py)")
    
    def _notify_progress(self, callback: Optional[Callable]) -> None:
        """Notify progress callback if provided."""
        if callback:
            try:
                callback(self.progress.to_dict())
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {e}")
    
    def _init_metrics(self) -> None:
        """Initialize metrics collector."""
        if not self._metrics:
            from .observability.metrics import MetricsCollector
            self._metrics = MetricsCollector()
    
    def _start_profiling(self) -> None:
        """Start profiling."""
        if not self._profiler:
            from .observability.profiler import Profiler
            self._profiler = Profiler()
        self._profiler.start("full_parse")
    
    def _stop_profiling(self, filing: ParsedFiling) -> None:
        """Stop profiling and save results."""
        if self._profiler:
            self._profiler.stop()
            # Use log directory parent + 'profiles' subdirectory
            log_dir = self.config.get('log_dir')
            if log_dir:
                profile_dir = Path(log_dir).parent / 'profiles'
                profile_dir.mkdir(parents=True, exist_ok=True)
                profile_path = profile_dir / f"profile_{filing.metadata.filing_id}.json"
                self._profiler.save_profile(profile_path)
                self.logger.info(f"Profile saved: {profile_path}")
    
    def get_statistics(self) -> dict[str, any]:
        """Get parser statistics."""
        stats = {
            'mode': self.mode.value,
            'progress': self.progress.to_dict()
        }
        if self._metrics:
            stats['metrics'] = self._metrics.get_summary()
        return stats


__all__ = ['XBRLParser', 'ParsingProgress']
