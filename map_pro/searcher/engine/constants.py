# Path: searcher/engine/constants.py
"""
Taxonomy Recognition Constants

Pattern-based taxonomy recognition configuration.
100% AGNOSTIC - no hardcoded taxonomy names.

Architecture:
- Regex patterns for namespace matching
- URL templates for download generation
- Alternative URL patterns for retry logic
- All patterns are configurable, not hardcoded
"""

import re

# ================================================================
# NAMESPACE PATTERN CONFIGURATIONS
# ================================================================

# IMPORTANT: These patterns are ONLY for TAXONOMY LIBRARY recognition and downloads
# Company XBRL filing downloads use SECURLBuilder (separate code path)
# 
# These patterns:
# 1. Match taxonomy namespaces found in parsed XBRL files
# 2. Generate download URLs for standard taxonomy libraries (US-GAAP, DEI, etc.)
# 
# They DO NOT affect company filing search or downloads which use SEC EDGAR API

# Generic namespace patterns that work for ANY taxonomy
# Pattern groups: (authority_domain, taxonomy_name, version)
NAMESPACE_PATTERNS = [
    # Pattern 1: xbrl.sec.gov style - http://xbrl.sec.gov/{taxonomy}/{version}
    # MUST come FIRST to match before generic pattern
    {
        'pattern': r'https?://xbrl\.([^/]+)/([^/]+)/(\d{4})',
        'authority_group': 1,
        'taxonomy_group': 2,
        'version_group': 3,
        'url_template': 'https://xbrl.{authority}/{taxonomy}/{version}/{taxonomy}-{version}.zip',
    },
    
    # Pattern 2: fasb.org style - http://fasb.org/{taxonomy}/{version}
    {
        'pattern': r'https?://(?:www\.)?([^/]+)/([^/]+)/(\d{4})',
        'authority_group': 1,
        'taxonomy_group': 2,
        'version_group': 3,
        'url_template': 'https://xbrl.{authority}/{taxonomy}/{version}/{taxonomy}-{version}.zip',
    },
    
    # Pattern 3: Generic versioned - http://{domain}/{taxonomy}/{version}
    {
        'pattern': r'https?://(?:www\.)?([^/]+)/(?:taxonomy/)?([^/]+)/(\d{4})',
        'authority_group': 1,
        'taxonomy_group': 2,
        'version_group': 3,
        'url_template': 'https://{authority}/{taxonomy}/{version}.zip',
    },
    
    # Pattern 4: Nested paths - http://{domain}/path/{taxonomy}/{version}
    {
        'pattern': r'https?://(?:www\.)?([^/]+)/[^/]+/([^/]+)/(\d{4})',
        'authority_group': 1,
        'taxonomy_group': 2,
        'version_group': 3,
        'url_template': 'https://{authority}/taxonomies/{taxonomy}-{version}.zip',
    },
]

# ================================================================
# ALTERNATIVE URL TEMPLATES
# ================================================================

# Generic alternative URL patterns for ANY taxonomy
# Each template will be tried with extracted taxonomy info
ALTERNATIVE_URL_TEMPLATES = [
    # Common XBRL hosting patterns
    'https://xbrl.{authority}/{taxonomy}-{version}.zip',
    'https://xbrl.{authority}/{taxonomy}/{version}/{taxonomy}-{version}.zip',
    'https://www.xbrl.org/taxonomies/{taxonomy}/{version}.zip',
    'https://{authority}/taxonomy/{taxonomy}-{version}.zip',
    'https://{authority}/taxonomies/{taxonomy}/{version}/{taxonomy}-{version}.zip',
    'https://{authority}/info/edgar/edgartaxonomies/{taxonomy}-{version}.zip',
    'https://www.{authority}/content/dam/{authority}/standards/taxonomy/{version}.zip',
]

# ================================================================
# AUTHORITY DOMAIN MAPPINGS
# ================================================================

# Map authority domains to known variants (for alternative URL generation)
AUTHORITY_VARIANTS = {
    'fasb.org': ['fasb.org', 'xbrl.fasb.org'],
    'sec.gov': ['sec.gov', 'xbrl.sec.gov', 'www.sec.gov'],
    'ifrs.org': ['ifrs.org', 'www.ifrs.org', 'xbrl.ifrs.org'],
    'esma.europa.eu': ['esma.europa.eu', 'www.esma.europa.eu'],
}

# ================================================================
# MARKET TYPE INFERENCE
# ================================================================

# Infer market type from authority domain (generic patterns)
MARKET_TYPE_PATTERNS = [
    (r'sec\.gov', 'sec'),
    (r'fasb\.org', 'sec'),
    (r'ifrs\.org', 'ifrs'),
    (r'esma\.europa\.eu', 'esma'),
    (r'fca\.org\.uk', 'fca'),
]

# ================================================================
# HELPER FUNCTIONS
# ================================================================

def compile_patterns():
    """
    Compile regex patterns for performance.
    
    Returns:
        List of compiled pattern dictionaries
    """
    compiled = []
    for pattern_config in NAMESPACE_PATTERNS:
        compiled_config = pattern_config.copy()
        compiled_config['compiled'] = re.compile(pattern_config['pattern'], re.IGNORECASE)
        compiled.append(compiled_config)
    return compiled


def get_authority_variants(authority: str) -> list[str]:
    """
    Get authority domain variants for alternative URL generation.
    
    Args:
        authority: Authority domain
        
    Returns:
        List of authority variants
    """
    # Check exact match
    for key, variants in AUTHORITY_VARIANTS.items():
        if authority.lower() in key.lower() or key.lower() in authority.lower():
            return variants
    
    # Return original if no variants found
    return [authority]


def infer_market_type(authority: str) -> str:
    """
    Infer market type from authority domain.
    
    Args:
        authority: Authority domain
        
    Returns:
        Market type identifier
    """
    for pattern, market_type in MARKET_TYPE_PATTERNS:
        if re.search(pattern, authority, re.IGNORECASE):
            return market_type
    
    # Default to authority domain
    return authority.split('.')[0] if '.' in authority else authority


__all__ = [
    'NAMESPACE_PATTERNS',
    'ALTERNATIVE_URL_TEMPLATES',
    'AUTHORITY_VARIANTS',
    'MARKET_TYPE_PATTERNS',
    'compile_patterns',
    'get_authority_variants',
    'infer_market_type',
]