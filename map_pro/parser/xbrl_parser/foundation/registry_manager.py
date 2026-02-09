# Path: xbrl_parser/foundation/registry_manager.py
"""
Taxonomy Registry Management

Multi-registry support for SEC, ESMA, FRC, and IFRS taxonomies.

Features:
- Registry identification by namespace
- Fetch URL generation
- Mirror URL support
- No hardcoded URLs (all from url_addresses.py)
"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin
import logging

from ..foundation.url_addresses import REGISTRY_METADATA


@dataclass
class TaxonomyRegistry:
    """
    Configuration for taxonomy registry.
    
    Attributes:
        name: Registry display name
        region: Geographic region
        authority: Regulatory authority
        base_urls: Primary base URLs for fetching
        namespace_patterns: Namespace patterns for identification
        mirror_urls: Optional mirror URLs for fallback
    """
    name: str
    region: str
    authority: str
    base_urls: list[str]
    namespace_patterns: list[str]
    mirror_urls: Optional[list[str]] = None


def _create_registries_from_metadata() -> dict[str, TaxonomyRegistry]:
    """
    Create registry instances from metadata.
    
    Returns:
        dict mapping registry code to TaxonomyRegistry instance
    """
    registries = {}
    
    for code, meta in REGISTRY_METADATA.items():
        registries[code] = TaxonomyRegistry(
            name=meta['name'],
            region=meta['region'],
            authority=meta['authority'],
            base_urls=meta['base_urls'],
            namespace_patterns=meta['namespace_patterns'],
            mirror_urls=meta.get('mirror_urls')
        )
    
    return registries


# Standard taxonomy registries (loaded from url_addresses.py)
TAXONOMY_REGISTRIES = _create_registries_from_metadata()


class RegistryManager:
    """
    Manage multiple taxonomy registries.
    
    Identifies which registry a namespace belongs to and provides
    appropriate fetch URLs.
    
    Example:
        manager = RegistryManager()
        registry = manager.identify_registry("http://xbrl.sec.gov/dei/2023")
        urls = manager.get_fetch_urls(namespace, schema_location)
    """
    
    def __init__(self, registries: dict[str, TaxonomyRegistry] = None):
        """
        Initialize registry manager.
        
        Args:
            registries: dict of registry configurations (uses default if not provided)
        """
        self.registries = registries if registries is not None else TAXONOMY_REGISTRIES
        self.logger = logging.getLogger(__name__)
    
    def identify_registry(self, namespace: str) -> Optional[TaxonomyRegistry]:
        """
        Identify which registry a namespace belongs to.
        
        Args:
            namespace: Taxonomy namespace
            
        Returns:
            TaxonomyRegistry or None if unknown
        """
        for registry in self.registries.values():
            for pattern in registry.namespace_patterns:
                if namespace.startswith(pattern):
                    return registry
        
        return None
    
    def get_fetch_urls(self, namespace: str, schema_location: str) -> list[str]:
        """
        Get URLs to try for fetching taxonomy.
        
        Args:
            namespace: Taxonomy namespace
            schema_location: Schema location
            
        Returns:
            list of URLs to try in order
        """
        registry = self.identify_registry(namespace)
        
        if not registry:
            # Unknown registry, try schema_location directly
            if schema_location.startswith('http'):
                return [schema_location]
            else:
                self.logger.warning(f"Unknown registry for namespace: {namespace}")
                return []
        
        urls = []
        
        # Try base URLs
        for base_url in registry.base_urls:
            if schema_location.startswith('http'):
                # Schema location is already absolute
                urls.append(schema_location)
            else:
                # Relative location, combine with base
                urls.append(urljoin(base_url, schema_location))
        
        # Try mirror URLs
        if registry.mirror_urls:
            for mirror_url in registry.mirror_urls:
                if not schema_location.startswith('http'):
                    urls.append(urljoin(mirror_url, schema_location))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls


__all__ = ['RegistryManager', 'TaxonomyRegistry', 'TAXONOMY_REGISTRIES']
