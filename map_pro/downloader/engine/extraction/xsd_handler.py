# Path: downloader/engine/extraction/xsd_handler.py
"""
XSD Handler

Downloads individual XSD schema files and follows their imports/includes.
100% AGNOSTIC - automatically discovers dependencies by parsing schema files.

Strategy:
1. Download primary XSD file
2. Parse for <xs:import> and <xs:include> declarations
3. Recursively download dependencies
4. Build complete taxonomy locally
"""

import aiohttp
import asyncio
from pathlib import Path
from typing import Set, Optional, List
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
import base64

from downloader.core.logger import get_logger
from downloader.core.config_loader import ConfigLoader
from downloader.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT
from downloader.engine.extraction.constants import (
    XML_NAMESPACES,
    XPATH_IMPORT,
    XPATH_INCLUDE,
    XPATH_LINKBASE_REF,
    ATTR_SCHEMA_LOCATION,
    ATTR_HREF,
    XSD_DOWNLOAD_TIMEOUT,
    XSD_MAX_IMPORT_DEPTH,
    XSD_DEFAULT_FILENAME,
)

logger = get_logger(__name__, 'engine')


class XSDHandler:
    """
    Handles individual XSD file downloads with dependency resolution.
    
    Automatically discovers and downloads all required schema files
    by parsing import/include declarations.
    """
    
    def __init__(self, timeout: int = None, max_depth: int = None, config: Optional[ConfigLoader] = None):
        """
        Initialize XSD handler.

        Args:
            timeout: HTTP request timeout (uses constant if None)
            max_depth: Maximum import depth (uses constant if None)
            config: Optional ConfigLoader instance for authentication
        """
        self.timeout = timeout or XSD_DOWNLOAD_TIMEOUT
        self.max_depth = max_depth or XSD_MAX_IMPORT_DEPTH
        self.config = config if config else ConfigLoader()
        self._session: Optional[aiohttp.ClientSession] = None
        self._downloaded: Set[str] = set()  # Track downloaded files
    
    async def download_schema(
        self,
        schema_url: str,
        target_dir: Path
    ) -> dict:
        """
        Download XSD schema and all dependencies.
        
        Args:
            schema_url: URL of primary schema file
            target_dir: Local directory to save files
            
        Returns:
            Dictionary with download results
        """
        logger.info(f"{LOG_INPUT} Downloading XSD schema: {schema_url}")
        logger.info(f"{LOG_OUTPUT} Target directory: {target_dir}")
        
        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Reset tracking
        self._downloaded.clear()
        
        # Create session
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        
        # Download primary schema and dependencies
        files_downloaded = await self._download_recursive(
            schema_url,
            target_dir,
            depth=0,
            max_depth=self.max_depth
        )
        
        logger.info(f"{LOG_OUTPUT} Downloaded {len(files_downloaded)} schema files")
        
        return {
            'success': len(files_downloaded) > 0,
            'files_downloaded': len(files_downloaded),
            'files': list(files_downloaded),
            'target_dir': target_dir,
        }
    
    async def _download_recursive(
        self,
        url: str,
        target_dir: Path,
        depth: int,
        max_depth: int
    ) -> Set[str]:
        """
        Recursively download XSD and dependencies.
        
        Args:
            url: URL to download
            target_dir: Local directory
            depth: Current recursion depth
            max_depth: Maximum depth
            
        Returns:
            Set of downloaded file paths
        """
        # Check depth limit
        if depth > max_depth:
            logger.warning(f"Max depth {max_depth} reached, stopping recursion")
            return set()
        
        # Skip if already downloaded
        if url in self._downloaded:
            logger.debug(f"Already downloaded: {url}")
            return set()
        
        logger.debug(f"{LOG_PROCESS} [{depth}] Downloading: {url}")

        try:
            # Build headers with authentication if needed
            headers = self._build_headers(url)

            # For Companies House, try multiple formats with fallback
            if self._is_companies_house_url(url):
                content, actual_format = await self._download_companies_house_with_fallback(url, headers)
                if content is None:
                    return set()
            else:
                # Standard download
                async with self._session.get(url, headers=headers, allow_redirects=True) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return set()
                    content = await response.read()
                    actual_format = response.headers.get('Content-Type', '')

            # Determine local filename from URL and content type
            parsed = urlparse(url)
            filename = Path(parsed.path).name

            if not filename or filename == '/' or filename == 'content':
                # For Companies House documents, use appropriate extension
                if 'xhtml' in actual_format or 'xml' in actual_format:
                    filename = 'accounts.xhtml'
                elif 'html' in actual_format:
                    filename = 'accounts.html'
                elif 'pdf' in actual_format:
                    filename = 'accounts.pdf'
                else:
                    filename = XSD_DEFAULT_FILENAME

            local_path = target_dir / filename

            # Save file
            local_path.write_bytes(content)
            self._downloaded.add(url)

            logger.info(f"{LOG_OUTPUT} [{depth}] Saved: {filename}")

            # Parse for dependencies
            dependencies = self._extract_dependencies(content, url)

            if dependencies:
                logger.debug(f"{LOG_PROCESS} Found {len(dependencies)} dependencies")

            # Download dependencies recursively
            downloaded_files = {str(local_path)}

            for dep_url in dependencies:
                dep_files = await self._download_recursive(
                    dep_url,
                    target_dir,
                    depth + 1,
                    max_depth
                )
                downloaded_files.update(dep_files)

            return downloaded_files

        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return set()
    
    def _extract_dependencies(self, xml_content: bytes, base_url: str) -> List[str]:
        """
        Extract import/include URLs from XSD content.
        
        Args:
            xml_content: XSD file content
            base_url: Base URL for resolving relative paths
            
        Returns:
            List of absolute URLs to download
        """
        dependencies = []
        
        try:
            # Parse XML
            root = ET.fromstring(xml_content)
            
            # Find <xs:import> elements
            for imp in root.findall(XPATH_IMPORT, XML_NAMESPACES):
                schema_loc = imp.get(ATTR_SCHEMA_LOCATION)
                if schema_loc:
                    abs_url = urljoin(base_url, schema_loc)
                    dependencies.append(abs_url)
            
            # Find <xs:include> elements
            for inc in root.findall(XPATH_INCLUDE, XML_NAMESPACES):
                schema_loc = inc.get(ATTR_SCHEMA_LOCATION)
                if schema_loc:
                    abs_url = urljoin(base_url, schema_loc)
                    dependencies.append(abs_url)
            
            # Find <link:linkbaseRef> elements (XBRL linkbases)
            for link in root.findall(XPATH_LINKBASE_REF):
                href = link.get(ATTR_HREF)
                if href:
                    abs_url = urljoin(base_url, href)
                    dependencies.append(abs_url)
        
        except ET.ParseError as e:
            logger.debug(f"XML parse error (might not be XML): {e}")
        except Exception as e:
            logger.warning(f"Error extracting dependencies: {e}")
        
        return dependencies

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

    async def _download_companies_house_with_fallback(
        self,
        url: str,
        base_headers: dict
    ) -> tuple[Optional[bytes], str]:
        """
        Download from Companies House with format fallback.

        Tries formats in order of preference:
        1. application/xhtml+xml (iXBRL - preferred for parsing)
        2. text/html (alternative iXBRL format)
        3. application/pdf (fallback - not parseable but better than nothing)

        Args:
            url: Document URL
            base_headers: Base headers including auth

        Returns:
            Tuple of (content bytes or None, content-type string)
        """
        # Format preference order: iXBRL first, PDF last
        formats_to_try = [
            'application/xhtml+xml',  # iXBRL (preferred)
            'text/html',              # Alternative iXBRL
            'application/pdf',        # Fallback (not parseable)
        ]

        for accept_format in formats_to_try:
            headers = base_headers.copy()
            headers['Accept'] = accept_format

            logger.info(f"{LOG_PROCESS} Trying format: {accept_format}")

            try:
                async with self._session.get(url, headers=headers, allow_redirects=True) as response:
                    if response.status == 200:
                        content = await response.read()
                        actual_type = response.headers.get('Content-Type', accept_format)
                        logger.info(f"{LOG_OUTPUT} Successfully downloaded as {actual_type}")
                        return content, actual_type
                    elif response.status == 406:
                        # Format not available, try next
                        logger.info(f"{LOG_PROCESS} Format {accept_format} not available (406)")
                        continue
                    else:
                        logger.warning(f"HTTP {response.status} for {url} with Accept: {accept_format}")
                        continue
            except Exception as e:
                logger.warning(f"Error trying format {accept_format}: {e}")
                continue

        logger.error(f"All format attempts failed for {url}")
        return None, ''

    def _build_headers(self, url: str) -> dict[str, str]:
        """
        Build HTTP request headers with authentication if needed.

        Args:
            url: URL being requested

        Returns:
            Dictionary of headers
        """
        headers = {}

        # Add Companies House Basic Auth if needed
        if self._is_companies_house_url(url):
            api_key = self.config.get('uk_ch_api_key')
            if api_key:
                credentials = f"{api_key}:"
                encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
                headers['Authorization'] = f"Basic {encoded}"
            # Request iXBRL format for parseable XBRL data
            headers['Accept'] = 'application/xhtml+xml'

        return headers

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


__all__ = ['XSDHandler']