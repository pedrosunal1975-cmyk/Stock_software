# Path: xbrl_parser/foundation/http_fetcher.py
"""
HTTP/HTTPS Fetcher with Retry Logic

Reliable resource fetching with automatic retry and exponential backoff.

Features:
- Automatic retry with exponential backoff
- Connection pooling
- Timeout handling
- Fetch statistics tracking
"""

from typing import Optional
from datetime import datetime
import logging

import requests
from requests import Session
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ...core.config_loader import ConfigLoader


class HTTPFetcher:
    """
    HTTP/HTTPS fetcher with retry logic.
    
    Features:
    - Automatic retry with exponential backoff
    - Connection pooling
    - Timeout handling
    - Fetch statistics tracking
    
    Example:
        fetcher = HTTPFetcher(config)
        content, metadata = fetcher.fetch("https://example.com/taxonomy.xsd")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize HTTP fetcher.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.logger = logging.getLogger(__name__)
        self.session = self._create_session()
        self.fetch_attempts: list[dict] = []
        
        # Get configuration
        self.http_timeout = self.config.get('http_timeout', 30)
        self.max_retries = self.config.get('http_max_retries', 3)
    
    def _create_session(self) -> Session:
        """Create configured HTTP session with pooling."""
        session = Session()
        
        # set headers
        session.headers.update({
            'User-Agent': 'XBRL-Parser/1.0',
            'Accept': 'application/xml, text/xml, */*',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        return session
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, 
                                       requests.exceptions.Timeout)),
        reraise=True
    )
    def fetch(self, url: str) -> tuple[bytes, dict[str, str]]:
        """
        Fetch resource with retry logic.
        
        Args:
            url: URL to fetch
            
        Returns:
            tuple of (content bytes, metadata dict)
            
        Raises:
            requests.HTTPError: For HTTP errors (4xx, 5xx)
            requests.Timeout: For timeout errors
            requests.ConnectionError: For connection errors
        """
        start_time = datetime.now()
        
        try:
            self.logger.debug(f"Fetching {url}")
            
            response = self.session.get(
                url,
                timeout=self.http_timeout,
                allow_redirects=True
            )
            
            response.raise_for_status()
            
            # Extract metadata
            metadata = {
                'url': url,
                'status_code': response.status_code,
                'content_type': response.headers.get('Content-Type', ''),
                'content_length': len(response.content),
                'last_modified': response.headers.get('Last-Modified', ''),
                'etag': response.headers.get('ETag', ''),
                'fetch_time': datetime.now().isoformat(),
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
            
            # Log successful fetch
            self.fetch_attempts.append({
                'url': url,
                'success': True,
                'attempts': 1,
                'duration': metadata['duration_seconds']
            })
            
            self.logger.info(
                f"Fetched {url}: {metadata['content_length']} bytes in {metadata['duration_seconds']:.2f}s"
            )
            
            return response.content, metadata
            
        except requests.exceptions.HTTPError as e:
            # HTTP error (4xx, 5xx)
            self.fetch_attempts.append({
                'url': url,
                'success': False,
                'error': str(e),
                'status_code': e.response.status_code if e.response else None
            })
            
            self.logger.error(
                f"HTTP error fetching {url}: {e.response.status_code if e.response else 'unknown'} - {str(e)}"
            )
            raise
            
        except requests.exceptions.Timeout as e:
            # Timeout
            self.fetch_attempts.append({
                'url': url,
                'success': False,
                'error': 'Timeout'
            })
            
            self.logger.error(f"Timeout fetching {url} (timeout={self.http_timeout}s)")
            raise
            
        except Exception as e:
            # Other errors
            self.fetch_attempts.append({
                'url': url,
                'success': False,
                'error': str(e)
            })
            
            self.logger.error(f"Error fetching {url}: {str(e)}")
            raise
    
    def fetch_with_fallback(self, urls: list[str]) -> tuple[bytes, dict[str, str]]:
        """
        Try multiple URLs with fallback.
        
        Args:
            urls: list of URLs to try in order
            
        Returns:
            tuple of (content bytes, metadata dict) from first successful fetch
            
        Raises:
            Exception: If all URLs fail
        """
        errors = []
        
        for url in urls:
            try:
                return self.fetch(url)
            except Exception as e:
                errors.append((url, str(e)))
                continue
        
        # All URLs failed
        error_msg = f"Failed to fetch from any URL. Tried: {', '.join(urls)}. Errors: {errors}"
        raise Exception(error_msg)
    
    def get_fetch_stats(self) -> dict:
        """Get fetch statistics."""
        total = len(self.fetch_attempts)
        successful = sum(1 for a in self.fetch_attempts if a['success'])
        
        return {
            'total_attempts': total,
            'successful': successful,
            'failed': total - successful,
            'success_rate': successful / total if total > 0 else 0
        }


__all__ = ['HTTPFetcher']