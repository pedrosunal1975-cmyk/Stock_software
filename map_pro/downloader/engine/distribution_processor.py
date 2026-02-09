# Path: downloader/engine/distribution_processor.py
"""
Distribution Processor

Handles routing and processing of different distribution types.
Automatically detects and processes:
- ZIP archives
- Individual XSD schemas
- Directory structures

100% distribution-agnostic - no hardcoded assumptions.
"""

from pathlib import Path
from typing import Optional

from downloader.core.logger import get_logger
from downloader.core.config_loader import ConfigLoader
from downloader.engine.distribution_detector import DistributionDetector
from downloader.engine.extraction.xsd_handler import XSDHandler
from downloader.engine.extraction.directory_handler import DirectoryHandler
from downloader.engine.archive_downloader import ArchiveDownloader
from downloader.engine.result import ProcessingResult, ExtractionResult
from downloader.constants import LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'engine')


class DistributionProcessor:
    """
    Processes downloads based on distribution type.
    
    Routes to appropriate handler:
    - archive â†’ ArchiveDownloader
    - xsd â†’ XSDHandler
    - directory â†’ DirectoryHandler
    """
    
    def __init__(self, archive_downloader: ArchiveDownloader, config: Optional[ConfigLoader] = None):
        """
        Initialize distribution processor.
        
        Args:
            archive_downloader: Archive download/extraction handler
            config: Optional ConfigLoader instance for User-Agent configuration
        """
        self.archive_downloader = archive_downloader
        self.config = config if config else ConfigLoader()
    
    async def download_and_extract(self, url: str, target_dir: Path) -> ProcessingResult:
        """
        Download and extract using distribution-agnostic approach.
        
        Automatically detects distribution type (ZIP, XSD, directory) and
        routes to appropriate handler.
        
        Args:
            url: Source URL
            target_dir: Target directory for extracted files
            
        Returns:
            ProcessingResult
        """
        result = ProcessingResult(success=False)
        
        logger.info(f"{LOG_PROCESS} Starting distribution-agnostic download")
        
        # Step 1: Detect distribution type
        logger.info(f"{LOG_PROCESS} Detecting distribution type")
        detector = DistributionDetector(config=self.config)
        
        try:
            detection = await detector.detect(url)
            await detector.close()
            
            if not detection['exists']:
                result.error_stage = 'detection'
                # Build detailed error message from detection result
                if 'error' in detection:
                    # Exception occurred
                    actual_error = detection['error']
                elif 'status' in detection:
                    # HTTP request succeeded but got non-200 status
                    actual_error = f"HTTP {detection['status']}"
                else:
                    actual_error = "URL not accessible"
                
                result.error_message = f"URL not found: {url} - {actual_error}"
                logger.error(f"{LOG_OUTPUT} URL not accessible: {actual_error}")
                return result
            
            dist_type = detection['type']
            working_url = detection['url']  # May be different from original
            
            logger.info(f"{LOG_OUTPUT} Detected type: {dist_type}")
            logger.info(f"{LOG_OUTPUT} Working URL: {working_url}")
            
            # Step 2: Route to appropriate handler
            if dist_type == 'archive':
                return await self._handle_archive(working_url, target_dir)

            elif dist_type == 'ixbrl':
                return await self._handle_ixbrl(working_url, target_dir)

            elif dist_type == 'xsd':
                return await self._handle_xsd(working_url, target_dir)

            elif dist_type == 'directory':
                return await self._handle_directory(working_url, target_dir)

            else:
                # Unknown type - try single file download as fallback
                logger.warning(f"Unknown distribution type, trying single file download")
                return await self._handle_ixbrl(working_url, target_dir)
        
        except Exception as e:
            result.error_stage = 'detection'
            result.error_message = str(e)
            logger.error(f"Error in distribution detection: {e}")
            return result
    
    async def _handle_ixbrl(self, url: str, target_dir: Path) -> ProcessingResult:
        """
        Handle iXBRL/XHTML single file downloads.

        Downloads the file directly to target directory without extraction.

        Args:
            url: iXBRL file URL
            target_dir: Target directory

        Returns:
            ProcessingResult
        """
        result = ProcessingResult(success=False)

        logger.info(f"{LOG_PROCESS} Handling as iXBRL single file")

        try:
            # Ensure target directory exists
            target_dir.mkdir(parents=True, exist_ok=True)

            # Download directly to target (no temp, no extraction)
            temp_result = await self.archive_downloader.download_to_temp(url)
            if not temp_result.success:
                result.error_stage = 'download'
                result.download_result = temp_result
                return result

            result.download_result = temp_result

            # Move file to target directory (no extraction needed)
            import shutil
            source_path = temp_result.file_path
            target_path = target_dir / source_path.name

            shutil.move(str(source_path), str(target_path))

            result.success = True
            result.extraction_result = ExtractionResult(
                success=True,
                files_extracted=1,
                extract_directory=target_dir
            )
            logger.info(f"{LOG_OUTPUT} iXBRL download complete: {target_path.name}")
            return result

        except Exception as e:
            result.error_stage = 'ixbrl_download'
            result.error_message = str(e)
            logger.error(f"iXBRL download error: {e}")
            return result

    async def _handle_archive(self, url: str, target_dir: Path) -> ProcessingResult:
        """
        Handle ZIP/archive downloads.

        Args:
            url: Archive URL
            target_dir: Target directory

        Returns:
            ProcessingResult
        """
        result = ProcessingResult(success=False)

        logger.info(f"{LOG_PROCESS} Handling as archive")
        
        # Download to temp
        temp_result = await self.archive_downloader.download_to_temp(url)
        if not temp_result.success:
            result.error_stage = 'download'
            result.download_result = temp_result
            return result
        
        result.download_result = temp_result
        
        # Extract
        extract_result = await self.archive_downloader.extract(
            temp_result.file_path,
            target_dir
        )
        if not extract_result.success:
            result.error_stage = 'extraction'
            result.extraction_result = extract_result
            return result
        
        result.extraction_result = extract_result
        result.success = True
        return result
    
    async def _handle_xsd(self, url: str, target_dir: Path) -> ProcessingResult:
        """
        Handle individual XSD file downloads.
        
        Args:
            url: XSD URL
            target_dir: Target directory
            
        Returns:
            ProcessingResult
        """
        result = ProcessingResult(success=False)
        
        logger.info(f"{LOG_PROCESS} Handling as XSD schema")
        
        try:
            xsd_handler = XSDHandler()
            xsd_result = await xsd_handler.download_schema(url, target_dir)
            await xsd_handler.close()
            
            if xsd_result['success']:
                result.success = True
                result.extraction_result = ExtractionResult(
                    success=True,
                    files_extracted=xsd_result['files_downloaded'],
                    extract_directory=target_dir
                )
                logger.info(f"{LOG_OUTPUT} XSD download complete: {xsd_result['files_downloaded']} files")
            else:
                result.error_stage = 'xsd_download'
                result.error_message = "XSD download failed"
                logger.error("XSD download failed")
            
            return result
        
        except Exception as e:
            result.error_stage = 'xsd_download'
            result.error_message = str(e)
            logger.error(f"XSD download error: {e}")
            return result
    
    async def _handle_directory(self, url: str, target_dir: Path) -> ProcessingResult:
        """
        Handle directory mirroring.
        
        Args:
            url: Directory URL
            target_dir: Target directory
            
        Returns:
            ProcessingResult
        """
        result = ProcessingResult(success=False)
        
        logger.info(f"{LOG_PROCESS} Handling as directory structure")
        
        try:
            dir_handler = DirectoryHandler()
            dir_result = await dir_handler.mirror_directory(url, target_dir)
            await dir_handler.close()
            
            if dir_result['success']:
                result.success = True
                result.extraction_result = ExtractionResult(
                    success=True,
                    files_extracted=dir_result['files_downloaded'],
                    extract_directory=target_dir
                )
                logger.info(f"{LOG_OUTPUT} Directory mirror complete: {dir_result['files_downloaded']} files")
            else:
                result.error_stage = 'directory_mirror'
                result.error_message = "Directory mirror failed"
                logger.error("Directory mirror failed")
            
            return result
        
        except Exception as e:
            result.error_stage = 'directory_mirror'
            result.error_message = str(e)
            logger.error(f"Directory mirror error: {e}")
            return result


__all__ = ['DistributionProcessor']