# Path: downloader/engine/validator.py
"""
Download and Extraction Validator

Pre-download and post-extraction validation.
Ensures files exist physically before database updates.

Architecture:
- URL validation before download
- File size validation
- Directory existence verification
- Instance file discovery
- Physical reality checks
"""

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import os

from downloader.core.logger import get_logger
from downloader.core.config_loader import ConfigLoader
from downloader.engine.result import ValidationResult
from downloader.constants import (
    MIN_ZIP_SIZE,
    INSTANCE_FILE_PATTERNS,
    MAX_EXTRACTION_DEPTH,
    LOG_INPUT,
    LOG_PROCESS,
    LOG_OUTPUT,
)
from downloader.engine.constants import VALID_URL_SCHEMES

logger = get_logger(__name__, 'engine')


class Validator:
    """
    Validates downloads and extractions.
    
    Critical principle: Database reflects reality.
    Always verify physical files before updating database.
    
    Example:
        validator = Validator()
        
        # Before download
        url_valid = validator.validate_url('https://example.com/file.zip')
        
        # After extraction
        result = validator.validate_extraction(
            directory='/path/to/extracted',
            expected_files=10
        )
        if result.valid:
            update_database()
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize validator.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
    
    def validate_url(self, url: str) -> bool:
        """
        Validate URL format and accessibility.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid format
        """
        logger.debug(f"{LOG_PROCESS} Validating URL: {url}")
        
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                logger.warning(f"Invalid URL format: {url}")
                return False
            
            # Must be HTTP or HTTPS
            if parsed.scheme not in VALID_URL_SCHEMES:
                logger.warning(f"URL must be HTTP/HTTPS: {url}")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False
    
    def validate_download(
        self,
        file_path: Path,
        min_size: int = MIN_ZIP_SIZE
    ) -> ValidationResult:
        """
        Validate downloaded file.
        
        CRITICAL: Checks physical file existence and size.
        
        Args:
            file_path: Path to downloaded file
            min_size: Minimum expected file size in bytes
            
        Returns:
            ValidationResult with check details
        """
        logger.info(f"{LOG_INPUT} Validating download: {file_path}")
        
        result = ValidationResult(valid=True)
        
        # Check 1: File exists
        if file_path.exists():
            result.add_check('file_exists', True)
        else:
            result.add_check('file_exists', False, 'File does not exist on disk')
            result.valid = False
            return result
        
        # Check 2: Is actually a file (not directory)
        if file_path.is_file():
            result.add_check('is_file', True)
        else:
            result.add_check('is_file', False, 'Path is not a file')
            result.valid = False
            return result
        
        # Check 3: File size > minimum
        try:
            file_size = file_path.stat().st_size
            if file_size >= min_size:
                result.add_check('minimum_size', True)
            else:
                result.add_check(
                    'minimum_size',
                    False,
                    f'File too small: {file_size} bytes (minimum {min_size})'
                )
                result.valid = False
        except Exception as e:
            result.add_check('minimum_size', False, f'Cannot read file size: {e}')
            result.valid = False
        
        # Check 4: File is readable
        try:
            if os.access(file_path, os.R_OK):
                result.add_check('readable', True)
            else:
                result.add_check('readable', False, 'File is not readable')
                result.valid = False
        except Exception as e:
            result.add_check('readable', False, f'Cannot check read access: {e}')
            result.valid = False
        
        logger.info(f"{LOG_OUTPUT} Validation: {'PASSED' if result.valid else 'FAILED'}")
        
        return result
    
    def validate_extraction(
        self,
        directory: Path,
        expected_min_files: int = 1
    ) -> ValidationResult:
        """
        Validate extraction directory.
        
        CRITICAL: Verifies physical files exist before database update.
        
        Args:
            directory: Path to extraction directory
            expected_min_files: Minimum expected files
            
        Returns:
            ValidationResult with verification details
        """
        logger.info(f"{LOG_INPUT} Validating extraction: {directory}")
        
        result = ValidationResult(valid=True)
        
        # Check 1: Directory exists
        if directory.exists():
            result.add_check('directory_exists', True)
            result.directory_exists = True
        else:
            result.add_check('directory_exists', False, 'Directory does not exist')
            result.valid = False
            result.directory_exists = False
            return result
        
        # Check 2: Is actually a directory
        if directory.is_dir():
            result.add_check('is_directory', True)
        else:
            result.add_check('is_directory', False, 'Path is not a directory')
            result.valid = False
            return result
        
        # Check 3: Count files (recursive)
        try:
            file_count = self._count_files_recursive(directory)
            result.file_count = file_count
            
            if file_count >= expected_min_files:
                result.add_check('minimum_files', True)
            else:
                result.add_check(
                    'minimum_files',
                    False,
                    f'Too few files: {file_count} (expected >={expected_min_files})'
                )
                result.valid = False
        except Exception as e:
            result.add_check('minimum_files', False, f'Cannot count files: {e}')
            result.valid = False
        
        # Check 4: Directory is accessible
        try:
            if os.access(directory, os.R_OK | os.X_OK):
                result.add_check('accessible', True)
            else:
                result.add_check('accessible', False, 'Directory not accessible')
                result.valid = False
        except Exception as e:
            result.add_check('accessible', False, f'Cannot check access: {e}')
            result.valid = False
        
        logger.info(f"{LOG_OUTPUT} Validation: {'PASSED' if result.valid else 'FAILED'}")
        logger.info(f"{LOG_OUTPUT} Files found: {result.file_count}")
        
        return result
    
    def find_instance_file(self, directory: Path) -> Optional[Path]:
        """
        Find instance file in extracted directory.
        
        Searches for main XBRL instance document using known patterns.
        
        Args:
            directory: Root directory to search
            
        Returns:
            Path to instance file or None if not found
        """
        logger.info(f"{LOG_INPUT} Searching for instance file in: {directory}")
        
        if not directory.exists() or not directory.is_dir():
            logger.warning("Directory does not exist")
            return None
        
        # Try each pattern
        for pattern in INSTANCE_FILE_PATTERNS:
            try:
                # Use rglob for recursive search
                for file_path in directory.rglob(pattern):
                    # Check depth to avoid too deep searches
                    try:
                        depth = len(file_path.relative_to(directory).parts)
                        if depth > MAX_EXTRACTION_DEPTH:
                            continue
                    except ValueError:
                        continue
                    
                    if file_path.is_file():
                        logger.info(f"{LOG_OUTPUT} Found instance file: {file_path.name}")
                        return file_path
            
            except Exception as e:
                logger.warning(f"Error searching pattern {pattern}: {e}")
                continue
        
        logger.warning(f"{LOG_OUTPUT} No instance file found")
        return None
    
    def _count_files_recursive(
        self,
        directory: Path,
        max_depth: int = MAX_EXTRACTION_DEPTH
    ) -> int:
        """
        Count files recursively in directory.
        
        Args:
            directory: Root directory
            max_depth: Maximum depth to search
            
        Returns:
            Number of files found
        """
        count = 0
        
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    # Check depth
                    try:
                        depth = len(item.relative_to(directory).parts)
                        if depth <= max_depth:
                            count += 1
                    except ValueError:
                        continue
        except Exception as e:
            logger.warning(f"Error counting files: {e}")
        
        return count
    
    def verify_temp_space(self, required_bytes: int) -> bool:
        """
        Verify sufficient space in temp directory.
        
        Args:
            required_bytes: Required space in bytes
            
        Returns:
            True if sufficient space available
        """
        temp_dir = self.config.get('downloader_temp_dir')
        
        if not temp_dir:
            logger.warning("Temp directory not configured")
            return False
        
        try:
            stat = os.statvfs(temp_dir)
            free_bytes = stat.f_bavail * stat.f_frsize
            
            if free_bytes >= required_bytes:
                return True
            else:
                logger.warning(
                    f"Insufficient temp space: {free_bytes} bytes available, "
                    f"{required_bytes} required"
                )
                return False
        except Exception as e:
            logger.error(f"Cannot check temp space: {e}")
            return False


__all__ = ['Validator']