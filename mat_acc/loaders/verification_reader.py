# Path: mat_acc/loaders/verification_reader.py
"""
Verification Reader for mat_acc

Reads and interprets verification report contents.
Works with paths provided by VerificationDataLoader (the blind reader).

Separation of concerns:
- verification_data.py: DISCOVERS paths (blind, recursive, agnostic)
- verification_reader.py: READS and INTERPRETS contents

This module understands the verification report JSON structure.
"""

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from config_loader import ConfigLoader
from loaders.verification_data import VerifiedFilingEntry


@dataclass
class VerificationCheck:
    """
    Represents a single verification check result.

    Attributes:
        check_name: Name of the check (e.g., 'calculation_consistency')
        check_type: Type of check (e.g., 'horizontal', 'vertical')
        passed: Whether the check passed
        severity: Severity level (info, warning, critical)
        message: Human-readable message
        concept: XBRL concept being checked
        context_id: Context identifier
        expected_value: Expected calculated value
        actual_value: Actual reported value
        difference: Difference between expected and actual
        details: Additional check details
    """
    check_name: str
    check_type: str
    passed: bool
    severity: str
    message: str
    concept: Optional[str] = None
    context_id: Optional[str] = None
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    difference: Optional[float] = None
    details: Optional[dict] = None


@dataclass
class VerificationSummary:
    """
    Summary of verification results.

    Attributes:
        score: Overall verification score (0-100)
        total_checks: Total number of checks performed
        passed: Number of checks that passed
        failed: Number of checks that failed
        skipped: Number of checks that were skipped
        critical_issues: Number of critical issues
        warning_issues: Number of warning issues
        info_issues: Number of informational issues
    """
    score: float
    total_checks: int
    passed: int
    failed: int
    skipped: int
    critical_issues: int = 0
    warning_issues: int = 0
    info_issues: int = 0


@dataclass
class VerificationReport:
    """
    Complete verification report for a filing.

    Attributes:
        filing_id: Unique filing identifier
        market: Market identifier
        company: Company name
        form: Form type
        date: Filing date
        verified_at: Timestamp of verification
        processing_time_ms: Time taken to verify (milliseconds)
        summary: VerificationSummary object
        checks: List of VerificationCheck objects
        raw_data: Original JSON data (optional)
    """
    filing_id: str
    market: str
    company: str
    form: str
    date: str
    verified_at: str
    processing_time_ms: float
    summary: VerificationSummary
    checks: list[VerificationCheck] = field(default_factory=list)
    raw_data: Optional[dict] = None


