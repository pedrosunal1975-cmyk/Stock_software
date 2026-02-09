# Path: downloader/engine/archive_downloader.py
"""
Archive Downloader

Handles downloading and extracting ZIP/TAR archive files.
Separated from main coordinator for better modularity.
"""

import os
from pathlib import Path

from downloader.core.logger import get_logger
from downloader.core.config_loader import ConfigLoader
from downloader.engine.protocol_handlers import HTTPHandler
from downloader.engine.retry_manager import RetryManager
from downloader.engine.extraction.archive_handler import ArchiveHandler
from downloader.engine.result import DownloadResult, ExtractionResult
from downloader.constants import LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'engine')


class ArchiveDownloader:
    """
    Downloads and extracts archive files.
    
    Handles:
    - Downloading archives to temp directory
    - Extracting archives to target directory
    - Retry logic
    - File verification
    """
    
    def __init__(
        self,
        http_handler: HTTPHandler,
        retry_manager: RetryManager,
        temp_dir: Path,
        config: ConfigLoader
    ):
        """
        Initialize archive downloader.
        
        Args:
            http_handler: HTTP download handler
            retry_manager: Retry manager for failed downloads
            temp_dir: Temporary directory for downloads
            config: Configuration loader
        """
        self.http_handler = http_handler
        self.retry_manager = retry_manager
        self.temp_dir = temp_dir
        self.config = config
    
    async def download_to_temp(self, url: str) -> DownloadResult:
        """
        Download archive file to temporary directory.
        
        Args:
            url: Source URL
            
        Returns:
            DownloadResult
        """
        # Extract filename from URL
        filename = os.path.basename(url)
        temp_path = self.temp_dir / filename
        
        logger.info(f"{LOG_PROCESS} Downloading to temp: {temp_path.name}")
        
        # Download with retry
        async def download_with_retry():
            return await self.http_handler.download(
                url=url,
                output_path=temp_path
            )
        
        try:
            download_result = await self.retry_manager.retry_async(
                download_with_retry
            )
            
            # Verify download succeeded
            if not download_result or not download_result.success:
                logger.error(f"Download failed")
                return DownloadResult(
                    success=False,
                    error_message="Download failed"
                )
            
            # Verify file exists
            if not temp_path.exists():
                logger.error(f"Downloaded file not found: {temp_path}")
                return DownloadResult(
                    success=False,
                    error_message=f"File not found: {temp_path}"
                )
            
            logger.info(f"{LOG_OUTPUT} Download complete: {temp_path.name}")
            
            return DownloadResult(
                success=True,
                file_path=temp_path
            )
        
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return DownloadResult(
                success=False,
                error_message=f"Unexpected error: {e}"
            )
    
    async def extract(self, archive_path: Path, target_dir: Path) -> ExtractionResult:
        """
        Extract archive to target directory.
        
        Args:
            archive_path: Path to archive file
            target_dir: Extraction destination
            
        Returns:
            ExtractionResult
        """
        logger.info(f"{LOG_PROCESS} Extracting: {archive_path.name} → {target_dir}")
        
        try:
            # Use ArchiveHandler for format-agnostic extraction
            handler = ArchiveHandler(self.config)
            extract_result = handler.extract(
                archive_path=archive_path,
                target_dir=target_dir,
                cleanup_archive=True  # Remove temp file after extraction
            )
            
            if extract_result.success:
                logger.info(
                    f"{LOG_OUTPUT} Extraction complete: {extract_result.files_extracted} "
                    f"files extracted to {target_dir}"
                )
            else:
                logger.error(f"Extraction failed: {extract_result.error_message}")
            
            return extract_result
        
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return ExtractionResult(
                success=False,
                error_message=str(e)
            )


__all__ = ['ArchiveDownloader']