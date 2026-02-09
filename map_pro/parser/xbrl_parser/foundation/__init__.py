# Path: xbrl_parser/foundation/__init__.py
"""
Foundation layer components.

Core infrastructure for XML parsing, URI resolution, and namespace management.
"""

from ..foundation.xml_parser import XMLParser, XMLParseResult
from ..foundation.http_fetcher import HTTPFetcher
from ..foundation.taxonomy_cache import TaxonomyCache
from ..foundation.registry_manager import (
    RegistryManager,
    TaxonomyRegistry,
    TAXONOMY_REGISTRIES
)
from ..foundation.uri_resolver import URIResolver
from ..foundation.namespace_info import (
    TaxonomyType,
    NamespaceInfo,
    TaxonomyDetectionResult,
    MarketMetadata
)
from ..foundation.namespace_registry import NamespaceRegistry
from ..foundation.qname import QName, QNameResolver
from ..foundation.taxonomy_detector import TaxonomyDetector, MarketExtractor

__all__ = [
    # XML parsing
    'XMLParser',
    'XMLParseResult',
    # URI resolution
    'HTTPFetcher',
    'TaxonomyCache',
    'RegistryManager',
    'TaxonomyRegistry',
    'TAXONOMY_REGISTRIES',
    'URIResolver',
    # Namespace registry
    'TaxonomyType',
    'NamespaceInfo',
    'TaxonomyDetectionResult',
    'MarketMetadata',
    'NamespaceRegistry',
    'QName',
    'QNameResolver',
    'TaxonomyDetector',
    'MarketExtractor'
]
