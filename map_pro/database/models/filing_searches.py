# Path: database/models/filing_searches.py
"""
Filing Search Model

Search results from market APIs.
Stores filing URLs and metadata for downloader to process.

Architecture:
- Metadata from search results (exact as-is)
- Download and extraction status tracking
- No judgment of data quality
"""

from sqlalchemy import Column, String, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid as uuid_module

from database.models.base import Base
from database.core.logger import get_logger
from database.constants import (
    MAX_MARKET_ID_LENGTH,
    MAX_FORM_TYPE_LENGTH,
    MAX_ACCESSION_NUMBER_LENGTH,
    MAX_STATUS_LENGTH,
    STATUS_PENDING,
)

logger = get_logger(__name__, 'models')


class FilingSearch(Base):
    """
    Filing search result.
    
    Stores search results from market APIs (SEC, FRC, etc.).
    Contains filing URL and metadata for downloader.
    
    Status Flow:
        pending → downloading → completed/failed
        pending → downloading → completed → extracting → completed/failed
    
    Example:
        # Store SEC search result
        search = FilingSearch(
            entity_id=entity.entity_id,
            market_type='sec',
            form_type='10-K',  # EXACT from API
            filing_date=date(2024, 12, 31),
            filing_url='https://www.sec.gov/...',  # EXACT URL
            accession_number='0001234567-24-000123',
            search_metadata={...},  # Raw API response
            download_status='pending'
        )
    """
    __tablename__ = 'filing_searches'
    
    search_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
        comment="Unique search result identifier"
    )
    entity_id = Column(
        UUID(as_uuid=True),
        ForeignKey('entities.entity_id', ondelete='CASCADE'),
        nullable=False,
        comment="Reference to entity"
    )
    market_type = Column(
        String(MAX_MARKET_ID_LENGTH),
        nullable=False,
        comment="Market identifier"
    )
    form_type = Column(
        String(MAX_FORM_TYPE_LENGTH),
        nullable=False,
        comment="Filing form type EXACT from market"
    )
    filing_date = Column(
        Date,
        nullable=False,
        comment="Filing date from search result"
    )
    filing_url = Column(
        Text,
        nullable=False,
        comment="Filing URL EXACT from search result"
    )
    accession_number = Column(
        String(MAX_ACCESSION_NUMBER_LENGTH),
        comment="Market-specific filing identifier"
    )
    search_metadata = Column(
        JSONB,
        comment="Raw search result metadata (as-is from API)"
    )
    download_status = Column(
        String(MAX_STATUS_LENGTH),
        default=STATUS_PENDING,
        comment="Download status: pending, downloading, completed, failed"
    )
    extraction_status = Column(
        String(MAX_STATUS_LENGTH),
        default=STATUS_PENDING,
        comment="Extraction status: pending, completed, failed, not_needed"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Search result creation timestamp"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Record last update timestamp"
    )
    
    # Table indexes
    __table_args__ = (
        Index('idx_filing_searches_entity', 'entity_id'),
        Index('idx_filing_searches_status', 'download_status', 'extraction_status'),
        Index('idx_filing_searches_date', 'filing_date'),
    )
    
    # Relationships
    entity = relationship("Entity", back_populates="filing_searches")
    downloaded_filing = relationship(
        "DownloadedFiling",
        back_populates="filing_search",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    @property
    def is_downloaded(self) -> bool:
        """
        Check if filing has been downloaded.
        
        Returns:
            True if download completed
        """
        return self.download_status == 'completed'
    
    @property
    def is_extracted(self) -> bool:
        """
        Check if filing has been extracted.
        
        Returns:
            True if extraction completed or not needed
        """
        return self.extraction_status in ('completed', 'not_needed')
    
    @property
    def ready_for_download(self) -> bool:
        """
        Check if filing is ready for download.
        
        Returns:
            True if download can proceed
        """
        return self.download_status == 'pending'
    
    @property
    def ready_for_extraction(self) -> bool:
        """
        Check if filing is ready for extraction.
        
        Returns:
            True if extraction can proceed
        """
        return (
            self.download_status == 'completed' and
            self.extraction_status == 'pending'
        )
    
    def __repr__(self) -> str:
        return (
            f"<FilingSearch(id={self.search_id}, "
            f"form='{self.form_type}', date={self.filing_date})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert filing search to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'search_id': str(self.search_id),
            'entity_id': str(self.entity_id),
            'market_type': self.market_type,
            'form_type': self.form_type,
            'filing_date': str(self.filing_date),
            'filing_url': self.filing_url,
            'accession_number': self.accession_number,
            'download_status': self.download_status,
            'extraction_status': self.extraction_status,
            'is_downloaded': self.is_downloaded,
            'is_extracted': self.is_extracted,
        }


__all__ = ['FilingSearch']