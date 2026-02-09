# Path: xbrl_parser/foundation/uri_resolver.py
"""
URI Resolution Integration

Main integration point for URI resolution, combining HTTP fetching,
caching, and registry management.

Features:
- Local and remote URI resolution  
- Automatic caching
- Multi-registry support
- No hardcoded URLs
"""

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urljoin
from datetime import datetime
import logging

from ...core.config_loader import ConfigLoader
from ..foundation.http_fetcher import HTTPFetcher
from ..foundation.taxonomy_cache import TaxonomyCache
from ..foundation.registry_manager import RegistryManager


class URIResolver:
    """
    Resolve URIs to local files or remote resources.
    
    Features:
    - Local/remote URI resolution
    - Relative URI resolution
    - HTTP fetching with caching
    - Multi-registry support
    
    Example:
        resolver = URIResolver(config)
        content, metadata = resolver.get_resource(
            "http://xbrl.sec.gov/dei/2023/dei-2023.xsd",
            base_uri="http://xbrl.sec.gov/dei/2023/"
        )
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize URI resolver.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.logger = logging.getLogger(__name__)

        # Get configuration - FAIL if not configured
        cache_dir = self.config.get('taxonomy_cache_dir')
        if not cache_dir:
            raise ValueError(
                "Taxonomy cache directory not configured. "
                "Required: PARSER_TAXONOMY_CACHE_DIR in .env"
            )
        cache_dir = Path(cache_dir)
        max_cache_mb = self.config.get('taxonomy_cache_size_mb', 1024)

        # Initialize components
        self.fetcher = HTTPFetcher(self.config)
        self.cache = TaxonomyCache(cache_dir, max_cache_mb)
        self.registry_manager = RegistryManager()
        
        # Resolution cache (URI -> resolved path)
        self.resolution_cache: dict[tuple[str, Optional[str]], tuple] = {}
    
    def resolve(self, uri: str, base_uri: Optional[str] = None) -> tuple:
        """
        Resolve URI to resource location.
        
        Args:
            uri: URI to resolve
            base_uri: Optional base URI for relative resolution
            
        Returns:
            tuple of (path_or_url, is_remote)
        """
        # Check cache first
        cache_key = (uri, base_uri)
        if cache_key in self.resolution_cache:
            return self.resolution_cache[cache_key]
        
        # Make absolute if relative
        if base_uri and not self._is_absolute_uri(uri):
            uri = urljoin(base_uri, uri)
        
        # Determine if local or remote
        parsed = urlparse(uri)
        
        if parsed.scheme in ['http', 'https']:
            # Remote resource
            result = (uri, True)
        elif parsed.scheme == 'file' or not parsed.scheme:
            # Local file
            if parsed.scheme == 'file':
                # Remove file:// prefix
                local_path = parsed.path
            else:
                local_path = uri
            
            path = Path(local_path)
            if not path.is_absolute() and base_uri:
                # Resolve relative to base
                base_path = Path(urlparse(base_uri).path).parent
                path = (base_path / path).resolve()
            
            result = (path, False)
        else:
            raise ValueError(f"Unsupported URI scheme: {parsed.scheme} in {uri}")
        
        # Cache result
        self.resolution_cache[cache_key] = result
        return result
    
    def _is_absolute_uri(self, uri: str) -> bool:
        """Check if URI is absolute."""
        parsed = urlparse(uri)
        return bool(parsed.scheme) or uri.startswith('/')
    
    def get_resource(
        self,
        uri: str,
        base_uri: Optional[str] = None,
        namespace: Optional[str] = None,
        version: Optional[str] = None
    ) -> tuple[bytes, dict[str, str]]:
        """
        Get resource content (local or remote).
        
        Args:
            uri: URI to fetch
            base_uri: Optional base URI for relative resolution
            namespace: Optional namespace for cache lookup
            version: Optional version for cache lookup
            
        Returns:
            tuple of (content bytes, metadata dict)
            
        Raises:
            FileNotFoundError: For missing local files
            requests.HTTPError: For HTTP errors
        """
        path_or_url, is_remote = self.resolve(uri, base_uri)
        
        if is_remote:
            # Check cache first
            if namespace:
                cached = self.cache.get(namespace, version, str(path_or_url))
                if cached:
                    return cached
            
            # Fetch from network
            if namespace:
                # Try registry-aware fetching
                urls = self.registry_manager.get_fetch_urls(namespace, str(path_or_url))
                if urls:
                    try:
                        content, metadata = self.fetcher.fetch_with_fallback(urls)
                    except Exception:
                        # Fallback to direct URL
                        content, metadata = self.fetcher.fetch(str(path_or_url))
                else:
                    content, metadata = self.fetcher.fetch(str(path_or_url))
            else:
                content, metadata = self.fetcher.fetch(str(path_or_url))
            
            # Cache if namespace provided
            if namespace:
                self.cache.put(namespace, version, str(path_or_url), content, metadata)
            
            return content, metadata
        else:
            # Read from local file
            path = path_or_url
            if not path.exists():
                raise FileNotFoundError(f"Local file not found: {path}")
            
            with open(path, 'rb') as f:
                content = f.read()
            
            metadata = {
                'url': str(path),
                'is_local': True,
                'size_bytes': len(content),
                'last_modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat()
            }
            
            return content, metadata
    
    def invalidate_cache(self, namespace: Optional[str] = None):
        """
        Invalidate taxonomy cache.
        
        Args:
            namespace: If provided, only invalidate this namespace
        """
        self.cache.invalidate(namespace)
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return self.cache.get_stats()
    
    def get_fetch_stats(self) -> dict:
        """Get HTTP fetch statistics."""
        return self.fetcher.get_fetch_stats()


__all__ = ['URIResolver']
