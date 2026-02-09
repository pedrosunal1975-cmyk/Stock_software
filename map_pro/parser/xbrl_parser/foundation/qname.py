# Path: xbrl_parser/foundation/qname.py
"""
QName Resolution

Qualified name handling with namespace resolution.

Features:
- QName parsing and formatting
- Clark notation support
- Namespace resolution
- Element-context resolution
"""

from dataclasses import dataclass
from typing import Optional
from lxml import etree

from ..foundation.namespace_registry import NamespaceRegistry


@dataclass
class QName:
    """
    Qualified name with namespace information.
    
    A QName consists of a namespace URI and a local name,
    optionally with a prefix for display purposes.
    
    Attributes:
        namespace_uri: Full namespace URI
        local_name: Local part of the name
        prefix: Optional prefix for display
        
    Example:
        # From prefix notation
        qname = QName("http://fasb.org/us-gaap/2023", "Assets", "us-gaap")
        str(qname)  # "us-gaap:Assets"
        
        # From Clark notation
        qname = QName.from_clark_notation("{http://fasb.org/us-gaap/2023}Assets")
    """
    namespace_uri: str
    local_name: str
    prefix: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation using prefix notation."""
        if self.prefix:
            return f"{self.prefix}:{self.local_name}"
        return self.local_name
    
    def __eq__(self, other) -> bool:
        """Equality based on namespace and local name."""
        if not isinstance(other, QName):
            return False
        return (self.namespace_uri == other.namespace_uri and 
                self.local_name == other.local_name)
    
    def __hash__(self) -> int:
        """Hash based on namespace and local name."""
        return hash((self.namespace_uri, self.local_name))
    
    def to_clark_notation(self) -> str:
        """
        Convert to Clark notation: {namespace}local.
        
        Returns:
            Clark notation string
            
        Example:
            "{http://fasb.org/us-gaap/2023}Assets"
        """
        if self.namespace_uri:
            return f"{{{self.namespace_uri}}}{self.local_name}"
        return self.local_name
    
    @classmethod
    def from_clark_notation(cls, clark: str) -> 'QName':
        """
        Parse Clark notation.
        
        Args:
            clark: Clark notation string like "{namespace}local"
            
        Returns:
            QName instance
            
        Example:
            qname = QName.from_clark_notation("{http://example.com}Element")
        """
        if clark.startswith('{'):
            end = clark.find('}')
            if end != -1:
                namespace = clark[1:end]
                local = clark[end+1:]
                return cls(namespace_uri=namespace, local_name=local)
        
        # No namespace
        return cls(namespace_uri='', local_name=clark)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'namespace_uri': self.namespace_uri,
            'local_name': self.local_name,
            'prefix': self.prefix,
            'clark': self.to_clark_notation()
        }


class QNameResolver:
    """
    Resolve QName strings using namespace registry.
    
    Converts between string representations and QName objects,
    resolving prefixes to full namespace URIs.
    
    Example:
        registry = NamespaceRegistry()
        registry.register("us-gaap", "http://fasb.org/us-gaap/2023", "file.xml")
        
        resolver = QNameResolver(registry)
        qname = resolver.resolve("us-gaap:Assets")
        # QName(namespace_uri="http://fasb.org/us-gaap/2023", local_name="Assets")
    """
    
    def __init__(self, registry: NamespaceRegistry):
        """
        Initialize resolver.
        
        Args:
            registry: Namespace registry for prefix resolution
        """
        self.registry = registry
    
    def resolve(self, qname_str: str, default_namespace: Optional[str] = None) -> QName:
        """
        Resolve QName string to full QName.
        
        Args:
            qname_str: String like "us-gaap:Assets" or "Assets"
            default_namespace: Namespace to use if no prefix
            
        Returns:
            QName with resolved namespace
            
        Raises:
            ValueError: If prefix is unknown
            
        Example:
            qname = resolver.resolve("us-gaap:Assets")
            qname = resolver.resolve("Assets", default_namespace="http://example.com")
        """
        if ':' in qname_str:
            # Has prefix
            prefix, local_name = qname_str.split(':', 1)
            namespace_uri = self.registry.get_uri(prefix)
            
            if not namespace_uri:
                raise ValueError(f"Unknown namespace prefix: {prefix}")
            
            return QName(
                namespace_uri=namespace_uri,
                local_name=local_name,
                prefix=prefix
            )
        else:
            # No prefix - use default namespace
            if default_namespace:
                return QName(
                    namespace_uri=default_namespace,
                    local_name=qname_str
                )
            else:
                # No namespace
                return QName(
                    namespace_uri='',
                    local_name=qname_str
                )
    
    def format(self, qname: QName, use_prefix: bool = True) -> str:
        """
        Format QName as string.
        
        Args:
            qname: QName to format
            use_prefix: If True, use prefix form. Otherwise, use Clark notation.
            
        Returns:
            Formatted string
            
        Example:
            # With prefix
            resolver.format(qname, use_prefix=True)  # "us-gaap:Assets"
            
            # Clark notation
            resolver.format(qname, use_prefix=False)  # "{http://...}Assets"
        """
        if use_prefix:
            if qname.prefix:
                return f"{qname.prefix}:{qname.local_name}"
            else:
                # Find prefix for namespace
                prefix = self.registry.get_prefix(qname.namespace_uri)
                if prefix:
                    return f"{prefix}:{qname.local_name}"
                else:
                    return qname.local_name
        else:
            return qname.to_clark_notation()
    
    def resolve_from_element(self, qname_str: str, element: etree._Element) -> QName:
        """
        Resolve QName in context of XML element.
        
        Uses the element's namespace declarations rather than the registry.
        Useful for resolving QNames in attribute values.
        
        Args:
            qname_str: QName string to resolve
            element: XML element providing namespace context
            
        Returns:
            Resolved QName
            
        Raises:
            ValueError: If prefix is not declared in element context
            
        Example:
            # Element has xmlns:us-gaap="http://fasb.org/us-gaap/2023"
            qname = resolver.resolve_from_element("us-gaap:Assets", element)
        """
        if ':' in qname_str:
            prefix, local_name = qname_str.split(':', 1)
            # Look up in element's namespace map
            namespace_uri = element.nsmap.get(prefix)
            
            if not namespace_uri:
                raise ValueError(
                    f"Prefix {prefix} not declared in element context"
                )
            
            return QName(
                namespace_uri=namespace_uri,
                local_name=local_name,
                prefix=prefix
            )
        else:
            # Use element's default namespace
            default_ns = element.nsmap.get(None)
            return QName(
                namespace_uri=default_ns or '',
                local_name=qname_str
            )


__all__ = ['QName', 'QNameResolver']
