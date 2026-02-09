# Path: verification/engine/checks_v2/tools/naming/__init__.py
"""
Naming Tools for XBRL Verification

Provides concept name normalization and extraction across all processing stages.

Key Components:
- Normalizer: Multi-strategy concept name normalizer
- LocalNameExtractor: Extract local name from qualified names
- normalize_name: Quick function for canonical normalization
- extract_local_name: Quick function for local name extraction

XBRL concept names appear in many formats:
- us-gaap:Assets (colon separator - calculation linkbase)
- us-gaap_Assets (underscore separator - presentation)
- {http://fasb.org/us-gaap/2024}Assets (Clark notation)
- v_CustomConcept (company extension)

These tools provide consistent normalization for comparison while
preserving original names for output.
"""

from .normalizer import Normalizer, normalize_name
from .local_name_extractor import LocalNameExtractor, extract_local_name

__all__ = [
    'Normalizer',
    'LocalNameExtractor',
    'normalize_name',
    'extract_local_name',
]
