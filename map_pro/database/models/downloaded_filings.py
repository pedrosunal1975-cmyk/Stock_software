# Path: database/models/downloaded_filings.py
"""
Downloaded Filing Model

Tracks downloaded and extracted filings with file system verification.
Database reflects reality - filesystem is source of truth.

Architecture:
- File existence verification (critical)
- Download and extraction path tracking
- Ready-for-parsing status
"""

from pathlib import Path
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid as uuid_module

from database.models.base import Base
from database.core.logger import get_logger
from database.constants import MAX_DIRECTORY_DEPTH

logger = get_logger(__name__, 'models')


class DownloadedFiling(Base):
    """
    Downloaded filing tracker.
    
    Tracks downloaded and extracted filings with file system verification.
    
    CRITICAL PRINCIPLE: Database is metadata - filesystem is truth.
    Always use .files_actually_exist and .ready_for_parsing properties
    to verify files exist before processing.
    
    Example:
        # Create record after download
        filing = DownloadedFiling(
            search_id=search.search_id,
            entity_id=entity.entity_id,
            download_directory='/mnt/.../BOEING_CO/filings/10-K/000123...',
            download_completed_at=datetime.now()
        )
        
        # CRITICAL: Verify before use
        if filing.files_actually_exist:
            if filing.ready_for_parsing:
                parser.parse(filing.instance_file_path)
            else:
                logger.warning("Files exist but instance not found")
        else:
            logger.error("Download directory missing!")
    """
    __tablename__ = 'downloaded_filings'
    
    filing_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
        comment="Unique downloaded filing identifier"
    )
    search_id = Column(
        UUID(as_uuid=True),
        ForeignKey('filing_searches.search_id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        comment="Reference to search result"
    )
    entity_id = Column(
        UUID(as_uuid=True),
        ForeignKey('entities.entity_id', ondelete='CASCADE'),
        nullable=False,
        comment="Reference to entity"
    )
    download_directory = Column(
        Text,
        nullable=False,
        comment="Path to download directory on filesystem"
    )
    extraction_directory = Column(
        Text,
        comment="Path to extraction directory (if extracted)"
    )
    instance_file_path = Column(
        Text,
        comment="Path to main XBRL instance document"
    )
    download_completed_at = Column(
        DateTime(timezone=True),
        comment="Download completion timestamp"
    )
    extraction_completed_at = Column(
        DateTime(timezone=True),
        comment="Extraction completion timestamp"
    )
    parse_status = Column(
        String(50),
        default='pending',
        comment="Parsing status: pending, completed, failed"
    )
    parsed_at = Column(
        DateTime(timezone=True),
        comment="Parsing completion timestamp"
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
    
    # Table indexes
    __table_args__ = (
        Index('idx_downloaded_filings_entity', 'entity_id'),
        Index('idx_downloaded_filings_search', 'search_id'),
        Index('idx_downloaded_filings_parse_status', 'parse_status'),
    )
    
    # Relationships
    filing_search = relationship("FilingSearch", back_populates="downloaded_filing")
    entity = relationship("Entity", back_populates="downloaded_filings")
    
    @property
    def download_directory_exists(self) -> bool:
        """
        Check if download directory actually exists on disk.
        
        CRITICAL: This checks REALITY, not database.
        
        Returns:
            True if directory exists, False otherwise
        """
        if not self.download_directory:
            return False
        
        try:
            path = Path(self.download_directory)
            return path.exists() and path.is_dir()
        except Exception as e:
            logger.warning(
                f"Error checking download directory for filing {self.filing_id}: {e}"
            )
            return False
    
    @property
    def extraction_directory_exists(self) -> bool:
        """
        Check if extraction directory actually exists on disk.
        
        Returns:
            True if directory exists, False otherwise
        """
        if not self.extraction_directory:
            return False
        
        try:
            path = Path(self.extraction_directory)
            return path.exists() and path.is_dir()
        except Exception as e:
            logger.warning(
                f"Error checking extraction directory for filing {self.filing_id}: {e}"
            )
            return False
    
    @property
    def files_actually_exist(self) -> bool:
        """
        Check if filing files actually exist on disk.
        
        CRITICAL: Use this instead of trusting database status.
        This is the TRUTH about file existence.
        
        Returns:
            True if files exist, False otherwise
        """
        # Check download directory
        if not self.download_directory_exists:
            return False
        
        # If extracted, check extraction directory
        if self.extraction_directory:
            return self.extraction_directory_exists
        
        return True
    
    @property
    def instance_file_exists(self) -> bool:
        """
        Check if instance file actually exists on disk.
        
        Returns:
            True if instance file exists, False otherwise
        """
        if not self.instance_file_path:
            return False
        
        try:
            path = Path(self.instance_file_path)
            return path.exists() and path.is_file()
        except Exception as e:
            logger.warning(
                f"Error checking instance file for filing {self.filing_id}: {e}"
            )
            return False
    
    @property
    def ready_for_parsing(self) -> bool:
        """
        Check if filing is ready for parser to process.
        
        CRITICAL: This is the correct way to check readiness.
        Verifies:
        1. Files actually exist on disk
        2. Instance file path is set
        3. Instance file actually exists
        
        Returns:
            True only if filing is genuinely ready to parse
        """
        # Files must exist
        if not self.files_actually_exist:
            return False
        
        # Instance file must be set and exist
        if not self.instance_file_path:
            return False
        
        if not self.instance_file_exists:
            return False
        
        return True
    
    @property
    def working_directory(self) -> Path:
        """
        Get working directory for processing.
        
        Returns extraction directory if available, otherwise download directory.
        
        Returns:
            Path to working directory (may not exist)
        """
        if self.extraction_directory:
            return Path(self.extraction_directory)
        elif self.download_directory:
            return Path(self.download_directory)
        return None
    
    def find_instance_file(self) -> Path:
        """
        Find instance file in working directory.
        
        Searches for main XBRL instance document.
        Uses deep recursive search (up to MAX_DIRECTORY_DEPTH).
        
        Returns:
            Path to instance file or None if not found
        """
        working_dir = self.working_directory
        if not working_dir or not working_dir.exists():
            return None
        
        # Common instance file patterns
        instance_patterns = [
            '**/*-ins.xml',
            '**/instance.xml',
            '**/*.htm',
            '**/*.html',
        ]
        
        for pattern in instance_patterns:
            try:
                for file_path in working_dir.glob(pattern):
                    # Check depth to avoid too deep searches
                    depth = len(file_path.relative_to(working_dir).parts)
                    if depth > MAX_DIRECTORY_DEPTH:
                        continue
                    
                    if file_path.is_file():
                        return file_path
            except Exception as e:
                logger.warning(f"Error searching for instance file: {e}")
                continue
        
        return None
    
    def __repr__(self) -> str:
        return f"<DownloadedFiling(id={self.filing_id}, entity_id={self.entity_id})>"
    
    def to_dict(self) -> dict:
        """
        Convert downloaded filing to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'filing_id': str(self.filing_id),
            'search_id': str(self.search_id),
            'entity_id': str(self.entity_id),
            'download_directory': self.download_directory,
            'extraction_directory': self.extraction_directory,
            'instance_file_path': self.instance_file_path,
            'download_completed_at': str(self.download_completed_at) if self.download_completed_at else None,
            'extraction_completed_at': str(self.extraction_completed_at) if self.extraction_completed_at else None,
            'files_actually_exist': self.files_actually_exist,
            'ready_for_parsing': self.ready_for_parsing,
        }


__all__ = ['DownloadedFiling']