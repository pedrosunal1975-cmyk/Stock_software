# Path: library/engine/url_discovery.py
"""
Smart URL Discovery System

Automatically finds downloadable taxonomy library URLs through systematic variations.
NO HARDCODED VALUES - all configuration imported from constants.py

Strategy:
1. Try primary URL pattern
2. Try authority variations
3. Try protocol variations (https/http)
4. Try alternative URL structures
5. Verify each URL before using (HTTP HEAD request)
"""

import asyncio
from typing import Dict, List, Optional, TYPE_CHECKING
from urllib.parse import urlparse

# Lazy import for aiohttp - only needed when actually discovering URLs
# This allows other parts of the library module to run without aiohttp installed
if TYPE_CHECKING:
    import aiohttp

from library.core.logger import get_logger
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT
from library.engine.constants import (
    URL_DISCOVERY_TIMEOUT,
    URL_DISCOVERY_MAX_REDIRECTS,
    URL_DISCOVERY_MAX_CANDIDATES,
    URL_PROTOCOLS,
    URL_CONSTRUCTION_PATTERNS,
    get_authority_variations,
)

logger = get_logger(__name__, 'engine')


class URLDiscovery:
    """
    Smart URL discovery with systematic variation testing.
    
    Automatically finds downloadable URLs from namespace declarations
    by trying known variations and verifying each one.
    
    All configuration from constants.py - NO HARDCODED VALUES.
    """
    
    def __init__(
        self,
        timeout: int = None,
        max_redirects: int = None,
        max_candidates: int = None
    ):
        """
        Initialize URL discovery.
        
        Args:
            timeout: Request timeout (uses constant if None)
            max_redirects: Maximum redirects (uses constant if None)
            max_candidates: Maximum candidates to test (uses constant if None)
        """
        self.timeout = timeout or URL_DISCOVERY_TIMEOUT
        self.max_redirects = max_redirects or URL_DISCOVERY_MAX_REDIRECTS
        self.max_candidates = max_candidates or URL_DISCOVERY_MAX_CANDIDATES
        self._session = None
        
        logger.debug(
            f"{LOG_PROCESS} URL discovery initialized "
            f"(timeout={self.timeout}s, max_redirects={self.max_redirects})"
        )
    
    async def find_download_url(
        self,
        namespace: str,
        taxonomy_name: str,
        version: str
    ) -> Optional[str]:
        """
        Find downloadable URL from namespace through systematic variations.
        
        Args:
            namespace: Original namespace URI from parsed.json
            taxonomy_name: Taxonomy name (e.g., 'us-gaap', 'dei')
            version: Version (e.g., '2024')
            
        Returns:
            Working download URL or None
        """
        logger.info(
            f"{LOG_INPUT} Finding download URL for: {namespace} "
            f"({taxonomy_name} v{version})"
        )
        
        # Generate all possible URL variations
        candidates = self._generate_url_candidates(namespace, taxonomy_name, version)
        
        # Limit candidates
        if len(candidates) > self.max_candidates:
            logger.warning(
                f"{LOG_PROCESS} Limiting candidates from {len(candidates)} to {self.max_candidates}"
            )
            candidates = candidates[:self.max_candidates]
        
        logger.info(f"{LOG_PROCESS} Testing {len(candidates)} candidate URLs")
        
        # Try each candidate until one works
        working_url = await self._test_candidates(candidates)
        
        if working_url:
            logger.info(f"{LOG_OUTPUT} Found working URL: {working_url}")
        else:
            logger.warning(f"{LOG_OUTPUT} No working URL found for {namespace}")
        
        return working_url
    
    def _generate_url_candidates(
        self,
        namespace: str,
        taxonomy_name: str,
        version: str
    ) -> List[str]:
        """
        Generate all possible URL variations.
        
        Uses patterns and variations from constants.py
        
        Returns list ordered by likelihood of success.
        """
        parsed = urlparse(namespace)
        base_authority = parsed.netloc
        
        # Get authority variations from constants
        authority_variants = get_authority_variations(base_authority)
        
        candidates = []
        
        # Try each protocol (https first)
        for protocol in URL_PROTOCOLS:
            # Try each authority variation
            for authority in authority_variants:
                # Try each URL construction pattern
                for pattern in URL_CONSTRUCTION_PATTERNS:
                    try:
                        # Replace protocol in pattern
                        url = pattern.format(
                            authority=authority,
                            taxonomy=taxonomy_name,
                            version=version
                        )
                        # Override protocol
                        if protocol == 'http':
                            url = url.replace('https://', 'http://', 1)
                        
                        candidates.append(url)
                    except (KeyError, ValueError) as e:
                        logger.debug(f"Error formatting pattern {pattern}: {e}")
                        continue
        
        return candidates
    
    async def _test_candidates(self, candidates: List[str]) -> Optional[str]:
        """
        Test candidates using HTTP HEAD requests.

        Returns first working URL.
        """
        # Lazy import aiohttp - only needed when actually testing URLs
        import aiohttp

        # Create session
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        
        # Test each candidate
        for i, url in enumerate(candidates, 1):
            logger.debug(f"{LOG_PROCESS} [{i}/{len(candidates)}] Testing: {url}")
            
            try:
                async with self._session.head(
                    url,
                    allow_redirects=True,
                    max_redirects=self.max_redirects
                ) as response:
                    if response.status == 200:
                        logger.info(f"{LOG_OUTPUT} ✓ Found: {url}")
                        return url
                    else:
                        logger.debug(f"✗ Status {response.status}")
            
            except asyncio.TimeoutError:
                logger.debug(f"✗ Timeout")
            
            except aiohttp.ClientError as e:
                logger.debug(f"✗ Error: {type(e).__name__}")
            
            except Exception as e:
                logger.debug(f"✗ Unexpected: {type(e).__name__}")
        
        return None
    
    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def batch_find_urls(
        self,
        libraries: List[Dict[str, str]]
    ) -> Dict[str, Optional[str]]:
        """
        Find download URLs for multiple libraries.
        
        Args:
            libraries: List of dicts with keys: namespace, taxonomy_name, version
            
        Returns:
            Dictionary mapping namespace to working URL (or None)
        """
        logger.info(f"{LOG_INPUT} Batch finding URLs for {len(libraries)} libraries")
        
        results = {}
        
        for lib in libraries:
            namespace = lib['namespace']
            taxonomy_name = lib['taxonomy_name']
            version = lib['version']
            
            url = await self.find_download_url(namespace, taxonomy_name, version)
            results[namespace] = url
        
        found_count = sum(1 for url in results.values() if url is not None)
        logger.info(
            f"{LOG_OUTPUT} Batch complete: {found_count}/{len(libraries)} URLs found"
        )
        
        return results
    
    async def __aenter__(self):
        """Async context manager entry."""
        import aiohttp

        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


__all__ = ['URLDiscovery']