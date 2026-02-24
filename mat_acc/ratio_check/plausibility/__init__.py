# Path: mat_acc/ratio_check/plausibility/__init__.py
"""
Plausibility Engine

Interpretive layer that audits ratio analysis output for anomalies.
Does NOT modify existing calculations - only observes and annotates.

Two expectation sources:
  NORMATIVE - hardcoded accounting/mathematical necessities
  DECLARED  - from company's own filing (iXBRL facts)
"""

from .models import Finding, Severity, ExpectationSource, PlausibilityReport
from .auditor import PlausibilityAuditor

__all__ = [
    'Finding',
    'Severity',
    'ExpectationSource',
    'PlausibilityReport',
    'PlausibilityAuditor',
]
