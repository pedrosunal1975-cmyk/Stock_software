# Path: database/models/markets.py
"""
Market Model

Registry of supported regulatory markets (SEC, FRC, ESMA, etc.).
Market-agnostic design supports any XBRL-compliant market.

Architecture:
- Reference data for all markets
- Market-specific API configuration
- Rate limiting configuration
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.models.base import Base
from database.core.logger import get_logger
from database.constants import (
    MAX_MARKET_ID_LENGTH,
    MAX_MARKET_NAME_LENGTH,
    MAX_COUNTRY_CODE_LENGTH,
    DEFAULT_RATE_LIMIT,
    STATUS_ACTIVE,
)

logger = get_logger(__name__, 'models')


class Market(Base):
    """
    Regulatory market registry.
    
    Stores configuration for all supported markets.
    Market-agnostic design - no hardcoded market assumptions.
    
    Example:
        # SEC market
        sec = Market(
            market_id='sec',
            market_name='U.S. Securities and Exchange Commission',
            market_country='USA',
            api_base_url='https://www.sec.gov/cgi-bin/browse-edgar',
            is_active=True
        )
        
        # FRC market
        frc = Market(
            market_id='frc',
            market_name='Financial Reporting Council',
            market_country='GBR',
            is_active=True
        )
    """
    __tablename__ = 'markets'
    
    market_id = Column(
        String(MAX_MARKET_ID_LENGTH),
        primary_key=True,
        comment="Unique market identifier (e.g., 'sec', 'frc', 'esma')"
    )
    market_name = Column(
        String(MAX_MARKET_NAME_LENGTH),
        nullable=False,
        comment="Full market name"
    )
    market_country = Column(
        String(MAX_COUNTRY_CODE_LENGTH),
        nullable=False,
        comment="ISO 3166-1 alpha-3 country code"
    )
    api_base_url = Column(
        Text,
        comment="Base URL for market API (if available)"
    )
    is_active = Column(
        Boolean,
        default=True,
        comment="Whether market is actively supported"
    )
    rate_limit_per_minute = Column(
        Integer,
        default=DEFAULT_RATE_LIMIT,
        comment="API rate limit (requests per minute)"
    )
    user_agent_required = Column(
        Boolean,
        default=False,
        comment="Whether market requires user agent in requests"
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
    
    # Relationships
    entities = relationship(
        "Entity",
        back_populates="market",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Market(id='{self.market_id}', name='{self.market_name}')>"
    
    def to_dict(self) -> dict:
        """
        Convert market to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'market_id': self.market_id,
            'market_name': self.market_name,
            'market_country': self.market_country,
            'api_base_url': self.api_base_url,
            'is_active': self.is_active,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'user_agent_required': self.user_agent_required,
        }


__all__ = ['Market']