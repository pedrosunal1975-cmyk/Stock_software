# Path: mat_acc/loaders/taxonomy_data.py
"""
Taxonomy Data Loader - Blind Doorkeeper for Taxonomy Libraries

Discovers taxonomy library directories in the taxonomy data bank.
Structure-agnostic doorkeeper - only returns paths, does NOT verify content.

Architecture:
- Recursively scans taxonomy libraries directory
- Returns directory paths and basic file counts
- No assumptions about internal structure
- Content verification is taxonomy_reader.py's job

This is the DISCOVERY layer:
- taxonomy_data.py: WHERE are taxonomies? (paths only)
- taxonomy_reader.py: WHAT is in them? (content interpretation)

Example:
    from loaders import TaxonomyDataLoader

    loader = TaxonomyDataLoader(config)
    taxonomies = loader.discover_all_taxonomies()
    for tax in taxonomies:
        print(f"{tax.taxonomy_name}: {tax.file_count} files")
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config_loader import ConfigLoader
from .constants import (
    MAX_DIRECTORY_DEPTH,
    SCHEMA_FILE_PATTERNS,
    LABEL_LINKBASE_PATTERNS,
)


logger = logging.getLogger('loaders.taxonomy_data')


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class TaxonomyEntry:
    """
    Entry representing a discovered taxonomy library.

    Attributes:
        taxonomy_path: Absolute path to taxonomy directory
        taxonomy_name: Name of the taxonomy (directory name)
        source_type: Source type ('libraries' or 'manual')
        relative_path: Path relative to base taxonomy directory
        file_count: Total files in directory (recursive)
        schema_count: Count of .xsd schema files
        has_labels: Whether label linkbase files exist
    """
    taxonomy_path: Path
    taxonomy_name: str
    source_type: str
    relative_path: Path
    file_count: int = 0
    schema_count: int = 0
    has_labels: bool = False

    @property
    def exists(self) -> bool:
        """Check if taxonomy directory exists."""
        return self.taxonomy_path.exists()


# ==============================================================================
# TAXONOMY DATA LOADER
# ==============================================================================

class TaxonomyDataLoader:
    """
    Blind doorkeeper for discovering taxonomy library directories.

    Recursively scans the taxonomy libraries directory to find all
    available taxonomy packages. Does NOT interpret content - that's
    the job of TaxonomyReader.

    This loader is:
    - Market agnostic (works with US-GAAP, IFRS, UK-GAAP, etc.)
    - Structure agnostic (different taxonomy layouts supported)
    - Read-only (never modifies taxonomy files)

    Example:
        loader = TaxonomyDataLoader(config)

        # Discover all taxonomies
        all_taxonomies = loader.discover_all_taxonomies()

        # Search for specific taxonomy
        us_gaap = loader.find_taxonomy_by_name('us-gaap')
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize taxonomy data loader.

        Args:
            config: ConfigLoader instance. If None, creates new instance.
        """
        self.config = config if config else ConfigLoader()
        self.taxonomy_base = self.config.get('taxonomy_dir')

        if not self.taxonomy_base:
            raise ValueError(
                "Taxonomy directory not configured. "
                "Check MAT_ACC_TAXONOMY_DIR in .env"
            )

        logger.info(f"TaxonomyDataLoader initialized: {self.taxonomy_base}")

    def discover_all_taxonomies(self) -> list[TaxonomyEntry]:
        """
        Discover all taxonomy libraries in the configured directory.

        Handles both flat structures (us-gaap/) and nested structures
        (ifrs-full/2022/, ifrs-full/2023/).

        Returns:
            List of TaxonomyEntry objects for each discovered taxonomy
        """
        logger.info(f"Discovering taxonomies in: {self.taxonomy_base}")

        if not self.taxonomy_base.exists():
            logger.warning(f"Taxonomy directory does not exist: {self.taxonomy_base}")
            return []

        entries = []

        # Scan top-level directories as potential taxonomy libraries
        try:
            for item in self.taxonomy_base.iterdir():
                if item.is_dir():
                    # Try to scan as a taxonomy directory (flat structure)
                    entry = self._scan_taxonomy_directory(
                        item,
                        source_type='libraries'
                    )
                    if entry:
                        entries.append(entry)
                    else:
                        # No schemas at top level - check for nested structure
                        # (e.g., ifrs-full/2022/, ifrs-full/2023/)
                        nested_entries = self._scan_nested_taxonomy(
                            item,
                            source_type='libraries'
                        )
                        entries.extend(nested_entries)
        except PermissionError as e:
            logger.error(f"Permission denied scanning {self.taxonomy_base}: {e}")
        except Exception as e:
            logger.error(f"Error scanning taxonomy directory: {e}")

        logger.info(f"Discovered {len(entries)} taxonomy libraries")
        return entries

    def _scan_nested_taxonomy(
        self,
        parent_dir: Path,
        source_type: str
    ) -> list[TaxonomyEntry]:
        """
        Scan nested taxonomy structure (e.g., ifrs-full/2022/, ifrs-full/2023/).

        Args:
            parent_dir: Parent taxonomy directory (e.g., ifrs-full/)
            source_type: Source type identifier

        Returns:
            List of TaxonomyEntry objects for each version subdirectory
        """
        entries = []
        parent_name = parent_dir.name

        try:
            for subdir in parent_dir.iterdir():
                if subdir.is_dir():
                    entry = self._scan_taxonomy_directory(
                        subdir,
                        source_type=source_type
                    )
                    if entry:
                        # Update taxonomy name to include parent (e.g., ifrs-full-2022)
                        entry.taxonomy_name = f"{parent_name}-{subdir.name}"
                        entries.append(entry)
                        logger.debug(
                            f"Found nested taxonomy: {entry.taxonomy_name}"
                        )
        except Exception as e:
            logger.error(f"Error scanning nested taxonomy {parent_dir}: {e}")

        return entries

    def find_taxonomy_by_name(
        self,
        name: str,
        partial_match: bool = True
    ) -> Optional[TaxonomyEntry]:
        """
        Find a specific taxonomy by name.

        Args:
            name: Taxonomy name to search for (e.g., 'us-gaap', 'ifrs')
            partial_match: If True, matches if name is contained in taxonomy name

        Returns:
            TaxonomyEntry if found, None otherwise
        """
        logger.debug(f"Searching for taxonomy: {name}")

        name_lower = name.lower()
        taxonomies = self.discover_all_taxonomies()

        for tax in taxonomies:
            tax_name_lower = tax.taxonomy_name.lower()
            if partial_match:
                if name_lower in tax_name_lower:
                    logger.debug(f"Found taxonomy: {tax.taxonomy_name}")
                    return tax
            else:
                if name_lower == tax_name_lower:
                    logger.debug(f"Found taxonomy: {tax.taxonomy_name}")
                    return tax

        logger.debug(f"Taxonomy not found: {name}")
        return None

    def find_taxonomies_by_pattern(self, pattern: str) -> list[TaxonomyEntry]:
        """
        Find taxonomies matching a name pattern.

        Args:
            pattern: Pattern to match in taxonomy names (case-insensitive)

        Returns:
            List of matching TaxonomyEntry objects
        """
        logger.debug(f"Searching taxonomies with pattern: {pattern}")

        pattern_lower = pattern.lower()
        taxonomies = self.discover_all_taxonomies()

        matches = [
            tax for tax in taxonomies
            if pattern_lower in tax.taxonomy_name.lower()
        ]

        logger.debug(f"Found {len(matches)} taxonomies matching '{pattern}'")
        return matches

    def get_taxonomy_path(self, name: str) -> Optional[Path]:
        """
        Get the path to a specific taxonomy library.

        Args:
            name: Taxonomy name (e.g., 'us-gaap-2024')

        Returns:
            Path to taxonomy directory or None if not found
        """
        entry = self.find_taxonomy_by_name(name, partial_match=False)
        if entry:
            return entry.taxonomy_path
        return None

    def _scan_taxonomy_directory(
        self,
        directory: Path,
        source_type: str,
        depth: int = 0
    ) -> Optional[TaxonomyEntry]:
        """
        Scan a directory to create a TaxonomyEntry.

        Args:
            directory: Directory to scan
            source_type: Source type identifier
            depth: Current recursion depth

        Returns:
            TaxonomyEntry if valid taxonomy directory, None otherwise
        """
        if depth > MAX_DIRECTORY_DEPTH:
            return None

        try:
            # Count files recursively
            file_count = 0
            schema_count = 0
            has_labels = False

            for item in directory.rglob('*'):
                if item.is_file():
                    file_count += 1
                    item_lower = item.name.lower()

                    # Count schema files
                    if any(item_lower.endswith(p) for p in SCHEMA_FILE_PATTERNS):
                        schema_count += 1

                    # Check for label files
                    if not has_labels:
                        if any(p in item_lower for p in LABEL_LINKBASE_PATTERNS):
                            has_labels = True

            # Only include if it has schema files (likely a real taxonomy)
            if schema_count == 0:
                logger.debug(f"Skipping {directory.name}: no schema files")
                return None

            relative_path = directory.relative_to(self.taxonomy_base)

            entry = TaxonomyEntry(
                taxonomy_path=directory,
                taxonomy_name=directory.name,
                source_type=source_type,
                relative_path=relative_path,
                file_count=file_count,
                schema_count=schema_count,
                has_labels=has_labels,
            )

            logger.debug(
                f"Found taxonomy: {entry.taxonomy_name} "
                f"({entry.file_count} files, {entry.schema_count} schemas)"
            )

            return entry

        except Exception as e:
            logger.error(f"Error scanning {directory}: {e}")
            return None

    def get_summary(self) -> dict:
        """
        Get summary of available taxonomies.

        Returns:
            Dictionary with taxonomy discovery statistics
        """
        taxonomies = self.discover_all_taxonomies()

        total_files = sum(t.file_count for t in taxonomies)
        total_schemas = sum(t.schema_count for t in taxonomies)
        with_labels = sum(1 for t in taxonomies if t.has_labels)

        return {
            'taxonomy_base': str(self.taxonomy_base),
            'taxonomy_count': len(taxonomies),
            'total_files': total_files,
            'total_schemas': total_schemas,
            'with_labels': with_labels,
            'taxonomies': [t.taxonomy_name for t in taxonomies],
        }


__all__ = ['TaxonomyDataLoader', 'TaxonomyEntry']
