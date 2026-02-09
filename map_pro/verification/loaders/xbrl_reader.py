# Path: verification/loaders/xbrl_reader.py
"""
XBRL Linkbase Reader for Verification Module

Reads and parses XBRL linkbase files (calculation, presentation, definition).
Focuses on calculation linkbase for verification checks.

RESPONSIBILITY: Parse company-declared calculation relationships
for use in verification checks.

Company calculation linkbase is the source of truth for how
values should relate to each other.
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .constants import (
    XLINK_NAMESPACE,
    XBRL_LINKBASE_NAMESPACE,
    XLINK_ATTRS,
    LINKBASE_ELEMENTS,
    CALCULATION_LINKBASE_PATTERNS,
    PRESENTATION_LINKBASE_PATTERNS,
)
from .xbrl_filings import XBRLFilingsLoader


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


class XBRLReader:
    """
    Reads XBRL linkbase files for verification.

    Parses calculation and presentation linkbases to extract
    company-declared relationships for verification checks.

    Example:
        reader = XBRLReader()
        calc_networks = reader.read_calculation_linkbase(filing_path)
        for network in calc_networks:
            print(f"Role: {network.role}, Arcs: {len(network.arcs)}")
    """

    def __init__(self, config=None):
        """Initialize XBRL reader."""
        self.logger = logging.getLogger('input.xbrl_reader')
        self._xbrl_loader = XBRLFilingsLoader(config) if config else None

    def read_calculation_linkbase(self, filing_path: Path) -> list[CalculationNetwork]:
        """
        Read calculation linkbase from a filing directory.

        Args:
            filing_path: Path to filing directory

        Returns:
            List of CalculationNetwork objects
        """
        self.logger.info(f"Reading calculation linkbase from {filing_path}")

        # Find calculation linkbase file
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

        # Find presentation linkbase file
        pre_file = self._find_linkbase_file(filing_path, PRESENTATION_LINKBASE_PATTERNS)
        if not pre_file:
            self.logger.warning(f"No presentation linkbase found in {filing_path}")
            return []

        return self._parse_presentation_linkbase(pre_file)

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

    def _find_linkbase_file(self, filing_path: Path, patterns: list[str]) -> Optional[Path]:
        """
        Find a linkbase file matching the given patterns.

        Args:
            filing_path: Filing directory path
            patterns: List of filename patterns to match

        Returns:
            Path to linkbase file or None
        """
        if not filing_path.exists():
            return None

        # Search recursively for matching files
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
        """
        Parse a calculation linkbase XML file.

        Args:
            file_path: Path to calculation linkbase file

        Returns:
            List of CalculationNetwork objects
        """
        networks = []

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Find all calculationLink elements
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
            # Get role
            role = calc_link.get(XLINK_ATTRS['role'], '')

            network = CalculationNetwork(role=role)

            # Build locator map (label -> href)
            locators = {}
            for loc in calc_link.iter():
                if loc.tag.endswith('loc'):
                    label = loc.get(XLINK_ATTRS['label'], '')
                    href = loc.get(XLINK_ATTRS['href'], '')
                    if label and href:
                        # Extract concept name from href
                        concept = self._extract_concept_from_href(href)
                        locators[label] = concept

            # Parse calculationArc elements
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
        """
        Parse a presentation linkbase XML file.

        Args:
            file_path: Path to presentation linkbase file

        Returns:
            List of PresentationNetwork objects
        """
        networks = []

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Find all presentationLink elements
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

            # Build locator map
            locators = {}
            for loc in pre_link.iter():
                if loc.tag.endswith('loc'):
                    label = loc.get(XLINK_ATTRS['label'], '')
                    href = loc.get(XLINK_ATTRS['href'], '')
                    if label and href:
                        concept = self._extract_concept_from_href(href)
                        locators[label] = concept

            # Parse presentationArc elements
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

    def _extract_concept_from_href(self, href: str) -> str:
        """
        Extract concept name from xlink:href.

        href format: schema.xsd#us-gaap_Assets
        Returns: us-gaap:Assets
        """
        if '#' in href:
            fragment = href.split('#')[-1]
            # Replace underscore with colon for namespace separator
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
]
