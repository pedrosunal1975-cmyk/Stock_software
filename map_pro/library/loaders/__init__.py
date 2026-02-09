# Path: library/loaders/__init__.py
"""
Library Loaders Module

Blind mole pattern for file discovery and content reading.

Discovery (Doorkeepers):
- ParsedLoader: Finds parsed.json files at any depth
- TaxonomyLoader: Finds taxonomy directories

Content Readers:
- ParsedReader: Reads parsed.json and extracts namespaces
- TaxonomyReader: Verifies physical taxonomy existence
"""

from library.loaders.parsed_loader import ParsedLoader, ParsedFileLocation
from library.loaders.taxonomy_loader import TaxonomyLoader, TaxonomyLocation
from library.loaders.parsed_reader import ParsedReader, ParsedFilingInfo
from library.loaders.taxonomy_reader import TaxonomyReader, TaxonomyVerification

__all__ = [
    'ParsedLoader',
    'ParsedFileLocation',
    'TaxonomyLoader',
    'TaxonomyLocation',
    'ParsedReader',
    'ParsedFilingInfo',
    'TaxonomyReader',
    'TaxonomyVerification',
]