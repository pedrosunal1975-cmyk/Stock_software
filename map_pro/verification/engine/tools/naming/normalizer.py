# Path: verification/engine/checks_v2/tools/naming/normalizer.py
"""
Concept Name Normalizer for XBRL Verification

Provides multi-strategy normalization of concept names for comparison.

Strategies:
- 'canonical': Extract local name, lowercase, remove separators
- 'local_name': Extract local part only (Assets from us-gaap:Assets)
- 'full_qualified': Keep namespace prefix, normalize separators
- 'auto': Detect format and apply best strategy

The normalizer maintains bidirectional mapping to preserve original names.
Original names are always preserved and returned in verification results.
"""

import logging
from typing import Optional

from ...constants.naming import (
    CONCEPT_SEPARATORS,
    CANONICAL_SEPARATOR,
    KNOWN_TAXONOMY_PREFIXES,
    MAX_EXTENSION_PREFIX_LENGTH,
    CLARK_NOTATION_START,
    CLARK_NOTATION_END,
)


def normalize_name(name: str) -> str:
    """
    Quick canonical normalization of any name.

    Removes spaces, underscores, hyphens and lowercases.
    This is the standard normalization used throughout verification.

    Args:
        name: Name to normalize

    Returns:
        Normalized name for comparison (lowercase, no separators)

    Example:
        >>> normalize_name('Assets')
        'assets'
        >>> normalize_name('NetCashProvidedByUsedInOperatingActivities')
        'netcashprovidedbyusedinoperatingactivities'
    """
    if not name:
        return ''
    return name.lower().replace('_', '').replace('-', '').replace(' ', '')


