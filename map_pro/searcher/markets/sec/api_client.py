# Path: searcher/markets/sec/api_client.py
"""
SEC API Client

Async HTTP client for SEC EDGAR API with rate limiting and retry logic.
Enforces SEC's requirements (10 req/sec, user agent).
"""

import asyncio
from typing import Optional
import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from searcher.core.config_loader import ConfigLoader
from searcher.core.logger import get_logger
from searcher.constants import (
    LOG_INPUT,
    LOG_PROCESS,
    LOG_OUTPUT,
    RETRYABLE_STATUS_CODES,
)
from searcher.markets.sec.constants import (
    HEADER_USER_AGENT,
    HEADER_ACCEPT,
    HEADER_ACCEPT_ENCODING,
    ERROR_API_FAILED,
    HTTP_OK,
    HTTP_NOT_FOUND,
    HTTP_TOO_MANY_REQUESTS,
)

logger = get_logger(__name__, 'markets')


class SECAPIClient:
    """
    Async HTTP client for SEC EDGAR API.
    
    Features:
    - Rate limiting (10 requests/second per SEC guidelines)
    - Automatic retry with exponential backoff
    - User agent enforcement (required by SEC)
    - Timeout handling
    """
    
    def __init__(self, config: ConfigLoader = None):
        """
        Initialize SEC API client.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        
        # Get SEC configuration
        self.user_agent = self.config.get('sec_user_agent')
        self.rate_limit = self.config.get('sec_rate_limit')
        self.timeout = self.config.get('sec_timeout')
        self.retry_attempts = self.config.get('sec_retry_attempts')
        
        # Rate limiting state
        self._last_request_time: float = 0
        self._min_interval: float = 1.0 / self.rate_limit
        
        # Session (created on first use)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def get_json(self, url: str) -> dict:
        """
        GET request returning JSON data.
        
        Args:
            url: URL to fetch
            
        Returns:
            Parsed JSON data as dictionary
            
        Raises:
            Exception: If request fails after retries
        """
        logger.debug(f"{LOG_INPUT} GET {url}")
        
        # Apply rate limiting
        await self._wait_for_rate_limit()
        
        # Make request with retry logic
        data = await self._make_request_with_retry(url)
        
        logger.debug(f"{LOG_OUTPUT} Received {len(str(data))} bytes")
        
        return data
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _make_request_with_retry(self, url: str) -> dict:
        """
        Make HTTP request with automatic retry.
        
        Args:
            url: URL to fetch
            
        Returns:
            Parsed JSON response
        """
        session = await self._get_session()
        
        try:
            logger.debug(f"{LOG_PROCESS} Making request to {url}")
            
            async with session.get(
                url,
                headers=self._build_headers(),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                
                # Check for rate limiting
                if response.status == HTTP_TOO_MANY_REQUESTS:
                    logger.warning("Rate limited by SEC - waiting before retry")
                    await asyncio.sleep(2)
                    raise aiohttp.ClientError("Rate limited")
                
                # Check for server errors (retryable)
                if response.status in RETRYABLE_STATUS_CODES:
                    logger.warning(f"Server error {response.status} - will retry")
                    raise aiohttp.ClientError(f"Server error: {response.status}")
                
                # Raise for other errors
                response.raise_for_status()
                
                # Parse JSON
                data = await response.json()
                return data
        
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {url}")
            raise
        
        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def _wait_for_rate_limit(self) -> None:
        """Enforce rate limit (10 requests/second)."""
        import time
        
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self._min_interval:
            wait_time = self._min_interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.3f}s")
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper connector."""
        if self._session is None or self._session.closed:
            # Create connector that properly closes connections
            connector = aiohttp.TCPConnector(force_close=True)
            self._session = aiohttp.ClientSession(connector=connector)
        
        return self._session
    
    def _build_headers(self) -> dict[str, str]:
        """
        Build HTTP headers for SEC requests.
        
        Returns:
            Headers dictionary
        """
        return {
            HEADER_USER_AGENT: self.user_agent,
            HEADER_ACCEPT: 'application/json',
            HEADER_ACCEPT_ENCODING: 'gzip, deflate',
        }
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_filing_index(
        self,
        cik: str,
        accession_number: str
    ) -> Optional[dict]:
        """
        Get filing index.json (gracefully handles missing files).
        
        CRITICAL: Many filings don't have index.json. This is NORMAL.
        Returns None without warnings when file doesn't exist.
        
        Args:
            cik: CIK with leading zeros
            accession_number: Filing accession number (with dashes)
            
        Returns:
            Dictionary with filing index or None if not found
        """
        from searcher.markets.sec.url_builder import SECURLBuilder
        from searcher.markets.sec.response_parser import SECResponseParser, ResponseContentType
        
        url_builder = SECURLBuilder()
        url = url_builder.build_filing_index_url(cik, accession_number)
        
        logger.debug(f"{LOG_PROCESS} Fetching index.json for {accession_number}")
        
        try:
            # Apply rate limiting
            await self._wait_for_rate_limit()
            
            session = await self._get_session()
            
            async with session.get(
                url,
                headers=self._build_headers(),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                
                # 404 means index.json doesn't exist (normal)
                if response.status == HTTP_NOT_FOUND:
                    logger.debug(f"No index.json for {accession_number} (404)")
                    return None

                # Non-200 status
                if response.status != HTTP_OK:
                    logger.debug(f"index.json request returned {response.status}")
                    return None
                
                # Get response text
                response_text = await response.text()
                
                # Check if SEC returned HTML instead of JSON
                parser = SECResponseParser()
                content_type = parser.detect_content_type(response, response_text)
                
                if content_type == ResponseContentType.HTML:
                    logger.debug(f"No index.json for {accession_number} (HTML response)")
                    return None
                
                # Parse JSON
                import json
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError:
                    logger.debug(f"Invalid JSON in index.json for {accession_number}")
                    return None
        
        except Exception as e:
            logger.debug(f"Error fetching index.json for {accession_number}: {e}")
            return None
    
    async def check_url_exists(self, url: str) -> bool:
        """
        Check if URL exists using HEAD request.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL exists (HTTP 200)
        """
        try:
            await self._wait_for_rate_limit()
            
            session = await self._get_session()
            
            async with session.head(
                url,
                headers=self._build_headers(),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                return response.status == HTTP_OK
        
        except Exception:
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


__all__ = ['SECAPIClient']