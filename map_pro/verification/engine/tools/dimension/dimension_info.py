# Path: verification/engine/checks_v2/tools/dimension/dimension_info.py
"""
Dimension Data Structures for XBRL Verification

Provides dataclasses for storing dimensional information.

Techniques consolidated from:
- checks/handlers/dimension_handler.py

DESIGN: Simple data containers with helper methods.
"""

from dataclasses import dataclass, field
from typing import Optional

from ..naming import extract_local_name


@dataclass
class DimensionMember:
    """A member of a dimension domain."""
    name: str
    namespace: str = ""
    is_default: bool = False
    parent_member: Optional[str] = None


@dataclass
class Dimension:
    """
    An XBRL dimension (axis) with its members.

    Attributes:
        name: Dimension name (e.g., 'ClassOfStockAxis')
        namespace: Namespace prefix
        domain: Domain concept name
        default_member: Default member name
        members: Dict mapping member name to DimensionMember
    """
    name: str
    namespace: str = ""
    domain: str = ""
    default_member: str = ""
    members: dict[str, DimensionMember] = field(default_factory=dict)

    def is_default_value(self, member: str) -> bool:
        """
        Check if a member is the default (or domain) for this dimension.

        Args:
            member: Member name to check

        Returns:
            True if member is the default
        """
        if not member:
            return True  # No value means default

        # Extract local names for comparison
        member_local = extract_local_name(member)
        default_local = extract_local_name(self.default_member) if self.default_member else ''
        domain_local = extract_local_name(self.domain) if self.domain else ''

        # Normalize for comparison (lowercase)
        member_norm = member_local.lower()
        default_norm = default_local.lower()
        domain_norm = domain_local.lower()

        return member_norm == default_norm or member_norm == domain_norm


@dataclass
class RoleDimensions:
    """
    Dimensions applicable to a specific role (statement).

    Attributes:
        role: Role URI
        role_name: Short role name (e.g., 'ConsolidatedBalanceSheets')
        hypercube: Hypercube concept name
        dimensions: Dict mapping dimension name to Dimension
    """
    role: str
    role_name: str = ""
    hypercube: str = ""
    dimensions: dict[str, Dimension] = field(default_factory=dict)

    def get_dimension_names(self) -> list[str]:
        """Get list of dimension names for this role."""
        return list(self.dimensions.keys())

    def has_dimension(self, name: str) -> bool:
        """Check if role has a specific dimension."""
        local_name = extract_local_name(name)
        for dim_name in self.dimensions.keys():
            if extract_local_name(dim_name).lower() == local_name.lower():
                return True
        return False


@dataclass
class ContextDimensions:
    """
    Dimensional qualifiers for a specific context.

    Attributes:
        context_id: XBRL context identifier
        dimensions: Dict mapping dimension -> member
        period_type: 'instant' or 'duration'
        period_value: Date or start-end string
        entity: Entity identifier
    """
    context_id: str
    dimensions: dict[str, str] = field(default_factory=dict)
    period_type: str = ""
    period_value: str = ""
    entity: str = ""

    def has_dimension(self, dimension_name: str) -> bool:
        """Check if context has a specific dimension."""
        dim_local = extract_local_name(dimension_name).lower()
        for dim in self.dimensions.keys():
            stored_local = extract_local_name(dim).lower()
            if stored_local == dim_local:
                return True
        return False

    def get_member(self, dimension_name: str) -> Optional[str]:
        """Get the member value for a dimension."""
        dim_local = extract_local_name(dimension_name).lower()
        for dim, member in self.dimensions.items():
            stored_local = extract_local_name(dim).lower()
            if stored_local == dim_local:
                return member
        return None

    def is_dimensional(self) -> bool:
        """Check if context has any dimensional qualifiers."""
        return len(self.dimensions) > 0


__all__ = [
    'DimensionMember',
    'Dimension',
    'RoleDimensions',
    'ContextDimensions',
]
