# Path: mat_acc/ratio_check/math_verify/__init__.py
"""
Mathematical Integrity Unit (MIU)

Ensures numeric correctness BEFORE ratio calculations begin.
Reads iXBRL source files directly to extract mathematically
correct values, cross-validates against parsed data, and
verifies accounting identities.

Three layers:
    ixbrl_extractor.py    - Layer 1: Extract numeric truth from iXBRL
    fact_reconciler.py    - Layer 2: Cross-source reconciliation
    identity_validator.py - Layer 3: Mathematical identity validation
"""

from .ixbrl_extractor import IXBRLExtractor, VerifiedFact
from .fact_reconciler import FactReconciler, ReconciliationResult
from .identity_validator import IdentityValidator, IdentityCheck


__all__ = [
    'IXBRLExtractor',
    'VerifiedFact',
    'FactReconciler',
    'ReconciliationResult',
    'IdentityValidator',
    'IdentityCheck',
]
