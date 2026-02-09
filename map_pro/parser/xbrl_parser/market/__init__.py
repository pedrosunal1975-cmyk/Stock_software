# Path: xbrl_parser/market/__init__.py
"""
Market-Specific Validation Module

Components for market/region-specific XBRL validation.

This module provides:
- Market auto-detection
- SEC validation (US GAAP)
- ESEF validation (European)
- FRC validation (UK)
- Market registry coordination

Example:
    from ..market import MarketRegistry
    
    # Auto-detect and validate
    registry = MarketRegistry()
    errors = registry.validate(parsed_filing)
    
    # Specific market
    from ..market import SECValidator
    sec_validator = SECValidator()
    errors = sec_validator.validate(filing)
"""

from ..market.detector import MarketDetector
from ..market.registry import MarketRegistry
from ..market.us_sec import SECValidator
from ..market.eu_esef import ESEFValidator
from ..market.uk_frc import FRCValidator
from ..market import constants


__all__ = [
    # Detection and coordination
    'MarketDetector',
    'MarketRegistry',
    
    # Validators
    'SECValidator',
    'ESEFValidator',
    'FRCValidator',
    
    # Constants
    'constants'
]
