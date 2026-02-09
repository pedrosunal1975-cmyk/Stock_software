# Path: verification/output/report_generator.py
"""
Report Generator for Verification Module

Creates verification report based on company XBRL calculation linkbase.
Single report format - taxonomy-based verification has been removed.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader
from ..engine.coordinator import VerificationResult
from ..engine.checks import CheckResult
from ..constants import LOG_OUTPUT, REPORT_FILE


class ReportGenerator:
    """
    Creates verification report JSON file.

    Generates comprehensive report including:
    - Filing information
    - Verification scores
    - Quality classification
    - Detailed check results (XBRL-based)
    - Issues summary
    - Recommendations

    Example:
        generator = ReportGenerator()
        path = generator.generate_report(verification_result)
        print(f"Report saved to: {path}")
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize report generator.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.output_dir = self.config.get('output_dir')
        self.logger = logging.getLogger('output.report_generator')

    def generate_report(
        self,
        result: VerificationResult,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate verification report JSON.

        Args:
            result: VerificationResult from coordinator
            output_path: Optional custom output path

        Returns:
            Path to generated report file
        """
        self.logger.info(f"{LOG_OUTPUT} Generating verification report for {result.filing_id}")

        # Determine output path
        if output_path is None:
            output_path = self._get_default_output_path(result)

        # Build report structure
        report = self._build_report(result)

        # Write report
        self._write_report(report, output_path)

        self.logger.info(f"{LOG_OUTPUT} Report saved to: {output_path}")

        return output_path

    def _get_default_output_dir(self, result: VerificationResult) -> Path:
        """Get default output directory for reports."""
        if not self.output_dir:
            raise ValueError("Output directory not configured")

        # Create directory structure: output_dir/market/company/form/date/
        report_dir = (
            self.output_dir /
            result.market /
            result.company /
            result.form /
            result.date
        )
        report_dir.mkdir(parents=True, exist_ok=True)

        return report_dir

    def _get_default_output_path(self, result: VerificationResult) -> Path:
        """Get default output path for report file."""
        report_dir = self._get_default_output_dir(result)
        return report_dir / REPORT_FILE

    def _build_report(self, result: VerificationResult) -> dict:
        """Build report dictionary from verification result."""
        report = {
            'report_type': 'xbrl_verification',
            'verification_source': 'company_xbrl_calculation_linkbase',
            'filing_info': {
                'filing_id': result.filing_id,
                'market': result.market,
                'company': result.company,
                'form': result.form,
                'date': result.date,
            },
            'verification_timestamp': result.verified_at.isoformat() if result.verified_at else None,
            'processing_time_seconds': result.processing_time_seconds,
        }

        # Add scores
        if result.scores:
            report['scores'] = {
                'horizontal_score': round(result.scores.horizontal_score, 2),
                'vertical_score': round(result.scores.vertical_score, 2),
                'library_score': round(result.scores.library_score, 2),
                'overall_score': round(result.scores.overall_score, 2),
            }

            report['check_counts'] = {
                'horizontal_checks': result.scores.horizontal_checks,
                'vertical_checks': result.scores.vertical_checks,
                'library_checks': result.scores.library_checks,
            }

        # Add quality classification
        if result.quality:
            report['quality'] = {
                'level': result.quality.level,
                'description': result.quality.description,
                'confidence': round(result.quality.confidence, 2),
            }

        # Add issues summary
        report['issues_summary'] = result.issues_summary

        # Add recommendation
        report['recommendation'] = result.recommendation

        # Add statement information
        if result.statement_info:
            report['statement_info'] = result.statement_info

        # Add formula registry summary (company XBRL trees only)
        if result.formula_registry_summary:
            report['formula_registry'] = {
                'company_calculation_trees': result.formula_registry_summary.get('company_trees', 0),
                'company_concepts': result.formula_registry_summary.get('company_concepts', 0),
            }

        # Add XBRL calculation results summary
        xbrl_results = result.xbrl_calculation_results
        if xbrl_results:
            passed = sum(1 for r in xbrl_results if r.passed)
            failed = sum(1 for r in xbrl_results if not r.passed)
            total = len(xbrl_results)

            report['xbrl_calculation_summary'] = {
                'total_checks': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': round(passed / total * 100, 2) if total > 0 else 0.0,
            }

        # Add detailed check results
        report['check_results'] = {
            'horizontal': self._serialize_check_results(result.horizontal_results),
            'vertical': self._serialize_check_results(result.vertical_results),
            'library': self._serialize_check_results(result.library_results),
        }

        # Add XBRL calculation details separately for easy access
        if xbrl_results:
            report['xbrl_calculation_results'] = self._serialize_check_results(xbrl_results)

        return report

    def _serialize_check_results(self, results: list[CheckResult]) -> list[dict]:
        """Convert check results to serializable format."""
        serialized = []

        for result in results:
            item = {
                'check_name': result.check_name,
                'check_type': result.check_type,
                'passed': result.passed,
                'severity': result.severity,
                'message': result.message,
            }

            if result.expected_value is not None:
                item['expected_value'] = result.expected_value

            if result.actual_value is not None:
                item['actual_value'] = result.actual_value

            if result.difference is not None:
                item['difference'] = result.difference

            if result.details:
                item['details'] = result.details

            serialized.append(item)

        return serialized

    def _write_report(self, report: dict, output_path: Path) -> None:
        """Write report to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)


__all__ = ['ReportGenerator']
