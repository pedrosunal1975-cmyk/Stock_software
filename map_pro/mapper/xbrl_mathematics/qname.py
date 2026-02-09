"""
XBRL QName Resolution

This module contains the QName resolution algorithm as defined by the
XBRL 2.1 Specification.

SOURCE AUTHORITY:
----------------
XBRL 2.1 Specification Section 5.1 "Taxonomy schemas"
XML Namespaces Specification

Published by: XBRL International (now IFRS Foundation)

CRITICAL NOTE:
-------------
This module contains ONLY the QName resolution ALGORITHM.
The actual namespace declarations come from XBRL files - NOT here.

SCOPE:
------
UNIVERSAL - applies to all XBRL 2.1 filings globally
"""

from typing import Optional


def resolve_qname(
    qname: str,
    namespace_map: dict[str, str]
) -> str:
    """
    Resolve a prefixed QName to its full namespace URI form.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 5.1
    XML Namespaces Recommendation
    
    SPECIFICATION ALGORITHM:
    -----------------------
    To resolve QName "prefix:local-name":
    1. Split into prefix and local-name
    2. Look up namespace URI for prefix in namespace map
    3. Full name = namespace_uri + ":" + local_name
    
    SPECIFICATION EXAMPLE:
    ---------------------
    Input:  QName = "us-gaap:Assets"
            Prefix = "us-gaap"
            Namespace map = {"us-gaap": "http://fasb.org/us-gaap/2024"}
    Output: "http://fasb.org/us-gaap/2024:Assets"
    
    IMPORTANT:
    ---------
    The namespace map comes from XBRL instance/taxonomy files (xmlns declarations).
    This function only implements the RESOLUTION ALGORITHM.
    
    Args:
        qname: Prefixed name (e.g., "us-gaap:Assets")
        namespace_map: Mapping of prefixes to namespace URIs
        
    Returns:
        Fully qualified name with namespace URI
        
    Raises:
        ValueError: If prefix not found in namespace map
        
    Examples:
        >>> ns_map = {"us-gaap": "http://fasb.org/us-gaap/2024"}
        >>> resolve_qname("us-gaap:Assets", ns_map)
        'http://fasb.org/us-gaap/2024:Assets'
        
        >>> ns_map = {"aci": "http://www.albertsons.com/20250222"}
        >>> resolve_qname("aci:CustomConcept", ns_map)
        'http://www.albertsons.com/20250222:CustomConcept'
    """
    if ':' not in qname:
        # No prefix = default namespace
        default_ns = namespace_map.get('default', namespace_map.get(''))
        if default_ns is None:
            raise ValueError(f"No default namespace defined for unprefixed name: {qname}")
        return f"{default_ns}:{qname}"
    
    # XBRL 2.1 Spec Section 5.1: Split prefix and local name
    prefix, local_name = qname.split(':', 1)
    
    # Look up namespace URI
    namespace_uri = namespace_map.get(prefix)
    
    if namespace_uri is None:
        raise ValueError(
            f"Undefined namespace prefix: '{prefix}' in QName '{qname}'"
        )
    
    # Construct full qualified name
    return f"{namespace_uri}:{local_name}"


def split_qname(qname: str) -> tuple[Optional[str], str]:
    """
    Split a QName into prefix and local name.
    
    SOURCE:
    -------
    XML Namespaces Recommendation
    
    Args:
        qname: Prefixed or unprefixed name
        
    Returns:
        Tuple of (prefix, local_name) where prefix is None for unprefixed names
        
    Examples:
        >>> split_qname("us-gaap:Assets")
        ('us-gaap', 'Assets')
        
        >>> split_qname("Assets")
        (None, 'Assets')
        
        >>> split_qname("aci:Store:Location")  # Multiple colons
        ('aci', 'Store:Location')
    """
    if ':' not in qname:
        return (None, qname)
    
    # Split on first colon only (local name may contain colons)
    prefix, local_name = qname.split(':', 1)
    return (prefix, local_name)


def extract_namespace(
    full_qname: str
) -> tuple[str, str]:
    """
    Extract namespace URI and local name from fully qualified name.
    
    This is the REVERSE of resolve_qname().
    
    Args:
        full_qname: Fully qualified name with namespace URI
                   (e.g., "http://fasb.org/us-gaap/2024:Assets")
        
    Returns:
        Tuple of (namespace_uri, local_name)
        
    Examples:
        >>> extract_namespace("http://fasb.org/us-gaap/2024:Assets")
        ('http://fasb.org/us-gaap/2024', 'Assets')
    """
    if ':' not in full_qname:
        raise ValueError(f"Invalid fully qualified name (no namespace): {full_qname}")
    
    # Find last colon (separates namespace from local name)
    # Use rsplit to handle URIs with colons
    parts = full_qname.rsplit(':', 1)
    
    if len(parts) != 2:
        raise ValueError(f"Invalid fully qualified name format: {full_qname}")
    
    namespace_uri, local_name = parts
    return (namespace_uri, local_name)


def normalize_namespace_uri(namespace_uri: str) -> str:
    """
    Normalize a namespace URI for comparison.
    
    Removes trailing slashes and ensures consistent format.
    
    Args:
        namespace_uri: Raw namespace URI
        
    Returns:
        Normalized namespace URI
        
    Examples:
        >>> normalize_namespace_uri("http://fasb.org/us-gaap/2024/")
        'http://fasb.org/us-gaap/2024'
        
        >>> normalize_namespace_uri("http://fasb.org/us-gaap/2024")
        'http://fasb.org/us-gaap/2024'
    """
    # Remove trailing slash
    return namespace_uri.rstrip('/')


# Export public functions
__all__ = [
    'resolve_qname',
    'split_qname',
    'extract_namespace',
    'normalize_namespace_uri',
]