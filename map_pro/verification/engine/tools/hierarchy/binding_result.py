# Path: verification/engine/checks_v2/tools/hierarchy/binding_result.py
"""
Binding Result Data Structures for XBRL Verification

Provides dataclasses for binding check results.

Techniques consolidated from:
- checks/binding/binding_checker.py

DESIGN: Simple data containers for binding results.
"""

from dataclasses import dataclass, field
from typing import Optional

from ...constants.enums import BindingStatus


@dataclass
class BindingResult:
    """
    Result of checking if a calculation binds.

    Attributes:
        binds: Whether the calculation binds (can be verified)
        status: Detailed status explaining why it binds or doesn't
        parent_value: Parent value if found
        parent_unit: Parent unit if found
        parent_decimals: Parent decimals if found
        children_found: List of child info dicts
        children_missing: List of concept names not found in context
        message: Human-readable explanation
    """
    binds: bool
    status: BindingStatus
    parent_value: Optional[float] = None
    parent_unit: Optional[str] = None
    parent_decimals: Optional[int] = None
    children_found: list = field(default_factory=list)
    children_missing: list = field(default_factory=list)
    message: str = ""

    def is_skipped(self) -> bool:
        """Check if binding was skipped (not verified)."""
        return not self.binds

    def get_found_count(self) -> int:
        """Get number of children found."""
        return len(self.children_found)

    def get_missing_count(self) -> int:
        """Get number of children missing."""
        return len(self.children_missing)

    def get_completeness(self) -> float:
        """Get completeness ratio (found / total)."""
        total = len(self.children_found) + len(self.children_missing)
        if total == 0:
            return 0.0
        return len(self.children_found) / total


__all__ = ['BindingResult']
