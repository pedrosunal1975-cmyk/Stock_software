# Path: verification/engine/checks_v2/tools/context/classifier.py
"""
Context Classifier for XBRL Verification

Classifies XBRL contexts as dimensional or default based on their structure.

Techniques consolidated from:
- checks/context/context_classification.py

DESIGN: Stateless tool that can be reused across all processing stages.
"""

import logging
from typing import Optional

from ...constants.patterns import DIMENSIONAL_CONTEXT_INDICATORS


class ContextClassifier:
    """
    Classify XBRL context types.

    Determines if a context is dimensional (contains axis/member qualifiers)
    or default (no dimensional qualifiers).

    This is a STATELESS tool - it performs classification based on
    context_id string patterns without maintaining any state.

    Strategies:
    - 'pattern': Use indicator patterns (axis, member) to detect dimensional
    - 'strict': Only exact pattern matches count as dimensional

    Usage:
        classifier = ContextClassifier()

        # Dimensional context
        is_dim = classifier.is_dimensional('Duration_1_1_2024_To_12_31_2024_axis_member')
        # -> True

        # Default context
        is_dim = classifier.is_dimensional('Duration_1_1_2024_To_12_31_2024')
        # -> False

        # Change strategy
        classifier.set_strategy('strict')
    """

    def __init__(self, strategy: str = 'pattern'):
        """
        Initialize the classifier.

        Args:
            strategy: Classification strategy ('pattern' or 'strict')
        """
        self.logger = logging.getLogger('tools.context.classifier')
        self._strategy = strategy
        self._indicators = DIMENSIONAL_CONTEXT_INDICATORS

    def set_strategy(self, strategy: str) -> None:
        """
        Set the classification strategy.

        Args:
            strategy: 'pattern' (default) or 'strict'
        """
        if strategy not in ('pattern', 'strict'):
            raise ValueError(f"Unknown strategy: {strategy}")
        self._strategy = strategy

    def is_dimensional(self, context_id: str) -> bool:
        """
        Check if a context is dimensional.

        Dimensional contexts contain axis and member identifiers.

        Args:
            context_id: The XBRL context identifier

        Returns:
            True if context is dimensional
        """
        if not context_id:
            return False

        context_lower = context_id.lower()

        if self._strategy == 'pattern':
            return self._check_pattern(context_lower)
        elif self._strategy == 'strict':
            return self._check_strict(context_lower)
        else:
            return self._check_pattern(context_lower)

    def _check_pattern(self, context_lower: str) -> bool:
        """Check using pattern matching (default strategy)."""
        for indicator in self._indicators:
            if indicator in context_lower:
                return True
        return False

    def _check_strict(self, context_lower: str) -> bool:
        """
        Check using strict matching.

        Requires BOTH 'axis' AND 'member' to be present.
        """
        has_axis = 'axis' in context_lower
        has_member = 'member' in context_lower
        return has_axis and has_member

    def is_default(self, context_id: str) -> bool:
        """
        Check if a context is default (non-dimensional).

        Args:
            context_id: The XBRL context identifier

        Returns:
            True if context is default (non-dimensional)
        """
        return not self.is_dimensional(context_id)

    def classify(self, context_id: str) -> str:
        """
        Classify a context as 'dimensional' or 'default'.

        Args:
            context_id: The XBRL context identifier

        Returns:
            'dimensional' or 'default'
        """
        return 'dimensional' if self.is_dimensional(context_id) else 'default'

    def get_indicators(self) -> list[str]:
        """Get the current dimensional indicators."""
        return list(self._indicators)


__all__ = ['ContextClassifier']
