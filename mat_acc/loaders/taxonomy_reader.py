# Path: mat_acc/loaders/taxonomy_reader.py
"""
Taxonomy Reader - Content Interpreter for Taxonomy Libraries

Reads and interprets taxonomy library content discovered by TaxonomyDataLoader.
Extracts labels, element definitions, and other taxonomy metadata.

Architecture:
- Uses TaxonomyDataLoader for directory discovery
- Parses XML schema (.xsd) and linkbase files
- Extracts element labels for display
- Market agnostic - works with any XBRL taxonomy

This is the INTERPRETATION layer:
- taxonomy_data.py: WHERE are taxonomies? (paths only)
- taxonomy_reader.py: WHAT is in them? (content interpretation)

Example:
    from loaders import TaxonomyDataLoader, TaxonomyReader

    loader = TaxonomyDataLoader(config)
    reader = TaxonomyReader(config)

    taxonomy = loader.find_taxonomy_by_name('us-gaap')
    labels = reader.get_labels_for_taxonomy(taxonomy)
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

from config_loader import ConfigLoader
from .taxonomy_data import TaxonomyDataLoader, TaxonomyEntry
from .taxonomy_analyzer import TaxonomyFileAnalyzer
from .constants import (
    SCHEMA_FILE_PATTERNS,
    LABEL_LINKBASE_PATTERNS,
    XLINK_NAMESPACE,
    XBRL_LINKBASE_NAMESPACE,
)


logger = logging.getLogger('loaders.taxonomy_reader')


# ==============================================================================
# NAMESPACE CONSTANTS
# ==============================================================================

# XML Schema namespace
XS_NAMESPACE = 'http://www.w3.org/2001/XMLSchema'

# Common namespace prefixes for ElementTree parsing
NS_MAP = {
    'xs': XS_NAMESPACE,
    'xsd': XS_NAMESPACE,
    'link': XBRL_LINKBASE_NAMESPACE,
    'xlink': XLINK_NAMESPACE,
}


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class TaxonomyElement:
    """
    Definition of a taxonomy element from schema.

    Attributes:
        name: Element local name (e.g., 'Assets')
        element_id: Full element ID
        namespace: Namespace URI
        element_type: XSD type (e.g., 'monetaryItemType')
        substitution_group: Substitution group (e.g., 'item')
        period_type: 'instant' or 'duration'
        balance: 'debit' or 'credit' (for monetary items)
        abstract: Whether element is abstract
        nillable: Whether element can be nil
    """
    name: str
    element_id: str = ''
    namespace: str = ''
    element_type: str = ''
    substitution_group: str = ''
    period_type: str = ''
    balance: str = ''
    abstract: bool = False
    nillable: bool = True


@dataclass
class TaxonomyLabel:
    """
    Label for a taxonomy element.

    Attributes:
        element_name: Element local name
        label_text: Human-readable label
        label_role: Label role (standard, terse, verbose, etc.)
        language: Language code (en-US, en, etc.)
    """
    element_name: str
    label_text: str
    label_role: str = 'standard'
    language: str = 'en'


@dataclass
class TaxonomyInfo:
    """
    Complete taxonomy information.

    Attributes:
        taxonomy_name: Name of the taxonomy
        taxonomy_path: Path to taxonomy directory
        namespace: Primary namespace URI
        version: Taxonomy version if available
        element_count: Number of elements defined
        label_count: Number of labels available
        elements: Dictionary of element name -> TaxonomyElement
        labels: Dictionary of element name -> list of TaxonomyLabel
    """
    taxonomy_name: str
    taxonomy_path: Path
    namespace: str = ''
    version: str = ''
    element_count: int = 0
    label_count: int = 0
    elements: dict = field(default_factory=dict)
    labels: dict = field(default_factory=dict)

    def get_label(
        self,
        element_name: str,
        role: str = 'standard',
        language: str = 'en'
    ) -> Optional[str]:
        """
        Get label for an element.

        Args:
            element_name: Element local name
            role: Label role (default: standard)
            language: Language code (default: en)

        Returns:
            Label text or None if not found
        """
        if element_name not in self.labels:
            return None

        for label in self.labels[element_name]:
            # Match role and language
            if role in label.label_role and language in label.language:
                return label.label_text

        # Fallback: any label for this element
        if self.labels[element_name]:
            return self.labels[element_name][0].label_text

        return None


# ==============================================================================
# TAXONOMY READER
# ==============================================================================

class TaxonomyReader:
    """
    Reads and interprets taxonomy library content.

    Parses schema files to extract element definitions.
    Parses label linkbases to extract human-readable labels.

    Example:
        reader = TaxonomyReader(config)

        # Get all info for a taxonomy
        info = reader.read_taxonomy(taxonomy_entry)
        print(f"Elements: {info.element_count}")

        # Get label for a concept
        label = reader.get_element_label('us-gaap', 'Assets')
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize taxonomy reader.

        Args:
            config: ConfigLoader instance. If None, creates new instance.
        """
        self.config = config if config else ConfigLoader()
        self.loader = TaxonomyDataLoader(self.config)

        # Content-based file analyzer (replaces pattern matching)
        self.analyzer = TaxonomyFileAnalyzer()

        # Cache for loaded taxonomies
        self._taxonomy_cache: dict[str, TaxonomyInfo] = {}

        logger.info("TaxonomyReader initialized")

    def read_taxonomy(self, taxonomy: TaxonomyEntry) -> Optional[TaxonomyInfo]:
        """
        Read complete taxonomy information.

        Args:
            taxonomy: TaxonomyEntry from TaxonomyDataLoader

        Returns:
            TaxonomyInfo with elements and labels, or None on error
        """
        logger.info(f"Reading taxonomy: {taxonomy.taxonomy_name}")

        # Check cache
        cache_key = str(taxonomy.taxonomy_path)
        if cache_key in self._taxonomy_cache:
            return self._taxonomy_cache[cache_key]

        try:
            info = TaxonomyInfo(
                taxonomy_name=taxonomy.taxonomy_name,
                taxonomy_path=taxonomy.taxonomy_path,
            )

            # Read schema files for element definitions
            self._read_schema_files(taxonomy, info)

            # Read label linkbases
            self._read_label_files(taxonomy, info)

            info.element_count = len(info.elements)
            info.label_count = sum(len(v) for v in info.labels.values())

            # Cache the result
            self._taxonomy_cache[cache_key] = info

            logger.info(
                f"Read taxonomy {taxonomy.taxonomy_name}: "
                f"{info.element_count} elements, {info.label_count} labels"
            )

            return info

        except Exception as e:
            logger.error(f"Error reading taxonomy {taxonomy.taxonomy_name}: {e}")
            return None

    def get_element_label(
        self,
        taxonomy_name: str,
        element_name: str,
        role: str = 'standard',
        language: str = 'en'
    ) -> Optional[str]:
        """
        Get label for a specific element from a taxonomy.

        Args:
            taxonomy_name: Name of taxonomy (e.g., 'us-gaap')
            element_name: Element local name (e.g., 'Assets')
            role: Label role
            language: Language code

        Returns:
            Label text or None if not found
        """
        # Find and load taxonomy
        taxonomy_entry = self.loader.find_taxonomy_by_name(taxonomy_name)
        if not taxonomy_entry:
            return None

        info = self.read_taxonomy(taxonomy_entry)
        if not info:
            return None

        return info.get_label(element_name, role, language)

    def get_labels_for_concepts(
        self,
        concept_names: list[str],
        taxonomy_name: Optional[str] = None
    ) -> dict[str, str]:
        """
        Get labels for multiple concepts.

        If taxonomy_name is provided, only search that taxonomy.
        Otherwise, search all available taxonomies.

        Args:
            concept_names: List of concept names (may include namespace prefix)
            taxonomy_name: Optional specific taxonomy to search

        Returns:
            Dictionary mapping concept name to label
        """
        results = {}

        # Determine which taxonomies to search
        if taxonomy_name:
            taxonomies = [self.loader.find_taxonomy_by_name(taxonomy_name)]
            taxonomies = [t for t in taxonomies if t is not None]
        else:
            taxonomies = self.loader.discover_all_taxonomies()

        # Load all taxonomies
        taxonomy_infos = []
        for tax in taxonomies:
            info = self.read_taxonomy(tax)
            if info:
                taxonomy_infos.append(info)

        # Find labels for each concept
        for concept in concept_names:
            # Extract local name (remove namespace prefix)
            local_name = self._extract_local_name(concept)

            # Search taxonomies for label
            for info in taxonomy_infos:
                label = info.get_label(local_name)
                if label:
                    results[concept] = label
                    break

            # If no label found, use local name
            if concept not in results:
                results[concept] = local_name

        return results

    def _read_schema_files(
        self,
        taxonomy: TaxonomyEntry,
        info: TaxonomyInfo
    ) -> None:
        """
        Read schema files to extract element definitions.

        Args:
            taxonomy: TaxonomyEntry
            info: TaxonomyInfo to populate
        """
        schema_files = []

        # Find all schema files
        for pattern in SCHEMA_FILE_PATTERNS:
            for schema_file in taxonomy.taxonomy_path.rglob(f'*{pattern}'):
                schema_files.append(schema_file)

        logger.debug(f"Found {len(schema_files)} schema files")

        # Parse each schema file
        for schema_file in schema_files:
            try:
                self._parse_schema(schema_file, info)
            except Exception as e:
                logger.warning(f"Error parsing {schema_file.name}: {e}")

    def _parse_schema(self, schema_path: Path, info: TaxonomyInfo) -> None:
        """
        Parse a single schema file.

        Args:
            schema_path: Path to .xsd file
            info: TaxonomyInfo to populate
        """
        try:
            tree = ET.parse(schema_path)
            root = tree.getroot()

            # Get target namespace
            target_ns = root.get('targetNamespace', '')
            if target_ns and not info.namespace:
                info.namespace = target_ns

            # Find all element definitions
            for elem in root.iter():
                if elem.tag.endswith('}element') or elem.tag == 'element':
                    name = elem.get('name')
                    if name:
                        element = TaxonomyElement(
                            name=name,
                            element_id=elem.get('id', ''),
                            namespace=target_ns,
                            element_type=elem.get('type', ''),
                            substitution_group=elem.get('substitutionGroup', ''),
                            abstract=elem.get('abstract', 'false').lower() == 'true',
                            nillable=elem.get('nillable', 'true').lower() == 'true',
                        )

                        # Extract XBRL-specific attributes
                        for attr_name, attr_value in elem.attrib.items():
                            if 'periodType' in attr_name:
                                element.period_type = attr_value
                            elif 'balance' in attr_name:
                                element.balance = attr_value

                        info.elements[name] = element

        except ET.ParseError as e:
            logger.warning(f"XML parse error in {schema_path.name}: {e}")

    def _read_label_files(
        self,
        taxonomy: TaxonomyEntry,
        info: TaxonomyInfo
    ) -> None:
        """
        Read label linkbase files using content-based detection.

        Uses TaxonomyFileAnalyzer to find files containing labels,
        regardless of filename patterns or extensions (.xml, .xsd).

        Args:
            taxonomy: TaxonomyEntry
            info: TaxonomyInfo to populate
        """
        # Use content-based analyzer to find label sources
        label_files = self.analyzer.find_label_sources(taxonomy.taxonomy_path)

        logger.debug(f"Found {len(label_files)} label files via content analysis")

        # Parse each label file
        for label_file in label_files:
            try:
                self._parse_labels(label_file, info)
            except Exception as e:
                logger.warning(f"Error parsing labels from {label_file.name}: {e}")

        # If no labels found via linkbase structure, try generating from elements
        if not info.labels and info.elements:
            logger.debug(f"No linkbase labels found, generating from element names")
            self._generate_labels_from_elements(info)

    def _parse_labels(self, label_path: Path, info: TaxonomyInfo) -> None:
        """
        Parse a label linkbase file.

        Args:
            label_path: Path to label linkbase XML file
            info: TaxonomyInfo to populate
        """
        try:
            tree = ET.parse(label_path)
            root = tree.getroot()

            # Build locator map (label -> href/element)
            locators = {}
            for elem in root.iter():
                if elem.tag.endswith('}loc') or 'loc' in elem.tag:
                    label_attr = elem.get(f'{{{XLINK_NAMESPACE}}}label')
                    href = elem.get(f'{{{XLINK_NAMESPACE}}}href', '')
                    if label_attr and href:
                        # Extract element name from href
                        if '#' in href:
                            element_id = href.split('#')[-1]
                            # Remove namespace prefix if present
                            element_name = element_id.split('_')[-1] if '_' in element_id else element_id
                            locators[label_attr] = element_name

            # Find label arcs to map locators to labels
            label_arcs = {}
            for elem in root.iter():
                if 'labelArc' in elem.tag:
                    from_attr = elem.get(f'{{{XLINK_NAMESPACE}}}from')
                    to_attr = elem.get(f'{{{XLINK_NAMESPACE}}}to')
                    if from_attr and to_attr:
                        if from_attr not in label_arcs:
                            label_arcs[from_attr] = []
                        label_arcs[from_attr].append(to_attr)

            # Find labels
            labels_map = {}
            for elem in root.iter():
                if elem.tag.endswith('}label') and elem.text:
                    label_attr = elem.get(f'{{{XLINK_NAMESPACE}}}label')
                    role = elem.get(f'{{{XLINK_NAMESPACE}}}role', 'standard')
                    lang = elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')

                    if label_attr:
                        labels_map[label_attr] = {
                            'text': elem.text.strip(),
                            'role': role,
                            'language': lang,
                        }

            # Map labels to elements via arcs
            for locator_label, element_name in locators.items():
                if locator_label in label_arcs:
                    for label_ref in label_arcs[locator_label]:
                        if label_ref in labels_map:
                            label_data = labels_map[label_ref]
                            tax_label = TaxonomyLabel(
                                element_name=element_name,
                                label_text=label_data['text'],
                                label_role=label_data['role'],
                                language=label_data['language'],
                            )

                            if element_name not in info.labels:
                                info.labels[element_name] = []
                            info.labels[element_name].append(tax_label)

        except ET.ParseError as e:
            logger.warning(f"XML parse error in {label_path.name}: {e}")

    def _generate_labels_from_elements(self, info: TaxonomyInfo) -> None:
        """
        Generate human-readable labels from element names.

        Fallback for taxonomies without label linkbases (ecd, dei, cyd).
        Converts camelCase/PascalCase to "Title Case With Spaces".

        Examples:
            IndividualAxis -> Individual Axis
            AllIndividualsMember -> All Individuals Member
            DocumentFiscalPeriodFocus -> Document Fiscal Period Focus

        Args:
            info: TaxonomyInfo to populate with generated labels
        """
        import re

        for element_name, element in info.elements.items():
            if element_name in info.labels:
                continue  # Already has a label

            # Convert camelCase/PascalCase to spaces
            # Insert space before uppercase letters that follow lowercase
            label_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', element_name)
            # Insert space before uppercase letters in sequences (e.g., XMLParser -> XML Parser)
            label_text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', label_text)

            tax_label = TaxonomyLabel(
                element_name=element_name,
                label_text=label_text,
                label_role='generated',
                language='en',
            )
            info.labels[element_name] = [tax_label]

        logger.debug(f"Generated {len(info.labels)} labels from element names")

    def _extract_local_name(self, concept: str) -> str:
        """
        Extract local name from a concept QName.

        Args:
            concept: Concept name possibly with namespace prefix

        Returns:
            Local name without prefix
        """
        # Handle colon separator (us-gaap:Assets)
        if ':' in concept:
            return concept.split(':')[-1]

        # Handle underscore separator (us-gaap_Assets)
        if '_' in concept:
            parts = concept.split('_')
            # Check if first part looks like a namespace prefix
            if len(parts) >= 2 and '-' in parts[0]:
                return '_'.join(parts[1:])

        return concept

    def clear_cache(self) -> None:
        """Clear the taxonomy cache."""
        self._taxonomy_cache.clear()
        self.analyzer.clear_cache()
        logger.info("Taxonomy cache cleared")


__all__ = [
    'TaxonomyReader',
    'TaxonomyInfo',
    'TaxonomyElement',
    'TaxonomyLabel',
]
