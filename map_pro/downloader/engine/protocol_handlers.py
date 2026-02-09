# Path: downloader/engine/protocol_handlers.py
"""
Protocol Handlers

HTTP/HTTPS download handlers with streaming support.
Handles headers, timeouts, and connection management.

Architecture:
- Async HTTP client with streaming
- Proper User-Agent headers
- Connection pooling
- Timeout configuration
- Resume capability support
"""

import asyncio
from pathlib import Path
from typing import Optional
import aiohttp
import time

from downloader.core.logger import get_logger
from downloader.core.config_loader import ConfigLoader
from downloader.engine.stream_handler import StreamHandler
from downloader.engine.result import DownloadResult
from downloader.constants import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_TIMEOUT,
    HTTP_OK,
    HTTP_PARTIAL_CONTENT,
    LOG_INPUT,
    LOG_PROCESS,
    LOG_OUTPUT,
)
from downloader.engine.constants import (
    DEFAULT_CONNECT_TIMEOUT,
    MAX_CONCURRENT_CONNECTIONS,
    FORCE_CLOSE_CONNECTIONS,
    DEFAULT_USER_AGENT,
    DEFAULT_ACCEPT_HEADER,
    DEFAULT_ACCEPT_ENCODING,
    HEADER_USER_AGENT,
    HEADER_ACCEPT,
    HEADER_ACCEPT_ENCODING,
    HEADER_RANGE,
)

logger = get_logger(__name__, 'engine')


