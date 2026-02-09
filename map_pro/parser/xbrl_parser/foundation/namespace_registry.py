# Path: xbrl_parser/foundation/namespace_registry.py
"""
Namespace Registry Service

Central registry for namespace-to-prefix mappings across XBRL filing.

Features:
- Namespace registration and tracking
- Prefix-URI bidirectional mapping
- Conflict detection
- Standard taxonomy detection
- XML element extraction
"""

from typing import Optional
from lxml import etree
import logging

from ..foundation.namespace_info import NamespaceInfo
from ..foundation.url_addresses import (
    TAXONOMY_DETECTION_PATTERNS,
    MARKET_METADATA_MAP,
    SEC_NAMESPACE_PATTERNS,
    ESMA_NAMESPACE_PATTERNS,
    FRC_NAMESPACE_PATTERNS,
    IFRS_NAMESPACE_PATTERNS
)


class NamespaceRegistry:
    """
    Registry of all namespaces encountered in filing.
    
    Tracks namespace-to-prefix mappings, detects conflicts,
    and identifies standard taxonomies.
    
    Example:
        registry = NamespaceRegistry()
        registry.register("us-gaap", "http://fasb.org/us-gaap/2023", "instance.xml")
        
        uri = registry.get_uri("us-gaap")
        prefix = registry.get_prefix(uri)
    """
    
    def __init__(self):
        """Initialize empty registry."""
        # URI -> NamespaceInfo
        self.by_uri: dict[str, NamespaceInfo] = {}
        
        # Prefix -> URI (for quick lookup)
        self.by_prefix: dict[str, str] = {}
        
        # Track conflicts
        self.conflicts: list[dict] = []
        
        self.logger = logging.getLogger(__name__)
    
    def register(self, prefix: str, uri: str, declared_in: str):
        """
        Register namespace declaration.
        
        Args:
            prefix: Namespace prefix
            uri: Namespace URI
            declared_in: File where declared
        """
        # Check if URI already registered
        if uri in self.by_uri:
            info = self.by_uri[uri]
            
            # Add prefix if new
            info.add_prefix(prefix)
            
            # Add declaration location
            info.add_declaration(declared_in)
            
            # Update prefix mapping
            old_uri = self.by_prefix.get(prefix)
            if old_uri and old_uri != uri:
                # Prefix conflict
                self._log_conflict(prefix, old_uri, uri, declared_in)
            
            self.by_prefix[prefix] = uri
            
        else:
            # New namespace
            info = NamespaceInfo(
                uri=uri,
                prefixes=[prefix],
                preferred_prefix=prefix,
                declared_in=[declared_in],
                is_standard=self._is_standard_taxonomy(uri),
                is_extension=not self._is_standard_taxonomy(uri),
                taxonomy_type=self._detect_taxonomy_type(uri),
                region=self._detect_region(uri),
                first_seen=declared_in
            )
            
            self.by_uri[uri] = info
            
            # Check for prefix conflict
            old_uri = self.by_prefix.get(prefix)
            if old_uri and old_uri != uri:
                self._log_conflict(prefix, old_uri, uri, declared_in)
            
            self.by_prefix[prefix] = uri
    
    def get_by_uri(self, uri: str) -> Optional[NamespaceInfo]:
        """
        Get namespace info by URI.
        
        Args:
            uri: Namespace URI
            
        Returns:
            NamespaceInfo or None if not found
        """
        return self.by_uri.get(uri)
    
    def get_by_prefix(self, prefix: str) -> Optional[NamespaceInfo]:
        """
        Get namespace info by prefix.
        
        Args:
            prefix: Namespace prefix
            
        Returns:
            NamespaceInfo or None if not found
        """
        uri = self.by_prefix.get(prefix)
        if uri:
            return self.by_uri.get(uri)
        return None
    
    def get_uri(self, prefix: str) -> Optional[str]:
        """
        Get URI for prefix.
        
        Args:
            prefix: Namespace prefix
            
        Returns:
            Namespace URI or None if not found
        """
        return self.by_prefix.get(prefix)
    
    def get_prefix(self, uri: str, preferred: bool = True) -> Optional[str]:
        """
        Get prefix for URI.
        
        Args:
            uri: Namespace URI
            preferred: If True, return preferred prefix
            
        Returns:
            Namespace prefix or None if not found
        """
        info = self.by_uri.get(uri)
        if not info:
            return None
        
        if preferred:
            return info.preferred_prefix
        else:
            return info.prefixes[0] if info.prefixes else None
    
    def has_uri(self, uri: str) -> bool:
        """Check if URI is registered."""
        return uri in self.by_uri
    
    def has_prefix(self, prefix: str) -> bool:
        """Check if prefix is registered."""
        return prefix in self.by_prefix
    
    def extract_from_element(self, element: etree._Element):
        """
        Extract namespace declarations from XML element.
        
        Args:
            element: XML element with namespace declarations
        """
        # Get namespace map from element
        for prefix, uri in element.nsmap.items():
            # Handle default namespace (None prefix)
            if prefix is None:
                prefix = "__default__"
            
            # Determine location
            location = element.base if hasattr(element, 'base') else "unknown"
            
            self.register(prefix, uri, location)
    
    def get_all_uris(self) -> list[str]:
        """Get all registered namespace URIs."""
        return list(self.by_uri.keys())
    
    def get_all_prefixes(self) -> list[str]:
        """Get all registered namespace prefixes."""
        return list(self.by_prefix.keys())
    
    def get_standard_namespaces(self) -> dict[str, NamespaceInfo]:
        """Get all standard taxonomy namespaces."""
        return {
            uri: info for uri, info in self.by_uri.items()
            if info.is_standard
        }
    
    def get_extension_namespaces(self) -> dict[str, NamespaceInfo]:
        """Get all extension taxonomy namespaces."""
        return {
            uri: info for uri, info in self.by_uri.items()
            if info.is_extension
        }
    
    def export(self) -> dict:
        """
        Export registry to dictionary.
        
        Returns:
            Dictionary representation of registry
        """
        return {
            'namespaces': {
                uri: info.to_dict() for uri, info in self.by_uri.items()
            },
            'conflicts': self.conflicts,
            'statistics': {
                'total_namespaces': len(self.by_uri),
                'standard_namespaces': len(self.get_standard_namespaces()),
                'extension_namespaces': len(self.get_extension_namespaces()),
                'total_prefixes': len(self.by_prefix),
                'conflicts': len(self.conflicts)
            }
        }
    
    def _is_standard_taxonomy(self, uri: str) -> bool:
        """Check if URI represents a standard taxonomy."""
        # Collect all standard namespace patterns
        all_patterns = (
            SEC_NAMESPACE_PATTERNS +
            ESMA_NAMESPACE_PATTERNS +
            FRC_NAMESPACE_PATTERNS +
            IFRS_NAMESPACE_PATTERNS +
            ['xbrl.org/2003', 'xbrl.org/2005', 'xbrl.org/2006']
        )
        
        return any(pattern in uri for pattern in all_patterns)
    
    def _detect_taxonomy_type(self, uri: str) -> Optional[str]:
        """Detect taxonomy type from URI."""
        # Check against detection patterns
        for taxonomy_type, patterns in TAXONOMY_DETECTION_PATTERNS.items():
            if any(pattern in uri for pattern in patterns):
                return taxonomy_type
        return None
    
    def _detect_region(self, uri: str) -> Optional[str]:
        """Detect region from URI."""
        # Detect taxonomy type first
        taxonomy_type = self._detect_taxonomy_type(uri)
        
        # Look up region from metadata map
        if taxonomy_type and taxonomy_type in MARKET_METADATA_MAP:
            market, authority, framework = MARKET_METADATA_MAP[taxonomy_type]
            return market
        
        return None
    
    def _log_conflict(self, prefix: str, old_uri: str, new_uri: str, location: str):
        """Log namespace prefix conflict."""
        conflict = {
            'prefix': prefix,
            'existing_uri': old_uri,
            'new_uri': new_uri,
            'declared_in': location
        }
        self.conflicts.append(conflict)
        
        self.logger.warning(
            f"Namespace prefix conflict: {prefix} maps to both {old_uri} and {new_uri} (in {location})"
        )


__all__ = ['NamespaceRegistry']