class Normalizer:
    """
    Multi-strategy concept name normalizer.

    Provides flexible normalization with:
    - Multiple strategies for different use cases
    - Bidirectional mapping to preserve original names
    - Automatic format detection

    Usage:
        normalizer = Normalizer()

        # Quick canonical normalization
        norm = normalizer.normalize('us-gaap:Assets')  # -> 'assets'

        # Register and track originals
        norm = normalizer.register('us-gaap:Assets', source='linkbase')
        original = normalizer.get_original(norm, source='linkbase')

        # Use specific strategy
        norm = normalizer.normalize('us-gaap:Assets', strategy='local_name')  # -> 'Assets'
    """

    def __init__(self):
        """Initialize normalizer with empty mappings."""
        self.logger = logging.getLogger('tools.naming.normalizer')
        # Maps: normalized_name -> {source: original_name}
        self._originals: dict[str, dict[str, str]] = {}
        # Strategy dispatch
        self._strategies = {
            'canonical': self._normalize_canonical,
            'local_name': self._extract_local_name,
            'full_qualified': self._normalize_full_qualified,
            'auto': self._normalize_auto,
        }

    def normalize(self, concept: str, strategy: str = 'canonical') -> str:
        """
        Normalize a concept name using specified strategy.

        Args:
            concept: Original concept name
            strategy: Normalization strategy:
                - 'canonical': Lowercase, no separators (default)
                - 'local_name': Extract local part only
                - 'full_qualified': Keep prefix, normalize separators
                - 'auto': Detect and apply best strategy

        Returns:
            Normalized concept name
        """
        if not concept:
            return ''

        if strategy not in self._strategies:
            strategy = 'canonical'

        return self._strategies[strategy](concept)

    def register(self, concept: str, source: str = 'default') -> str:
        """
        Register a concept and return its normalized form.

        Maintains mapping from normalized -> original for each source.

        Args:
            concept: Original concept name
            source: Source identifier (e.g., 'linkbase', 'statement', 'taxonomy')

        Returns:
            Normalized concept name
        """
        normalized = self.normalize(concept)

        if normalized not in self._originals:
            self._originals[normalized] = {}

        self._originals[normalized][source] = concept

        return normalized

    def get_original(self, normalized: str, source: str = 'default') -> str:
        """
        Get original concept name from normalized form.

        Args:
            normalized: Normalized concept name
            source: Source to get original from

        Returns:
            Original concept name, or normalized if not found
        """
        if normalized in self._originals:
            if source in self._originals[normalized]:
                return self._originals[normalized][source]
            # Return any original if specific source not found
            if self._originals[normalized]:
                return next(iter(self._originals[normalized].values()))

        return normalized

    def get_all_originals(self, normalized: str) -> dict[str, str]:
        """
        Get all original names for a normalized concept.

        Args:
            normalized: Normalized concept name

        Returns:
            Dictionary mapping source -> original_name
        """
        return self._originals.get(normalized, {})

    def build_normalized_lookup(
        self,
        concepts: dict,
        source: str = 'default'
    ) -> dict:
        """
        Build a lookup dictionary with normalized keys.

        Useful for creating fact lookups that work with any separator format.

        Args:
            concepts: Dictionary with concept names as keys
            source: Source identifier for these concepts

        Returns:
            New dictionary with normalized keys, original values
        """
        normalized_lookup = {}

        for concept, value in concepts.items():
            norm_key = self.register(concept, source)
            normalized_lookup[norm_key] = value

        return normalized_lookup

    def clear(self):
        """Clear all registered mappings."""
        self._originals.clear()

    # =========================================================================
    # Strategy Implementations
    # =========================================================================

    def _normalize_canonical(self, concept: str) -> str:
        """
        Canonical normalization: extract local name, lowercase, remove separators.

        This is the standard normalization for comparison.
        """
        local_name = self._extract_local_name(concept)
        return normalize_name(local_name)

    def _extract_local_name(self, concept: str) -> str:
        """
        Extract local name from qualified concept.

        Handles:
        - Clark notation: {namespace}LocalName
        - Colon separator: us-gaap:Assets
        - Underscore separator: us-gaap_Assets, v_CustomConcept
        """
        if not concept:
            return ''

        # Handle Clark notation: {namespace}LocalName
        if concept.startswith(CLARK_NOTATION_START) and CLARK_NOTATION_END in concept:
            return concept.split(CLARK_NOTATION_END)[-1]

        # Handle colon separator (us-gaap:Assets)
        # But NOT if it looks like a URL (contains ://)
        if ':' in concept and '://' not in concept:
            return concept.split(':')[-1]

        # Handle underscore separator (us-gaap_Assets or v_CustomConcept)
        if '_' in concept:
            parts = concept.split('_', 1)
            if len(parts) == 2:
                prefix = parts[0].lower()

                # Check if prefix is a known taxonomy prefix
                if prefix in KNOWN_TAXONOMY_PREFIXES:
                    return parts[1]

                # Check if prefix looks like a company extension
                # Company extension prefixes are typically:
                # 1. Short (1-6 characters)
                # 2. All alphabetic
                # 3. The rest starts with uppercase (CamelCase concept)
                is_company_prefix = (
                    len(prefix) <= MAX_EXTENSION_PREFIX_LENGTH and
                    prefix.isalpha() and
                    len(parts[1]) > 0 and
                    parts[1][0].isupper()
                )
                if is_company_prefix:
                    return parts[1]

        return concept

    def _normalize_full_qualified(self, concept: str) -> str:
        """
        Keep namespace prefix, normalize separator to canonical.
        """
        if not concept:
            return ''

        # Handle Clark notation
        if concept.startswith(CLARK_NOTATION_START) and CLARK_NOTATION_END in concept:
            parts = concept.split(CLARK_NOTATION_END)
            local = parts[-1]
            return local.lower()

        # Replace all separators with canonical
        result = concept
        for sep in CONCEPT_SEPARATORS:
            if sep != CANONICAL_SEPARATOR:
                result = result.replace(sep, CANONICAL_SEPARATOR)

        return result.lower()

    def _normalize_auto(self, concept: str) -> str:
        """
        Auto-detect format and apply appropriate normalization.
        """
        if not concept:
            return ''

        # Clark notation -> canonical
        if concept.startswith(CLARK_NOTATION_START):
            return self._normalize_canonical(concept)

        # Qualified name -> canonical
        if ':' in concept or '_' in concept:
            return self._normalize_canonical(concept)

        # Already local name
        return normalize_name(concept)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def is_qualified_name(self, concept: str) -> bool:
        """Check if concept has a namespace qualifier."""
        if not concept:
            return False
        return (
            CLARK_NOTATION_START in concept or
            ':' in concept or
            '_' in concept
        )

    def get_namespace_prefix(self, concept: str) -> Optional[str]:
        """
        Extract namespace prefix from concept.

        Returns None if no prefix found.
        """
        if not concept:
            return None

        # Clark notation
        if concept.startswith(CLARK_NOTATION_START) and CLARK_NOTATION_END in concept:
            return concept[1:concept.index(CLARK_NOTATION_END)]

        # Colon separator
        if ':' in concept and '://' not in concept:
            return concept.split(':')[0]

        # Underscore separator
        if '_' in concept:
            parts = concept.split('_', 1)
            prefix = parts[0].lower()
            if prefix in KNOWN_TAXONOMY_PREFIXES or len(prefix) <= MAX_EXTENSION_PREFIX_LENGTH:
                return parts[0]

        return None


__all__ = ['Normalizer', 'normalize_name']
