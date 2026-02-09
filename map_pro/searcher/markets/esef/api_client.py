# Path: searcher/markets/esef/api_client.py
"""
ESEF API Client

HTTP client for filings.xbrl.org API.
Handles authentication, rate limiting, and error handling.
"""

import aiohttp
import asyncio
from typing import Optional

from searcher.core.config_loader import ConfigLoader
from searcher.core.logger import get_logger
from searcher.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT
from searcher.markets.esef.constants import (
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    BACKOFF_FACTOR,
    HTTP_OK,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_NOT_FOUND,
)

logger = get_logger(__name__, 'markets')


class ESEFAPIClient:
    """
    HTTP client for filings.xbrl.org API.

    Features:
    - Async HTTP requests with aiohttp
    - Automatic retry with exponential backoff
    - Rate limit handling
    - JSON-API response parsing
    """

    def __init__(self, config: ConfigLoader = None):
        """
        Initialize API client.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self._session: Optional[aiohttp.ClientSession] = None

        # Load configuration
        self.timeout = self.config.get('esef_timeout', DEFAULT_TIMEOUT)
        self.max_retries = self.config.get('esef_max_retries', MAX_RETRIES)
        self.retry_delay = self.config.get('esef_retry_delay', RETRY_DELAY)
        self.backoff_factor = self.config.get('esef_backoff_factor', BACKOFF_FACTOR)

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create HTTP session.

        Returns:
            aiohttp.ClientSession: HTTP session
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def _build_headers(self) -> dict[str, str]:
        """
        Build HTTP request headers.

        Returns:
            dict: Request headers
        """
        headers = {
            'Accept': 'application/vnd.api+json',  # JSON-API content type
            'Content-Type': 'application/vnd.api+json',
        }

        # Add user agent if configured
        user_agent = self.config.get('esef_user_agent')
        if user_agent:
            headers['User-Agent'] = user_agent

        return headers

    async def get_json(self, url: str) -> Optional[dict]:
        """
        Fetch JSON data from URL with retry logic.

        Args:
            url: API URL

        Returns:
            dict: Parsed JSON response or None on error
        """
        logger.debug(f"{LOG_INPUT} ESEF API request: {url}")

        session = await self._get_session()
        headers = self._build_headers()

        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with session.get(url, headers=headers) as response:
                    status = response.status

                    if status == HTTP_OK:
                        data = await response.json()
                        logger.debug(f"{LOG_OUTPUT} ESEF API success: {status}")
                        return data

                    elif status == HTTP_NOT_FOUND:
                        logger.warning(f"{LOG_OUTPUT} ESEF API not found: {url}")
                        return None

                    elif status == HTTP_TOO_MANY_REQUESTS:
                        # Rate limited - wait and retry
                        retry_after = response.headers.get('Retry-After', '60')
                        wait_time = int(retry_after)
                        logger.warning(
                            f"{LOG_PROCESS} Rate limited, waiting {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    else:
                        # Other error
                        body = await response.text()
                        logger.error(
                            f"{LOG_OUTPUT} ESEF API error {status}: {body[:200]}"
                        )
                        last_error = f"HTTP {status}"

            except asyncio.TimeoutError:
                logger.warning(f"{LOG_PROCESS} Request timeout (attempt {attempt + 1})")
                last_error = "Timeout"

            except aiohttp.ClientError as e:
                logger.warning(f"{LOG_PROCESS} Request error: {e} (attempt {attempt + 1})")
                last_error = str(e)

            # Exponential backoff before retry
            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay * (self.backoff_factor ** attempt)
                logger.debug(f"{LOG_PROCESS} Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        logger.error(f"{LOG_OUTPUT} ESEF API failed after {self.max_retries} attempts: {last_error}")
        return None

    async def check_url_exists(self, url: str) -> bool:
        """
        Check if URL exists using HEAD request.

        Args:
            url: URL to check

        Returns:
            bool: True if URL returns 200
        """
        session = await self._get_session()
        headers = self._build_headers()

        try:
            async with session.head(url, headers=headers) as response:
                return response.status == HTTP_OK
        except Exception as e:
            logger.debug(f"HEAD request failed: {e}")
            return False

    async def download_file(self, url: str) -> Optional[bytes]:
        """
        Download file content from URL.

        Args:
            url: File URL

        Returns:
            bytes: File content or None on error
        """
        logger.info(f"{LOG_INPUT} Downloading: {url}")

        session = await self._get_session()

        try:
            async with session.get(url) as response:
                if response.status == HTTP_OK:
                    content = await response.read()
                    logger.info(f"{LOG_OUTPUT} Downloaded {len(content)} bytes")
                    return content
                else:
                    logger.error(f"{LOG_OUTPUT} Download failed: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"{LOG_OUTPUT} Download error: {e}")
            return None

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


__all__ = ['ESEFAPIClient']
