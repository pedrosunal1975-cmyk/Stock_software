# Path: searcher/markets/sec/company_lookup.py
"""
SEC Company Lookup

Resolves company identifiers (ticker, CIK, name) using SEC's company_tickers.json.
Implements caching for performance.
"""

from typing import Optional
import re

from searcher.core.logger import get_logger
from searcher.markets.sec.constants import (
    CIK_PATTERN,
    TICKER_PATTERN,
    ERROR_INVALID_CIK,
    ERROR_INVALID_TICKER,
    ERROR_COMPANY_NOT_FOUND,
)

logger = get_logger(__name__, 'markets')


class SECCompanyLookup:
    """
    Resolves company identifiers to CIK numbers.
    
    Supports:
    - Ticker → CIK (e.g., 'AAPL' → '0000320193')
    - Name → CIK (e.g., 'Apple' → '0000320193')
    - CIK validation and normalization
    
    Caches company_tickers.json for performance.
    """
    
    def __init__(self, api_client=None):
        """
        Initialize company lookup.
        
        Args:
            api_client: Optional SECAPIClient instance
        """
        self.api_client = api_client
        self._cache: Optional[dict] = None
    
    async def resolve_identifier(self, identifier: str) -> str:
        """
        Resolve any identifier (ticker, CIK, or name) to CIK.
        
        Args:
            identifier: Ticker, CIK, or company name
            
        Returns:
            Padded CIK number (e.g., '0000320193')
            
        Raises:
            ValueError: If identifier cannot be resolved
        """
        identifier = identifier.strip()
        
        # Check if it's already a valid CIK
        if self._is_valid_cik(identifier):
            return self._normalize_cik(identifier)
        
        # Check if it's a ticker
        if self._is_valid_ticker(identifier):
            cik = await self._ticker_to_cik(identifier.upper())
            if cik:
                return cik
        
        # Try as company name
        cik = await self._name_to_cik(identifier)
        if cik:
            return cik
        
        raise ValueError(f"{ERROR_COMPANY_NOT_FOUND}: {identifier}")
    
    async def _ticker_to_cik(self, ticker: str) -> Optional[str]:
        """
        Convert ticker to CIK.
        
        Args:
            ticker: Stock ticker (uppercase)
            
        Returns:
            Padded CIK or None if not found
        """
        await self._ensure_cache_loaded()
        
        ticker_upper = ticker.upper()
        
        for key, entry in self._cache.items():
            # Skip the 'fields' metadata key if present
            if key == 'fields':
                continue
            
            # Check ticker match (SEC API contract - stable field name)
            company_ticker = entry.get('ticker', '')
            if company_ticker.upper() == ticker_upper:
                # Get CIK (SEC API contract - stable field name)
                cik = str(entry.get('cik_str'))
                return self._normalize_cik(cik)
        
        return None
    
    async def _name_to_cik(self, name: str) -> Optional[str]:
        """
        Convert company name to CIK (fuzzy matching).
        
        Args:
            name: Company name or partial name
            
        Returns:
            Padded CIK or None if not found
        """
        await self._ensure_cache_loaded()
        
        name_lower = name.lower()
        
        # Try exact match first
        for key, entry in self._cache.items():
            # Skip the 'fields' metadata key if present
            if key == 'fields':
                continue
            
            # SEC API contract - stable field name
            company_name = entry.get('title', '').lower()
            if company_name == name_lower:
                cik = str(entry.get('cik_str'))
                return self._normalize_cik(cik)
        
        # Try contains match
        for key, entry in self._cache.items():
            # Skip the 'fields' metadata key if present
            if key == 'fields':
                continue
            
            # SEC API contract - stable field name
            company_name = entry.get('title', '').lower()
            if name_lower in company_name:
                cik = str(entry.get('cik_str'))
                logger.debug(f"Fuzzy match: '{name}' → '{entry.get('title')}'")
                return self._normalize_cik(cik)
        
        return None
    
    async def _ensure_cache_loaded(self) -> None:
        """Load company_tickers.json into cache if not already loaded."""
        if self._cache is not None:
            return
        
        if not self.api_client:
            from searcher.markets.sec.api_client import SECAPIClient
            self.api_client = SECAPIClient()
        
        from searcher.markets.sec.url_builder import SECURLBuilder
        url_builder = SECURLBuilder()
        
        url = url_builder.build_company_tickers_url()
        
        logger.info("Loading company_tickers.json...")
        self._cache = await self.api_client.get_json(url)
        logger.info(f"Loaded {len(self._cache)} companies")
    
    def _is_valid_cik(self, identifier: str) -> bool:
        """
        Check if identifier is a valid CIK.
        
        Args:
            identifier: Potential CIK
            
        Returns:
            True if valid CIK format
        """
        return bool(re.match(CIK_PATTERN, identifier.strip()))
    
    def _is_valid_ticker(self, identifier: str) -> bool:
        """
        Check if identifier is a valid ticker.
        
        Args:
            identifier: Potential ticker
            
        Returns:
            True if valid ticker format
        """
        # Uppercase before checking pattern
        return bool(re.match(TICKER_PATTERN, identifier.strip().upper()))
    
    def _normalize_cik(self, cik: str) -> str:
        """
        Normalize CIK to 10-digit padded format.
        
        Args:
            cik: CIK number
            
        Returns:
            Padded CIK (e.g., '0000320193')
        """
        from searcher.markets.sec.constants import CIK_LENGTH, CIK_PADDING_CHAR
        
        cik_clean = str(cik).strip().lstrip(CIK_PADDING_CHAR)
        
        # Edge case: if CIK is "0" or becomes empty after stripping
        if not cik_clean:
            cik_clean = '0'
        
        return cik_clean.zfill(CIK_LENGTH)


__all__ = ['SECCompanyLookup']