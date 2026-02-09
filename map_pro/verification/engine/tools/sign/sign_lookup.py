# Path: verification/engine/checks_v2/tools/sign/sign_lookup.py
"""
Sign Correction Lookup for XBRL Verification

Provides multi-strategy sign correction lookup.

Lookup Strategies (in order):
1. Exact match: (concept, context_id)
2. Normalized concept match: (normalized_concept, context_id)
3. Period-based fallback: Same concept + period, different dimensional hash
4. No correction: Return 1 (no change)

The period-based fallback handles cases where sign="-" exists in one
dimensional context but the fact being verified is in a different
dimensional context with the same period.
"""

import logging
from typing import Optional, Tuple

from .sign_info import SignInfo
from .sign_parser import SignParser
from ..naming import Normalizer, extract_local_name
from ..period import PeriodExtractor
from ...constants.enums import SignSource


class SignLookup:
    """
    Multi-strategy sign correction lookup.

    Uses parsed sign corrections from SignParser and applies various
    matching strategies to find applicable corrections.

    Usage:
        # Create with parser's corrections
        parser = SignParser()
        parser.parse_document('/path/to/instance.htm')

        lookup = SignLookup(parser.get_corrections())

        # Get sign correction multiplier
        multiplier = lookup.get_correction('us-gaap:NetIncome', 'c-1')
        # Returns 1 (no correction) or -1 (negate value)

        # Apply correction to value
        corrected_value, was_corrected = lookup.apply_correction(
            'us-gaap:NetIncome', 'c-1', 1000000
        )
    """

    def __init__(self, corrections: dict = None):
        """
        Initialize lookup with parsed corrections.

        Args:
            corrections: Dictionary of (concept, context_id) -> SignInfo
        """
        self.logger = logging.getLogger('tools.sign.sign_lookup')
        self.corrections = corrections or {}
        self._normalizer = Normalizer()
        self._period_extractor = PeriodExtractor()

    def set_corrections(self, corrections: dict):
        """
        Set or update corrections dictionary.

        Args:
            corrections: New corrections dictionary
        """
        self.corrections = corrections

    def add_correction(
        self,
        concept: str,
        context_id: str,
        multiplier: int,
        source: SignSource = None,
        notes: str = ""
    ):
        """
        Add a single sign correction.

        Args:
            concept: XBRL concept name
            context_id: XBRL context reference
            multiplier: Sign multiplier (1 or -1)
            source: Source of correction (optional)
            notes: Additional notes
        """
        key = (concept, context_id)
        self.corrections[key] = SignInfo(
            concept=concept,
            context_id=context_id,
            sign_multiplier=multiplier,
            source=source or SignSource.XBRL_ATTRIBUTE,
            notes=notes,
        )

    def get_correction(
        self,
        concept: str,
        context_id: str,
        do_normalize: bool = True
    ) -> int:
        """
        Get sign correction multiplier for a fact.

        Lookup strategies (in order):
        1. Exact match: (concept, context_id)
        2. Normalized concept match
        3. Period-based fallback (same concept + period, different hash)

        Args:
            concept: XBRL concept name
            context_id: XBRL context reference
            do_normalize: If True, try normalized concept matching

        Returns:
            1 if no correction needed, -1 if value should be negated
        """
        # Strategy 1: Exact match
        key = (concept, context_id)
        if key in self.corrections:
            self.logger.debug(f"Sign correction FOUND (exact): {concept} in {context_id}")
            return self.corrections[key].sign_multiplier

        # Strategy 2: Normalized concept match
        if do_normalize:
            result = self._lookup_normalized(concept, context_id)
            if result is not None:
                return result

        # Strategy 3: Period-based fallback
        result = self._lookup_period_fallback(concept, context_id)
        if result is not None:
            return result

        # No correction found
        return 1

    def _lookup_normalized(
        self,
        concept: str,
        context_id: str
    ) -> Optional[int]:
        """
        Try normalized concept name lookup.

        Handles both us-gaap:Name and us-gaap_Name formats.
        """
        # Try with underscore/colon conversion
        if '_' in concept:
            norm_concept = concept.replace('_', ':')
            key = (norm_concept, context_id)
            if key in self.corrections:
                return self.corrections[key].sign_multiplier

        # Extract local name and normalize
        local_name = extract_local_name(concept)
        normalized_lookup = self._normalizer.normalize(local_name)

        # Search for matching normalized concept in same context
        for (stored_concept, ctx), info in self.corrections.items():
            if ctx != context_id:
                continue

            stored_local = extract_local_name(stored_concept)
            normalized_stored = self._normalizer.normalize(stored_local)

            if normalized_stored == normalized_lookup:
                self.logger.debug(
                    f"Sign correction FOUND (normalized): {concept} in {context_id}"
                )
                return info.sign_multiplier

        return None

    def _lookup_period_fallback(
        self,
        concept: str,
        context_id: str
    ) -> Optional[int]:
        """
        Period-based fallback lookup.

        When exact context match fails, try matching by period
        (ignoring dimensional hash). This handles cases where sign="-"
        exists for same concept/period but in a different dimensional context.
        """
        lookup_period = self._period_extractor.extract_period_portion(context_id)
        if not lookup_period or not self.corrections:
            return None

        local_name = extract_local_name(concept)
        normalized_lookup = self._normalizer.normalize(local_name)

        # Find sign corrections for same concept and same period
        period_matches = []
        for (stored_concept, stored_ctx), info in self.corrections.items():
            stored_local = extract_local_name(stored_concept)
            if self._normalizer.normalize(stored_local) != normalized_lookup:
                continue

            stored_period = self._period_extractor.extract_period_portion(stored_ctx)
            if stored_period == lookup_period:
                period_matches.append((stored_ctx, info))

        if period_matches:
            # Found match for same concept + period with different hash
            matched_ctx, matched_info = period_matches[0]
            self.logger.info(
                f"Sign correction FOUND (period fallback): '{concept}' "
                f"in period '{lookup_period}'. "
                f"Lookup: '{context_id}', matched: '{matched_ctx}' "
                f"-> {matched_info.sign_multiplier}"
            )
            return matched_info.sign_multiplier

        # Log diagnostic if correction exists but for different period
        if self.corrections:
            self._log_period_mismatch(concept, context_id, lookup_period, normalized_lookup)

        return None

    def _log_period_mismatch(
        self,
        concept: str,
        context_id: str,
        lookup_period: str,
        normalized_lookup: str
    ):
        """Log diagnostic when correction exists for different period."""
        matching_concepts = []
        for (stored_concept, stored_ctx), info in self.corrections.items():
            stored_local = extract_local_name(stored_concept)
            if self._normalizer.normalize(stored_local) == normalized_lookup:
                matching_concepts.append((stored_ctx, info.sign_multiplier))

        if matching_concepts:
            self.logger.debug(
                f"Sign correction exists for '{concept}' but in different period(s). "
                f"Looking for: '{context_id}' (period: {lookup_period}). "
                f"Available: {[ctx for ctx, _ in matching_concepts[:3]]}"
            )

    def apply_correction(
        self,
        concept: str,
        context_id: str,
        value: float
    ) -> Tuple[float, bool]:
        """
        Apply sign correction to a value.

        Args:
            concept: XBRL concept name
            context_id: XBRL context reference
            value: Original value

        Returns:
            Tuple of (corrected_value, was_corrected)
        """
        multiplier = self.get_correction(concept, context_id)
        if multiplier == -1:
            return -abs(value), True
        return value, False

    def get_info(
        self,
        concept: str,
        context_id: str
    ) -> Optional[SignInfo]:
        """
        Get full SignInfo for a fact (exact match only).

        Args:
            concept: XBRL concept name
            context_id: XBRL context reference

        Returns:
            SignInfo if found, None otherwise
        """
        key = (concept, context_id)
        return self.corrections.get(key)


__all__ = ['SignLookup']
