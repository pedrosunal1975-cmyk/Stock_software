# Path: searcher/markets/uk/api_client.py
"""
UK Companies House API Client

Async HTTP client for Companies House API with rate limiting and retry logic.
Enforces Companies House requirements (600 req/5min, API key authentication).
"""

import asyncio
import time
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
from searcher.markets.uk.constants import (
    DEFAULT_TIMEOUT,
    DOWNLOAD_TIMEOUT,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW,
    MAX_RETRIES,
    RETRY_DELAY,
    BACKOFF_FACTOR,
    HTTP_OK,
    HTTP_NOT_FOUND,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_UNAUTHORIZED,
    MSG_RATE_LIMIT_EXCEEDED,
    MSG_API_KEY_INVALID,
)

logger = get_logger(__name__, 'markets')


class UKAPIClient:
    """
    Async HTTP client for UK Companies House API.

    Features:
    - Rate limiting (600 requests per 5 minutes)
    - Basic authentication with API key
    - Automatic retry with exponential backoff
    - Timeout handling
    - Request tracking
    """

    def __init__(self, config: ConfigLoader = None):
        """
        Initialize UK Companies House API client.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()

        # Get UK Companies House configuration
        self.api_key = self.config.get('uk_ch_api_key')
        self.user_agent = self.config.get('uk_ch_user_agent')
        self.base_url = self.config.get('uk_ch_base_url')
        self.timeout = self.config.get('uk_ch_timeout', DEFAULT_TIMEOUT)
        self.download_timeout = self.config.get('uk_ch_download_timeout', DOWNLOAD_TIMEOUT)
        self.max_retries = self.config.get('uk_ch_max_retries', MAX_RETRIES)
        self.retry_delay = self.config.get('uk_ch_retry_delay', RETRY_DELAY)

        # Validate API key
        if not self.api_key:
            raise ValueError("UK Companies House API key not configured")

        # Rate limiting state (track timestamps of recent requests)
        self._request_times: list[float] = []
        self._rate_limit_lock = asyncio.Lock()

        # Session (created on first use)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            # Basic auth: API key as username, empty password
            auth = aiohttp.BasicAuth(self.api_key, '')

            self._session = aiohttp.ClientSession(
                auth=auth,
                headers={
                    'User-Agent': self.user_agent,
                    'Accept': 'application/json',
                },
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def _enforce_rate_limit(self):
        """
        Enforce rate limiting: 600 requests per 5-minute window.

        Uses sliding window algorithm to track request timestamps.
        Waits if limit would be exceeded.
        """
        async with self._rate_limit_lock:
            now = time.time()

            # Remove requests older than 5 minutes
            cutoff = now - RATE_LIMIT_WINDOW
            self._request_times = [t for t in self._request_times if t > cutoff]

            # Check if we're at the limit
            if len(self._request_times) >= RATE_LIMIT_REQUESTS:
                # Calculate wait time until oldest request ages out
                oldest = self._request_times[0]
                wait_time = RATE_LIMIT_WINDOW - (now - oldest)

                if wait_time > 0:
                    logger.warning(
                        f"{MSG_RATE_LIMIT_EXCEEDED} Waiting {wait_time:.1f}s",
                        extra={LOG_PROCESS: 'rate_limit'}
                    )
                    await asyncio.sleep(wait_time)
                    now = time.time()

            # Record this request
            self._request_times.append(now)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_DELAY, max=60),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def get_json(self, url: str) -> dict:
        """
        GET request returning JSON data.

        Args:
            url: URL to fetch (absolute or relative to base_url)

        Returns:
            dict: Parsed JSON response

        Raises:
            aiohttp.ClientResponseError: HTTP error
            ValueError: Invalid JSON response
        """
        # Enforce rate limiting
        await self._enforce_rate_limit()

        # Construct full URL if relative
        if not url.startswith('http'):
            url = f"{self.base_url}{url}"

        logger.debug(f"GET {url}", extra={LOG_INPUT: 'api_request'})

        session = await self._get_session()

        async with session.get(url) as response:
            # Log response
            logger.debug(
                f"Response: {response.status}",
                extra={LOG_PROCESS: 'api_response', 'status_code': response.status}
            )

            # Handle rate limiting (shouldn't happen with our enforcement)
            if response.status == HTTP_TOO_MANY_REQUESTS:
                logger.warning(
                    f"{MSG_RATE_LIMIT_EXCEEDED} (Server-side)",
                    extra={LOG_PROCESS: 'rate_limit_server'}
                )
                await asyncio.sleep(60)
                raise aiohttp.ClientError("Rate limit exceeded")

            # Handle unauthorized (bad API key)
            if response.status == HTTP_UNAUTHORIZED:
                logger.error(MSG_API_KEY_INVALID, extra={LOG_OUTPUT: 'error'})
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message="Invalid API key"
                )

            # Handle not found
            if response.status == HTTP_NOT_FOUND:
                return None

            # Raise for other errors
            response.raise_for_status()

            # Parse JSON
            try:
                data = await response.json()
                logger.debug(
                    f"Parsed JSON response",
                    extra={LOG_OUTPUT: 'api_data', 'keys': list(data.keys()) if isinstance(data, dict) else None}
                )
                return data
            except Exception as e:
                logger.error(f"Failed to parse JSON: {e}", extra={LOG_OUTPUT: 'error'})
                raise ValueError(f"Invalid JSON response: {e}")

    async def get_content(self, url: str) -> bytes:
        """
        GET request returning binary content (for document downloads).

        Args:
            url: URL to fetch

        Returns:
            bytes: Response content

        Raises:
            aiohttp.ClientResponseError: HTTP error
        """
        # Enforce rate limiting
        await self._enforce_rate_limit()

        # Construct full URL if relative
        if not url.startswith('http'):
            url = f"{self.base_url}{url}"

        logger.debug(f"GET (binary) {url}", extra={LOG_INPUT: 'api_request'})

        session = await self._get_session()

        # Use longer timeout for downloads
        timeout = aiohttp.ClientTimeout(total=self.download_timeout)

        async with session.get(url, timeout=timeout) as response:
            logger.debug(
                f"Response: {response.status}",
                extra={LOG_PROCESS: 'api_response', 'status_code': response.status}
            )

            # Handle rate limiting
            if response.status == HTTP_TOO_MANY_REQUESTS:
                logger.warning(
                    f"{MSG_RATE_LIMIT_EXCEEDED} (Server-side)",
                    extra={LOG_PROCESS: 'rate_limit_server'}
                )
                await asyncio.sleep(60)
                raise aiohttp.ClientError("Rate limit exceeded")

            # Handle unauthorized
            if response.status == HTTP_UNAUTHORIZED:
                logger.error(MSG_API_KEY_INVALID, extra={LOG_OUTPUT: 'error'})
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message="Invalid API key"
                )

            # Raise for errors
            response.raise_for_status()

            # Read content
            content = await response.read()
            logger.debug(
                f"Downloaded {len(content)} bytes",
                extra={LOG_OUTPUT: 'download', 'size_bytes': len(content)}
            )
            return content

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("API client session closed", extra={LOG_PROCESS: 'cleanup'})

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
