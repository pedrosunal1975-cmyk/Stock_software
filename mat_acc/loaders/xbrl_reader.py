# Path: mat_acc/loaders/xbrl_reader.py
"""
XBRL Linkbase Reader for mat_acc

Reads and parses XBRL linkbase files (calculation, presentation, definition).
Focuses on calculation linkbase for financial analysis.

RESPONSIBILITY: Parse company-declared calculation relationships
for use in ratio calculations and financial analysis.

Company calculation linkbase is the source of truth for how
values should relate to each other.

Adapted from map_pro/verification/loaders/xbrl_reader.py
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .constants import (
    XLINK_NAMESPACE,
    XLINK_ATTRS,
    CALCULATION_LINKBASE_PATTERNS,
    PRESENTATION_LINKBASE_PATTERNS,
    DEFINITION_LINKBASE_PATTERNS,
    LABEL_LINKBASE_PATTERNS,
)
from .xbrl_data import XBRLDataLoader


@dataclass
class CalculationArc:
    """
    A calculation relationship arc.

    Attributes:
        parent_concept: Parent concept (receives the sum)
        child_concept: Child concept (contributes to sum)
        weight: Calculation weight (+1 or -1)
        order: Display order
        role: Extended link role
    """
    parent_concept: str
    child_concept: str
    weight: float = 1.0
    order: float = 0.0
    role: Optional[str] = None


@dataclass
class CalculationNetwork:
    """
    A calculation network from a calculation linkbase.

    Contains all calculation relationships for a specific role (statement).

    Attributes:
        role: Extended link role URI
        arcs: List of calculation arcs
    """
    role: str
    arcs: list[CalculationArc] = field(default_factory=list)


@dataclass
class PresentationArc:
    """
    A presentation relationship arc.

    Attributes:
        parent_concept: Parent concept
        child_concept: Child concept
        order: Display order
        preferred_label: Preferred label role
        role: Extended link role
    """
    parent_concept: str
    child_concept: str
    order: float = 0.0
    preferred_label: Optional[str] = None
    role: Optional[str] = None


@dataclass
class PresentationNetwork:
    """
    A presentation network from a presentation linkbase.

    Attributes:
        role: Extended link role URI
        arcs: List of presentation arcs
    """
    role: str
    arcs: list[PresentationArc] = field(default_factory=list)


@dataclass
class DefinitionArc:
    """
    A definition relationship arc.

    Attributes:
        parent_concept: Parent concept
        child_concept: Child concept
        arcrole: Arc role (relationship type)
        order: Display order
        role: Extended link role
    """
    parent_concept: str
    child_concept: str
    arcrole: Optional[str] = None
    order: float = 0.0
    role: Optional[str] = None


@dataclass
class DefinitionNetwork:
    """
    A definition network from a definition linkbase.

    Attributes:
        role: Extended link role URI
        arcs: List of definition arcs
    """
    role: str
    arcs: list[DefinitionArc] = field(default_factory=list)


class XBRLReader:
    """
    Reads XBRL linkbase files for financial analysis.

    Parses calculation and presentation linkbases to extract
    company-declared relationships for ratio calculations.

    Example:
        reader = XBRLReader(config)
        calc_networks = reader.read_calculation_linkbase(filing_path)
        for network in calc_networks:
            print(f"Role: {network.role}, Arcs: {len(network.arcs)}")
    """

    def __init__(self, config=None):
        """Initialize XBRL reader."""
        self.logger = logging.getLogger('input.xbrl_reader')
        self._xbrl_loader = XBRLDataLoader(config) if config else None

    def read_calculation_linkbase(self, filing_path: Path) -> list[CalculationNetwork]:
        """
        Read calculation linkbase from a filing directory.

        Args:
            filing_path: Path to filing directory

        Returns:
            List of CalculationNetwork objects
        """
        self.logger.info(f"Reading calculation linkbase from {filing_path}")

        calc_file = self._find_linkbase_file(filing_path, CALCULATION_LINKBASE_PATTERNS)
        if not calc_file:
            self.logger.warning(f"No calculation linkbase found in {filing_path}")
            return []

        return self._parse_calculation_linkbase(calc_file)

    def read_presentation_linkbase(self, filing_path: Path) -> list[PresentationNetwork]:
        """
        Read presentation linkbase from a filing directory.

        Args:
            filing_path: Path to filing directory

        Returns:
            List of PresentationNetwork objects
        """
        self.logger.info(f"Reading presentation linkbase from {filing_path}")

        pre_file = self._find_linkbase_file(filing_path, PRESENTATION_LINKBASE_PATTERNS)
        if not pre_file:
            self.logger.warning(f"No presentation linkbase found in {filing_path}")
            return []

        return self._parse_presentation_linkbase(pre_file)

    def read_definition_linkbase(self, filing_path: Path) -> list[DefinitionNetwork]:
        """
        Read definition linkbase from a filing directory.

        Args:
            filing_path: Path to filing directory

        Returns:
            List of DefinitionNetwork objects
        """
        self.logger.info(f"Reading definition linkbase from {filing_path}")

        def_file = self._find_linkbase_file(filing_path, DEFINITION_LINKBASE_PATTERNS)
        if not def_file:
            self.logger.warning(f"No definition linkbase found in {filing_path}")
            return []

        return self._parse_definition_linkbase(def_file)

    def get_declared_calculations(self, filing_path: Path) -> list[CalculationArc]:
        """
        Get all calculation relationships declared by the company.

        Args:
            filing_path: Path to filing directory

        Returns:
            Flattened list of all CalculationArc objects
        """
        networks = self.read_calculation_linkbase(filing_path)
        all_arcs = []
        for network in networks:
            all_arcs.extend(network.arcs)
        return all_arcs

    def get_calculation_children(
        self,
        filing_path: Path,
        parent_concept: str
    ) -> list[CalculationArc]:
        """
        Get all calculation children for a parent concept.

        Args:
            filing_path: Path to filing directory
            parent_concept: Parent concept name

        Returns:
            List of CalculationArc objects where parent matches
        """
        all_arcs = self.get_declared_calculations(filing_path)
        parent_lower = parent_concept.lower()

        children = []
        for arc in all_arcs:
            if parent_lower in arc.parent_concept.lower():
                children.append(arc)

        return children

    def _find_linkbase_file(self, filing_path: Path, patterns: list[str]) -> Optional[Path]:
        """Find a linkbase file matching the given patterns."""
        if not filing_path.exists():
            return None

        for file_path in filing_path.rglob('*'):
            if not file_path.is_file():
                continue

            filename_lower = file_path.name.lower()
            for pattern in patterns:
                if pattern.lower() in filename_lower:
                    self.logger.debug(f"Found linkbase file: {file_path}")
                    return file_path

        return None

    def _parse_calculation_linkbase(self, file_path: Path) -> list[CalculationNetwork]:
        """Parse a calculation linkbase XML file."""
        networks = []

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            for calc_link in root.iter():
                if calc_link.tag.endswith('calculationLink'):
                    network = self._parse_calculation_link(calc_link)
                    if network:
                        networks.append(network)

            self.logger.info(f"Parsed {len(networks)} calculation networks from {file_path}")

        except ET.ParseError as e:
            self.logger.error(f"XML parse error in {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")

        return networks

    def _parse_calculation_link(self, calc_link) -> Optional[CalculationNetwork]:
        """Parse a single calculationLink element."""
        try:
            role = calc_link.get(XLINK_ATTRS['role'], '')
            network = CalculationNetwork(role=role)

            locators = {}
            for loc in calc_link.iter():
                if loc.tag.endswith('loc'):
                    label = loc.get(XLINK_ATTRS['label'], '')
                    href = loc.get(XLINK_ATTRS['href'], '')
                    if label and href:
                        concept = self._extract_concept_from_href(href)
                        locators[label] = concept

            for arc in calc_link.iter():
                if arc.tag.endswith('calculationArc'):
                    from_label = arc.get(XLINK_ATTRS['from'], '')
                    to_label = arc.get(XLINK_ATTRS['to'], '')
                    weight_str = arc.get('weight', '1')
                    order_str = arc.get('order', '0')

                    try:
                        weight = float(weight_str)
                    except ValueError:
                        weight = 1.0

                    try:
                        order = float(order_str)
                    except ValueError:
                        order = 0.0

                    parent_concept = locators.get(from_label, from_label)
                    child_concept = locators.get(to_label, to_label)

                    if parent_concept and child_concept:
                        network.arcs.append(CalculationArc(
                            parent_concept=parent_concept,
                            child_concept=child_concept,
                            weight=weight,
                            order=order,
                            role=role
                        ))

            return network if network.arcs else None

        except Exception as e:
            self.logger.error(f"Error parsing calculationLink: {e}")
            return None

    def _parse_presentation_linkbase(self, file_path: Path) -> list[PresentationNetwork]:
        """Parse a presentation linkbase XML file."""
        networks = []

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            for pre_link in root.iter():
                if pre_link.tag.endswith('presentationLink'):
                    network = self._parse_presentation_link(pre_link)
                    if network:
                        networks.append(network)

            self.logger.info(f"Parsed {len(networks)} presentation networks from {file_path}")

        except ET.ParseError as e:
            self.logger.error(f"XML parse error in {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")

        return networks

    def _parse_presentation_link(self, pre_link) -> Optional[PresentationNetwork]:
        """Parse a single presentationLink element."""
        try:
            role = pre_link.get(XLINK_ATTRS['role'], '')
            network = PresentationNetwork(role=role)

            locators = {}
            for loc in pre_link.iter():
                if loc.tag.endswith('loc'):
                    label = loc.get(XLINK_ATTRS['label'], '')
                    href = loc.get(XLINK_ATTRS['href'], '')
                    if label and href:
                        concept = self._extract_concept_from_href(href)
                        locators[label] = concept

            for arc in pre_link.iter():
                if arc.tag.endswith('presentationArc'):
                    from_label = arc.get(XLINK_ATTRS['from'], '')
                    to_label = arc.get(XLINK_ATTRS['to'], '')
                    order_str = arc.get('order', '0')
                    pref_label = arc.get('preferredLabel')

                    try:
                        order = float(order_str)
                    except ValueError:
                        order = 0.0

                    parent_concept = locators.get(from_label, from_label)
                    child_concept = locators.get(to_label, to_label)

                    if parent_concept and child_concept:
                        network.arcs.append(PresentationArc(
                            parent_concept=parent_concept,
                            child_concept=child_concept,
                            order=order,
                            preferred_label=pref_label,
                            role=role
                        ))

            return network if network.arcs else None

        except Exception as e:
            self.logger.error(f"Error parsing presentationLink: {e}")
            return None

    def _parse_definition_linkbase(self, file_path: Path) -> list[DefinitionNetwork]:
        """Parse a definition linkbase XML file."""
        networks = []

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            for def_link in root.iter():
                if def_link.tag.endswith('definitionLink'):
                    network = self._parse_definition_link(def_link)
                    if network:
                        networks.append(network)

            self.logger.info(f"Parsed {len(networks)} definition networks from {file_path}")

        except ET.ParseError as e:
            self.logger.error(f"XML parse error in {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")

        return networks

    def _parse_definition_link(self, def_link) -> Optional[DefinitionNetwork]:
        """Parse a single definitionLink element."""
        try:
            role = def_link.get(XLINK_ATTRS['role'], '')
            network = DefinitionNetwork(role=role)

            locators = {}
            for loc in def_link.iter():
                if loc.tag.endswith('loc'):
                    label = loc.get(XLINK_ATTRS['label'], '')
                    href = loc.get(XLINK_ATTRS['href'], '')
                    if label and href:
                        concept = self._extract_concept_from_href(href)
                        locators[label] = concept

            for arc in def_link.iter():
                if arc.tag.endswith('definitionArc'):
                    from_label = arc.get(XLINK_ATTRS['from'], '')
                    to_label = arc.get(XLINK_ATTRS['to'], '')
                    arcrole = arc.get(XLINK_ATTRS['arcrole'], '')
                    order_str = arc.get('order', '0')

                    try:
                        order = float(order_str)
                    except ValueError:
                        order = 0.0

                    parent_concept = locators.get(from_label, from_label)
                    child_concept = locators.get(to_label, to_label)

                    if parent_concept and child_concept:
                        network.arcs.append(DefinitionArc(
                            parent_concept=parent_concept,
                            child_concept=child_concept,
                            arcrole=arcrole,
                            order=order,
                            role=role
                        ))

            return network if network.arcs else None

        except Exception as e:
            self.logger.error(f"Error parsing definitionLink: {e}")
            return None

    def _extract_concept_from_href(self, href: str) -> str:
        """
        Extract concept name from xlink:href.

        href format: schema.xsd#us-gaap_Assets
        Returns: us-gaap:Assets
        """
        if '#' in href:
            fragment = href.split('#')[-1]
            if '_' in fragment:
                parts = fragment.split('_', 1)
                return f"{parts[0]}:{parts[1]}"
            return fragment
        return href


__all__ = [
    'XBRLReader',
    'CalculationNetwork',
    'CalculationArc',
    'PresentationNetwork',
    'PresentationArc',
    'DefinitionNetwork',
    'DefinitionArc',
]
