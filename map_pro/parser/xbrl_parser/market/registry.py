# Path: xbrl_parser/market/registry.py
"""
Market Validator Registry

Manage and coordinate market-specific validators.

This module provides:
- Market validator registration
- Automatic validator selection based on market
- Multi-market validation support

Example:
    from ..market import MarketRegistry
    
    registry = MarketRegistry()
    
    # Auto-detect and validate
    errors = registry.validate(parsed_filing)
    
    # Validate specific market
    errors = registry.validate(parsed_filing, market_id="US_SEC")
"""

import logging
from typing import Optional

from ..models.parsed_filing import ParsedFiling
from ..models.error import ParsingError
from ..market.detector import MarketDetector
from ..market.constants import (
    MARKET_US_SEC,
    MARKET_EU_ESEF,
    MARKET_UK_FRC,
    MARKET_UNKNOWN,
    ALL_MARKETS
)


class MarketRegistry:
    """
    Registry for market-specific validators.
    
    Manages validators for different markets and coordinates
    their execution based on detected or specified market.
    
    Example:
        registry = MarketRegistry()
        
        # Register validators
        registry.register(MARKET_US_SEC, SECValidator())
        registry.register(MARKET_EU_ESEF, ESEFValidator())
        
        # Auto-detect and validate
        errors = registry.validate(filing)
    """
    
    def __init__(self):
        """Initialize market registry."""
        self.logger = logging.getLogger(__name__)
        self.detector = MarketDetector()
        
        # Validator storage
        self.validators: dict[str, any] = {}
        
        # Auto-register default validators
        self._register_default_validators()
        
        self.logger.debug("MarketRegistry initialized")
    
    def register(self, market_id: str, validator: any) -> None:
        """
        Register validator for market.
        
        Args:
            market_id: Market identifier
            validator: Validator instance
            
        Example:
            registry.register(MARKET_US_SEC, SECValidator())
        """
        if market_id not in ALL_MARKETS:
            self.logger.warning(f"Unknown market ID: {market_id}")
        
        self.validators[market_id] = validator
        self.logger.debug(f"Registered validator for {market_id}")
    
    def unregister(self, market_id: str) -> bool:
        """
        Unregister validator for market.
        
        Args:
            market_id: Market identifier
            
        Returns:
            True if validator was removed
        """
        if market_id in self.validators:
            del self.validators[market_id]
            self.logger.debug(f"Unregistered validator for {market_id}")
            return True
        return False
    
    def get_validator(self, market_id: str) -> Optional[any]:
        """
        Get validator for market.
        
        Args:
            market_id: Market identifier
            
        Returns:
            Validator instance or None
        """
        return self.validators.get(market_id)
    
    def list_markets(self) -> list[str]:
        """
        list markets with registered validators.
        
        Returns:
            list of market IDs
        """
        return list(self.validators.keys())
    
    def validate(
        self,
        filing: ParsedFiling,
        market_id: Optional[str] = None
    ) -> list[ParsingError]:
        """
        Validate filing using market-specific rules.
        
        Args:
            filing: Parsed filing to validate
            market_id: Optional market ID (auto-detect if None)
            
        Returns:
            list of validation errors
            
        Example:
            # Auto-detect market
            errors = registry.validate(filing)
            
            # Specific market
            errors = registry.validate(filing, market_id=MARKET_US_SEC)
        """
        # Detect market if not specified
        if market_id is None:
            market_id, confidence = self.detector.detect(filing)
            
            if market_id == MARKET_UNKNOWN:
                self.logger.warning(
                    "Could not detect market - skipping market-specific validation"
                )
                return []
            
            self.logger.info(
                f"Auto-detected market: {market_id} (confidence: {confidence:.2%})"
            )
        
        # Get validator for market
        validator = self.get_validator(market_id)
        
        if validator is None:
            self.logger.warning(f"No validator registered for {market_id}")
            return []
        
        # Run validation
        self.logger.info(f"Running {market_id} validation")
        
        try:
            errors = validator.validate(filing)
            self.logger.info(
                f"{market_id} validation completed: {len(errors)} issues found"
            )
            return errors
            
        except Exception as e:
            self.logger.error(
                f"Market validation failed for {market_id}: {e}",
                exc_info=True
            )
            return []
    
    def validate_all_markets(
        self,
        filing: ParsedFiling
    ) -> dict[str, list[ParsingError]]:
        """
        Validate filing against all registered market validators.
        
        Useful for filings that might be submitted to multiple markets.
        
        Args:
            filing: Parsed filing to validate
            
        Returns:
            dict mapping market_id to list of errors
            
        Example:
            results = registry.validate_all_markets(filing)
            for market_id, errors in results.items():
                print(f"{market_id}: {len(errors)} issues")
        """
        results = {}
        
        for market_id in self.validators.keys():
            self.logger.info(f"Validating against {market_id}")
            errors = self.validate(filing, market_id=market_id)
            results[market_id] = errors
        
        return results
    
    def detect_market(self, filing: ParsedFiling) -> tuple[str, float]:
        """
        Detect market without validation.
        
        Args:
            filing: Parsed filing
            
        Returns:
            tuple of (market_id, confidence)
        """
        return self.detector.detect(filing)
    
    def _register_default_validators(self):
        """Register default validators for all markets."""
        # Import validators here to avoid circular imports
        try:
            from ..market.us_sec import SECValidator
            self.register(MARKET_US_SEC, SECValidator())
        except ImportError:
            self.logger.debug("SECValidator not available")
        
        try:
            from ..market.eu_esef import ESEFValidator
            self.register(MARKET_EU_ESEF, ESEFValidator())
        except ImportError:
            self.logger.debug("ESEFValidator not available")
        
        try:
            from ..market.uk_frc import FRCValidator
            self.register(MARKET_UK_FRC, FRCValidator())
        except ImportError:
            self.logger.debug("FRCValidator not available")


__all__ = ['MarketRegistry']
