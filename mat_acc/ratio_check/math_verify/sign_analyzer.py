# Path: mat_acc/ratio_check/math_verify/sign_analyzer.py
"""
Sign Analyzer - Validates numeric signs against mathematical logic.

After iXBRL extraction provides mathematically correct values,
this module validates signs using UNIVERSAL mathematical rules:

1. Total assets must be positive (no company has negative assets)
2. Shares outstanding must be positive
3. Revenue/cost concepts must be positive (absolute amounts)
4. Income/loss concepts can be positive or negative

Uses keyword-based pattern matching on local concept names to
remain taxonomy-agnostic (works with US-GAAP, IFRS, UK-GAAP, etc.)

This is a VALIDATION layer, not a correction layer.
"""

import re
from dataclasses import dataclass
from typing import Optional

from core.logger.ipo_logging import get_process_logger

from .ixbrl_extractor import VerifiedFact


logger = get_process_logger('math_verify.sign')


@dataclass
class SignCheck:
    """Result of sign validation for a single fact."""
    concept: str
    value: float
    expected_sign: str = ''
    actual_sign: str = ''
    consistent: bool = True
    note: str = ''


# Keywords for concepts that MUST be positive (mathematical certainty)
# These are universal across all taxonomies and markets
_MUST_POSITIVE_PATTERNS = [
    re.compile(r'^Assets$', re.IGNORECASE),
    re.compile(r'^AssetsCurrent$', re.IGNORECASE),
    re.compile(r'^AssetsNoncurrent$', re.IGNORECASE),
    re.compile(r'^Liabilities$', re.IGNORECASE),
    re.compile(r'^LiabilitiesCurrent$', re.IGNORECASE),
    re.compile(r'Shares.*Outstanding', re.IGNORECASE),
    re.compile(r'NumberOf.*Shares', re.IGNORECASE),
]

# Keywords for concepts that are TYPICALLY positive (absolute amounts)
# Negative would be unusual but not mathematically impossible
_TYPICALLY_POSITIVE_PATTERNS = [
    re.compile(r'^Revenue', re.IGNORECASE),
    re.compile(r'^Turnover', re.IGNORECASE),
    re.compile(r'CostOf(Goods|Revenue)', re.IGNORECASE),
    re.compile(r'^Inventory', re.IGNORECASE),
    re.compile(r'^Cash(AndCash)?Equiv', re.IGNORECASE),
    re.compile(r'^AccountsReceivable', re.IGNORECASE),
    re.compile(r'^AccountsPayable', re.IGNORECASE),
    re.compile(r'Depreciation', re.IGNORECASE),
    re.compile(r'Amortisation|Amortization', re.IGNORECASE),
    re.compile(r'InterestExpense', re.IGNORECASE),
    re.compile(r'PropertyPlantAndEquipment', re.IGNORECASE),
]

# Keywords for concepts that CAN be negative (profit/loss items)
# Negative = loss, positive = profit. Both are mathematically valid.
_BIDIRECTIONAL_PATTERNS = [
    re.compile(r'(Profit|Loss|Income)', re.IGNORECASE),
    re.compile(r'Earnings', re.IGNORECASE),
    re.compile(r'Comprehensive', re.IGNORECASE),
    re.compile(r'RetainedEarnings|AccumulatedDeficit', re.IGNORECASE),
    re.compile(r'Equity|NetAssets', re.IGNORECASE),
    re.compile(r'OtherComprehensive', re.IGNORECASE),
    re.compile(r'GainLoss|GainOrLoss', re.IGNORECASE),
]


class SignAnalyzer:
    """
    Validates numeric signs using universal mathematical rules.
    Taxonomy-agnostic: works on local concept names with patterns.
    """

    def __init__(self):
        """Initialize sign analyzer."""
        self.logger = get_process_logger('math_verify.sign')

    def analyze(self, facts: list[VerifiedFact]) -> list[SignCheck]:
        """Analyze sign consistency for verified facts."""
        checks = []
        anomalies = 0

        for fact in facts:
            check = self._check_single(fact)
            if check:
                checks.append(check)
                if not check.consistent:
                    anomalies += 1

        if anomalies > 0:
            self.logger.warning(
                f"Sign analysis: {anomalies} anomalies out of {len(checks)}"
            )
        else:
            self.logger.info(f"Sign analysis: {len(checks)} facts consistent")

        return checks

    def summarize(self, checks: list[SignCheck]) -> dict:
        """Produce summary statistics from sign checks."""
        total = len(checks)
        consistent = sum(1 for c in checks if c.consistent)
        anomalies = [c for c in checks if not c.consistent]

        return {
            'total_checked': total,
            'consistent': consistent,
            'anomalies': len(anomalies),
            'anomaly_concepts': [
                (a.concept, a.value, a.note) for a in anomalies
            ],
        }

    def _check_single(self, fact: VerifiedFact) -> Optional[SignCheck]:
        """Check sign consistency for a single fact."""
        local_name = self._local_name(fact.concept)
        if not local_name:
            return None

        check = SignCheck(
            concept=fact.concept,
            value=fact.value,
            actual_sign='positive' if fact.value >= 0 else 'negative',
        )

        # Must be positive (mathematical certainty)
        if self._matches_any(local_name, _MUST_POSITIVE_PATTERNS):
            check.expected_sign = 'must be positive'
            check.consistent = fact.value >= 0
            if not check.consistent:
                check.note = f'{local_name}: negative total is anomalous'
            return check

        # Bidirectional (can be positive or negative)
        if self._matches_any(local_name, _BIDIRECTIONAL_PATTERNS):
            check.expected_sign = 'positive or negative'
            check.consistent = True
            if fact.value < 0:
                check.note = 'loss/deficit (valid)'
            return check

        # Typically positive
        if self._matches_any(local_name, _TYPICALLY_POSITIVE_PATTERNS):
            check.expected_sign = 'typically positive'
            check.consistent = fact.value >= 0
            if not check.consistent:
                check.note = f'{local_name}: unexpected negative'
            return check

        # Unclassified: no opinion
        return None

    def _matches_any(self, name: str, patterns: list) -> bool:
        """Check if name matches any pattern in the list."""
        return any(p.search(name) for p in patterns)

    def _local_name(self, concept: str) -> str:
        """Extract local name from QName."""
        return concept.split(':')[-1] if ':' in concept else concept


__all__ = ['SignAnalyzer', 'SignCheck']
