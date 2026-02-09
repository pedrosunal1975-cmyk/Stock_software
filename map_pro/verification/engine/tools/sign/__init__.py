# Path: verification/engine/checks_v2/tools/sign/__init__.py
"""
Sign Tools for XBRL Verification

Provides sign correction parsing and lookup across all processing stages.

Key Components:
- SignParser: Parse sign="-" attributes from iXBRL documents
- SignLookup: Multi-strategy sign correction lookup
- SignInfo: Data class holding sign correction information
- SemanticSignInferrer: Infer sign from concept name semantics

XBRL Sign Handling:
In iXBRL, negative values are often displayed as positive text with a
sign="-" attribute. This module parses these attributes and provides
lookup mechanisms to apply sign corrections during verification.

Sign Correction Lookup Strategies:
1. Exact match: (concept, context_id)
2. Normalized concept match: (normalized_concept, context_id)
3. Period-based fallback: Same concept + period, different dimensional hash
4. Semantic inference: Infer from concept name (Payments -> negative)
"""

from .sign_info import SignInfo, SignSource
from .sign_parser import SignParser
from .sign_lookup import SignLookup
from .semantic_inferrer import SemanticSignInferrer

__all__ = [
    'SignInfo',
    'SignSource',
    'SignParser',
    'SignLookup',
    'SemanticSignInferrer',
]
