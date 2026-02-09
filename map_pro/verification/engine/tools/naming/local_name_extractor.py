# Path: verification/engine/checks_v2/tools/naming/local_name_extractor.py
"""
Local Name Extractor for XBRL Concepts

Extracts local name from qualified XBRL concept names.

This is a focused utility that extracts the local part without
normalizing (preserving case and format).

Examples:
    us-gaap:Assets -> Assets
    {http://fasb.org/us-gaap/2024}Assets -> Assets
    us-gaap_Assets -> Assets
    v_CustomRevenue -> CustomRevenue
    Assets -> Assets (unchanged)
"""

import logging
from typing import Optional

from ...constants.naming import (
    KNOWN_TAXONOMY_PREFIXES,
    MAX_EXTENSION_PREFIX_LENGTH,
    CLARK_NOTATION_START,
    CLARK_NOTATION_END,
)


def extract_local_name(concept: str) -> str:
    """
    Quick local name extraction.

    Extracts the local name from a qualified concept without normalizing.
    Preserves case and format of the local name.

    Args:
        concept: Qualified or unqualified concept name

    Returns:
        Local name (e.g., 'Assets' from 'us-gaap:Assets')

    Example:
        >>> extract_local_name('us-gaap:Assets')
        'Assets'
        >>> extract_local_name('{http://fasb.org/us-gaap/2024}NetIncome')
        'NetIncome'
    """
    if not concept:
        return ''

    extractor = LocalNameExtractor()
    return extractor.extract(concept)


class LocalNameExtractor:
    """
    Extracts local name from qualified XBRL concept names.

    Handles multiple qualification formats:
    - Clark notation: {namespace}LocalName
    - Colon notation: prefix:LocalName
    - Underscore notation: prefix_LocalName

    The local name is returned without normalization, preserving
    the original case and format.
    """

    def __init__(self):
        """Initialize the extractor."""
        self.logger = logging.getLogger('tools.naming.local_name_extractor')

    def extract(self, concept: str) -> str:
        """
        Extract local name from a concept.

        Handles all common qualification formats while preserving
        the original format of the local name.

        Args:
            concept: Full concept name (qualified or unqualified)

        Returns:
            Local name portion
        """
        if not concept:
            return ''

        # Strategy 1: Clark notation {namespace}LocalName
        local = self._extract_from_clark(concept)
        if local:
            return local

        # Strategy 2: Colon notation prefix:LocalName
        local = self._extract_from_colon(concept)
        if local:
            return local

        # Strategy 3: Underscore notation prefix_LocalName
        local = self._extract_from_underscore(concept)
        if local:
            return local

        # No qualification found - return as-is
        return concept

    def _extract_from_clark(self, concept: str) -> Optional[str]:
        """
        Extract from Clark notation: {namespace}LocalName

        Returns None if not Clark notation.
        """
        if not concept.startswith(CLARK_NOTATION_START):
            return None

        if CLARK_NOTATION_END not in concept:
            return None

        # Find the closing brace and take everything after
        close_idx = concept.index(CLARK_NOTATION_END)
        return concept[close_idx + 1:]

    def _extract_from_colon(self, concept: str) -> Optional[str]:
        """
        Extract from colon notation: prefix:LocalName

        Avoids URLs by checking for ://

        Returns None if not colon notation.
        """
        if ':' not in concept:
            return None

        # Avoid URLs like http://example.com
        if '://' in concept:
            return None

        # Take the part after the last colon
        return concept.split(':')[-1]

    def _extract_from_underscore(self, concept: str) -> Optional[str]:
        """
        Extract from underscore notation: prefix_LocalName

        Only extracts if prefix looks like a namespace prefix:
        - Known taxonomy prefix (us-gaap, ifrs, etc.)
        - Company extension prefix (short, alphabetic)

        Returns None if not a qualified underscore notation.
        """
        if '_' not in concept:
            return None

        parts = concept.split('_', 1)
        if len(parts) != 2:
            return None

        prefix = parts[0].lower()
        local = parts[1]

        # Check for known taxonomy prefix
        if prefix in KNOWN_TAXONOMY_PREFIXES:
            return local

        # Check for company extension pattern:
        # - Short prefix (1-6 chars)
        # - All alphabetic
        # - Local name starts with uppercase
        is_extension = (
            len(prefix) <= MAX_EXTENSION_PREFIX_LENGTH and
            prefix.isalpha() and
            len(local) > 0 and
            local[0].isupper()
        )

        if is_extension:
            return local

        # Not a namespace prefix - return None
        return None

    def get_prefix(self, concept: str) -> Optional[str]:
        """
        Get the namespace prefix from a concept.

        Returns None if no prefix found.
        """
        if not concept:
            return None

        # Clark notation
        if concept.startswith(CLARK_NOTATION_START) and CLARK_NOTATION_END in concept:
            close_idx = concept.index(CLARK_NOTATION_END)
            return concept[1:close_idx]

        # Colon notation
        if ':' in concept and '://' not in concept:
            return concept.split(':')[0]

        # Underscore notation
        if '_' in concept:
            parts = concept.split('_', 1)
            prefix = parts[0].lower()
            if prefix in KNOWN_TAXONOMY_PREFIXES:
                return parts[0]
            # Check extension pattern
            if (len(prefix) <= MAX_EXTENSION_PREFIX_LENGTH and
                    prefix.isalpha() and
                    len(parts[1]) > 0 and
                    parts[1][0].isupper()):
                return parts[0]

        return None

    def is_qualified(self, concept: str) -> bool:
        """
        Check if concept has a namespace qualifier.

        Returns True if concept appears to be qualified.
        """
        if not concept:
            return False

        # Check each qualification format
        if concept.startswith(CLARK_NOTATION_START):
            return True

        if ':' in concept and '://' not in concept:
            return True

        if '_' in concept:
            # Check if first part is a namespace
            parts = concept.split('_', 1)
            prefix = parts[0].lower()
            if prefix in KNOWN_TAXONOMY_PREFIXES:
                return True
            # Check extension pattern
            if (len(parts) == 2 and
                    len(prefix) <= MAX_EXTENSION_PREFIX_LENGTH and
                    prefix.isalpha() and
                    len(parts[1]) > 0 and
                    parts[1][0].isupper()):
                return True

        return False


__all__ = ['LocalNameExtractor', 'extract_local_name']
