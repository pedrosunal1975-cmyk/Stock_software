# Path: xbrl_parser/foundation/url_addresses.py
"""
URL Address Configuration

Central repository for all taxonomy registry URLs and namespace patterns.

NO HARDCODED URLs should exist elsewhere - all references should import from here.
This file contains NO executable code, only data structures.
"""

# ==============================================================================
# SEC EDGAR REGISTRY
# ==============================================================================

SEC_BASE_URLS = [
    "https://xbrl.sec.gov/",
    "https://www.sec.gov/Archives/edgar/",
]

SEC_NAMESPACE_PATTERNS = [
    "http://xbrl.sec.gov/",
    "http://fasb.org/us-gaap/",
    "http://xbrl.us/dei/",
]

SEC_MIRROR_URLS = [
    "https://xbrl.fasb.org/",
]

# ==============================================================================
# ESMA ESEF REGISTRY
# ==============================================================================

ESMA_BASE_URLS = [
    "https://www.esma.europa.eu/",
    "https://esef.efrag.org/",
]

ESMA_NAMESPACE_PATTERNS = [
    "http://www.esma.europa.eu/taxonomy/",
    "http://xbrl.ifrs.org/taxonomy/",
]

# ==============================================================================
# UK FRC REGISTRY
# ==============================================================================

FRC_BASE_URLS = [
    "https://xbrl.frc.org.uk/",
    "https://www.frc.org.uk/",
]

FRC_NAMESPACE_PATTERNS = [
    "http://xbrl.frc.org.uk/",
    "http://www.xbrl.org.uk/",
]

# ==============================================================================
# IFRS FOUNDATION REGISTRY
# ==============================================================================

IFRS_BASE_URLS = [
    "https://www.ifrs.org/",
    "https://xbrl.ifrs.org/",
]

IFRS_NAMESPACE_PATTERNS = [
    "http://xbrl.ifrs.org/",
    "http://xbrl.iasb.org/",
]

# ==============================================================================
# REGISTRY METADATA
# ==============================================================================

REGISTRY_METADATA = {
    'IFRS': {
        'name': "IFRS Foundation",
        'region': "INTERNATIONAL",
        'authority': "IFRS_FOUNDATION",
        'base_urls': IFRS_BASE_URLS,
        'namespace_patterns': IFRS_NAMESPACE_PATTERNS,
        'mirror_urls': None
    },
    'SEC': {
        'name': "SEC EDGAR",
        'region': "US",
        'authority': "SEC",
        'base_urls': SEC_BASE_URLS,
        'namespace_patterns': SEC_NAMESPACE_PATTERNS,
        'mirror_urls': SEC_MIRROR_URLS
    },
    'ESMA': {
        'name': "ESMA ESEF",
        'region': "EU",
        'authority': "ESMA",
        'base_urls': ESMA_BASE_URLS,
        'namespace_patterns': ESMA_NAMESPACE_PATTERNS,
        'mirror_urls': None
    },
    'FRC': {
        'name': "UK FRC",
        'region': "UK",
        'authority': "FRC",
        'base_urls': FRC_BASE_URLS,
        'namespace_patterns': FRC_NAMESPACE_PATTERNS,
        'mirror_urls': None
    }
}

# ==============================================================================
# TAXONOMY DETECTION PATTERNS
# ==============================================================================
# These patterns are used by taxonomy_detector.py to identify which
# taxonomy is being used based on namespace URIs in the filing.
# Patterns are partial matches against full namespace URIs.

TAXONOMY_DETECTION_PATTERNS = {
    'US_GAAP': [
        'fasb.org/us-gaap',
        'xbrl.sec.gov/us-gaap'
    ],
    'IFRS': [
        'xbrl.ifrs.org',
        'xbrl.iasb.org'
    ],
    'UK_GAAP': [
        'xbrl.frc.org.uk',
        'xbrl.org.uk'
    ],
    'ESEF': [
        'esma.europa.eu',
        'esef.efrag.org'
    ],
    'DEI': [
        'xbrl.sec.gov/dei',
        'xbrl.us/dei'
    ]
}

# ==============================================================================
# MARKET METADATA MAPPING
# ==============================================================================
# Maps taxonomy types to their market metadata (market, authority, framework)

MARKET_METADATA_MAP = {
    'US_GAAP': ("US", "SEC", "US-GAAP"),
    'UK_GAAP': ("UK", "FRC", "UK-GAAP"),
    'ESEF': ("EU", "ESMA", "ESEF"),
    'IFRS': ("INTERNATIONAL", "IFRS_FOUNDATION", "IFRS"),
}

__all__ = [
    'SEC_BASE_URLS',
    'SEC_NAMESPACE_PATTERNS',
    'SEC_MIRROR_URLS',
    'ESMA_BASE_URLS',
    'ESMA_NAMESPACE_PATTERNS',
    'FRC_BASE_URLS',
    'FRC_NAMESPACE_PATTERNS',
    'IFRS_BASE_URLS',
    'IFRS_NAMESPACE_PATTERNS',
    'REGISTRY_METADATA',
    'TAXONOMY_DETECTION_PATTERNS',
    'MARKET_METADATA_MAP'
]