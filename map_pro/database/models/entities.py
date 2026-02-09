# Path: database/models/entities.py
"""
Entity Model

Company/entity registry across all markets.
Tracks entities with file system verification.

Architecture:
- Market-agnostic entity tracking
- File system verification (database reflects reality)
- Flexible identifier storage (JSONB)
"""

from pathlib import Path
from sqlalchemy import Column, String, Integer, Date, DateTime, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid as uuid_module

from database.models.base import Base
from database.core.logger import get_logger
from database.constants import (
    MAX_MARKET_ID_LENGTH,
    MAX_MARKET_ENTITY_ID_LENGTH,
    MAX_COMPANY_NAME_LENGTH,
    MAX_STATUS_LENGTH,
    STATUS_ACTIVE,
    DEFAULT_FILE_COUNT,
)

logger = get_logger(__name__, 'models')


class Entity(Base):
    """
    Company entity registry.
    
    Tracks companies across all markets with file system verification.
    Database is metadata store - filesystem is source of truth.
    
    CRITICAL: Always use .directory_exists property to verify
    that data directory actually exists before using paths.
    
    Example:
        # Create entity
        entity = Entity(
            market_type='sec',
            market_entity_id='0001234567',  # CIK
            company_name='BOEING CO',  # EXACT from search
            data_directory_path='/mnt/map_pro/data/entities/sec/BOEING_CO',
            identifiers={'cik': '0001234567', 'ticker': 'BA'}
        )
        
        # Verify before use
        if entity.directory_exists:
            process_entity(entity)
        else:
            download_entity_data(entity)
    """
    __tablename__ = 'entities'
    
    entity_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
        comment="Universal entity identifier (UUID)"
    )
    market_type = Column(
        String(MAX_MARKET_ID_LENGTH),
        ForeignKey('markets.market_id'),
        nullable=False,
        comment="Market identifier (e.g., 'sec', 'frc')"
    )
    market_entity_id = Column(
        String(MAX_MARKET_ENTITY_ID_LENGTH),
        nullable=False,
        comment="Market-specific entity ID (CIK, company number, etc.)"
    )
    company_name = Column(
        String(MAX_COMPANY_NAME_LENGTH),
        nullable=False,
        comment="Company name EXACT from source (no normalization)"
    )
    data_directory_path = Column(
        Text,
        comment="Path to entity data directory on filesystem"
    )
    entity_status = Column(
        String(MAX_STATUS_LENGTH),
        default=STATUS_ACTIVE,
        comment="Entity status (active, inactive)"
    )
    last_filing_date = Column(
        Date,
        comment="Date of most recent filing"
    )
    total_filings_count = Column(
        Integer,
        default=DEFAULT_FILE_COUNT,
        comment="Total number of filings (informational)"
    )
    identifiers = Column(
        JSONB,
        comment="Flexible identifier storage (CIK, LEI, ticker, etc.)"
    )
    search_history = Column(
        JSONB,
        comment="Search metadata and history"
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
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint(
            'market_type',
            'market_entity_id',
            name='entities_market_entity_unique'
        ),
        Index('idx_entities_market_type', 'market_type'),
        Index('idx_entities_status', 'entity_status'),
        Index('idx_entities_company_name', 'company_name'),
    )
    
    # Relationships
    market = relationship("Market", back_populates="entities")
    filing_searches = relationship(
        "FilingSearch",
        back_populates="entity",
        cascade="all, delete-orphan"
    )
    downloaded_filings = relationship(
        "DownloadedFiling",
        back_populates="entity",
        cascade="all, delete-orphan"
    )
    
    @property
    def directory_exists(self) -> bool:
        """
        Check if entity data directory actually exists on disk.
        
        CRITICAL: This checks REALITY, not database.
        Always use this before accessing files.
        
        Returns:
            True if directory exists, False otherwise
        """
        if not self.data_directory_path:
            return False
        
        try:
            path = Path(self.data_directory_path)
            return path.exists() and path.is_dir()
        except Exception as e:
            logger.warning(f"Error checking directory for entity {self.entity_id}: {e}")
            return False
    
    @property
    def filings_directory(self) -> Path:
        """
        Get path to filings directory.
        
        Returns:
            Path to filings directory (may not exist)
        """
        if not self.data_directory_path:
            return None
        
        return Path(self.data_directory_path) / 'filings'
    
    @property
    def filings_directory_exists(self) -> bool:
        """
        Check if filings directory exists.
        
        Returns:
            True if filings directory exists
        """
        filings_dir = self.filings_directory
        if not filings_dir:
            return False
        
        return filings_dir.exists() and filings_dir.is_dir()
    
    def __repr__(self) -> str:
        return f"<Entity(id={self.entity_id}, name='{self.company_name}', market='{self.market_type}')>"
    
    def to_dict(self) -> dict:
        """
        Convert entity to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'entity_id': str(self.entity_id),
            'market_type': self.market_type,
            'market_entity_id': self.market_entity_id,
            'company_name': self.company_name,
            'data_directory_path': self.data_directory_path,
            'entity_status': self.entity_status,
            'last_filing_date': str(self.last_filing_date) if self.last_filing_date else None,
            'total_filings_count': self.total_filings_count,
            'identifiers': self.identifiers,
            'directory_exists': self.directory_exists,
        }


__all__ = ['Entity']