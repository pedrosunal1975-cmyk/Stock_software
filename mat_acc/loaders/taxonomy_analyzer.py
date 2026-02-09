# Path: mat_acc/loaders/taxonomy_analyzer.py
"""
Content-Based Taxonomy File Analyzer

Analyzes taxonomy files by inspecting their XML content, not filenames.
Detects what each file contains (labels, elements, linkbases) regardless
of naming conventions used by different taxonomy publishers.

This solves the problem of hardcoded filename patterns that break when:
- SEC uses: ecd-2025.xsd (labels embedded)
- FASB uses: us-gaap-lab-2025.xml (separate label file)
- IFRS uses: lab_full_ifrs-en_2022.xml (different naming)
- Future taxonomies use: who knows what naming?

The solution: Parse the file, check what's inside.

Example:
    analyzer = TaxonomyFileAnalyzer()
    analysis = analyzer.analyze_directory('/path/to/taxonomy')

    # Find all files containing labels
    label_sources = analysis.get_files_with_capability('labels')

    # Find all files with element definitions
    schema_files = analysis.get_files_with_capability('elements')
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger('loaders.taxonomy_analyzer')


# ==============================================================================
# XML CONTENT SIGNATURES
# ==============================================================================
# These are the actual XML elements/attributes that indicate content type.
# This is what we look for INSIDE files, not in filenames.

CONTENT_SIGNATURES = {
    # Label content signatures
    'labels': [
        '{http://www.xbrl.org/2003/linkbase}label',
        '{http://www.xbrl.org/2003/linkbase}labelArc',
        'labelLink',
    ],

    # Element definition signatures
    'elements': [
        '{http://www.w3.org/2001/XMLSchema}element',
        'element',
    ],

    # Presentation linkbase signatures
    'presentation': [
        '{http://www.xbrl.org/2003/linkbase}presentationArc',
        '{http://www.xbrl.org/2003/linkbase}presentationLink',
        'presentationArc',
    ],

    # Calculation linkbase signatures
    'calculation': [
        '{http://www.xbrl.org/2003/linkbase}calculationArc',
        '{http://www.xbrl.org/2003/linkbase}calculationLink',
        'calculationArc',
    ],

    # Definition linkbase signatures
    'definition': [
        '{http://www.xbrl.org/2003/linkbase}definitionArc',
        '{http://www.xbrl.org/2003/linkbase}definitionLink',
        'definitionArc',
    ],

    # Reference linkbase signatures
    'reference': [
        '{http://www.xbrl.org/2003/linkbase}referenceArc',
        '{http://www.xbrl.org/2003/linkbase}referenceLink',
        'referenceArc',
    ],

    # Documentation content
    'documentation': [
        '{http://www.w3.org/2001/XMLSchema}documentation',
        'documentation',
    ],
}

# XML extensions to analyze
ANALYZABLE_EXTENSIONS = {'.xml', '.xsd'}


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class FileCapabilities:
    """
    What a single file contains.

    Attributes:
        file_path: Path to the analyzed file
        capabilities: Set of content types found (labels, elements, etc.)
        element_count: Number of element definitions found
        label_count: Number of labels found
        namespaces: Set of namespace URIs found
        target_namespace: Target namespace if schema file
        error: Error message if analysis failed
    """
    file_path: Path
    capabilities: set = field(default_factory=set)
    element_count: int = 0
    label_count: int = 0
    namespaces: set = field(default_factory=set)
    target_namespace: str = ''
    error: str = ''

    def has_capability(self, capability: str) -> bool:
        """Check if file has a specific capability."""
        return capability in self.capabilities


@dataclass
class DirectoryAnalysis:
    """
    Analysis results for an entire taxonomy directory.

    Attributes:
        directory_path: Path to analyzed directory
        files: Dictionary of file path -> FileCapabilities
        total_files: Total files analyzed
        total_labels: Total labels found across all files
        total_elements: Total elements found across all files
        errors: List of files that failed analysis
    """
    directory_path: Path
    files: dict = field(default_factory=dict)
    total_files: int = 0
    total_labels: int = 0
    total_elements: int = 0
    errors: list = field(default_factory=list)

    def get_files_with_capability(self, capability: str) -> list[Path]:
        """
        Get all files that have a specific capability.

        Args:
            capability: Content type to search for (labels, elements, etc.)

        Returns:
            List of file paths with that capability
        """
        return [
            fc.file_path for fc in self.files.values()
            if fc.has_capability(capability)
        ]

    def get_all_capabilities(self) -> set:
        """Get union of all capabilities found."""
        all_caps = set()
        for fc in self.files.values():
            all_caps.update(fc.capabilities)
        return all_caps

    def summary(self) -> dict:
        """Get summary statistics."""
        return {
            'directory': str(self.directory_path),
            'total_files': self.total_files,
            'total_labels': self.total_labels,
            'total_elements': self.total_elements,
            'capabilities': {
                cap: len(self.get_files_with_capability(cap))
                for cap in ['labels', 'elements', 'presentation',
                           'calculation', 'definition', 'reference']
            },
            'errors': len(self.errors),
        }


# ==============================================================================
# TAXONOMY FILE ANALYZER
# ==============================================================================

class TaxonomyFileAnalyzer:
    """
    Content-based taxonomy file analyzer.

    Inspects XML/XSD files to determine what they contain,
    without relying on filename patterns.

    Example:
        analyzer = TaxonomyFileAnalyzer()

        # Analyze single file
        caps = analyzer.analyze_file(Path('/path/to/ecd-2025.xsd'))
        print(f"Has labels: {caps.has_capability('labels')}")

        # Analyze entire directory
        analysis = analyzer.analyze_directory(Path('/path/to/taxonomy'))
        label_files = analysis.get_files_with_capability('labels')
    """

    def __init__(self, max_elements_sample: int = 1000):
        """
        Initialize analyzer.

        Args:
            max_elements_sample: Maximum elements to check per file
                                (for performance on large files)
        """
        self.max_elements_sample = max_elements_sample
        self._cache: dict[str, FileCapabilities] = {}

    def analyze_file(self, file_path: Path) -> FileCapabilities:
        """
        Analyze a single file to determine its capabilities.

        Args:
            file_path: Path to XML/XSD file

        Returns:
            FileCapabilities describing what the file contains
        """
        # Check cache
        cache_key = str(file_path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        caps = FileCapabilities(file_path=file_path)

        # Skip non-XML files
        if file_path.suffix.lower() not in ANALYZABLE_EXTENSIONS:
            caps.error = f'Not an analyzable file type: {file_path.suffix}'
            return caps

        try:
            # Parse XML
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Get target namespace if present
            caps.target_namespace = root.get('targetNamespace', '')

            # Collect all namespaces used
            for elem in root.iter():
                if elem.tag.startswith('{'):
                    ns = elem.tag.split('}')[0][1:]
                    caps.namespaces.add(ns)

            # Check for each content type
            element_count = 0
            label_count = 0

            for elem in root.iter():
                tag = elem.tag

                # Count and check for element definitions
                for sig in CONTENT_SIGNATURES['elements']:
                    if tag.endswith(sig) or tag == sig:
                        if elem.get('name'):  # Only count named elements
                            element_count += 1
                            caps.capabilities.add('elements')
                        break

                # Check for labels
                for sig in CONTENT_SIGNATURES['labels']:
                    if sig in tag:
                        if 'label' in tag.lower() and 'Arc' not in tag:
                            # It's a label element (not labelArc)
                            if elem.text and elem.text.strip():
                                label_count += 1
                        caps.capabilities.add('labels')
                        break

                # Check other content types
                for cap_type, signatures in CONTENT_SIGNATURES.items():
                    if cap_type in ('elements', 'labels'):
                        continue  # Already handled
                    for sig in signatures:
                        if sig in tag:
                            caps.capabilities.add(cap_type)
                            break

            caps.element_count = element_count
            caps.label_count = label_count

        except ET.ParseError as e:
            caps.error = f'XML parse error: {e}'
            logger.debug(f"Parse error in {file_path.name}: {e}")
        except Exception as e:
            caps.error = f'Analysis error: {e}'
            logger.debug(f"Analysis error in {file_path.name}: {e}")

        # Cache result
        self._cache[cache_key] = caps

        return caps

    def analyze_directory(
        self,
        directory_path: Path,
        recursive: bool = True
    ) -> DirectoryAnalysis:
        """
        Analyze all XML/XSD files in a directory.

        Args:
            directory_path: Path to taxonomy directory
            recursive: Whether to search subdirectories

        Returns:
            DirectoryAnalysis with results for all files
        """
        analysis = DirectoryAnalysis(directory_path=directory_path)

        if not directory_path.exists():
            logger.warning(f"Directory does not exist: {directory_path}")
            return analysis

        # Find all analyzable files
        if recursive:
            files = list(directory_path.rglob('*'))
        else:
            files = list(directory_path.glob('*'))

        # Filter to analyzable extensions
        files = [
            f for f in files
            if f.is_file() and f.suffix.lower() in ANALYZABLE_EXTENSIONS
        ]

        logger.debug(f"Analyzing {len(files)} files in {directory_path}")

        # Analyze each file
        for file_path in files:
            caps = self.analyze_file(file_path)
            analysis.files[str(file_path)] = caps
            analysis.total_files += 1
            analysis.total_labels += caps.label_count
            analysis.total_elements += caps.element_count

            if caps.error:
                analysis.errors.append((file_path, caps.error))

        logger.info(
            f"Analyzed {analysis.total_files} files: "
            f"{analysis.total_elements} elements, {analysis.total_labels} labels"
        )

        return analysis

    def find_label_sources(self, directory_path: Path) -> list[Path]:
        """
        Find all files containing labels in a taxonomy.

        This is the main method for the taxonomy reader to use.
        It finds labels whether they're in:
        - Separate label linkbase files (us-gaap style)
        - Embedded in schema files (ecd/dei style)
        - Any other format

        Args:
            directory_path: Path to taxonomy directory

        Returns:
            List of file paths containing label content
        """
        analysis = self.analyze_directory(directory_path)
        label_files = analysis.get_files_with_capability('labels')

        # Sort by label count (files with most labels first)
        label_files.sort(
            key=lambda p: analysis.files[str(p)].label_count,
            reverse=True
        )

        logger.info(
            f"Found {len(label_files)} label sources in {directory_path.name}"
        )

        return label_files

    def clear_cache(self) -> None:
        """Clear the analysis cache."""
        self._cache.clear()


__all__ = [
    'TaxonomyFileAnalyzer',
    'FileCapabilities',
    'DirectoryAnalysis',
    'CONTENT_SIGNATURES',
]
