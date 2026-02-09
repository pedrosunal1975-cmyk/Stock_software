# Path: verification/loaders/taxonomy_calc_reader.py
"""
Taxonomy Calculation Linkbase Reader

Reads calculation relationships from standard taxonomy libraries.
These define how concepts should relate mathematically according
to the standard (US-GAAP, IFRS, etc.).

RESPONSIBILITY: Parse taxonomy calculation linkbase files to extract
standard calculation relationships for verification checks.

IMPORTANT: This is separate from company XBRL calculation linkbase.
- Company XBRL: How the company declares their calculations
- Taxonomy calculation: How the standard defines calculations

Both sources should be used for verification and comparison.
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .taxonomy import TaxonomyLoader
from .constants import (
    XLINK_NAMESPACE,
    XBRL_LINKBASE_NAMESPACE,
    XLINK_ATTRS,
    CALCULATION_LINKBASE_PATTERNS,
)


@dataclass
class CalculationRelationship:
    """
    A calculation relationship from standard taxonomy.

    Represents a parent-child relationship where:
    parent_value = sum(child_value * weight for each child)

    Attributes:
        parent_concept: Parent concept name (e.g., 'us-gaap:Assets')
        child_concept: Child concept name (e.g., 'us-gaap:CurrentAssets')
        weight: Calculation weight (+1 for addition, -1 for subtraction)
        order: Display/calculation order
        role: Statement role URI (identifies which statement)
    """
    parent_concept: str
    child_concept: str
    weight: float = 1.0
    order: float = 0.0
    role: str = ''


@dataclass
class TaxonomyCalculations:
    """
    All calculation relationships from a taxonomy.

    Provides multiple access patterns for efficient lookup.

    Attributes:
        taxonomy_id: Taxonomy identifier (e.g., 'us-gaap-2024')
        relationships: All relationships as flat list
        by_parent: Lookup by parent concept
        by_child: Lookup by child concept
        by_role: Lookup by statement role
    """
    taxonomy_id: str
    relationships: list[CalculationRelationship] = field(default_factory=list)
    by_parent: dict[str, list[CalculationRelationship]] = field(default_factory=dict)
    by_child: dict[str, list[CalculationRelationship]] = field(default_factory=dict)
    by_role: dict[str, list[CalculationRelationship]] = field(default_factory=dict)

    def build_indexes(self) -> None:
        """Build lookup indexes from relationships list."""
        self.by_parent.clear()
        self.by_child.clear()
        self.by_role.clear()

        for rel in self.relationships:
            # Index by parent
            if rel.parent_concept not in self.by_parent:
                self.by_parent[rel.parent_concept] = []
            self.by_parent[rel.parent_concept].append(rel)

            # Index by child
            if rel.child_concept not in self.by_child:
                self.by_child[rel.child_concept] = []
            self.by_child[rel.child_concept].append(rel)

            # Index by role
            if rel.role not in self.by_role:
                self.by_role[rel.role] = []
            self.by_role[rel.role].append(rel)

    def get_children(self, parent_concept: str, role: str = None) -> list[tuple[str, float]]:
        """
        Get all children of a parent concept with their weights.

        Args:
            parent_concept: Parent concept name
            role: Optional role filter

        Returns:
            List of (child_concept, weight) tuples
        """
        relationships = self.by_parent.get(parent_concept, [])

        if role:
            relationships = [r for r in relationships if r.role == role]

        return [(r.child_concept, r.weight) for r in sorted(relationships, key=lambda x: x.order)]

    def get_parents(self, child_concept: str, role: str = None) -> list[str]:
        """
        Get all parents that a concept contributes to.

        Args:
            child_concept: Child concept name
            role: Optional role filter

        Returns:
            List of parent concept names
        """
        relationships = self.by_child.get(child_concept, [])

        if role:
            relationships = [r for r in relationships if r.role == role]

        return list(set(r.parent_concept for r in relationships))


class TaxonomyCalcReader:
    """
    Reads calculation linkbase from standard taxonomy libraries.

    Parses taxonomy calculation linkbase files to extract standard
    calculation relationships for use in verification checks.

    Example:
        reader = TaxonomyCalcReader()
        calculations = reader.read_taxonomy_calculations('us-gaap-2024')

        # Get children of Assets
        children = calculations.get_children('us-gaap:Assets')
        for child, weight in children:
            print(f"  {'+' if weight > 0 else '-'} {child}")

        # Get all relationships for Balance Sheet role
        bs_rels = calculations.by_role.get('http://fasb.org/role/statement/StatementOfFinancialPositionClassified')
    """

    def __init__(self, config=None):
        """
        Initialize taxonomy calculation reader.

        Args:
            config: Optional ConfigLoader for path resolution
        """
        self.logger = logging.getLogger('input.taxonomy_calc_reader')
        self._taxonomy_loader = TaxonomyLoader(config) if config else None
        self._cache: dict[str, TaxonomyCalculations] = {}

    def read_taxonomy_calculations(self, taxonomy_id: str) -> Optional[TaxonomyCalculations]:
        """
        Read all calculation relationships from a taxonomy.

        Args:
            taxonomy_id: Taxonomy identifier (directory name, e.g., 'us-gaap-2024')

        Returns:
            TaxonomyCalculations object or None if not found
        """
        # Check cache first
        if taxonomy_id in self._cache:
            self.logger.debug(f"Using cached calculations for {taxonomy_id}")
            return self._cache[taxonomy_id]

        self.logger.info(f"Reading taxonomy calculations: {taxonomy_id}")

        try:
            # Get taxonomy directory
            if self._taxonomy_loader:
                taxonomy_dir = self._taxonomy_loader.get_taxonomy_directory(taxonomy_id)
            else:
                # Try to construct path from config
                from ..core.config_loader import ConfigLoader
                config = ConfigLoader()
                taxonomy_path = config.get('taxonomy_path')
                if taxonomy_path:
                    taxonomy_dir = taxonomy_path / taxonomy_id
                else:
                    self.logger.error("No taxonomy path configured")
                    return None

            if not taxonomy_dir.exists():
                self.logger.warning(f"Taxonomy directory not found: {taxonomy_dir}")
                return None

            # Find calculation linkbase files
            calc_files = self._find_calculation_linkbases(taxonomy_dir)

            if not calc_files:
                self.logger.warning(f"No calculation linkbase found in {taxonomy_id}")
                return None

            self.logger.info(f"Found {len(calc_files)} calculation linkbase files")

            # Parse all calculation linkbases
            calculations = TaxonomyCalculations(taxonomy_id=taxonomy_id)

            for calc_file in calc_files:
                relationships = self._parse_calculation_linkbase(calc_file)
                calculations.relationships.extend(relationships)

            # Build indexes
            calculations.build_indexes()

            self.logger.info(
                f"Parsed {len(calculations.relationships)} calculation relationships "
                f"from {taxonomy_id} ({len(calculations.by_parent)} parent concepts)"
            )

            # Cache the result
            self._cache[taxonomy_id] = calculations

            return calculations

        except FileNotFoundError:
            self.logger.warning(f"Taxonomy not found: {taxonomy_id}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading taxonomy calculations {taxonomy_id}: {e}")
            return None

    def _find_calculation_linkbases(self, taxonomy_dir: Path) -> list[Path]:
        """
        Find all calculation linkbase files in taxonomy directory.

        Searches recursively for files matching calculation linkbase patterns.

        Args:
            taxonomy_dir: Taxonomy directory path

        Returns:
            List of calculation linkbase file paths
        """
        calc_files = []

        # Search recursively
        for file_path in taxonomy_dir.rglob('*'):
            if not file_path.is_file():
                continue

            filename_lower = file_path.name.lower()

            for pattern in CALCULATION_LINKBASE_PATTERNS:
                if pattern.lower() in filename_lower:
                    calc_files.append(file_path)
                    self.logger.debug(f"Found calculation linkbase: {file_path}")
                    break

        return calc_files

    def _parse_calculation_linkbase(self, file_path: Path) -> list[CalculationRelationship]:
        """
        Parse a calculation linkbase XML file.

        Args:
            file_path: Path to calculation linkbase file

        Returns:
            List of CalculationRelationship objects
        """
        relationships = []

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Find all calculationLink elements
            for calc_link in root.iter():
                if calc_link.tag.endswith('calculationLink'):
                    link_relationships = self._parse_calculation_link(calc_link)
                    relationships.extend(link_relationships)

            self.logger.debug(f"Parsed {len(relationships)} relationships from {file_path.name}")

        except ET.ParseError as e:
            self.logger.error(f"XML parse error in {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")

        return relationships

    def _parse_calculation_link(self, calc_link) -> list[CalculationRelationship]:
        """
        Parse a single calculationLink element.

        Args:
            calc_link: calculationLink XML element

        Returns:
            List of CalculationRelationship objects
        """
        relationships = []

        try:
            # Get role
            role = calc_link.get(XLINK_ATTRS['role'], '')

            # Build locator map (label -> concept)
            locators = {}
            for loc in calc_link.iter():
                if loc.tag.endswith('loc'):
                    label = loc.get(XLINK_ATTRS['label'], '')
                    href = loc.get(XLINK_ATTRS['href'], '')
                    if label and href:
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
                        relationships.append(CalculationRelationship(
                            parent_concept=parent_concept,
                            child_concept=child_concept,
                            weight=weight,
                            order=order,
                            role=role
                        ))

        except Exception as e:
            self.logger.error(f"Error parsing calculationLink: {e}")

        return relationships

    def _extract_concept_from_href(self, href: str) -> str:
        """
        Extract concept name from xlink:href.

        href format: schema.xsd#us-gaap_Assets
        Returns: us-gaap:Assets

        Args:
            href: XLink href value

        Returns:
            Normalized concept name (prefix:LocalName)
        """
        if '#' in href:
            fragment = href.split('#')[-1]
            # Replace underscore with colon for namespace separator
            if '_' in fragment:
                parts = fragment.split('_', 1)
                return f"{parts[0]}:{parts[1]}"
            return fragment
        return href

    def get_calculation_tree(
        self,
        taxonomy_id: str,
        parent_concept: str,
        role: str = None
    ) -> Optional[dict]:
        """
        Get a complete calculation tree for a concept.

        Recursively builds the tree structure showing all
        child relationships.

        Args:
            taxonomy_id: Taxonomy identifier
            parent_concept: Root concept for tree
            role: Optional role filter

        Returns:
            Dictionary representing calculation tree, or None
        """
        calculations = self.read_taxonomy_calculations(taxonomy_id)
        if not calculations:
            return None

        return self._build_tree(calculations, parent_concept, role, visited=set())

    def _build_tree(
        self,
        calculations: TaxonomyCalculations,
        concept: str,
        role: str,
        visited: set
    ) -> dict:
        """Build calculation tree recursively."""
        if concept in visited:
            return {'concept': concept, 'circular': True}

        visited.add(concept)

        children = calculations.get_children(concept, role)

        tree = {
            'concept': concept,
            'children': []
        }

        for child_concept, weight in children:
            child_tree = self._build_tree(calculations, child_concept, role, visited.copy())
            child_tree['weight'] = weight
            tree['children'].append(child_tree)

        return tree

    def clear_cache(self) -> None:
        """Clear the taxonomy calculations cache."""
        self._cache.clear()
        self.logger.info("Taxonomy calculations cache cleared")

    def list_available_taxonomies(self) -> list[str]:
        """
        List available taxonomy directories.

        Returns:
            List of taxonomy directory names
        """
        if not self._taxonomy_loader:
            return []

        try:
            taxonomies = self._taxonomy_loader.list_taxonomies()
            return [t.name for t in taxonomies]
        except Exception as e:
            self.logger.error(f"Error listing taxonomies: {e}")
            return []


__all__ = [
    'TaxonomyCalcReader',
    'TaxonomyCalculations',
    'CalculationRelationship',
]
