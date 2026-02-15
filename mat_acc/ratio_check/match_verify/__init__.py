# Path: mat_acc/ratio_check/match_verify/__init__.py
"""
Match Verify Package

Post-Match Financial Verification (PMFV) layer.
Validates matched components using financial intelligence:
- Qualifier rules: semantic name qualifiers
- Plausibility checks: cross-component value relationships
- Alternative promotion: try next-best candidate when match fails
"""

from .match_verifier import MatchVerifier
from .qualifier_rules import check_qualifier
from .plausibility_checks import check_plausibility


__all__ = [
    'MatchVerifier',
    'check_qualifier',
    'check_plausibility',
]
