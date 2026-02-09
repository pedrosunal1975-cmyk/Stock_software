# Path: verification/engine/checks_v2/constants/naming.py
"""
Naming Constants for XBRL Concept Normalization

Constants for handling concept name variations across different XBRL sources.

XBRL concept names appear with different separators:
- Calculation linkbase: us-gaap:Assets (colon)
- Presentation/mapped: us-gaap_Assets (underscore)
- Some sources: us-gaap-Assets (dash)
- Clark notation: {http://fasb.org/us-gaap/2024}Assets

These constants enable consistent normalization for comparison while
preserving original names in results.
"""

# ==============================================================================
# CONCEPT NAME SEPARATORS
# ==============================================================================
# Separators used in different XBRL sources.
# These can be interchanged when matching concept names.

CONCEPT_SEPARATORS = [
    ':',   # Colon - used in calculation linkbase (us-gaap:Assets)
    '_',   # Underscore - used in presentation/mapped (us-gaap_Assets)
    '-',   # Dash - sometimes used (us-gaap-Assets)
    ' ',   # Space - rare but possible
]

# The canonical separator used for internal normalization
# This is used only during comparison, original names are preserved
CANONICAL_SEPARATOR = '_'


# ==============================================================================
# TAXONOMY PREFIX PATTERNS
# ==============================================================================
# Known taxonomy namespace prefixes (standard namespaces).
# Used to identify and strip namespace prefixes from concept names.

KNOWN_TAXONOMY_PREFIXES = {
    # US GAAP taxonomies
    'us-gaap',
    'usgaap',
    # International standards
    'ifrs-full',
    'ifrs',
    # SEC-specific
    'dei',           # Document and Entity Information
    'srt',           # SEC Reporting Taxonomy
    'ecd',           # Executive Compensation Disclosure
    # Reference taxonomies
    'country',       # Country codes
    'currency',      # Currency codes
    'exch',          # Exchange codes
    'naics',         # Industry classification
    'sic',           # Standard Industrial Classification
    'stpr',          # State/Province codes
    'invest',        # Investment taxonomy
    # Generic
    'custom',        # Custom extensions
}


# ==============================================================================
# COMPANY EXTENSION PATTERNS
# ==============================================================================
# Company extension prefixes are typically short (1-6 characters).
# Examples: 'v', 'aapl', 'msft', 'plug', 'goog'
#
# These prefixes indicate company-specific concepts not in standard taxonomies.
# They follow the pattern: prefix_ConceptName (e.g., plug_CustomRevenue)

MAX_EXTENSION_PREFIX_LENGTH = 6


# ==============================================================================
# NAME EQUIVALENT CHARACTERS
# ==============================================================================
# Characters that are considered equivalent in name comparisons.
# Format: (char1, char2) pairs that can be interchanged.

NAME_EQUIVALENT_CHARS = [
    ('-', '_'),   # Hyphen and underscore
    (' ', '_'),   # Space and underscore
    (' ', '-'),   # Space and hyphen
]


# ==============================================================================
# CLARK NOTATION DETECTION
# ==============================================================================
# Clark notation format: {namespace}LocalName
# Example: {http://fasb.org/us-gaap/2024}Assets

CLARK_NOTATION_START = '{'
CLARK_NOTATION_END = '}'


__all__ = [
    # Separators
    'CONCEPT_SEPARATORS',
    'CANONICAL_SEPARATOR',
    # Taxonomy prefixes
    'KNOWN_TAXONOMY_PREFIXES',
    # Extension patterns
    'MAX_EXTENSION_PREFIX_LENGTH',
    # Equivalent characters
    'NAME_EQUIVALENT_CHARS',
    # Clark notation
    'CLARK_NOTATION_START',
    'CLARK_NOTATION_END',
]
