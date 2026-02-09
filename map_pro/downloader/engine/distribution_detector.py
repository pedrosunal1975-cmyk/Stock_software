# Path: downloader/engine/distribution_detector.py
"""
Distribution Type Detector

Automatically detects how a taxonomy is distributed (ZIP, XSD, directory, etc.)
100% AGNOSTIC - no hardcoded assumptions about markets or taxonomies.

Strategy:
1. HTTP HEAD request to check Content-Type
2. URL pattern analysis
3. Try multiple variations if needed
"""

import aiohttp
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse

from downloader.core.logger import get_logger
from downloader.core.config_loader import ConfigLoader
from downloader.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT
from downloader.engine.constants import (
    ARCHIVE_CONTENT_TYPES,
    XSD_CONTENT_TYPES,
    IXBRL_CONTENT_TYPES,
    IXBRL_EXTENSIONS,
    DIRECTORY_CONTENT_TYPES,
    DIST_TYPE_ARCHIVE,
    DIST_TYPE_XSD,
    DIST_TYPE_DIRECTORY,
    DIST_TYPE_IXBRL,
    DIST_TYPE_UNKNOWN,
    DETECTION_TIMEOUT,
    ARCHIVE_EXTENSIONS,
    SCHEMA_EXTENSIONS,
    XSD_ENTRY_PATTERNS,
    DEFAULT_USER_AGENT,
    HEADER_USER_AGENT,
)

logger = get_logger(__name__, 'engine')


