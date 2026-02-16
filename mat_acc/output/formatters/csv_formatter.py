# Path: mat_acc/output/formatters/csv_formatter.py
"""
CSV Formatter

Renders ReportData as CSV for spreadsheet import.
Each row is a data item; sections are separated by header rows.
Ratio and component data flatten into a tabular format.
"""

import csv
import io

from ..report_models import ReportData, ReportSection
from .base_formatter import BaseFormatter


class CsvFormatter(BaseFormatter):
    """Renders report as CSV."""

    @property
    def format_name(self) -> str:
        return 'csv'

    @property
    def file_extension(self) -> str:
        return '.csv'

    def format_report(self, report: ReportData) -> str:
        """Render report as CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            'section', 'key', 'label', 'value',
            'status', 'formula', 'numerator_value',
            'denominator_value', 'confidence', 'error',
        ])

        # Metadata row
        writer.writerow([
            'metadata', 'company', report.company, '', '',
            '', '', '', '', '',
        ])
        writer.writerow([
            'metadata', 'market', report.market, '', '',
            '', '', '', '', '',
        ])
        writer.writerow([
            'metadata', 'form', report.form, '', '',
            '', '', '', '', '',
        ])
        writer.writerow([
            'metadata', 'date', report.date, '', '',
            '', '', '', '', '',
        ])

        # Section data
        for section in report.sections:
            self._write_section(writer, section)

        return output.getvalue()

    def _write_section(
        self, writer: csv.writer, section: ReportSection,
    ) -> None:
        """Write one section's items as CSV rows."""
        for item in section.items:
            d = item.details
            writer.writerow([
                section.section_id,
                item.key,
                item.label,
                self._format_value(item.value),
                item.status,
                d.get('formula', ''),
                self._format_value(d.get('numerator_value')),
                self._format_value(d.get('denominator_value')),
                self._format_value(d.get('confidence')),
                d.get('error', ''),
            ])

    def _format_value(self, value) -> str:
        """Format a value for CSV output."""
        if value is None:
            return ''
        if isinstance(value, float):
            if abs(value) >= 1000:
                return f"{value:.0f}"
            return f"{value:.4f}"
        return str(value)


__all__ = ['CsvFormatter']
