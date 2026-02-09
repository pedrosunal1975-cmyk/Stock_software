# Path: downloader/engine/extraction/directory_handler.py
"""
Directory Handler

Mirrors remote directory structures for taxonomies distributed as directories.
100% AGNOSTIC - discovers structure automatically via HTML parsing.

Strategy:
1. Fetch directory listing (HTML)
2. Parse for links to files and subdirectories
3. Recursively mirror structure
4. Download all files
"""

import aiohttp
import asyncio
from pathlib import Path
from typing import Set, Optional, List, Tuple
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser

from downloader.core.logger import get_logger
from downloader.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT
from downloader.engine.extraction.constants import (
    DIRECTORY_TIMEOUT,
    DIRECTORY_MAX_DEPTH,
    SKIP_DIRECTORY_LINKS,
)

logger = get_logger(__name__, 'engine')


class DirectoryListingParser(HTMLParser):
    """
    Parse HTML directory listings.
    
    Extracts file and directory links from Apache-style directory indexes.
    """
    
    def __init__(self):
        super().__init__()
        self.links = []
        self._in_link = False
        self._current_href = None
    
    def handle_starttag(self, tag, attrs):
        """Handle opening tags."""
        if tag == 'a':
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href', '')
            
            # Skip parent directory and special links using constants
            if href and href not in SKIP_DIRECTORY_LINKS:
                self._current_href = href
                self._in_link = True
    
    def handle_endtag(self, tag):
        """Handle closing tags."""
        if tag == 'a':
            if self._current_href:
                self.links.append(self._current_href)
            self._current_href = None
            self._in_link = False


class DirectoryHandler:
    """
    Handles directory structure mirroring for distributed taxonomies.
    
    Automatically discovers and downloads entire directory trees.
    """
    
    def __init__(self, timeout: int = None, max_depth: int = None):
        """
        Initialize directory handler.
        
        Args:
            timeout: HTTP request timeout (uses constant if None)
            max_depth: Maximum directory depth (uses constant if None)
        """
        self.timeout = timeout or DIRECTORY_TIMEOUT
        self.max_depth = max_depth or DIRECTORY_MAX_DEPTH
        self._session: Optional[aiohttp.ClientSession] = None
        self._downloaded: Set[str] = set()
    
    async def mirror_directory(
        self,
        directory_url: str,
        target_dir: Path
    ) -> dict:
        """
        Mirror remote directory structure locally.
        
        Args:
            directory_url: Base URL of directory
            target_dir: Local directory to save files
            
        Returns:
            Dictionary with mirror results
        """
        logger.info(f"{LOG_INPUT} Mirroring directory: {directory_url}")
        logger.info(f"{LOG_OUTPUT} Target directory: {target_dir}")
        
        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Normalize URL (ensure trailing slash)
        if not directory_url.endswith('/'):
            directory_url += '/'
        
        # Reset tracking
        self._downloaded.clear()
        
        # Create session
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        
        # Mirror recursively
        files_downloaded = await self._mirror_recursive(
            directory_url,
            target_dir,
            depth=0
        )
        
        logger.info(f"{LOG_OUTPUT} Mirrored {len(files_downloaded)} files")
        
        return {
            'success': len(files_downloaded) > 0,
            'files_downloaded': len(files_downloaded),
            'files': list(files_downloaded),
            'target_dir': target_dir,
        }
    
    async def _mirror_recursive(
        self,
        url: str,
        local_dir: Path,
        depth: int
    ) -> Set[str]:
        """
        Recursively mirror directory.
        
        Args:
            url: URL of directory
            local_dir: Local directory path
            depth: Current recursion depth
            
        Returns:
            Set of downloaded file paths
        """
        # Check depth limit
        if depth > self.max_depth:
            logger.warning(f"Max depth {self.max_depth} reached")
            return set()
        
        # Skip if already processed
        if url in self._downloaded:
            return set()
        
        logger.debug(f"{LOG_PROCESS} [{depth}] Mirroring: {url}")
        
        try:
            # Fetch directory listing
            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return set()
                
                html_content = await response.text()
            
            # Parse links
            parser = DirectoryListingParser()
            parser.feed(html_content)
            
            self._downloaded.add(url)
            downloaded_files = set()
            
            # Process each link
            for link in parser.links:
                full_url = urljoin(url, link)
                
                # Determine if directory or file
                if link.endswith('/'):
                    # It's a subdirectory
                    subdir = local_dir / link.rstrip('/')
                    subdir.mkdir(exist_ok=True)
                    
                    # Mirror subdirectory recursively
                    sub_files = await self._mirror_recursive(
                        full_url,
                        subdir,
                        depth + 1
                    )
                    downloaded_files.update(sub_files)
                else:
                    # It's a file
                    file_path = await self._download_file(full_url, local_dir)
                    if file_path:
                        downloaded_files.add(file_path)
            
            return downloaded_files
        
        except Exception as e:
            logger.error(f"Error mirroring {url}: {e}")
            return set()
    
    async def _download_file(self, url: str, target_dir: Path) -> Optional[str]:
        """
        Download single file.
        
        Args:
            url: File URL
            target_dir: Local directory
            
        Returns:
            Local file path or None
        """
        try:
            # Get filename from URL
            parsed = urlparse(url)
            filename = Path(parsed.path).name
            
            if not filename:
                logger.warning(f"Could not determine filename from {url}")
                return None
            
            local_path = target_dir / filename
            
            # Download file
            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                
                content = await response.read()
                local_path.write_bytes(content)
                
                logger.info(f"{LOG_OUTPUT} Downloaded: {filename}")
                return str(local_path)
        
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None
    
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


__all__ = ['DirectoryHandler']