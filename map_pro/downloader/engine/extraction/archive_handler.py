# Path: downloader/engine/extraction/archive_handler.py
"""
Archive Handler Factory

Multi-format archive extraction with pluggable extractors.
Supports ZIP, TAR, TAR.GZ, TAR.XZ, and extensible for future formats.

Architecture:
- Factory pattern for archive type detection
- Individual extractor classes per format
- Common interface (ExtractionResult)
- Easy to extend for new formats

CRITICAL PRINCIPLE: Format-agnostic extraction.
No assumptions about archive format - detect and handle dynamically.
"""

import zipfile
import tarfile
from pathlib import Path
from typing import Optional, Type
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
    TAR_READ_MODE,
    TAR_GZ_MODE,
    TAR_BZ2_MODE,
    TAR_XZ_MODE,
)

logger = get_logger(__name__, 'extraction')


class BaseExtractor:
    """
    Base class for archive extractors.
    
    All format-specific extractors inherit from this.
    Provides common interface and validation.
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize base extractor.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.max_extraction_size = self.config.get(
            'max_archive_size',
            DEFAULT_MAX_ARCHIVE_SIZE
        )
    
    def extract(
        self,
        archive_path: Path,
        target_dir: Path,
        cleanup_archive: bool = True
    ) -> ExtractionResult:
        """
        Extract archive to target directory.
        
        Must be implemented by subclasses.
        
        Args:
            archive_path: Path to archive file
            target_dir: Target directory for extraction
            cleanup_archive: Whether to delete archive after extraction
            
        Returns:
            ExtractionResult with extraction details
        """
        raise NotImplementedError("Subclasses must implement extract()")
    
    def _validate_depth(self, member_path: str) -> bool:
        """
        Validate path depth to prevent zip bombs.
        
        Args:
            member_path: Relative path within archive
            
        Returns:
            True if depth is acceptable
        """
        depth = len(Path(member_path).parts)
        if depth > MAX_EXTRACTION_DEPTH:
            logger.error(f"Path too deep: {member_path} (depth={depth})")
            return False
        return True
    
    def _validate_path_traversal(
        self,
        member_path: Path,
        target_dir: Path
    ) -> bool:
        """
        Validate path doesn't escape target directory.
        
        Args:
            member_path: Full member path
            target_dir: Target extraction directory
            
        Returns:
            True if path is safe
        """
        try:
            # Check if resolved path is within target directory
            member_path.resolve().relative_to(target_dir.resolve())
            return True
        except ValueError:
            # Path escapes target directory
            logger.error(f"Unsafe path detected: {member_path}")
            return False


class ZipExtractor(BaseExtractor):
    """
    ZIP file extractor.
    
    Handles: .zip files
    """
    
    def extract(
        self,
        archive_path: Path,
        target_dir: Path,
        cleanup_archive: bool = True
    ) -> ExtractionResult:
        """
        Extract ZIP archive.
        
        Args:
            archive_path: Path to ZIP file
            target_dir: Target directory
            cleanup_archive: Whether to delete ZIP after extraction
            
        Returns:
            ExtractionResult
        """
        logger.info(f"{LOG_INPUT} Extracting ZIP: {archive_path.name}")
        
        start_time = time.time()
        result = ExtractionResult(
            success=False,
            archive_path=archive_path,
            extract_directory=target_dir
        )
        
        try:
            # Validate ZIP exists
            if not archive_path.exists():
                result.error_message = "ZIP file not found"
                logger.error(f"{LOG_OUTPUT} {result.error_message}")
                return result
            
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Open and validate ZIP
            with zipfile.ZipFile(archive_path, ZIP_READ_MODE) as zf:
                # Validate safety
                if not self._validate_zip_safe(zf, target_dir):
                    result.error_message = "ZIP contains unsafe paths"
                    logger.error(f"{LOG_OUTPUT} {result.error_message}")
                    return result
                
                # Check total size
                total_size = sum(info.file_size for info in zf.infolist())
                if total_size > self.max_extraction_size:
                    result.error_message = f"ZIP too large: {total_size} bytes"
                    logger.error(f"{LOG_OUTPUT} {result.error_message}")
                    return result
                
                logger.info(f"{LOG_PROCESS} Extracting {len(zf.namelist())} files...")
                
                # Extract all
                zf.extractall(target_dir)
                
                result.files_extracted = len(zf.namelist())
                result.directory_structure = zf.namelist()
            
            # Success
            result.success = True
            result.duration = time.time() - start_time
            
            logger.info(
                f"{LOG_OUTPUT} ZIP extraction complete: {result.files_extracted} files "
                f"in {result.duration:.2f}s"
            )
            
            # Cleanup if requested
            if cleanup_archive and result.success:
                try:
                    archive_path.unlink()
                    logger.info(f"{LOG_PROCESS} Deleted archive: {archive_path.name}")
                except Exception as e:
                    logger.warning(f"Cannot delete archive: {e}")
        
        except zipfile.BadZipFile as e:
            result.error_message = f"Invalid ZIP file: {e}"
            result.duration = time.time() - start_time
            logger.error(f"{LOG_OUTPUT} {result.error_message}")
        
        except Exception as e:
            result.error_message = f"ZIP extraction failed: {e}"
            result.duration = time.time() - start_time
            logger.error(f"{LOG_OUTPUT} {result.error_message}", exc_info=True)
        
        return result
    
    def _validate_zip_safe(self, zip_file: zipfile.ZipFile, target_dir: Path) -> bool:
        """Validate ZIP for path traversal attacks."""
        for member in zip_file.namelist():
            member_path = target_dir / member
            
            if not self._validate_path_traversal(member_path, target_dir):
                return False
            
            if not self._validate_depth(member):
                return False
        
        return True


class TarExtractor(BaseExtractor):
    """
    TAR archive extractor.
    
    Handles: .tar, .tar.gz, .tgz, .tar.bz2, .tar.xz
    """
    
    def extract(
        self,
        archive_path: Path,
        target_dir: Path,
        cleanup_archive: bool = True
    ) -> ExtractionResult:
        """
        Extract TAR archive (including compressed variants).
        
        Args:
            archive_path: Path to TAR file
            target_dir: Target directory
            cleanup_archive: Whether to delete TAR after extraction
            
        Returns:
            ExtractionResult
        """
        logger.info(f"{LOG_INPUT} Extracting TAR: {archive_path.name}")
        
        start_time = time.time()
        result = ExtractionResult(
            success=False,
            archive_path=archive_path,
            extract_directory=target_dir
        )
        
        try:
            # Validate TAR exists
            if not archive_path.exists():
                result.error_message = "TAR file not found"
                logger.error(f"{LOG_OUTPUT} {result.error_message}")
                return result
            
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Detect compression mode
            mode = self._detect_tar_mode(archive_path)
            logger.info(f"{LOG_PROCESS} TAR mode: {mode}")
            
            # Open and validate TAR
            with tarfile.open(archive_path, mode) as tf:
                # Validate safety
                if not self._validate_tar_safe(tf, target_dir):
                    result.error_message = "TAR contains unsafe paths"
                    logger.error(f"{LOG_OUTPUT} {result.error_message}")
                    return result
                
                # Get member list
                members = tf.getmembers()
                
                # Check total size
                total_size = sum(m.size for m in members if m.isfile())
                if total_size > self.max_extraction_size:
                    result.error_message = f"TAR too large: {total_size} bytes"
                    logger.error(f"{LOG_OUTPUT} {result.error_message}")
                    return result
                
                logger.info(f"{LOG_PROCESS} Extracting {len(members)} items...")
                
                # Extract all
                tf.extractall(target_dir)
                
                result.files_extracted = len(members)
                result.directory_structure = [m.name for m in members]
            
            # Success
            result.success = True
            result.duration = time.time() - start_time
            
            logger.info(
                f"{LOG_OUTPUT} TAR extraction complete: {result.files_extracted} items "
                f"in {result.duration:.2f}s"
            )
            
            # Cleanup if requested
            if cleanup_archive and result.success:
                try:
                    archive_path.unlink()
                    logger.info(f"{LOG_PROCESS} Deleted archive: {archive_path.name}")
                except Exception as e:
                    logger.warning(f"Cannot delete archive: {e}")
        
        except tarfile.TarError as e:
            result.error_message = f"Invalid TAR file: {e}"
            result.duration = time.time() - start_time
            logger.error(f"{LOG_OUTPUT} {result.error_message}")
        
        except Exception as e:
            result.error_message = f"TAR extraction failed: {e}"
            result.duration = time.time() - start_time
            logger.error(f"{LOG_OUTPUT} {result.error_message}", exc_info=True)
        
        return result
    
    def _detect_tar_mode(self, archive_path: Path) -> str:
        """
        Detect TAR compression mode from file extension.
        
        Args:
            archive_path: Path to TAR file
            
        Returns:
            Mode string for tarfile.open()
        """
        name_lower = archive_path.name.lower()
        
        if name_lower.endswith('.tar.gz') or name_lower.endswith('.tgz'):
            return TAR_GZ_MODE
        elif name_lower.endswith('.tar.bz2') or name_lower.endswith('.tbz2'):
            return TAR_BZ2_MODE
        elif name_lower.endswith('.tar.xz') or name_lower.endswith('.txz'):
            return TAR_XZ_MODE
        else:
            return TAR_READ_MODE  # Uncompressed TAR
    
    def _validate_tar_safe(self, tar_file: tarfile.TarFile, target_dir: Path) -> bool:
        """Validate TAR for path traversal attacks."""
        for member in tar_file.getmembers():
            member_path = target_dir / member.name
            
            if not self._validate_path_traversal(member_path, target_dir):
                return False
            
            if not self._validate_depth(member.name):
                return False
        
        return True


class ArchiveHandler:
    """
    Archive handler factory.
    
    Detects archive format and delegates to appropriate extractor.
    
    Supported formats:
    - .zip
    - .tar
    - .tar.gz, .tgz
    - .tar.bz2, .tbz2
    - .tar.xz, .txz
    
    Example:
        handler = ArchiveHandler()
        result = handler.extract(
            archive_path=Path('/mnt/map_pro/downloader/temp/filing.zip'),
            target_dir=Path('/mnt/map_pro/downloader/entities/...')
        )

        # Works with any supported format!
        result = handler.extract(
            archive_path=Path('/mnt/map_pro/downloader/temp/taxonomy.tar.gz'),
            target_dir=Path('/mnt/map_pro/taxonomies/libraries/...')
        )
    """
    
    # Map file extensions to extractor classes
    EXTRACTOR_MAP = {
        '.zip': ZipExtractor,
        '.tar': TarExtractor,
        '.tar.gz': TarExtractor,
        '.tgz': TarExtractor,
        '.tar.bz2': TarExtractor,
        '.tbz2': TarExtractor,
        '.tar.xz': TarExtractor,
        '.txz': TarExtractor,
    }
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize archive handler.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
    
    def extract(
        self,
        archive_path: Path,
        target_dir: Path,
        cleanup_archive: bool = True
    ) -> ExtractionResult:
        """
        Extract archive using appropriate extractor.
        
        Automatically detects format from file extension.
        
        Args:
            archive_path: Path to archive file
            target_dir: Target directory for extraction
            cleanup_archive: Whether to delete archive after extraction
            
        Returns:
            ExtractionResult
            
        Raises:
            ValueError: If archive format is not supported
        """
        logger.info(f"{LOG_INPUT} Processing archive: {archive_path.name}")
        
        # Detect format
        extractor_class = self._detect_format(archive_path)
        
        if extractor_class is None:
            error_msg = f"Unsupported archive format: {archive_path.suffix}"
            logger.error(f"{LOG_OUTPUT} {error_msg}")
            
            result = ExtractionResult(
                success=False,
                archive_path=archive_path,
                extract_directory=target_dir,
                error_message=error_msg
            )
            return result
        
        # Create extractor and extract
        logger.info(f"{LOG_PROCESS} Using {extractor_class.__name__}")
        extractor = extractor_class(config=self.config)
        
        return extractor.extract(archive_path, target_dir, cleanup_archive)
    
    def _detect_format(self, archive_path: Path) -> Optional[Type[BaseExtractor]]:
        """
        Detect archive format from file extension.
        
        Args:
            archive_path: Path to archive
            
        Returns:
            Extractor class or None if unsupported
        """
        name_lower = archive_path.name.lower()
        
        # Try compound extensions first (.tar.gz, .tar.xz, etc.)
        for ext, extractor_class in self.EXTRACTOR_MAP.items():
            if '.' in ext[1:]:  # Compound extension
                if name_lower.endswith(ext):
                    logger.debug(f"Detected format: {ext}")
                    return extractor_class
        
        # Try simple extensions
        suffix_lower = archive_path.suffix.lower()
        extractor_class = self.EXTRACTOR_MAP.get(suffix_lower)
        
        if extractor_class:
            logger.debug(f"Detected format: {suffix_lower}")
        else:
            logger.warning(f"Unknown format: {suffix_lower}")
        
        return extractor_class
    
    def is_supported(self, archive_path: Path) -> bool:
        """
        Check if archive format is supported.
        
        Args:
            archive_path: Path to archive
            
        Returns:
            True if format is supported
        """
        return self._detect_format(archive_path) is not None
    
    @classmethod
    def get_supported_formats(cls) -> list:
        """
        Get list of supported archive formats.
        
        Returns:
            List of supported extensions
        """
        return list(cls.EXTRACTOR_MAP.keys())


__all__ = [
    'ArchiveHandler',
    'BaseExtractor',
    'ZipExtractor',
    'TarExtractor',
]