# Path: verification/loaders/taxonomy_reader.py
"""
Taxonomy Reader for Verification Module

Reads and interprets standard taxonomy definition files.
Used for library checks - validating concepts against standard definitions.

RESPONSIBILITY: Parse taxonomy schema files to extract
concept definitions (period type, balance type, data type).
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .taxonomy import TaxonomyLoader


@dataclass
class ConceptDefinition:
    """
    Definition of a concept from a taxonomy schema.

    Attributes:
        name: Concept local name (e.g., 'Assets')
        namespace: Namespace prefix (e.g., 'us-gaap')
        full_name: Full qualified name (e.g., 'us-gaap:Assets')
        period_type: 'instant' or 'duration'
        balance_type: 'debit', 'credit', or None
        data_type: Data type (e.g., 'monetaryItemType')
        abstract: Whether concept is abstract
        substitution_group: Substitution group (e.g., 'xbrli:item')
    """
    name: str
    namespace: str = ''
    full_name: str = ''
    period_type: Optional[str] = None
    balance_type: Optional[str] = None
    data_type: Optional[str] = None
    abstract: bool = False
    substitution_group: Optional[str] = None


@dataclass
class TaxonomyDefinition:
    """
    Complete taxonomy definition with all concepts.

    Attributes:
        taxonomy_id: Taxonomy identifier (e.g., 'us-gaap-2023')
        namespace: Primary namespace
        concepts: Dictionary of concept definitions
        version: Taxonomy version
    """
    taxonomy_id: str
    namespace: str = ''
    concepts: dict[str, ConceptDefinition] = field(default_factory=dict)
    version: Optional[str] = None


class TaxonomyReader:
    """
    Reads and interprets taxonomy definition files.

    Parses taxonomy schemas to extract concept definitions
    for use in library verification checks.

    Example:
        reader = TaxonomyReader()
        taxonomy = reader.read_taxonomy('us-gaap-2023')

        # Check if concept exists
        concept = taxonomy.concepts.get('us-gaap:Assets')
        if concept:
            print(f"Period type: {concept.period_type}")
            print(f"Balance type: {concept.balance_type}")
    """

    # XML namespaces commonly used in XBRL schemas
    NAMESPACES = {
        'xsd': 'http://www.w3.org/2001/XMLSchema',
        'xbrli': 'http://www.xbrl.org/2003/instance',
        'link': 'http://www.xbrl.org/2003/linkbase',
    }

    def __init__(self, config=None):
        """Initialize taxonomy reader."""
        self.logger = logging.getLogger('input.taxonomy_reader')
        self.taxonomy_loader = TaxonomyLoader(config) if config else None
        self._cache: dict[str, TaxonomyDefinition] = {}

    def read_taxonomy(self, taxonomy_id: str) -> Optional[TaxonomyDefinition]:
        """
        Read a complete taxonomy definition.

        Args:
            taxonomy_id: Taxonomy identifier (directory name)

        Returns:
            TaxonomyDefinition or None if reading fails
        """
        # Check cache first
        if taxonomy_id in self._cache:
            return self._cache[taxonomy_id]

        self.logger.info(f"Reading taxonomy: {taxonomy_id}")

        try:
            if self.taxonomy_loader:
                taxonomy_dir = self.taxonomy_loader.get_taxonomy_directory(taxonomy_id)
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

            taxonomy = self._parse_taxonomy_directory(taxonomy_dir, taxonomy_id)
            if taxonomy:
                self._cache[taxonomy_id] = taxonomy

            return taxonomy

        except FileNotFoundError:
            self.logger.warning(f"Taxonomy not found: {taxonomy_id}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading taxonomy {taxonomy_id}: {e}")
            return None

    def get_concept_definition(
        self,
        taxonomy_id: str,
        concept_name: str
    ) -> Optional[ConceptDefinition]:
        """
        Get definition for a specific concept.

        Args:
            taxonomy_id: Taxonomy identifier
            concept_name: Full concept name (e.g., 'us-gaap:Assets')

        Returns:
            ConceptDefinition or None
        """
        taxonomy = self.read_taxonomy(taxonomy_id)
        if not taxonomy:
            return None

        return taxonomy.concepts.get(concept_name)

    def validate_concept_exists(
        self,
        taxonomy_id: str,
        concept_name: str
    ) -> bool:
        """
        Check if a concept exists in the taxonomy.

        Args:
            taxonomy_id: Taxonomy identifier
            concept_name: Full concept name

        Returns:
            True if concept exists
        """
        return self.get_concept_definition(taxonomy_id, concept_name) is not None

    def _parse_taxonomy_directory(
        self,
        taxonomy_dir: Path,
        taxonomy_id: str
    ) -> Optional[TaxonomyDefinition]:
        """Parse all schema files in a taxonomy directory."""
        taxonomy = TaxonomyDefinition(
            taxonomy_id=taxonomy_id,
        )

        # Find all XSD files
        schema_files = list(taxonomy_dir.rglob('*.xsd'))

        if not schema_files:
            self.logger.warning(f"No schema files found in {taxonomy_dir}")
            return None

        self.logger.info(f"Found {len(schema_files)} schema files")

        # Parse each schema file
        for schema_file in schema_files:
            self._parse_schema_file(schema_file, taxonomy)

        self.logger.info(f"Parsed {len(taxonomy.concepts)} concepts from {taxonomy_id}")

        return taxonomy

    def _parse_schema_file(self, file_path: Path, taxonomy: TaxonomyDefinition) -> None:
        """Parse a single schema file and add concepts to taxonomy."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Get target namespace
            target_ns = root.get('targetNamespace', '')

            # If this is the first schema with a namespace, use it
            if not taxonomy.namespace and target_ns:
                taxonomy.namespace = target_ns

            # Find namespace prefix for target namespace
            ns_prefix = self._find_namespace_prefix(root, target_ns)

            # Parse element declarations
            for element in root.iter():
                if element.tag.endswith('}element') or element.tag == 'element':
                    concept = self._parse_element(element, ns_prefix)
                    if concept:
                        taxonomy.concepts[concept.full_name] = concept

        except ET.ParseError as e:
            self.logger.debug(f"XML parse error in {file_path}: {e}")
        except Exception as e:
            self.logger.debug(f"Error parsing {file_path}: {e}")

    def _parse_element(self, element, ns_prefix: str) -> Optional[ConceptDefinition]:
        """Parse an element declaration into a ConceptDefinition."""
        try:
            name = element.get('name')
            if not name:
                return None

            # Get XBRL-specific attributes
            # These use xbrli namespace attributes
            period_type = element.get(f'{{{self.NAMESPACES["xbrli"]}}}periodType')
            balance_type = element.get(f'{{{self.NAMESPACES["xbrli"]}}}balance')

            # Also try without namespace (some schemas use unprefixed attributes)
            if not period_type:
                period_type = element.get('periodType')
            if not balance_type:
                balance_type = element.get('balance')

            # Get standard schema attributes
            data_type = element.get('type', '')
            abstract = element.get('abstract', 'false').lower() == 'true'
            substitution_group = element.get('substitutionGroup', '')

            full_name = f"{ns_prefix}:{name}" if ns_prefix else name

            return ConceptDefinition(
                name=name,
                namespace=ns_prefix,
                full_name=full_name,
                period_type=period_type,
                balance_type=balance_type,
                data_type=data_type,
                abstract=abstract,
                substitution_group=substitution_group,
            )

        except Exception as e:
            self.logger.debug(f"Error parsing element: {e}")
            return None

    def _find_namespace_prefix(self, root, target_ns: str) -> str:
        """Find the namespace prefix for the target namespace."""
        for prefix, uri in root.attrib.items():
            if uri == target_ns:
                # Remove 'xmlns:' prefix if present
                if prefix.startswith('{'):
                    continue
                if ':' in prefix:
                    return prefix.split(':')[1]
                return prefix

        # Also check nsmap for namespaces declared without prefix attribute
        nsmap = getattr(root, 'nsmap', {})
        for prefix, uri in nsmap.items():
            if uri == target_ns and prefix:
                return prefix

        # Extract prefix from target namespace if possible
        # e.g., http://fasb.org/us-gaap/2023 -> us-gaap
        if target_ns:
            parts = target_ns.rstrip('/').split('/')
            for part in reversed(parts):
                if part and not part.isdigit():
                    return part

        return ''

    def clear_cache(self) -> None:
        """Clear the taxonomy cache."""
        self._cache.clear()
        self.logger.info("Taxonomy cache cleared")


__all__ = ['TaxonomyReader', 'TaxonomyDefinition', 'ConceptDefinition']
