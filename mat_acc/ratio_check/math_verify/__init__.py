# Path: mat_acc/ratio_check/math_verify/__init__.py
"""
Mathematical Integrity Unit (MIU)

Ensures numeric correctness BEFORE ratio calculations begin.
Reads iXBRL source files directly to extract mathematically
correct values, cross-validates against parsed data, and
verifies accounting identities.

Modules:
    ixbrl_extractor.py    - Layer 1: Extract numeric truth from iXBRL
    context_filter.py     - Context parsing: primary vs dimensional
    fact_reconciler.py    - Layer 2: Cross-source reconciliation
    sign_analyzer.py      - Sign validation: mathematical consistency
    identity_validator.py - Layer 3: Mathematical identity validation
"""

from .ixbrl_extractor import IXBRLExtractor, VerifiedFact
from .context_filter import ContextFilter, ContextInfo
from .fact_reconciler import FactReconciler, ReconciliationResult
from .sign_analyzer import SignAnalyzer, SignCheck
from .identity_validator import IdentityValidator, IdentityCheck


__all__ = [
    # Layer 1: Extraction
    'IXBRLExtractor',
    'VerifiedFact',
    # Context filtering
    'ContextFilter',
    'ContextInfo',
    # Layer 2: Reconciliation
    'FactReconciler',
    'ReconciliationResult',
    # Sign validation
    'SignAnalyzer',
    'SignCheck',
    # Layer 3: Identity validation
    'IdentityValidator',
    'IdentityCheck',
]
