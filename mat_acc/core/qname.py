# Path: mat_acc/core/qname.py
"""
Shared QName parsing and manipulation utilities.

XBRL uses multiple QName formats across different systems:
1. Clark notation: {http://fasb.org/us-gaap/2024}Assets
2. Prefix format: us-gaap:Assets (iXBRL standard)
3. Underscore format: us-gaap_Assets (concept index)
4. Simple name: Assets (no namespace)

This module provides a single canonical implementation used
by all mat_acc subsystems, eliminating duplication.
"""
from typing import Optional, Tuple


def parse_qname(qname_str: str) -> Tuple[str, str]:
    """
    Parse QName into (namespace, local_name) tuple.

    Handles all XBRL QName formats universally:
    1. Clark notation: {http://fasb.org/us-gaap/2024}Assets
    2. Prefix format: us-gaap:Assets (iXBRL standard)
    3. Underscore format: us-gaap_Assets (concept index)
    4. Simple name: Assets (no namespace)

    Works for any taxonomy: US-GAAP, IFRS, ESEF, extensions.

    Returns:
        Tuple of (namespace_or_prefix, local_name).
        Empty strings when input is empty or unparseable.
    """
    if not qname_str:
        return ('', '')

    s = str(qname_str).strip()

    # Format 1: Clark notation {namespace-uri}LocalName
    if s.startswith('{'):
        parts = s.split('}', 1)
        if len(parts) == 2:
            return (parts[0][1:], parts[1])

    # Format 2: Prefix:LocalName (standard QName)
    if ':' in s:
        ns, local = s.split(':', 1)
        return (ns, local)

    # Format 3: Prefix_LocalName (uppercase = namespace boundary)
    if '_' in s:
        parts = s.rsplit('_', 1)
        if len(parts) == 2 and parts[1] and parts[1][0].isupper():
            return (parts[0], parts[1])

    # Format 4: Simple name (no namespace)
    return ('', s)


def get_local_name(qname_str: str) -> str:
    """
    Extract local name from any QName format.

    Convenience wrapper around parse_qname().

    Examples:
        get_local_name('us-gaap:Assets') -> 'Assets'
        get_local_name('ifrs-full_Equity') -> 'Equity'
        get_local_name('{http://...}Revenue') -> 'Revenue'
        get_local_name('Assets') -> 'Assets'
    """
    _, local = parse_qname(qname_str)
    return local


def alternate_qname(qname: str) -> Optional[str]:
    """
    Convert between colon and underscore QName formats.

    iXBRL uses colons (us-gaap:Assets), concept indices use
    underscores (us-gaap_Assets). This function converts
    between the two for cross-system lookups.

    Returns:
        Alternate format string, or None if not convertible.
    """
    if ':' in qname:
        return qname.replace(':', '_', 1)
    if '_' in qname:
        parts = qname.rsplit('_', 1)
        if len(parts) == 2 and parts[1] and parts[1][0].isupper():
            return parts[0] + ':' + parts[1]
    return None


def normalize_qname(qname: str) -> str:
    """
    Normalize QName to canonical colon-separated format.

    Converts underscore format to colon format. Already-colon
    and simple names pass through unchanged.

    Examples:
        normalize_qname('ifrs-full_Assets') -> 'ifrs-full:Assets'
        normalize_qname('us-gaap:Revenue') -> 'us-gaap:Revenue'
        normalize_qname('Assets') -> 'Assets'
    """
    if not qname:
        return qname

    if ':' in qname:
        return qname

    if '_' in qname:
        parts = qname.rsplit('_', 1)
        if len(parts) == 2 and parts[1] and parts[1][0].isupper():
            return f"{parts[0]}:{parts[1]}"

    return qname
