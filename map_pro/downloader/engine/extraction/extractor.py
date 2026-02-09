# Path: downloader/engine/extraction/extractor.py
"""
Archive Extractor

Generic ZIP archive extraction with safety checks.
Extracts directly to target directory (no intermediate 'extracted' folder).

CRITICAL PRINCIPLE: Extractor ONLY extracts archives.
It does NOT:
- Search for instance files
- Parse content
- Understand file types
- Know about markets

Architecture:
- Direct extraction to target directory
- Path traversal protection
- Size limit checking
- Depth limit checking
- NO instance file discovery (removed - parser's responsibility)
"""

import zipfile
from pathlib import Path
from typing import Optional
import time

from downloader.core.logger import get_logger
from downloader.core.config_loader import ConfigLoader
from downloader.engine.result import ExtractionResult
from downloader.constants import (
    MAX_EXTRACTION_DEPTH,
    LOG_INPUT,
    LOG_PROCESS,
    LOG_OUTPUT,
)
from downloader.engine.extraction.constants import (
    DEFAULT_MAX_ARCHIVE_SIZE,
    ZIP_READ_MODE,
)

logger = get_logger(__name__, 'extraction')


class Extractor:
    """
    ZIP archive extractor with safety checks.
    
    RESPONSIBILITY: Extract archives to disk. Nothing more.
    
    Features:
    - Direct extraction to target directory
    - Path traversal protection (zip bombs)
    - Size limit checking
    - Depth limit checking
    
    Does NOT:
    - Search for instance files (parser's job)
    - Parse content
    - Understand file types
    
    Example:
        extractor = Extractor()
        result = extractor.extract_zip(
            zip_path=Path('/mnt/map_pro/downloader/temp/filing.zip'),
            target_dir=Path('/mnt/map_pro/downloader/entities/sec/COMPANY/filings/10-K/000123')
        )
        
        # Result contains:
        # - success: bool
        # - files_extracted: int
        # - extract_directory: Path
        # - duration: float
        
        # Result does NOT contain instance_file
        # Parser will find it later when needed
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize extractor.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.max_extraction_size = self.config.get(
            'max_archive_size',
            DEFAULT_MAX_ARCHIVE_SIZE
        )
    
    def extract_zip(
        self,
        zip_path: Path,
        target_dir: Path,
        cleanup_zip: bool = True
    ) -> ExtractionResult:
        """
        Extract ZIP archive to target directory.
        
        Extracts DIRECTLY to target_dir (no 'extracted' subfolder).
        
        DOES NOT search for instance files - that's parser's responsibility.
        
        Args:
            zip_path: Path to ZIP file
            target_dir: Target directory for extraction
            cleanup_zip: Whether to delete ZIP after successful extraction
            
        Returns:
            ExtractionResult with extraction details (NO instance_file)
        """
        logger.info(f"{LOG_INPUT} Extracting: {zip_path.name}")
        logger.info(f"{LOG_PROCESS} Target: {target_dir}")
        
        start_time = time.time()
        result = ExtractionResult(
            success=False,
            archive_path=zip_path,
            extract_directory=target_dir
        )
        
        try:
            # Validate ZIP file exists
            if not zip_path.exists():
                result.error_message = "ZIP file not found"
                logger.error(f"{LOG_OUTPUT} {result.error_message}")
                return result
            
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Open and validate ZIP
            with zipfile.ZipFile(zip_path, ZIP_READ_MODE) as zf:
                # Check for path traversal attacks
                if not self._validate_zip_safe(zf, target_dir):
                    result.error_message = "ZIP contains unsafe paths"
                    logger.error(f"{LOG_OUTPUT} {result.error_message}")
                    return result
                
                # Check total extracted size
                total_size = sum(info.file_size for info in zf.infolist())
                if total_size > self.max_extraction_size:
                    result.error_message = f"ZIP too large: {total_size} bytes"
                    logger.error(f"{LOG_OUTPUT} {result.error_message}")
                    return result
                
                logger.info(f"{LOG_PROCESS} Extracting {len(zf.namelist())} files...")
                
                # Extract all files DIRECTLY to target_dir
                zf.extractall(target_dir)
                
                result.files_extracted = len(zf.namelist())
                result.directory_structure = zf.namelist()
            
            # Success
            result.success = True
            result.duration = time.time() - start_time
            
            logger.info(
                f"{LOG_OUTPUT} Extraction complete: {result.files_extracted} files "
                f"in {result.duration:.2f}s"
            )
            
            # Cleanup ZIP if requested
            if cleanup_zip and result.success:
                try:
                    zip_path.unlink()
                    logger.info(f"{LOG_PROCESS} Deleted temporary ZIP: {zip_path.name}")
                except Exception as e:
                    logger.warning(f"Cannot delete ZIP: {e}")
        
        except zipfile.BadZipFile as e:
            result.error_message = f"Invalid ZIP file: {e}"
            result.duration = time.time() - start_time
            logger.error(f"{LOG_OUTPUT} {result.error_message}")
        
        except PermissionError as e:
            result.error_message = f"Permission denied: {e}"
            result.duration = time.time() - start_time
            logger.error(f"{LOG_OUTPUT} {result.error_message}")
        
        except Exception as e:
            result.error_message = f"Extraction failed: {e}"
            result.duration = time.time() - start_time
            logger.error(f"{LOG_OUTPUT} {result.error_message}", exc_info=True)
        
        return result
    
    def _validate_zip_safe(self, zip_file: zipfile.ZipFile, target_dir: Path) -> bool:
        """
        Validate ZIP does not contain path traversal attacks.
        
        Args:
            zip_file: Open ZipFile object
            target_dir: Target extraction directory
            
        Returns:
            True if ZIP is safe to extract
        """
        for member in zip_file.namelist():
            # Resolve member path
            member_path = target_dir / member
            
            try:
                # Check if resolved path is within target directory
                member_path.resolve().relative_to(target_dir.resolve())
            except ValueError:
                # Path escapes target directory
                logger.error(f"Unsafe path in ZIP: {member}")
                return False
            
            # Check depth
            depth = len(Path(member).parts)
            if depth > MAX_EXTRACTION_DEPTH:
                logger.error(f"Path too deep in ZIP: {member} (depth={depth})")
                return False
        
        return True


__all__ = ['Extractor']