# Path: database/models/taxonomy_libraries.py
"""
Taxonomy Library Model

Taxonomy library registry with file system verification.
Supports dynamic taxonomy downloading based on parser declarations.

Architecture:
- Database reflects reality (filesystem is truth)
- File existence verification
- Dynamic taxonomy discovery from parsed.json
- Integrity verification via file hashing
- Dependency tracking (which filings require which taxonomies)
- Download tracking with intelligent retry
"""

from pathlib import Path
from sqlalchemy import Column, String, Integer, DateTime, Text, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid as uuid_module

from database.models.base import Base
from database.core.logger import get_logger
from database.constants import (
    MAX_TAXONOMY_NAME_LENGTH,
    MAX_TAXONOMY_VERSION_LENGTH,
    MAX_STATUS_LENGTH,
    STATUS_PENDING,
    DEFAULT_FILE_COUNT,
    TAXONOMY_EXTENSIONS,
)

logger = get_logger(__name__, 'models')


class TaxonomyLibrary(Base):
    """
    Taxonomy library registry with comprehensive tracking.
    
    Tracks standard taxonomy libraries (US-GAAP, IFRS, ESEF, etc.).
    Supports dynamic downloading based on parser declarations.
    
    CRITICAL PRINCIPLE: Database is a REFLECTION of reality.
    Always use .files_actually_exist property to verify files
    exist on disk before using library.
    
    Features:
    - File integrity verification (SHA256 hashing)
    - Dependency tracking (which filings need which taxonomies)
    - Download retry with intelligent escalation
    - Alternative URL tracking
    - Detailed failure reason tracking
    
    Workflow:
    1. Parser reads parsed.json → finds taxonomy namespace
    2. Library module queries database for namespace
    3. If not found → create record with status='pending'
    4. Library module adds to download queue (or calls downloader)
    5. Downloader processes pending libraries
    6. After download → verify file_hash, call sync_with_reality()
    7. Mapper uses is_truly_available to check before mapping
    """
    __tablename__ = 'taxonomy_libraries'
    
    # ================================================================
    # PRIMARY IDENTIFICATION
    # ================================================================
    library_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
        comment="Unique library identifier"
    )
    taxonomy_name = Column(
        String(MAX_TAXONOMY_NAME_LENGTH),
        nullable=False,
        comment="Taxonomy name (e.g., 'us-gaap', 'ifrs-full', 'esef')"
    )
    taxonomy_version = Column(
        String(MAX_TAXONOMY_VERSION_LENGTH),
        nullable=False,
        comment="Taxonomy version (e.g., '2024', '2023')"
    )
    taxonomy_namespace = Column(
        Text,
        nullable=False,
        unique=True,
        comment="Full taxonomy namespace URI (unique identifier)"
    )
    
    # ================================================================
    # DOWNLOAD URLS (EXISTING + NEW)
    # ================================================================
    source_url = Column(
        Text,
        comment="Download source URL (original)"
    )
    primary_url = Column(
        Text,
        comment="Primary download URL (original)"
    )
    current_url = Column(
        Text,
        comment="Currently trying URL"
    )
    alternative_urls_tried = Column(
        JSONB,
        default=list,
        comment="List of alternative URLs attempted"
    )
    
    # ================================================================
    # FILE SYSTEM PATHS
    # ================================================================
    library_directory = Column(
        Text,
        comment="Path to library directory on filesystem"
    )
    downloaded_file_path = Column(
        Text,
        comment="Path to downloaded ZIP file"
    )
    downloaded_file_size = Column(
        Integer,
        comment="Downloaded file size in bytes"
    )
    expected_file_size = Column(
        Integer,
        comment="Expected file size in bytes"
    )
    extraction_path = Column(
        Text,
        comment="Path where files were extracted"
    )
    
    # ================================================================
    # FILE VERIFICATION (EXISTING)
    # ================================================================
    file_size = Column(
        Integer,
        comment="Archive file size in bytes (for download verification)"
    )
    file_hash = Column(
        String(128),
        comment="SHA256 hash of archive file (format: 'sha256:hexdigest')"
    )
    total_files = Column(
        Integer,
        default=DEFAULT_FILE_COUNT,
        comment="Total files in library (database count)"
    )
    file_count = Column(
        Integer,
        default=0,
        comment="Number of files extracted (new tracking)"
    )
    
    # ================================================================
    # STATUS TRACKING (EXISTING + NEW)
    # ================================================================
    download_status = Column(
        String(MAX_STATUS_LENGTH),
        default=STATUS_PENDING,
        comment="Download status: pending, downloading, downloaded, extracting, ready, failed, completed"
    )
    status = Column(
        String(MAX_STATUS_LENGTH),
        default=STATUS_PENDING,
        comment="Overall status: pending, active, inactive, failed"
    )
    validation_status = Column(
        String(MAX_STATUS_LENGTH),
        default='pending',
        comment="Validation status: pending, valid, incomplete, corrupted"
    )
    
    # ================================================================
    # ATTEMPT TRACKING (NEW)
    # ================================================================
    download_attempts = Column(
        Integer,
        default=0,
        comment="Number of download attempts"
    )
    extraction_attempts = Column(
        Integer,
        default=0,
        comment="Number of extraction attempts"
    )
    total_attempts = Column(
        Integer,
        default=0,
        comment="Total attempts (download + extraction)"
    )
    
    # ================================================================
    # FAILURE TRACKING (EXISTING + NEW)
    # ================================================================
    download_error = Column(
        Text,
        comment="Error message if download failed (existing)"
    )
    failure_stage = Column(
        String(MAX_STATUS_LENGTH),
        comment="Failure stage: download, extraction, validation (new)"
    )
    failure_reason = Column(
        String(MAX_STATUS_LENGTH),
        comment="Specific failure reason code (new)"
    )
    failure_details = Column(
        Text,
        comment="Full error message and details (new)"
    )
    
    # ================================================================
    # DEPENDENCY TRACKING (EXISTING)
    # ================================================================
    required_by_filings = Column(
        JSONB,
        default=list,
        comment="List of filing_search IDs that require this taxonomy"
    )
    taxonomy_metadata = Column(
        JSONB,
        comment="Additional taxonomy metadata from parser or manual entry"
    )
    
    # ================================================================
    # TIMESTAMPS (EXISTING + NEW)
    # ================================================================
    last_attempt_date = Column(
        DateTime(timezone=True),
        comment="Last download/extraction attempt timestamp (new)"
    )
    last_success_date = Column(
        DateTime(timezone=True),
        comment="Last successful download timestamp (new)"
    )
    download_completed_at = Column(
        DateTime(timezone=True),
        comment="Download completion timestamp (existing)"
    )
    last_verified_at = Column(
        DateTime(timezone=True),
        comment="Last file verification timestamp (existing)"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Record creation timestamp"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Record last update timestamp"
    )
    
    # ================================================================
    # TABLE CONSTRAINTS
    # ================================================================
    __table_args__ = (
        UniqueConstraint(
            'taxonomy_name',
            'taxonomy_version',
            name='taxonomy_name_version_unique'
        ),
        Index('idx_taxonomy_namespace', 'taxonomy_namespace'),
        Index('idx_taxonomy_status', 'download_status'),
        Index('idx_taxonomy_name_version', 'taxonomy_name', 'taxonomy_version'),
        Index('idx_download_status', 'download_status'),
        Index('idx_overall_status', 'status'),
    )
    
    # ================================================================
    # FILESYSTEM VERIFICATION PROPERTIES (EXISTING)
    # ================================================================
    
    @property
    def directory_exists(self) -> bool:
        """
        Check if library directory actually exists on disk.
        
        CRITICAL: This checks REALITY, not database.
        
        Returns:
            True if directory exists, False otherwise
        """
        if not self.library_directory:
            return False
        
        try:
            path = Path(self.library_directory)
            return path.exists() and path.is_dir()
        except Exception as e:
            logger.warning(
                f"Error checking directory for library {self.library_id}: {e}"
            )
            return False
    
    @property
    def actual_file_count(self) -> int:
        """
        Count actual files in library directory.
        
        CRITICAL: This counts REAL files, not database records.
        Only counts taxonomy-relevant files (.xsd, .xml, etc.)
        
        Returns:
            Number of actual taxonomy files on disk
        """
        if not self.directory_exists:
            return 0
        
        try:
            path = Path(self.library_directory)
            count = 0
            
            for file_path in path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in TAXONOMY_EXTENSIONS:
                    count += 1
            
            return count
        except Exception as e:
            logger.warning(
                f"Error counting files for library {self.library_id}: {e}"
            )
            return 0
    
    @property
    def files_actually_exist(self) -> bool:
        """
        Check if library files actually exist on disk.
        
        CRITICAL: Use this instead of trusting download_status.
        This is the TRUTH about file existence.
        
        Returns:
            True if directory exists and contains files
        """
        return self.directory_exists and self.actual_file_count > 0
    
    @property
    def database_matches_reality(self) -> bool:
        """
        Check if database record matches physical reality.
        
        Compares database file count with actual files on disk.
        
        Returns:
            True if counts match
        """
        actual = self.actual_file_count
        recorded = self.total_files or 0
        return actual == recorded
    
    @property
    def is_truly_available(self) -> bool:
        """
        Check if library is TRULY available for use.
        
        This is the CORRECT way to check availability:
        - Database says download completed
        - Database says it has files
        - Files ACTUALLY exist on disk
        
        Returns:
            True only if library is genuinely ready to use
        """
        # Accept either 'completed' (old) or 'ready' (new)
        valid_statuses = {'completed', 'ready'}
        if self.download_status not in valid_statuses:
            return False
        
        # Check database file count
        if not self.total_files or self.total_files == 0:
            return False
        
        # CRITICAL: Verify files actually exist
        if not self.files_actually_exist:
            return False
        
        return True
    
    # ================================================================
    # RETRY TRACKING PROPERTIES (NEW)
    # ================================================================
    
    @property
    def needs_retry(self) -> bool:
        """
        Check if download needs retry.
        
        Returns:
            True if failed but under max attempts
        """
        return (
            self.download_status == 'failed' and
            self.total_attempts < 6  # MAX_TOTAL_ATTEMPTS
        )
    
    @property
    def download_failed_permanently(self) -> bool:
        """
        Check if download permanently failed.
        
        Returns:
            True if exceeded max attempts
        """
        return (
            self.status == 'failed' and
            self.total_attempts >= 6  # MAX_TOTAL_ATTEMPTS
        )
    
    # ================================================================
    # INTEGRITY VERIFICATION (EXISTING)
    # ================================================================
    
    def verify_integrity(self) -> bool:
        """
        Verify taxonomy library integrity via file hash.
        
        Only works if file_hash was recorded during download.
        Computes SHA256 of archive file and compares.
        
        Returns:
            True if hash matches or hash not recorded
            False if hash mismatch (corruption detected)
        """
        # If no hash recorded, cannot verify (assume OK)
        if not self.file_hash:
            return True
        
        # Extract expected hash
        if not self.file_hash.startswith('sha256:'):
            logger.warning(f"Invalid hash format for library {self.library_id}")
            return True
        
        expected_hash = self.file_hash[7:]  # Remove 'sha256:' prefix
        
        # Find archive file to verify
        if not self.library_directory:
            return False
        
        try:
            import hashlib
            
            # Look for archive file in parent directory
            library_path = Path(self.library_directory)
            archive_candidates = list(library_path.parent.glob('*.zip')) + \
                               list(library_path.parent.glob('*.tar.gz'))
            
            if not archive_candidates:
                logger.warning(f"No archive found to verify for {self.library_id}")
                return True  # Cannot verify, assume OK
            
            # Use first archive found
            archive_path = archive_candidates[0]
            
            # Compute SHA256
            sha256 = hashlib.sha256()
            with open(archive_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            
            actual_hash = sha256.hexdigest()
            
            if actual_hash != expected_hash:
                logger.error(
                    f"Hash mismatch for {self.taxonomy_name}/{self.taxonomy_version}: "
                    f"expected {expected_hash}, got {actual_hash}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error verifying integrity for {self.library_id}: {e}")
            return True  # Cannot verify, assume OK
    
    # ================================================================
    # DEPENDENCY TRACKING (EXISTING)
    # ================================================================
    
    def add_required_by_filing(self, filing_id: str) -> None:
        """
        Add filing to list of filings that require this taxonomy.
        
        Args:
            filing_id: Filing search UUID
        """
        if not self.required_by_filings:
            self.required_by_filings = []
        
        if filing_id not in self.required_by_filings:
            self.required_by_filings.append(filing_id)
    
    def remove_required_by_filing(self, filing_id: str) -> None:
        """
        Remove filing from required list.
        
        Args:
            filing_id: Filing search UUID
        """
        if self.required_by_filings and filing_id in self.required_by_filings:
            self.required_by_filings.remove(filing_id)
    
    # ================================================================
    # DATABASE-REALITY SYNC (EXISTING)
    # ================================================================
    
    def sync_with_reality(self) -> dict:
        """
        Synchronize database record with physical reality.
        
        Updates total_files to match actual file count.
        Updates download_status if files missing.
        
        Returns:
            Dictionary with sync results:
                - changed: bool (whether database was updated)
                - actual_files: int (files on disk)
                - recorded_files: int (files in database)
                - integrity_ok: bool (hash verification result)
        """
        actual_files = self.actual_file_count
        recorded_files = self.total_files or 0
        integrity_ok = self.verify_integrity()
        
        result = {
            'changed': False,
            'actual_files': actual_files,
            'recorded_files': recorded_files,
            'integrity_ok': integrity_ok
        }
        
        # Update file count if mismatch
        if actual_files != recorded_files:
            self.total_files = actual_files
            
            if actual_files == 0:
                self.download_status = 'failed'
                self.download_error = 'No files found on disk'
                logger.warning(
                    f"Library {self.taxonomy_name}/{self.taxonomy_version} "
                    f"marked completed but no files found"
                )
            
            result['changed'] = True
            self.last_verified_at = func.now()
        
        # Update status if integrity check failed
        if not integrity_ok:
            self.download_status = 'failed'
            self.download_error = 'File hash mismatch - corruption detected'
            result['changed'] = True
        
        return result
    
    # ================================================================
    # REPRESENTATION (EXISTING)
    # ================================================================
    
    def __repr__(self) -> str:
        return (
            f"<TaxonomyLibrary(name='{self.taxonomy_name}', "
            f"version='{self.taxonomy_version}', "
            f"status='{self.download_status}')>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert taxonomy library to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'library_id': str(self.library_id),
            'taxonomy_name': self.taxonomy_name,
            'taxonomy_version': self.taxonomy_version,
            'taxonomy_namespace': self.taxonomy_namespace,
            'source_url': self.source_url,
            'library_directory': self.library_directory,
            'download_status': self.download_status,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'total_files': self.total_files,
            'actual_file_count': self.actual_file_count,
            'files_actually_exist': self.files_actually_exist,
            'is_truly_available': self.is_truly_available,
            'database_matches_reality': self.database_matches_reality,
            'required_by_filings': self.required_by_filings,
            'download_error': self.download_error,
            # New fields
            'download_attempts': self.download_attempts,
            'total_attempts': self.total_attempts,
            'failure_stage': self.failure_stage,
            'failure_reason': self.failure_reason,
            'needs_retry': self.needs_retry,
        }


__all__ = ['TaxonomyLibrary']