class DistributionDetector:
    """
    Detects taxonomy distribution type without hardcoded assumptions.
    
    Supported distribution types:
    - archive: ZIP, tar.gz files
    - xsd: Individual schema files
    - directory: Directory structure to mirror
    - unknown: Cannot determine
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None, timeout: int = None):
        """
        Initialize detector.
        
        Args:
            config: Optional ConfigLoader instance for User-Agent configuration
            timeout: HTTP request timeout (uses constant if None)
        """
        self.config = config if config else ConfigLoader()
        self.timeout = timeout or DETECTION_TIMEOUT
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def detect(self, url: str) -> dict[str, any]:
        """
        Detect distribution type for given URL.

        Args:
            url: URL to check

        Returns:
            Dictionary with detection results:
            {
                'type': 'archive' | 'xsd' | 'directory' | 'unknown',
                'url': str,  # May be modified if alternative found
                'content_type': str,
                'content_length': int,
                'exists': bool,
                'alternatives': list[str],  # Alternative URLs tried
            }
        """
        logger.info(f"{LOG_INPUT} Detecting distribution type: {url}")

        # Special handling for Companies House URLs
        # Their Document API doesn't support HEAD requests, only GET
        # Request iXBRL format (application/xhtml+xml) for parseable XBRL data
        if self._is_companies_house_url(url):
            logger.info(f"{LOG_OUTPUT} Companies House document detected (requesting iXBRL)")
            return {
                'type': DIST_TYPE_XSD,  # Use XSD type for single file downloads (no extraction)
                'url': url,
                'content_type': 'application/xhtml+xml',  # Request iXBRL format
                'content_length': 0,  # Unknown until download
                'exists': True,  # Assume exists (will fail during download if not)
                'status': 200,
                'skip_head': True,  # Flag to indicate we skipped HEAD request
            }

        # Parse URL
        parsed = urlparse(url)
        base_path = Path(parsed.path)

        # Try primary URL first
        result = await self._check_url(url)

        if result['exists']:
            logger.info(f"{LOG_OUTPUT} Detected: {result['type']} at {url}")
            return result

        # Generate and try alternatives
        logger.debug(f"{LOG_PROCESS} Primary URL not found, trying alternatives")
        alternatives = self._generate_alternatives(url)

        for alt_url in alternatives:
            logger.debug(f"{LOG_PROCESS} Trying alternative: {alt_url}")
            alt_result = await self._check_url(alt_url)

            if alt_result['exists']:
                logger.info(f"{LOG_OUTPUT} Found at alternative URL: {alt_url}")
                return alt_result

        # Nothing found
        logger.warning(f"{LOG_OUTPUT} Could not detect distribution type for {url}")
        result['alternatives'] = alternatives
        return result
    
    async def _check_url(self, url: str) -> dict[str, any]:
        """
        Check single URL and determine type.

        Args:
            url: URL to check

        Returns:
            Detection result
        """
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

        # Build headers with User-Agent and auth (pass URL for market-specific headers)
        headers = self._build_headers(url=url)
        
        try:
            async with self._session.head(url, headers=headers, allow_redirects=True) as response:
                content_type = response.headers.get('Content-Type', '').lower()
                content_length = int(response.headers.get('Content-Length', 0))
                
                if response.status == 200:
                    dist_type = self._classify_content_type(content_type, url)
                    
                    return {
                        'type': dist_type,
                        'url': url,
                        'content_type': content_type,
                        'content_length': content_length,
                        'exists': True,
                        'status': response.status,
                    }
                else:
                    return {
                        'type': DIST_TYPE_UNKNOWN,
                        'url': url,
                        'content_type': content_type,
                        'content_length': 0,
                        'exists': False,
                        'status': response.status,
                    }
        
        except Exception as e:
            logger.warning(f"Error checking {url}: {e}")
            return {
                'type': DIST_TYPE_UNKNOWN,
                'url': url,
                'content_type': '',
                'content_length': 0,
                'exists': False,
                'error': str(e),
            }
    
    def _build_headers(self, url: Optional[str] = None) -> dict[str, str]:
        """
        Build HTTP request headers with User-Agent and authentication.

        Args:
            url: Optional URL to determine market-specific headers

        Returns:
            Dictionary of headers
        """
        # Determine user agent based on URL
        if url and self._is_companies_house_url(url):
            user_agent = self.config.get('uk_ch_user_agent')
            if not user_agent:
                user_agent = DEFAULT_USER_AGENT
        else:
            # Try SEC user agent first (if configured)
            user_agent = self.config.get('sec_user_agent')
            if not user_agent:
                user_agent = DEFAULT_USER_AGENT

        headers = {
            HEADER_USER_AGENT: user_agent,
        }

        # Add Companies House Basic Auth if needed
        if url and self._is_companies_house_url(url):
            auth_header = self._get_companies_house_auth()
            if auth_header:
                headers['Authorization'] = auth_header
            # Request iXBRL format for parseable XBRL data
            headers['Accept'] = 'application/xhtml+xml'

        return headers

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
    
    def _classify_content_type(self, content_type: str, url: str) -> str:
        """
        Classify distribution type from Content-Type and URL.

        Args:
            content_type: HTTP Content-Type header
            url: URL being checked

        Returns:
            Distribution type
        """
        url_lower = url.lower()

        # Check Content-Type first
        if any(ct in content_type for ct in ARCHIVE_CONTENT_TYPES):
            return DIST_TYPE_ARCHIVE

        # Check for iXBRL content type (application/xhtml+xml)
        if any(ct in content_type for ct in IXBRL_CONTENT_TYPES):
            return DIST_TYPE_IXBRL

        # Check URL extension for iXBRL files (.xhtml, .html)
        # This handles cases where content-type might be ambiguous
        if any(url_lower.endswith(ext) for ext in IXBRL_EXTENSIONS):
            return DIST_TYPE_IXBRL

        if any(ct in content_type for ct in XSD_CONTENT_TYPES):
            return DIST_TYPE_XSD

        if any(ct in content_type for ct in DIRECTORY_CONTENT_TYPES):
            return DIST_TYPE_DIRECTORY

        # Fallback: Check URL extension
        if any(url_lower.endswith(ext) for ext in ARCHIVE_EXTENSIONS):
            return DIST_TYPE_ARCHIVE

        if any(url_lower.endswith(ext) for ext in SCHEMA_EXTENSIONS):
            return DIST_TYPE_XSD

        if url_lower.endswith('/'):
            return DIST_TYPE_DIRECTORY

        return DIST_TYPE_UNKNOWN
    
    def _generate_alternatives(self, url: str) -> list:
        """
        Generate alternative URLs to try.
        
        Agnostic approach: Try common variations without hardcoding.
        
        Args:
            url: Original URL
            
        Returns:
            List of alternative URLs
        """
        parsed = urlparse(url)
        base_path = Path(parsed.path)
        
        alternatives = []
        
        # If URL is archive, try XSD variations
        if any(url.lower().endswith(ext) for ext in ARCHIVE_EXTENSIONS):
            base = url
            # Remove archive extension
            for ext in ARCHIVE_EXTENSIONS:
                if url.lower().endswith(ext):
                    base = url[:-len(ext)]
                    break
            
            # Try XSD entry patterns from constants
            for pattern in XSD_ENTRY_PATTERNS:
                alt_url = pattern.format(base=base)
                alternatives.append(alt_url)
            
            # Try directory listing
            parent = str(base_path.parent)
            alternatives.append(f"{parsed.scheme}://{parsed.netloc}{parent}/")
        
        # If URL is XSD, try archive
        elif any(url.lower().endswith(ext) for ext in SCHEMA_EXTENSIONS):
            base = url
            for ext in SCHEMA_EXTENSIONS:
                if url.lower().endswith(ext):
                    base = url[:-len(ext)]
                    break
            alternatives.append(f"{base}.zip")
        
        # If URL ends with /, it's probably a directory already
        # Try index files
        elif url.endswith('/'):
            alternatives.append(f"{url}index.html")
            alternatives.append(f"{url}index.htm")
        
        return alternatives
    
    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


__all__ = ['DistributionDetector']