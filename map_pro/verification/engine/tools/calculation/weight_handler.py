# Path: verification/engine/checks_v2/tools/calculation/weight_handler.py
"""
Weight Handler for XBRL Calculations

Handles calculation weights from XBRL linkbase.

Techniques consolidated from:
- checks/handlers/sign_weight_handler.py (weight portion)

DESIGN: Stateless tool for weight operations.
Sign corrections are handled separately in sign/ tools.

XBRL CALCULATION WEIGHTS:
- Weight of 1.0 means ADD to sum
- Weight of -1.0 means SUBTRACT from sum
"""

import logging
from typing import Optional

from ...constants.xbrl import WEIGHT_ADD, WEIGHT_SUBTRACT


class WeightHandler:
    """
    Handles calculation weights from XBRL linkbase.

    Provides:
    - Weight normalization
    - Weight validation
    - Weight application

    This is a STATELESS tool.

    Usage:
        handler = WeightHandler()

        # Normalize weight
        weight = handler.normalize_weight(1)  # -> 1.0

        # Apply weight to value
        contribution = handler.apply_weight(1000000, 1.0)  # -> 1000000
        contribution = handler.apply_weight(500000, -1.0)  # -> -500000
    """

    def __init__(self):
        self.logger = logging.getLogger('tools.calculation.weight_handler')

    def normalize_weight(self, weight) -> float:
        """
        Normalize a weight value to float.

        Args:
            weight: Raw weight value (int, float, or string)

        Returns:
            Normalized float weight
        """
        if weight is None:
            return WEIGHT_ADD

        try:
            w = float(weight)
            # Clamp to valid weights
            if w > 0:
                return WEIGHT_ADD
            elif w < 0:
                return WEIGHT_SUBTRACT
            else:
                return WEIGHT_ADD
        except (ValueError, TypeError):
            return WEIGHT_ADD

    def is_valid_weight(self, weight) -> bool:
        """
        Check if a weight is valid per XBRL spec.

        XBRL only allows weights of 1.0 or -1.0.

        Args:
            weight: Weight to check

        Returns:
            True if weight is valid
        """
        try:
            w = float(weight)
            return w in (WEIGHT_ADD, WEIGHT_SUBTRACT)
        except (ValueError, TypeError):
            return False

    def apply_weight(self, value: float, weight: float) -> float:
        """
        Apply a weight to a value.

        Args:
            value: Numeric value
            weight: Weight to apply (1.0 or -1.0)

        Returns:
            Weighted value (value * weight)
        """
        return value * self.normalize_weight(weight)

    def get_operation_name(self, weight: float) -> str:
        """
        Get human-readable operation name for a weight.

        Args:
            weight: Weight value

        Returns:
            'add' or 'subtract'
        """
        w = self.normalize_weight(weight)
        return 'add' if w > 0 else 'subtract'

    def is_add(self, weight: float) -> bool:
        """Check if weight indicates addition."""
        return self.normalize_weight(weight) > 0

    def is_subtract(self, weight: float) -> bool:
        """Check if weight indicates subtraction."""
        return self.normalize_weight(weight) < 0


__all__ = ['WeightHandler']
