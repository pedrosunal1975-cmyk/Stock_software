# Path: mat_acc/process/hierarchy/linkbase_parser.py
"""
Linkbase Parser - Parses XBRL presentation and calculation linkbases.

This module reads the presentation and calculation linkbase XML files
and extracts the hierarchical structure of financial statements.

MARKET AGNOSTIC: Works with any XBRL filing (SEC, ESEF, FCA, etc.)
The linkbase structure is standardized in XBRL 2.1 specification.

Structure of presentation linkbase:
- roleRef: Defines statement roles (e.g., Balance Sheet, Income Statement)
- presentationLink: One per statement, contains hierarchy
  - loc: Concept locators with labels
  - presentationArc: Parent-child relationships with order
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# XBRL namespaces (standard across all markets)
XBRL_NAMESPACES = {
    'link': 'http://www.xbrl.org/2003/linkbase',
    'xlink': 'http://www.w3.org/1999/xlink',
    'xbrli': 'http://www.xbrl.org/2003/instance',
}


@dataclass
class LinkbaseLocator:
    """Represents a locator (loc) element in a linkbase."""
    label: str
    href: str
    concept_name: str = ""

    def __post_init__(self):
        """Extract concept name from href."""
        if self.href and '#' in self.href:
            self.concept_name = self.href.split('#')[-1]
        elif self.href:
            self.concept_name = self.href.split('/')[-1]


@dataclass
class LinkbaseArc:
    """Represents an arc (presentationArc/calculationArc) element."""
    from_label: str
    to_label: str
    order: float = 0.0
    weight: float = 1.0
    preferred_label: str = ""
    use: str = "optional"
    priority: int = 0


@dataclass
class StatementRole:
    """Represents a statement role (e.g., Balance Sheet)."""
    role_uri: str
    role_definition: str = ""
    locators: dict[str, LinkbaseLocator] = field(default_factory=dict)
    arcs: list[LinkbaseArc] = field(default_factory=list)
    roots: list[str] = field(default_factory=list)

    @property
    def statement_type(self) -> str:
        """Detect statement type from role URI or definition."""
        uri_lower = self.role_uri.lower()
        def_lower = self.role_definition.lower()
        combined = uri_lower + " " + def_lower

        # Balance Sheet indicators
        if any(kw in combined for kw in [
            'balancesheet', 'balance_sheet', 'financialposition',
            'financial_position', 'statementoffinancialposition'
        ]):
            return 'BALANCE_SHEET'

        # Income Statement indicators
        if any(kw in combined for kw in [
            'incomestatement', 'income_statement', 'operations',
            'profitloss', 'profit_loss', 'earnings', 'comprehensiveincome'
        ]):
            return 'INCOME_STATEMENT'

        # Cash Flow indicators
        if any(kw in combined for kw in [
            'cashflow', 'cash_flow', 'cashflows'
        ]):
            return 'CASH_FLOW'

        # Equity Statement indicators
        if any(kw in combined for kw in [
            'stockholdersequity', 'shareholdersequity', 'equity',
            'changesinequity', 'statementofequity'
        ]):
            return 'EQUITY'

        return 'OTHER'


class LinkbaseParser:
    """
    Parses XBRL presentation and calculation linkbase files.

    Market agnostic - works with any XBRL filing that follows
    the XBRL 2.1 linkbase specification.

    Example:
        parser = LinkbaseParser()
        roles = parser.parse_presentation_linkbase(Path('filing_pre.xml'))

        for role in roles:
            print(f"{role.statement_type}: {len(role.locators)} concepts")
            for arc in role.arcs:
                print(f"  {arc.from_label} -> {arc.to_label}")
    """

    def __init__(self):
        """Initialize the linkbase parser."""
        self._namespaces = XBRL_NAMESPACES.copy()
        self._last_error: Optional[str] = None

    def parse_presentation_linkbase(
        self,
        linkbase_path: Path
    ) -> list[StatementRole]:
        """
        Parse a presentation linkbase XML file.

        Args:
            linkbase_path: Path to the presentation linkbase file (*_pre.xml)

        Returns:
            List of StatementRole objects, one per statement
        """
        try:
            tree = ET.parse(linkbase_path)
            root = tree.getroot()

            # Register namespaces from the document
            self._extract_namespaces(root)

            roles = []

            # Find all presentationLink elements
            for pres_link in root.iter():
                if pres_link.tag.endswith('}presentationLink') or pres_link.tag == 'presentationLink':
                    role = self._parse_presentation_link(pres_link)
                    if role:
                        roles.append(role)

            return roles

        except ET.ParseError as e:
            self._last_error = f"XML parse error: {e}"
            return []
        except Exception as e:
            self._last_error = f"Error parsing linkbase: {e}"
            return []

    def parse_calculation_linkbase(
        self,
        linkbase_path: Path
    ) -> list[StatementRole]:
        """
        Parse a calculation linkbase XML file.

        Args:
            linkbase_path: Path to the calculation linkbase file (*_cal.xml)

        Returns:
            List of StatementRole objects with calculation relationships
        """
        try:
            tree = ET.parse(linkbase_path)
            root = tree.getroot()

            self._extract_namespaces(root)

            roles = []

            # Find all calculationLink elements
            for calc_link in root.iter():
                if calc_link.tag.endswith('}calculationLink') or calc_link.tag == 'calculationLink':
                    role = self._parse_calculation_link(calc_link)
                    if role:
                        roles.append(role)

            return roles

        except ET.ParseError as e:
            self._last_error = f"XML parse error: {e}"
            return []
        except Exception as e:
            self._last_error = f"Error parsing linkbase: {e}"
            return []

    def find_linkbase_files(self, filing_dir: Path) -> dict[str, Optional[Path]]:
        """
        Find presentation and calculation linkbase files in a filing directory.

        Args:
            filing_dir: Path to the XBRL filing directory

        Returns:
            Dict with 'presentation' and 'calculation' keys
        """
        result = {
            'presentation': None,
            'calculation': None,
            'definition': None,
            'label': None,
        }

        if not filing_dir.exists():
            return result

        # Search for linkbase files by suffix pattern
        for xml_file in filing_dir.glob('*.xml'):
            name_lower = xml_file.name.lower()

            if name_lower.endswith('_pre.xml') or '_pre.' in name_lower:
                result['presentation'] = xml_file
            elif name_lower.endswith('_cal.xml') or '_cal.' in name_lower:
                result['calculation'] = xml_file
            elif name_lower.endswith('_def.xml') or '_def.' in name_lower:
                result['definition'] = xml_file
            elif name_lower.endswith('_lab.xml') or '_lab.' in name_lower:
                result['label'] = xml_file

        return result

    def _parse_presentation_link(self, pres_link: ET.Element) -> Optional[StatementRole]:
        """Parse a single presentationLink element."""
        # Get role URI
        role_uri = ""
        for attr_name in [
            '{http://www.w3.org/1999/xlink}role',
            'role',
            '{%s}role' % self._namespaces.get('xlink', ''),
        ]:
            if attr_name in pres_link.attrib:
                role_uri = pres_link.attrib[attr_name]
                break

        if not role_uri:
            return None

        # Get role title/definition
        role_definition = pres_link.attrib.get(
            '{http://www.w3.org/1999/xlink}title',
            pres_link.attrib.get('title', '')
        )

        role = StatementRole(role_uri=role_uri, role_definition=role_definition)

        # Parse locators
        for child in pres_link:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            if tag == 'loc':
                loc = self._parse_locator(child)
                if loc:
                    role.locators[loc.label] = loc

            elif tag == 'presentationArc':
                arc = self._parse_arc(child)
                if arc:
                    role.arcs.append(arc)

        # Determine root concepts (concepts that are parents but not children)
        role.roots = self._find_roots(role)

        return role

    def _parse_calculation_link(self, calc_link: ET.Element) -> Optional[StatementRole]:
        """Parse a single calculationLink element."""
        # Get role URI
        role_uri = ""
        for attr_name in [
            '{http://www.w3.org/1999/xlink}role',
            'role',
        ]:
            if attr_name in calc_link.attrib:
                role_uri = calc_link.attrib[attr_name]
                break

        if not role_uri:
            return None

        role_definition = calc_link.attrib.get(
            '{http://www.w3.org/1999/xlink}title',
            calc_link.attrib.get('title', '')
        )

        role = StatementRole(role_uri=role_uri, role_definition=role_definition)

        # Parse locators and arcs
        for child in calc_link:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            if tag == 'loc':
                loc = self._parse_locator(child)
                if loc:
                    role.locators[loc.label] = loc

            elif tag == 'calculationArc':
                arc = self._parse_arc(child, is_calculation=True)
                if arc:
                    role.arcs.append(arc)

        return role

    def _parse_locator(self, loc_elem: ET.Element) -> Optional[LinkbaseLocator]:
        """Parse a loc element."""
        xlink_ns = '{http://www.w3.org/1999/xlink}'

        label = loc_elem.attrib.get(f'{xlink_ns}label', loc_elem.attrib.get('label', ''))
        href = loc_elem.attrib.get(f'{xlink_ns}href', loc_elem.attrib.get('href', ''))

        if not label:
            return None

        return LinkbaseLocator(label=label, href=href)

    def _parse_arc(
        self,
        arc_elem: ET.Element,
        is_calculation: bool = False
    ) -> Optional[LinkbaseArc]:
        """Parse a presentationArc or calculationArc element."""
        xlink_ns = '{http://www.w3.org/1999/xlink}'

        from_label = arc_elem.attrib.get(f'{xlink_ns}from', arc_elem.attrib.get('from', ''))
        to_label = arc_elem.attrib.get(f'{xlink_ns}to', arc_elem.attrib.get('to', ''))

        if not from_label or not to_label:
            return None

        order = float(arc_elem.attrib.get('order', 0))
        use = arc_elem.attrib.get('use', 'optional')
        priority = int(arc_elem.attrib.get('priority', 0))

        # For calculation arcs, get weight
        weight = 1.0
        if is_calculation:
            weight = float(arc_elem.attrib.get('weight', 1.0))

        # For presentation arcs, get preferred label
        preferred_label = arc_elem.attrib.get('preferredLabel', '')

        return LinkbaseArc(
            from_label=from_label,
            to_label=to_label,
            order=order,
            weight=weight,
            preferred_label=preferred_label,
            use=use,
            priority=priority,
        )

    def _find_roots(self, role: StatementRole) -> list[str]:
        """Find root concepts (parents that are not children of anything)."""
        # Collect all "to" labels (children)
        children = {arc.to_label for arc in role.arcs}

        # Collect all "from" labels (parents)
        parents = {arc.from_label for arc in role.arcs}

        # Roots are parents that are not children
        root_labels = parents - children

        # Convert labels to concept names
        roots = []
        for label in root_labels:
            if label in role.locators:
                roots.append(role.locators[label].concept_name)

        return roots

    def _extract_namespaces(self, root: ET.Element) -> None:
        """Extract namespaces from root element."""
        for attr, value in root.attrib.items():
            if attr.startswith('{') and '}' in attr:
                continue
            if attr.startswith('xmlns:'):
                prefix = attr.split(':')[1]
                self._namespaces[prefix] = value

    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error


__all__ = [
    'LinkbaseParser',
    'LinkbaseLocator',
    'LinkbaseArc',
    'StatementRole',
    'XBRL_NAMESPACES',
]