class HTTPHandler:
    """
    HTTP/HTTPS download handler with streaming.
    
    Features:
    - Async HTTP with aiohttp
    - Streaming to disk (memory-efficient)
    - Resume support (Range header)
    - Progress tracking
    - Configurable timeouts and headers
    
    Example:
        handler = HTTPHandler()
        result = await handler.download(
            url='https://example.com/file.zip',
            output_path=Path('/mnt/map_pro/downloader/temp/file.zip')
        )
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize HTTP handler.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        
        self.chunk_size = self.config.get('chunk_size', DEFAULT_CHUNK_SIZE)
        self.timeout = self.config.get('request_timeout', DEFAULT_TIMEOUT)
        self.connect_timeout = self.config.get('connect_timeout', DEFAULT_CONNECT_TIMEOUT)
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def download(
        self,
        url: str,
        output_path: Path,
        headers: Optional[dict[str, str]] = None,
        resume: bool = False
    ) -> DownloadResult:
        """
        Download file from URL to local path.
        
        Args:
            url: Source URL
            output_path: Destination path
            headers: Optional custom headers
            resume: Whether to resume partial download
            
        Returns:
            DownloadResult with download statistics
        """
        logger.info(f"{LOG_INPUT} Downloading: {url}")
        logger.info(f"{LOG_INPUT} Output: {output_path}")
        
        start_time = time.time()
        result = DownloadResult(
            success=False,
            url=url,
            file_path=output_path
        )
        
        try:
            # Prepare headers (pass URL for market-specific headers)
            request_headers = self._build_headers(headers, url=url)

            # Check for resume
            resume_from = 0
            if resume and output_path.exists():
                resume_from = output_path.stat().st_size
                request_headers[HEADER_RANGE] = f'bytes={resume_from}-'
                logger.info(f"{LOG_PROCESS} Resuming from byte {resume_from}")
            
            # Get session
            session = await self._get_session()
            
            # Make request
            logger.info(f"{LOG_PROCESS} Sending HTTP GET request")
            
            async with session.get(
                url,
                headers=request_headers,
                timeout=aiohttp.ClientTimeout(
                    total=self.timeout,
                    connect=self.connect_timeout
                )
            ) as response:
                
                # Check status
                result.status_code = response.status
                
                if response.status not in (HTTP_OK, HTTP_PARTIAL_CONTENT):
                    result.error_message = f"HTTP {response.status}"
                    logger.error(f"{LOG_OUTPUT} HTTP error: {response.status}")
                    return result
                
                # Get content length
                content_length = response.headers.get('Content-Length')
                total_size = int(content_length) if content_length else None
                
                if total_size:
                    logger.info(f"{LOG_PROCESS} File size: {total_size} bytes")
                
                # Stream to file
                stream_handler = StreamHandler(chunk_size=self.chunk_size)
                
                bytes_written = await stream_handler.stream_to_file(
                    response_stream=response.content.iter_chunked(self.chunk_size),
                    output_path=output_path,
                    total_size=total_size,
                    resume_from=resume_from
                )
                
                # Update result
                result.success = True
                result.file_size = bytes_written
                result.chunks_downloaded = stream_handler.chunks_written
                result.duration = time.time() - start_time
                
                logger.info(
                    f"{LOG_OUTPUT} Download complete: {bytes_written} bytes "
                    f"in {result.duration:.2f}s "
                    f"({result.download_speed_mbps:.2f} MB/s)"
                )
        
        except asyncio.TimeoutError as e:
            result.error_message = f"Timeout: {e}"
            result.duration = time.time() - start_time
            logger.error(f"{LOG_OUTPUT} Download timeout: {e}")
        
        except aiohttp.ClientError as e:
            result.error_message = f"HTTP error: {e}"
            result.duration = time.time() - start_time
            logger.error(f"{LOG_OUTPUT} Download failed: {e}")
        
        except Exception as e:
            result.error_message = f"Unexpected error: {e}"
            result.duration = time.time() - start_time
            logger.error(f"{LOG_OUTPUT} Download failed: {e}", exc_info=True)
        
        return result
    
    def _build_headers(self, custom_headers: Optional[dict[str, str]] = None, url: Optional[str] = None) -> dict[str, str]:
        """
        Build HTTP request headers.

        Args:
            custom_headers: Optional custom headers
            url: Optional URL to determine market-specific headers

        Returns:
            Dictionary of headers
        """
        headers = {
            HEADER_USER_AGENT: self._get_user_agent(url),
            HEADER_ACCEPT: self._get_accept_header(url),
            HEADER_ACCEPT_ENCODING: DEFAULT_ACCEPT_ENCODING,
        }

        # Add Companies House Basic Auth if needed
        if url and self._is_companies_house_url(url):
            auth_header = self._get_companies_house_auth()
            if auth_header:
                headers['Authorization'] = auth_header

        if custom_headers:
            headers.update(custom_headers)

        return headers
    
    def _get_user_agent(self, url: Optional[str] = None) -> str:
        """
        Get User-Agent header value.

        Args:
            url: Optional URL to determine market-specific user agent

        Returns:
            User-Agent string
        """
        # Check for Companies House URLs
        if url and self._is_companies_house_url(url):
            uk_ua = self.config.get('uk_ch_user_agent')
            if uk_ua:
                return uk_ua

        # Try SEC user agent (if configured)
        sec_ua = self.config.get('sec_user_agent')
        if sec_ua:
            return sec_ua

        # Default user agent
        return DEFAULT_USER_AGENT

    def _is_companies_house_url(self, url: str) -> bool:
        """
        Check if URL is from Companies House Document API.

        Args:
            url: URL to check

        Returns:
            True if URL is from Companies House
        """
        return 'document-api.company-information.service.gov.uk' in url or \
               'api.companieshouse.gov.uk' in url

    def _get_accept_header(self, url: Optional[str] = None) -> str:
        """
        Get Accept header value based on URL.

        Args:
            url: Optional URL to determine accept header

        Returns:
            Accept header string
        """
        # Companies House documents: prefer iXBRL (application/xhtml+xml)
        # This returns parseable XBRL data instead of PDF
        if url and self._is_companies_house_url(url):
            return 'application/xhtml+xml'

        # Default
        return DEFAULT_ACCEPT_HEADER

    def _get_companies_house_auth(self) -> Optional[str]:
        """
        Get Companies House Basic Auth header value.

        Returns:
            Basic Auth header value or None
        """
        api_key = self.config.get('uk_ch_api_key')
        if not api_key:
            logger.warning("UK Companies House API key not configured")
            return None

        # Encode API key as Basic Auth (API key as username, empty password)
        import base64
        credentials = f"{api_key}:"
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        return f"Basic {encoded}"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create aiohttp session.
        
        Returns:
            ClientSession instance
        """
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=MAX_CONCURRENT_CONNECTIONS,
                force_close=FORCE_CLOSE_CONNECTIONS
            )
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        
        return self._session
    
    async def head_request(self, url: str) -> Optional[dict[str, any]]:
        """
        Make HEAD request to get file metadata.

        Args:
            url: URL to check

        Returns:
            Dictionary with metadata or None if failed
        """
        try:
            session = await self._get_session()

            async with session.head(url, headers=self._build_headers(url=url)) as response:
                if response.status == HTTP_OK:
                    content_length = response.headers.get('Content-Length')
                    content_type = response.headers.get('Content-Type')
                    
                    return {
                        'size': int(content_length) if content_length else None,
                        'content_type': content_type,
                        'status_code': response.status,
                        'supports_resume': 'Accept-Ranges' in response.headers
                    }
        
        except Exception as e:
            logger.warning(f"HEAD request failed: {e}")
        
        return None
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


__all__ = ['HTTPHandler']