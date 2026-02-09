# Path: downloader/engine/coordinator.py
"""
Download Coordinator

Main workflow orchestrator for download operations.
Coordinates: query â†’ download â†’ extract â†’ validate â†’ database update.
Handles both filing downloads and taxonomy library downloads.

Architecture:
- Complete download workflow management
- Type-based routing via PathResolver
- Failure handling via FailureHandler
- Component integration
- Database reflects reality principle
- IPO logging throughout
"""

import time
from typing import Optional
from pathlib import Path

from downloader.core.logger import get_logger
from downloader.core.config_loader import ConfigLoader
from downloader.core.data_paths import DataPathsManager
from downloader.engine.protocol_handlers import HTTPHandler
from downloader.engine.retry_manager import RetryManager
from downloader.engine.validator import Validator
from downloader.engine.db_operations import DatabaseRepository
from downloader.engine.path_resolver import PathResolver
from downloader.engine.failure_handler import FailureHandler
from downloader.engine.archive_downloader import ArchiveDownloader
from downloader.engine.distribution_processor import DistributionProcessor
from downloader.engine.result import ProcessingResult
from downloader.constants import (
    STATUS_DOWNLOADING,
    STATUS_COMPLETED,
    LOG_INPUT,
    LOG_PROCESS,
    LOG_OUTPUT,
)

logger = get_logger(__name__, 'engine')


