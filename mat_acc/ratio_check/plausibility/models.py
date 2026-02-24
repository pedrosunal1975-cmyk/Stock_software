# Path: mat_acc/ratio_check/plausibility/models.py
"""
Plausibility Data Models

Findings, severity levels, and expectation source types.
Every finding records whether its expectation comes from a
normative rule (hardcoded) or a declared value (from filing).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(Enum):
    """Finding severity - how anomalous the value is."""
    INFO = 'info'           # Noteworthy but consistent
    ADVISORY = 'advisory'   # Worth reviewing
    WARNING = 'warning'     # Likely problematic
    ALERT = 'alert'         # Almost certainly wrong


class ExpectationSource(Enum):
    """Where the expectation comes from."""
    NORMATIVE = 'normative'   # Hardcoded accounting/math rules
    DECLARED = 'declared'     # Company's own filing data


@dataclass
class Finding:
    """
    A single plausibility observation.

    Attributes:
        severity: How anomalous this is
        category: Check category (proportion, range, scale, coherence)
        target: Which component or ratio this finding relates to
        message: Human-readable explanation
        actual_value: The value that was observed
        expectation_source: NORMATIVE or DECLARED
        expectation_basis: What the expectation is based on
        expected_range: (min, max) tuple if applicable
        declared_value: The company-declared value if source=DECLARED
    """
    severity: Severity
    category: str
    target: str
    message: str
    actual_value: Optional[float] = None
    expectation_source: ExpectationSource = ExpectationSource.NORMATIVE
    expectation_basis: str = ''
    expected_range: Optional[tuple] = None
    declared_value: Optional[float] = None

    @property
    def severity_tag(self) -> str:
        """Short display tag for terminal output."""
        tags = {
            Severity.INFO: '[i]',
            Severity.ADVISORY: '[?]',
            Severity.WARNING: '[!]',
            Severity.ALERT: '[!!]',
        }
        return tags[self.severity]

    @property
    def source_tag(self) -> str:
        """Short display tag for expectation source."""
        if self.expectation_source == ExpectationSource.DECLARED:
            return 'declared'
        return 'normative'


@dataclass
class PlausibilityReport:
    """
    Complete plausibility audit result.

    Attributes:
        findings: All individual findings
        company: Company name for context
        market: Market identifier
    """
    findings: List[Finding] = field(default_factory=list)
    company: str = ''
    market: str = ''

    @property
    def warnings(self) -> List[Finding]:
        """Findings at WARNING or ALERT severity."""
        return [
            f for f in self.findings
            if f.severity in (Severity.WARNING, Severity.ALERT)
        ]

    @property
    def advisories(self) -> List[Finding]:
        """Findings at ADVISORY severity."""
        return [
            f for f in self.findings
            if f.severity == Severity.ADVISORY
        ]

    @property
    def infos(self) -> List[Finding]:
        """Findings at INFO severity."""
        return [
            f for f in self.findings
            if f.severity == Severity.INFO
        ]

    def for_target(self, target: str) -> List[Finding]:
        """Get all findings for a specific component or ratio."""
        return [f for f in self.findings if f.target == target]

    @property
    def summary_counts(self) -> Dict[str, int]:
        """Count findings by severity."""
        counts: Dict[str, int] = {}
        for f in self.findings:
            key = f.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts


__all__ = [
    'Severity', 'ExpectationSource', 'Finding', 'PlausibilityReport',
]
