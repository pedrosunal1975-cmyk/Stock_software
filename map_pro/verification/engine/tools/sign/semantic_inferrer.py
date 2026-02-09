# Path: verification/engine/checks_v2/tools/sign/semantic_inferrer.py
"""
Semantic Sign Inferrer for XBRL Concepts

Infers expected sign from concept name semantics as a fallback when
explicit sign information is not available.

Two modes of operation:
1. General mode (default): Uses broad patterns for cash flow analysis
   - Payments, Expenses, Costs, Losses -> typically negative
   - Proceeds, Revenues, Income, Gains -> typically positive

2. Deficit-only mode: Uses narrow patterns for calculation verification
   - Only matches AccumulatedDeficit patterns
   - Safer for equity calculations where Loss$ would incorrectly match NetIncomeLoss

This is a fallback strategy - explicit sign attributes always take precedence.
"""

import logging
import re
from typing import Optional, List

from ..naming import extract_local_name
from ...constants.patterns import (
    DEFICIT_SEMANTIC_PATTERNS,
    NEGATIVE_CONCEPT_PATTERNS,
    POSITIVE_CONCEPT_PATTERNS,
)


class SemanticSignInferrer:
    """
    Infer expected sign from concept name semantics.

    Uses pattern matching on concept names to guess whether a value
    should typically be positive or negative.

    Usage:
        # General mode (for cash flow analysis)
        inferrer = SemanticSignInferrer()

        # Deficit-only mode (for calculation verification)
        inferrer = SemanticSignInferrer(deficit_only=True)

        # Infer sign for accumulated deficit concept
        sign = inferrer.infer('us-gaap:RetainedEarningsAccumulatedDeficit')
        # Returns -1 (deficit should be negative for equity calculations)

        sign = inferrer.infer('us-gaap:NetIncomeLoss')
        # In deficit-only mode: Returns None (not a deficit pattern)
        # In general mode: Returns -1 (matches Loss$ pattern - DANGEROUS!)
    """

    def __init__(
        self,
        deficit_only: bool = False,
        custom_negative_patterns: Optional[List[str]] = None,
        custom_positive_patterns: Optional[List[str]] = None
    ):
        """
        Initialize the inferrer with compiled patterns.

        Args:
            deficit_only: If True, only use deficit patterns (safer for calculations)
            custom_negative_patterns: Override negative patterns with custom list
            custom_positive_patterns: Override positive patterns with custom list
        """
        self.logger = logging.getLogger('tools.sign.semantic_inferrer')
        self._deficit_only = deficit_only

        # Determine which patterns to use
        if custom_negative_patterns is not None:
            negative_patterns = custom_negative_patterns
        elif deficit_only:
            # Use only deficit patterns for safer calculation verification
            negative_patterns = DEFICIT_SEMANTIC_PATTERNS
        else:
            # Use broad patterns for general analysis
            negative_patterns = NEGATIVE_CONCEPT_PATTERNS

        if custom_positive_patterns is not None:
            positive_patterns = custom_positive_patterns
        else:
            positive_patterns = POSITIVE_CONCEPT_PATTERNS

        self._negative_patterns = [
            re.compile(p, re.IGNORECASE) for p in negative_patterns
        ]
        self._positive_patterns = [
            re.compile(p, re.IGNORECASE) for p in positive_patterns
        ]

    def infer(self, concept: str) -> Optional[int]:
        """
        Infer expected sign from concept name semantics.

        Args:
            concept: Concept name (with or without namespace)

        Returns:
            1 for expected positive, -1 for expected negative, None if unknown
        """
        if not concept:
            return None

        # Extract local name for pattern matching
        local_name = extract_local_name(concept)

        # Check negative patterns first
        for pattern in self._negative_patterns:
            if pattern.search(local_name):
                self.logger.debug(f"Inferred negative sign for '{concept}'")
                return -1

        # Check positive patterns
        for pattern in self._positive_patterns:
            if pattern.search(local_name):
                self.logger.debug(f"Inferred positive sign for '{concept}'")
                return 1

        # Cannot determine
        return None

    def is_likely_negative(self, concept: str) -> bool:
        """
        Check if concept is likely to be negative.

        Args:
            concept: Concept name

        Returns:
            True if concept name suggests negative value
        """
        return self.infer(concept) == -1

    def is_likely_positive(self, concept: str) -> bool:
        """
        Check if concept is likely to be positive.

        Args:
            concept: Concept name

        Returns:
            True if concept name suggests positive value
        """
        return self.infer(concept) == 1

    def explain_inference(self, concept: str) -> str:
        """
        Get explanation of sign inference for a concept.

        Args:
            concept: Concept name

        Returns:
            Human-readable explanation
        """
        local_name = extract_local_name(concept)

        for pattern in self._negative_patterns:
            if pattern.search(local_name):
                return f"'{local_name}' matches negative pattern: {pattern.pattern}"

        for pattern in self._positive_patterns:
            if pattern.search(local_name):
                return f"'{local_name}' matches positive pattern: {pattern.pattern}"

        return f"No sign pattern matched for '{local_name}'"


__all__ = ['SemanticSignInferrer']
