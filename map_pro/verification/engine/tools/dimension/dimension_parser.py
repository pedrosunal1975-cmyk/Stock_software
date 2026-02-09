# Path: verification/engine/checks_v2/tools/dimension/dimension_parser.py
"""
Dimension Parser for XBRL Verification

Parses definition linkbase and instance documents to understand dimensional structures.

Techniques consolidated from:
- checks/handlers/dimension_handler.py

DESIGN: Parser that can extract dimensional information from XBRL files.
Maintains parsed state for lookups during verification.

XBRL DIMENSIONAL CONCEPTS:
1. Hypercube (Table): Container for dimensional structure
2. Dimension (Axis): A dimensional qualifier (e.g., ClassOfStockAxis)
3. Domain: The set of allowed values for a dimension
4. Member: A specific value in a domain (e.g., CommonClassAMember)
5. Default Member: The member that applies when no explicit qualifier is given
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from .dimension_info import (
    Dimension,
    DimensionMember,
    RoleDimensions,
    ContextDimensions,
)
from ..naming import extract_local_name
from ...constants.xbrl import (
    XLINK_NAMESPACE,
    XBRL_INSTANCE_NAMESPACE as XBRLI_NAMESPACE,
    XBRL_DIMENSIONAL_INSTANCE_NAMESPACE as XBRLDI_NAMESPACE,
    XBRL_LINKBASE_NAMESPACE as LINK_NAMESPACE,
)


class DimensionParser:
    """
    Parses XBRL dimensional structures from linkbase and instance documents.

    Extracts:
    - Which dimensions apply to which roles
    - Default members for each dimension
    - Context dimensional qualifiers

    This is a STATEFUL tool - it accumulates parsed information.

    Usage:
        parser = DimensionParser()

        # Parse definition linkbase
        parser.parse_definition_linkbase('path/to/_def.xml')

        # Parse instance contexts
        parser.parse_instance_contexts('path/to/instance.xml')

        # Check if context is default
        is_default = parser.is_default_context('c-4', role_name='BalanceSheet')
    """

    # XML namespace mappings
    NS = {
        'link': LINK_NAMESPACE,
        'xlink': XLINK_NAMESPACE,
        'xbrli': XBRLI_NAMESPACE,
        'xbrldi': XBRLDI_NAMESPACE,
    }

    def __init__(self):
        self.logger = logging.getLogger('tools.dimension.parser')
        self.roles: dict[str, RoleDimensions] = {}
        self.contexts: dict[str, ContextDimensions] = {}
        self._parsed_def = False
        self._parsed_instance = False

    def parse_definition_linkbase(self, def_file: str | Path) -> bool:
        """
        Parse definition linkbase to extract dimensional structure.

        Args:
            def_file: Path to _def.xml file

        Returns:
            True if parsed successfully
        """
        try:
            tree = ET.parse(def_file)
            root = tree.getroot()

            for def_link in root.findall('.//link:definitionLink', self.NS):
                role_uri = def_link.get(f'{{{XLINK_NAMESPACE}}}role', '')
                role_name = role_uri.split('/')[-1]

                role_dims = RoleDimensions(role=role_uri, role_name=role_name)

                # Build locator map
                locators = {}
                for loc in def_link.findall('link:loc', self.NS):
                    label = loc.get(f'{{{XLINK_NAMESPACE}}}label', '')
                    href = loc.get(f'{{{XLINK_NAMESPACE}}}href', '')
                    if '#' in href:
                        concept = href.split('#')[-1]
                        locators[label] = concept

                # Process arcs
                for arc in def_link.findall('link:definitionArc', self.NS):
                    arcrole = arc.get(f'{{{XLINK_NAMESPACE}}}arcrole', '')
                    from_label = arc.get(f'{{{XLINK_NAMESPACE}}}from', '')
                    to_label = arc.get(f'{{{XLINK_NAMESPACE}}}to', '')

                    from_concept = locators.get(from_label, from_label)
                    to_concept = locators.get(to_label, to_label)

                    # Hypercube-dimension: identifies dimensions for a hypercube
                    if 'hypercube-dimension' in arcrole:
                        dim = Dimension(name=to_concept)
                        role_dims.dimensions[to_concept] = dim

                    # Dimension-default: sets the default member
                    elif 'dimension-default' in arcrole:
                        if from_concept in role_dims.dimensions:
                            role_dims.dimensions[from_concept].default_member = to_concept

                    # Dimension-domain: sets the domain
                    elif 'dimension-domain' in arcrole:
                        if from_concept in role_dims.dimensions:
                            role_dims.dimensions[from_concept].domain = to_concept

                    # All: links line items to hypercube
                    elif arcrole.endswith('/all'):
                        role_dims.hypercube = to_concept

                if role_dims.dimensions:
                    self.roles[role_name] = role_dims

            self._parsed_def = True
            self.logger.info(f"Parsed {len(self.roles)} roles with dimensions")
            return True

        except Exception as e:
            self.logger.error(f"Failed to parse definition linkbase: {e}")
            return False

    def parse_instance_contexts(self, instance_file: str | Path) -> bool:
        """
        Parse XBRL instance document to extract context definitions.

        Args:
            instance_file: Path to XBRL instance document (.xml or .htm)

        Returns:
            True if parsed successfully
        """
        try:
            tree = ET.parse(instance_file)
            root = tree.getroot()

            # Find all context elements
            for ctx in root.findall(f'.//{{{XBRLI_NAMESPACE}}}context'):
                ctx_id = ctx.get('id', '')
                if not ctx_id:
                    continue

                ctx_dims = ContextDimensions(context_id=ctx_id)

                # Extract period
                period = ctx.find(f'{{{XBRLI_NAMESPACE}}}period')
                if period is not None:
                    instant = period.find(f'{{{XBRLI_NAMESPACE}}}instant')
                    if instant is not None:
                        ctx_dims.period_type = 'instant'
                        ctx_dims.period_value = instant.text or ''
                    else:
                        start = period.find(f'{{{XBRLI_NAMESPACE}}}startDate')
                        end = period.find(f'{{{XBRLI_NAMESPACE}}}endDate')
                        if start is not None and end is not None:
                            ctx_dims.period_type = 'duration'
                            ctx_dims.period_value = f"{start.text}_{end.text}"

                # Extract entity
                entity = ctx.find(f'.//{{{XBRLI_NAMESPACE}}}identifier')
                if entity is not None:
                    ctx_dims.entity = entity.text or ''

                # Extract dimensional qualifiers from segment
                segment = ctx.find(f'.//{{{XBRLI_NAMESPACE}}}segment')
                if segment is not None:
                    for explicit in segment.findall(f'.//{{{XBRLDI_NAMESPACE}}}explicitMember'):
                        dimension = explicit.get('dimension', '')
                        member = explicit.text or ''
                        if dimension:
                            ctx_dims.dimensions[dimension] = member

                self.contexts[ctx_id] = ctx_dims

            self._parsed_instance = True
            self.logger.info(f"Parsed {len(self.contexts)} contexts")
            return True

        except Exception as e:
            self.logger.error(f"Failed to parse instance contexts: {e}")
            return False

    def is_default_context(
        self,
        context_id: str,
        role_name: str = None,
        context_dimensions: dict[str, str] = None
    ) -> bool:
        """
        Check if a context is a "default" context (no non-default dimensions).

        A context is default if:
        1. It has no dimensional qualifiers, OR
        2. All its dimensional qualifiers are default members

        Args:
            context_id: The context ID to check
            role_name: Optional role name to check against
            context_dimensions: Optional dict of dimension->member for the context

        Returns:
            True if context is default (no non-default dimensions)
        """
        # Get context dimensions
        dims = context_dimensions
        if dims is None and context_id in self.contexts:
            dims = self.contexts[context_id].dimensions

        if not dims:
            return True  # No dimensions = default

        # Check each dimension against role's defaults
        if role_name and role_name in self.roles:
            role_dims = self.roles[role_name]
            for dim_name, member in dims.items():
                dim_local = extract_local_name(dim_name)
                # Find matching dimension in role
                for role_dim_name, role_dim in role_dims.dimensions.items():
                    if self._names_match(dim_local, role_dim_name):
                        if not role_dim.is_default_value(member):
                            return False  # Non-default member found
        else:
            # No role info - any dimension makes it non-default
            return len(dims) == 0

        return True

    def get_role_for_statement(self, statement_name: str) -> Optional[RoleDimensions]:
        """
        Get the role dimensions for a statement by name matching.

        Args:
            statement_name: Name like "ConsolidatedBalanceSheets"

        Returns:
            RoleDimensions if found
        """
        statement_norm = statement_name.lower()
        for role_name, role_dims in self.roles.items():
            role_norm = role_name.lower()
            if statement_norm in role_norm or role_norm in statement_norm:
                return role_dims
        return None

    def get_context_info(self, context_id: str) -> Optional[ContextDimensions]:
        """Get context dimension information."""
        return self.contexts.get(context_id)

    def group_contexts_by_period(self) -> dict[str, list[str]]:
        """
        Group context IDs by their period.

        Returns:
            Dict mapping period_value -> list of context IDs
        """
        groups = {}
        for ctx_id, ctx_dims in self.contexts.items():
            period = ctx_dims.period_value
            if period not in groups:
                groups[period] = []
            groups[period].append(ctx_id)
        return groups

    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two names match (ignoring namespace prefixes)."""
        local1 = extract_local_name(name1)
        local2 = extract_local_name(name2)
        return local1.lower() == local2.lower()

    def get_summary(self) -> dict:
        """Get summary of parsed dimensional structure."""
        return {
            'roles_with_dimensions': len(self.roles),
            'total_contexts': len(self.contexts),
            'contexts_with_dimensions': sum(
                1 for ctx in self.contexts.values() if ctx.dimensions
            ),
            'roles': {
                name: {
                    'dimensions': list(role.dimensions.keys()),
                    'hypercube': role.hypercube,
                }
                for name, role in self.roles.items()
            }
        }


__all__ = ['DimensionParser']