class VerificationReader:
    """
    Reader for verification report contents.

    Loads and parses verification_report.json files.
    Provides structured access to verification results.

    Example:
        reader = VerificationReader()

        # Load report from entry
        report = reader.load_report(filing_entry)

        # Check if filing passed verification
        if reader.is_verified(report, min_score=95.0):
            print(f"Filing verified with score: {report.summary.score}")
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize verification reader.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.logger = logging.getLogger('input.verification_reader')
        self.min_verification_score = self.config.get('min_verification_score', 95.0)

    def load_report(
        self,
        entry: VerifiedFilingEntry,
        include_raw: bool = False
    ) -> Optional[VerificationReport]:
        """
        Load verification report from filing entry.

        Args:
            entry: VerifiedFilingEntry with path information
            include_raw: Whether to include raw JSON in result

        Returns:
            VerificationReport or None if failed to load
        """
        return self.load_report_from_path(entry.report_path, include_raw)

    def load_report_from_path(
        self,
        report_path: Path,
        include_raw: bool = False
    ) -> Optional[VerificationReport]:
        """
        Load verification report from file path.

        Args:
            report_path: Path to verification_report.json
            include_raw: Whether to include raw JSON in result

        Returns:
            VerificationReport or None if failed to load
        """
        if not report_path.exists():
            self.logger.error(f"Report file not found: {report_path}")
            return None

        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return self._parse_report(data, include_raw)

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {report_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load report from {report_path}: {e}")
            return None

    def _parse_report(
        self,
        data: dict,
        include_raw: bool = False
    ) -> VerificationReport:
        """
        Parse verification report from JSON data.

        Args:
            data: Parsed JSON dictionary
            include_raw: Whether to include raw data

        Returns:
            VerificationReport object
        """
        # Parse summary
        summary_data = data.get('summary', {})
        summary = VerificationSummary(
            score=summary_data.get('score', 0.0),
            total_checks=summary_data.get('total_checks', 0),
            passed=summary_data.get('passed', 0),
            failed=summary_data.get('failed', 0),
            skipped=summary_data.get('skipped', 0),
            critical_issues=summary_data.get('critical_issues', 0),
            warning_issues=summary_data.get('warning_issues', 0),
            info_issues=summary_data.get('info_issues', 0),
        )

        # Parse checks
        checks = []
        for check_data in data.get('checks', []):
            check = VerificationCheck(
                check_name=check_data.get('check_name', ''),
                check_type=check_data.get('check_type', ''),
                passed=check_data.get('passed', False),
                severity=check_data.get('severity', 'info'),
                message=check_data.get('message', ''),
                concept=check_data.get('concept'),
                context_id=check_data.get('context_id'),
                expected_value=check_data.get('expected_value'),
                actual_value=check_data.get('actual_value'),
                difference=check_data.get('difference'),
                details=check_data.get('details'),
            )
            checks.append(check)

        return VerificationReport(
            filing_id=data.get('filing_id', ''),
            market=data.get('market', ''),
            company=data.get('company', ''),
            form=data.get('form', ''),
            date=data.get('date', ''),
            verified_at=data.get('verified_at', ''),
            processing_time_ms=data.get('processing_time_ms', 0.0),
            summary=summary,
            checks=checks,
            raw_data=data if include_raw else None,
        )

    def is_verified(
        self,
        report: VerificationReport,
        min_score: Optional[float] = None
    ) -> bool:
        """
        Check if filing meets verification threshold.

        Args:
            report: VerificationReport to check
            min_score: Minimum score (default from config)

        Returns:
            True if filing meets threshold
        """
        threshold = min_score if min_score is not None else self.min_verification_score
        return report.summary.score >= threshold

    def get_passed_checks(self, report: VerificationReport) -> list[VerificationCheck]:
        """
        Get all checks that passed.

        Args:
            report: VerificationReport

        Returns:
            List of passed VerificationCheck objects
        """
        return [c for c in report.checks if c.passed]

    def get_failed_checks(self, report: VerificationReport) -> list[VerificationCheck]:
        """
        Get all checks that failed.

        Args:
            report: VerificationReport

        Returns:
            List of failed VerificationCheck objects
        """
        return [c for c in report.checks if not c.passed]

    def get_checks_by_severity(
        self,
        report: VerificationReport,
        severity: str
    ) -> list[VerificationCheck]:
        """
        Get checks by severity level.

        Args:
            report: VerificationReport
            severity: Severity level ('info', 'warning', 'critical')

        Returns:
            List of VerificationCheck objects with given severity
        """
        return [c for c in report.checks if c.severity == severity]

    def get_verified_concepts(self, report: VerificationReport) -> list[str]:
        """
        Get list of concepts that were verified (passed checks).

        Args:
            report: VerificationReport

        Returns:
            List of verified concept names
        """
        return [
            c.concept for c in report.checks
            if c.passed and c.concept
        ]

    def get_check_for_concept(
        self,
        report: VerificationReport,
        concept: str
    ) -> Optional[VerificationCheck]:
        """
        Get verification check for a specific concept.

        Args:
            report: VerificationReport
            concept: Concept name to find

        Returns:
            VerificationCheck or None if not found
        """
        for check in report.checks:
            if check.concept == concept:
                return check
        return None


__all__ = [
    'VerificationCheck',
    'VerificationSummary',
    'VerificationReport',
    'VerificationReader',
]
