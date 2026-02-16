# Path: mat_acc/output/report_generator.py
"""
Report Generator

Main orchestrator for output generation. Converts an AnalysisResult
into ReportData via registered section producers, then writes output
files via registered formatters.

Architecture:
    AnalysisResult  ->  [Section Producers]  ->  ReportData  ->  [Formatters]  ->  Files

Extensibility:
    - New calculation types: register a new section producer
    - New output formats: register a new formatter
    - Both use open registries; no code changes to existing modules

Usage:
    from output import ReportGenerator

    generator = ReportGenerator(config)
    report = generator.generate(analysis_result)
    paths = generator.write(report)
    print(generator.to_console(report))
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config_loader import ConfigLoader
from core.logger.ipo_logging import get_output_logger

from .report_models import ReportData
from .sections import (
    SectionRegistry,
    OverviewSection,
    ComponentsSection,
    RatiosSection,
)
from .formatters import (
    FormatterRegistry,
    JsonFormatter,
    TextFormatter,
    CsvFormatter,
)


logger = get_output_logger('report_generator')


def _register_defaults() -> None:
    """Register built-in section producers and formatters."""
    # Section producers (order matters for report layout)
    SectionRegistry.register(OverviewSection)
    SectionRegistry.register(ComponentsSection)
    SectionRegistry.register(RatiosSection)

    # Formatters
    FormatterRegistry.register(JsonFormatter)
    FormatterRegistry.register(TextFormatter)
    FormatterRegistry.register(CsvFormatter)


# Auto-register on module import
_register_defaults()


class ReportGenerator:
    """
    Generates financial analysis reports from AnalysisResult.

    Coordinates section producers and formatters to create
    multi-format output files.

    Example:
        generator = ReportGenerator(config)
        report = generator.generate(analysis_result, ratio_definitions=defs)
        paths = generator.write(report)
        console_text = generator.to_console(report)
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize report generator.

        Args:
            config: ConfigLoader instance (creates one if not provided)
        """
        self.config = config or ConfigLoader()
        self.logger = get_output_logger('report_generator')

    def generate(self, analysis_result, **kwargs) -> ReportData:
        """
        Build ReportData from an AnalysisResult.

        Runs all registered section producers to create the
        report's section list.

        Args:
            analysis_result: AnalysisResult from ratio_check
            **kwargs: Extra context passed to section producers
                      (e.g., ratio_definitions, value_lookup)

        Returns:
            ReportData ready for formatting
        """
        sections = SectionRegistry.build_all(analysis_result, **kwargs)

        report = ReportData(
            company=analysis_result.company,
            market=analysis_result.market,
            form=analysis_result.form,
            date=analysis_result.date,
            generated_at=datetime.now().isoformat(timespec='seconds'),
            sections=sections,
            summary=analysis_result.summary,
        )

        self.logger.info(
            f"Generated report: {len(sections)} sections "
            f"for {analysis_result.company}"
        )
        return report

    def write(
        self,
        report: ReportData,
        output_dir: Optional[Path] = None,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, Path]:
        """
        Write report to files in requested formats.

        Args:
            report: ReportData to write
            output_dir: Override output directory (default from config)
            formats: List of format names (default: from config flags)

        Returns:
            Dict mapping format name to written file path
        """
        if output_dir is None:
            output_dir = self._resolve_output_dir(report)

        if formats is None:
            formats = self._get_enabled_formats()

        written = {}
        for fmt_name in formats:
            formatter = FormatterRegistry.get(fmt_name)
            if formatter is None:
                self.logger.warning(f"No formatter for: {fmt_name}")
                continue

            filepath = formatter.write_report(report, output_dir)
            written[fmt_name] = filepath
            self.logger.info(f"Wrote {fmt_name}: {filepath}")

        return written

    def to_console(self, report: ReportData) -> str:
        """
        Render report as console-friendly text.

        Args:
            report: ReportData to render

        Returns:
            ASCII text string for console display
        """
        formatter = FormatterRegistry.get('text')
        if formatter is None:
            return f"[No text formatter available for {report.company}]"
        return formatter.format_report(report)

    def to_json(self, report: ReportData) -> str:
        """
        Render report as JSON string.

        Args:
            report: ReportData to render

        Returns:
            JSON string
        """
        formatter = FormatterRegistry.get('json')
        if formatter is None:
            return '{}'
        return formatter.format_report(report)

    def _resolve_output_dir(self, report: ReportData) -> Path:
        """Build output directory from config and report metadata."""
        reports_dir = self.config.get('reports_dir')
        if not reports_dir:
            raise ValueError("reports_dir not configured in .env")

        company = report.company.replace(' ', '_')
        return reports_dir / company

    def _get_enabled_formats(self) -> List[str]:
        """Read enabled format flags from config."""
        format_flags = {
            'json': self.config.get('output_json', True),
            'text': self.config.get('output_text', True),
            'csv': self.config.get('output_csv', True),
        }
        return [name for name, enabled in format_flags.items() if enabled]


__all__ = ['ReportGenerator']
