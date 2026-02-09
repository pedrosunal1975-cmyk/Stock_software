# Path: mat_acc/database/models/processed_filings.py
"""
Processed Filing Model

Tracks filings that have been processed by the hierarchy builder.
Stores filing metadata and links to statement hierarchies.

Architecture:
- Market agnostic (works with SEC, ESEF, FCA, etc.)
- Links to statement hierarchies via relationship
- Source path tracking for data provenance
"""

import uuid as uuid_module
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, String, Date, DateTime, Text, Integer
from sqlalchemy.orm import relationship

from database.models.base import Base


class ProcessedFiling(Base):
    """
    Processed filing record.

    Tracks a filing that has been processed by the hierarchy builder.
    Links to statement hierarchies built from this filing.

    Example:
        filing = ProcessedFiling(
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30),
            source_path='/mnt/map_pro/mapper/mapped_statements/sec/Apple_Inc/10_K/2024-09-30'
        )
    """
    __tablename__ = 'processed_filings'

    # Primary key - using string UUID for SQLite compatibility
    filing_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid_module.uuid4()),
        comment="Unique filing identifier"
    )

    # Filing identification (market agnostic)
    market = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Market code (sec, frc, esma, etc.)"
    )
    company_name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Company name exactly as in source"
    )
    form_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Form type (10-K, 10-Q, etc.)"
    )
    filing_date = Column(
        Date,
        nullable=False,
        index=True,
        comment="Filing date"
    )

    # Optional identifiers
    accession_number = Column(
        String(100),
        comment="SEC accession number or equivalent"
    )
    cik = Column(
        String(20),
        comment="CIK or market-specific entity ID"
    )

    # Source tracking
    source_path = Column(
        Text,
        comment="Path to source data (mapped filing folder)"
    )

    # Statistics
    statement_count = Column(
        Integer,
        default=0,
        comment="Number of statements in this filing"
    )
    total_node_count = Column(
        Integer,
        default=0,
        comment="Total nodes across all statements"
    )

    # Timestamps
    processed_at = Column(
        DateTime,
        default=datetime.utcnow,
        comment="When filing was processed"
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Record last update timestamp"
    )

    # Relationships
    hierarchies = relationship(
        "StatementHierarchy",
        back_populates="filing",
        cascade="all, delete-orphan"
    )

    @property
    def source_path_exists(self) -> bool:
        """
        Check if source path exists on filesystem.

        Returns:
            True if source path exists, False otherwise
        """
        if not self.source_path:
            return False
        try:
            return Path(self.source_path).exists()
        except Exception:
            return False

    @property
    def filing_key(self) -> str:
        """
        Get unique filing key for identification.

        Format: {market}/{company}/{form}/{date}

        Returns:
            Filing key string
        """
        company_safe = self.company_name.replace(' ', '_').replace('/', '_')
        form_safe = self.form_type.replace('-', '_')
        return f"{self.market}/{company_safe}/{form_safe}/{self.filing_date}"

    def __repr__(self) -> str:
        id_str = self.filing_id[:8] + '...' if self.filing_id else 'NEW'
        return (
            f"<ProcessedFiling("
            f"id={id_str}, "
            f"company='{self.company_name}', "
            f"form='{self.form_type}', "
            f"date={self.filing_date}"
            f")>"
        )

    def to_dict(self) -> dict:
        """
        Convert filing to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'filing_id': self.filing_id,
            'market': self.market,
            'company_name': self.company_name,
            'form_type': self.form_type,
            'filing_date': str(self.filing_date) if self.filing_date else None,
            'accession_number': self.accession_number,
            'cik': self.cik,
            'source_path': self.source_path,
            'statement_count': self.statement_count,
            'total_node_count': self.total_node_count,
            'processed_at': str(self.processed_at) if self.processed_at else None,
            'filing_key': self.filing_key,
        }


__all__ = ['ProcessedFiling']
