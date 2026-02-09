# Path: verification/output/summary_exporter.py
"""
Summary Exporter for Verification Module

Creates human-readable verification summary text files.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader
from ..engine.coordinator import VerificationResult
from ..constants import LOG_OUTPUT, SUMMARY_FILE


class SummaryExporter:
    """
    Creates human-readable verification summary files.

    Generates summary.txt with key findings and recommendations.

    Example:
        exporter = SummaryExporter()
        path = exporter.export_summary(verification_result)
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize summary exporter.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.output_dir = self.config.get('output_dir')
        self.logger = logging.getLogger('output.summary_exporter')

    def export_summary(
        self,
        result: VerificationResult,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Export verification summary to text file.

        Args:
            result: VerificationResult from coordinator
            output_path: Optional custom output path

        Returns:
            Path to generated summary file
        """
        self.logger.info(f"{LOG_OUTPUT} Exporting summary for {result.filing_id}")

        # Determine output path
        if output_path is None:
            output_path = self._get_default_output_path(result)

        # Build summary content
        content = self._build_summary(result)

        # Write summary
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        self.logger.info(f"{LOG_OUTPUT} Summary saved to: {output_path}")

        return output_path

    def _get_default_output_path(self, result: VerificationResult) -> Path:
        """Get default output path for summary."""
        if not self.output_dir:
            raise ValueError("Output directory not configured")

        report_dir = (
            self.output_dir /
            result.market /
            result.company /
            result.form /
            result.date
        )
        report_dir.mkdir(parents=True, exist_ok=True)

        return report_dir / SUMMARY_FILE

    def _build_summary(self, result: VerificationResult) -> str:
        """Build summary text content."""
        lines = []
        sep = '=' * 60

        # Header
        lines.append(sep)
        lines.append('VERIFICATION SUMMARY')
        lines.append(sep)
        lines.append('')

        # Filing Info
        lines.append('FILING INFORMATION')
        lines.append('-' * 40)
        lines.append(f'Company:    {result.company}')
        lines.append(f'Form:       {result.form}')
        lines.append(f'Date:       {result.date}')
        lines.append(f'Market:     {result.market}')
        lines.append(f'Filing ID:  {result.filing_id}')
        lines.append('')

        # Quality Classification
        if result.quality:
            lines.append('QUALITY CLASSIFICATION')
            lines.append('-' * 40)
            lines.append(f'Level:       {result.quality.level}')
            lines.append(f'Description: {result.quality.description}')
            lines.append(f'Confidence:  {result.quality.confidence:.0%}')
            lines.append('')

        # Scores
        if result.scores:
            lines.append('VERIFICATION SCORES')
            lines.append('-' * 40)
            lines.append(f'Horizontal Score: {result.scores.horizontal_score:6.1f}/100')
            lines.append(f'Vertical Score:   {result.scores.vertical_score:6.1f}/100')
            lines.append(f'Library Score:    {result.scores.library_score:6.1f}/100')
            lines.append(f'Overall Score:    {result.scores.overall_score:6.1f}/100')
            lines.append('')

        # Issues Summary
        lines.append('ISSUES FOUND')
        lines.append('-' * 40)
        critical = result.issues_summary.get('critical', 0)
        warnings = result.issues_summary.get('warnings', 0)
        info = result.issues_summary.get('info', 0)
        lines.append(f'Critical Issues:  {critical}')
        lines.append(f'Warnings:         {warnings}')
        lines.append(f'Info:             {info}')
        lines.append('')

        # Failed Checks Details
        failed_checks = self._get_failed_checks(result)
        if failed_checks:
            lines.append('FAILED CHECKS')
            lines.append('-' * 40)
            for check in failed_checks[:10]:  # Limit to first 10
                lines.append(f'- [{check.severity.upper()}] {check.check_name}')
                lines.append(f'  {check.message}')
            if len(failed_checks) > 10:
                lines.append(f'  ... and {len(failed_checks) - 10} more')
            lines.append('')

        # Recommendation
        lines.append('RECOMMENDATION')
        lines.append('-' * 40)
        lines.append(result.recommendation)
        lines.append('')

        # Footer
        lines.append(sep)
        lines.append(f'Verified at: {result.verified_at.strftime("%Y-%m-%d %H:%M:%S") if result.verified_at else "N/A"}')
        lines.append(f'Processing time: {result.processing_time_seconds:.2f} seconds')
        lines.append(sep)

        return '\n'.join(lines)

    def _get_failed_checks(self, result: VerificationResult) -> list:
        """Get all failed checks."""
        failed = []

        for check in result.horizontal_results:
            if not check.passed:
                failed.append(check)

        for check in result.vertical_results:
            if not check.passed:
                failed.append(check)

        for check in result.library_results:
            if not check.passed:
                failed.append(check)

        # Sort by severity
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        failed.sort(key=lambda c: severity_order.get(c.severity, 3))

        return failed


__all__ = ['SummaryExporter']
