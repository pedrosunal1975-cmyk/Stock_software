# Path: verification/engine/checks_v2/tools/sign/sign_info.py
"""
Sign Information Data Structures

Data classes for storing and passing sign correction information.
"""

from dataclasses import dataclass
from typing import Optional

from ...constants.enums import SignSource


@dataclass
class SignInfo:
    """
    Sign information for a specific fact.

    Stores all details about a sign correction, including the source
    of the information for diagnostic purposes.

    Attributes:
        concept: XBRL concept name (as stored)
        context_id: XBRL context reference
        sign_multiplier: 1 (no correction) or -1 (negate value)
        source: Where the sign info came from (iXBRL attribute, semantic, etc.)
        original_value: Optional original value before correction
        corrected_value: Optional value after applying correction
        notes: Additional diagnostic information
    """
    concept: str
    context_id: str
    sign_multiplier: int  # 1 or -1
    source: SignSource = SignSource.NONE
    original_value: Optional[float] = None
    corrected_value: Optional[float] = None
    notes: str = ""

    @property
    def needs_correction(self) -> bool:
        """Check if this sign info indicates a correction is needed."""
        return self.sign_multiplier == -1

    def apply_to(self, value: float) -> float:
        """
        Apply sign correction to a value.

        Args:
            value: Original value

        Returns:
            Corrected value
        """
        if self.sign_multiplier == -1:
            return -abs(value)
        return value


__all__ = ['SignInfo', 'SignSource']
