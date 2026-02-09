# Path: downloader/engine/result.py
"""
Download Result Objects

Type-safe, structured results for download operations.
Replaces raw dictionaries with proper data classes.

Architecture:
- DownloadResult: Single file download
- ExtractionResult: Single archive extraction
- ValidationResult: File/directory validation
- ProcessingResult: Complete download+extract+validate workflow
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class DownloadResult:
    """
    Result of a single file download operation.
    
    Attributes:
        success: Whether download succeeded
        file_path: Path where file was downloaded
        file_size: Size of downloaded file in bytes
        url: Source URL
        duration: Download duration in seconds
        error_message: Error message if failed
        status_code: HTTP status code
        chunks_downloaded: Number of chunks downloaded
    """
    success: bool
    file_path: Optional[Path] = None
    file_size: int = 0
    url: str = ''
    duration: float = 0.0
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    chunks_downloaded: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def download_speed_mbps(self) -> float:
        """Calculate download speed in MB/s."""
        if self.duration > 0 and self.file_size > 0:
            mb = self.file_size / (1024 * 1024)
            return mb / self.duration
        return 0.0
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for logging/storage."""
        return {
            'success': self.success,
            'file_path': str(self.file_path) if self.file_path else None,
            'file_size': self.file_size,
            'url': self.url,
            'duration': self.duration,
            'error_message': self.error_message,
            'status_code': self.status_code,
            'chunks_downloaded': self.chunks_downloaded,
            'download_speed_mbps': self.download_speed_mbps,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class ExtractionResult:
    """
    Result of archive extraction operation.
    
    Attributes:
        success: Whether extraction succeeded
        extract_directory: Path where files were extracted
        files_extracted: Number of files extracted
        archive_path: Path to archive file
        duration: Extraction duration in seconds
        error_message: Error message if failed
        directory_structure: Extracted directory structure
        instance_file: Path to discovered instance file
    """
    success: bool
    extract_directory: Optional[Path] = None
    files_extracted: int = 0
    archive_path: Optional[Path] = None
    duration: float = 0.0
    error_message: Optional[str] = None
    directory_structure: list[str] = field(default_factory=list)
    instance_file: Optional[Path] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for logging/storage."""
        return {
            'success': self.success,
            'extract_directory': str(self.extract_directory) if self.extract_directory else None,
            'files_extracted': self.files_extracted,
            'archive_path': str(self.archive_path) if self.archive_path else None,
            'duration': self.duration,
            'error_message': self.error_message,
            'directory_structure': self.directory_structure,
            'instance_file': str(self.instance_file) if self.instance_file else None,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class ValidationResult:
    """
    Result of file/directory validation.
    
    Attributes:
        valid: Whether validation passed
        checks_performed: List of validation checks performed
        checks_passed: List of checks that passed
        checks_failed: List of checks that failed
        error_messages: Detailed error messages
        warnings: Non-critical warnings
        file_count: Number of files found
        directory_exists: Whether target directory exists
    """
    valid: bool
    checks_performed: list[str] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    file_count: int = 0
    directory_exists: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    def add_check(self, check_name: str, passed: bool, message: str = ''):
        """Add validation check result."""
        self.checks_performed.append(check_name)
        if passed:
            self.checks_passed.append(check_name)
        else:
            self.checks_failed.append(check_name)
            if message:
                self.error_messages.append(f"{check_name}: {message}")
    
    def add_warning(self, message: str):
        """Add non-critical warning."""
        self.warnings.append(message)
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for logging/storage."""
        return {
            'valid': self.valid,
            'checks_performed': self.checks_performed,
            'checks_passed': self.checks_passed,
            'checks_failed': self.checks_failed,
            'error_messages': self.error_messages,
            'warnings': self.warnings,
            'file_count': self.file_count,
            'directory_exists': self.directory_exists,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class ProcessingResult:
    """
    Complete result for download + extract + validate workflow.
    
    Attributes:
        success: Whether entire workflow succeeded
        download_result: Download operation result
        extraction_result: Extraction operation result
        validation_result: Validation operation result
        total_duration: Total processing duration in seconds
        filing_directory: Final directory path for filing
        instance_file: Path to instance file
        cleanup_performed: Whether temp cleanup was performed
        error_stage: Which stage failed: detection, download, extract, validate
        error_message: Detailed error message
    """
    success: bool
    download_result: Optional[DownloadResult] = None
    extraction_result: Optional[ExtractionResult] = None
    validation_result: Optional[ValidationResult] = None
    total_duration: float = 0.0
    filing_directory: Optional[Path] = None
    instance_file: Optional[Path] = None
    cleanup_performed: bool = False
    error_stage: Optional[str] = None  # Which stage failed: detection, download, extract, validate
    error_message: Optional[str] = None  # Detailed error message
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for logging/storage."""
        return {
            'success': self.success,
            'download_result': self.download_result.to_dict() if self.download_result else None,
            'extraction_result': self.extraction_result.to_dict() if self.extraction_result else None,
            'validation_result': self.validation_result.to_dict() if self.validation_result else None,
            'total_duration': self.total_duration,
            'filing_directory': str(self.filing_directory) if self.filing_directory else None,
            'instance_file': str(self.instance_file) if self.instance_file else None,
            'cleanup_performed': self.cleanup_performed,
            'error_stage': self.error_stage,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat(),
        }


__all__ = [
    'DownloadResult',
    'ExtractionResult',
    'ValidationResult',
    'ProcessingResult',
]