class DownloadCoordinator:
    """
    Coordinates complete download workflow.
    
    Handles both:
    - Filing downloads â†’ /mnt/map_pro/downloader/entities/
    - Taxonomy downloads â†’ /mnt/map_pro/taxonomies/
    
    Workflow:
    1. Query database for pending downloads (filings + taxonomies)
    2. For each download:
       a. Determine type (filing or taxonomy) via PathResolver
       b. Download and extract (distribution-agnostic)
       c. Validate files exist
       d. Update database ONLY after physical verification
       e. Cleanup temp files
    
    CRITICAL: Database updated only after files verified on disk.
    
    Example:
        coordinator = DownloadCoordinator()
        await coordinator.process_pending_downloads(limit=10)
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize download coordinator.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        
        # Initialize core components
        self.http_handler = HTTPHandler(self.config)
        self.retry_manager = RetryManager(config=self.config)
        self.validator = Validator(self.config)
        self.path_manager = DataPathsManager(self.config)
        self.db_repo = DatabaseRepository()
        
        # Ensure all required directories exist
        self.path_manager.ensure_all_directories()
        
        # Get directories from config
        self.temp_dir = self.config.get('downloader_temp_dir')
        entities_dir = self.config.get('downloader_entities_dir')
        # CRITICAL FIX: Use library_taxonomies_libraries (not library_taxonomies_dir)
        # This points to /mnt/map_pro/taxonomies/libraries (correct destination)
        taxonomies_dir = self.config.get('library_taxonomies_libraries')
        
        # Initialize helper components
        self.path_resolver = PathResolver(
            entities_dir=entities_dir,
            taxonomies_dir=taxonomies_dir
        )
        self.failure_handler = FailureHandler(self.db_repo)
        
        # Initialize archive downloader
        self.archive_downloader = ArchiveDownloader(
            http_handler=self.http_handler,
            retry_manager=self.retry_manager,
            temp_dir=self.temp_dir,
            config=self.config
        )
        
        # Initialize distribution processor
        self.distribution_processor = DistributionProcessor(
            archive_downloader=self.archive_downloader,
            config=self.config
        )
    
    async def process_pending_downloads(self, limit: int = 100) -> dict:
        """
        Process pending downloads from database.
        
        Args:
            limit: Maximum number to process
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"{LOG_INPUT} Processing pending downloads (limit={limit})")
        
        start_time = time.time()
        stats = {
            'total': 0,
            'succeeded': 0,
            'failed': 0,
            'duration': 0.0
        }
        
        # Get pending filings
        pending_filings = self.db_repo.get_pending_downloads(limit=limit)
        
        # Get pending taxonomies
        pending_taxonomies = self.db_repo.get_pending_taxonomies(limit=limit)
        
        # Combine both lists
        all_pending = pending_filings + pending_taxonomies
        stats['total'] = len(all_pending)
        
        logger.info(
            f"{LOG_PROCESS} Found {len(pending_filings)} pending filings, "
            f"{len(pending_taxonomies)} pending taxonomies"
        )
        
        # Process each download
        for item in all_pending:
            result = await self.process_single_filing(item)
            
            if result.success:
                stats['succeeded'] += 1
            else:
                stats['failed'] += 1
        
        stats['duration'] = time.time() - start_time
        
        logger.info(
            f"{LOG_OUTPUT} Processing complete: {stats['succeeded']}/{stats['total']} succeeded "
            f"in {stats['duration']:.1f}s"
        )
        
        return stats
    
    async def process_single_filing(self, filing):
        """
        Process single download (filing or taxonomy).
        
        Routes to correct destination based on record type.
        
        Args:
            filing: FilingSearch or TaxonomyLibrary record
            
        Returns:
            ProcessingResult
        """
        result = ProcessingResult(success=False)
        start_time = time.time()
        
        # Determine download type
        download_type = self.path_resolver.determine_type(filing)
        
        logger.info(
            f"{LOG_INPUT} Processing {download_type}: "
            f"{filing.form_type if download_type == 'filing' else filing.taxonomy_name} / "
            f"{filing.filing_date if download_type == 'filing' else filing.taxonomy_version}"
        )
        
        try:
            # Update status to downloading
            if download_type == 'filing':
                self.db_repo.update_download_status(str(filing.search_id), STATUS_DOWNLOADING)
            else:
                self.db_repo.update_taxonomy_status(str(filing.library_id), STATUS_DOWNLOADING)
            
            # Build target directory based on type
            if download_type == 'filing':
                target_dir = self.path_resolver.build_filing_path(filing)
            else:
                target_dir = self.path_resolver.build_taxonomy_path(filing)
            
            logger.info(f"{LOG_PROCESS} Target directory: {target_dir}")
            logger.info(f"{LOG_PROCESS} Target directory (absolute): {target_dir.resolve()}")
            
            # Get download URL
            url = filing.filing_url if download_type == 'filing' else filing.source_url
            
            # Download and extract using distribution processor
            processing_result = await self.distribution_processor.download_and_extract(
                url,
                target_dir
            )
            
            if not processing_result.success:
                result.error_stage = processing_result.error_stage
                result.download_result = processing_result.download_result
                result.extraction_result = processing_result.extraction_result
                await self.failure_handler.handle_failure(filing, result, download_type)
                return result
            
            result.download_result = processing_result.download_result
            result.extraction_result = processing_result.extraction_result
            
            # Validate extraction
            validation_result = self.validator.validate_extraction(target_dir)
            if not validation_result.valid:
                result.error_stage = 'validation'
                await self.failure_handler.handle_failure(filing, result, download_type)
                return result
            
            logger.info(f"{LOG_OUTPUT} Validation passed: {validation_result.file_count} files found")
            
            # CRITICAL: Final paranoid verification
            if not target_dir.exists():
                logger.error(f"{LOG_OUTPUT} CRITICAL: Directory vanished after validation!")
                result.error_stage = 'verification'
                await self.failure_handler.handle_failure(filing, result, download_type)
                return result
            
            final_file_count = len(list(target_dir.rglob('*')))
            if final_file_count == 0:
                logger.error(f"{LOG_OUTPUT} CRITICAL: Directory exists but contains no files!")
                result.error_stage = 'verification'
                await self.failure_handler.handle_failure(filing, result, download_type)
                return result
            
            logger.info(
                f"{LOG_OUTPUT} Final verification passed: {final_file_count} files "
                f"confirmed in {target_dir}"
            )
            
            # Update database based on type
            if download_type == 'filing':
                # Create DownloadedFiling record
                db_success = self.db_repo.create_downloaded_filing(
                    search_id=str(filing.search_id),
                    entity_id=str(filing.entity_id),
                    download_directory=target_dir,
                    instance_file=None  # Could add instance file discovery here
                )
                
                if db_success:
                    # Update status to completed
                    self.db_repo.update_download_status(str(filing.search_id), STATUS_COMPLETED)
                    result.success = True
                    logger.info(f"{LOG_OUTPUT} Filing processed successfully")
                else:
                    result.error_stage = 'database'
                    logger.error("Database update failed despite successful download")
            else:
                # Update TaxonomyLibrary record
                db_success = self.db_repo.update_taxonomy_completion(
                    library_id=str(filing.library_id),
                    library_directory=target_dir,
                    total_files=final_file_count
                )
                
                if db_success:
                    result.success = True
                    logger.info(f"{LOG_OUTPUT} Taxonomy processed successfully")
                else:
                    result.error_stage = 'database'
                    logger.error("Database update failed despite successful download")
        
        except Exception as e:
            result.error_stage = 'unexpected'
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await self.failure_handler.handle_failure(filing, result, download_type)
        
        finally:
            result.total_duration = time.time() - start_time
        
        return result
    
    async def close(self):
        """Close coordinator and cleanup resources."""
        logger.info("Closing download coordinator")
        await self.http_handler.close()


__all__ = ['DownloadCoordinator']