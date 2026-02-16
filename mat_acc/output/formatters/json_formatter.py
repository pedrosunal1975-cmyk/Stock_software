# Path: mat_acc/output/formatters/json_formatter.py
"""
JSON Formatter

Renders ReportData as structured JSON. Preserves all section
and item detail for downstream consumption by other tools,
dashboards, or future comparison engines.
"""

import json
from typing import Any, Dict, List

from ..report_models import ReportData, ReportSection, SectionItem
from .base_formatter import BaseFormatter


class JsonFormatter(BaseFormatter):
    """Renders report as JSON."""

    @property
    def format_name(self) -> str:
        return 'json'

    @property
    def file_extension(self) -> str:
        return '.json'

    def format_report(self, report: ReportData) -> str:
        """Serialize report to JSON string."""
        data = self._serialize_report(report)
        return json.dumps(data, indent=2, default=str)

    def _serialize_report(self, report: ReportData) -> Dict[str, Any]:
        """Convert ReportData to plain dict."""
        return {
            'company': report.company,
            'market': report.market,
            'form': report.form,
            'date': report.date,
            'generated_at': report.generated_at,
            'summary': report.summary,
            'sections': [
                self._serialize_section(s) for s in report.sections
            ],
        }

    def _serialize_section(self, section: ReportSection) -> Dict[str, Any]:
        """Convert ReportSection to plain dict."""
        return {
            'section_id': section.section_id,
            'title': section.title,
            'section_type': section.section_type,
            'metadata': section.metadata,
            'items': [
                self._serialize_item(item) for item in section.items
            ],
        }

    def _serialize_item(self, item: SectionItem) -> Dict[str, Any]:
        """Convert SectionItem to plain dict."""
        return {
            'key': item.key,
            'label': item.label,
            'value': item.value,
            'status': item.status,
            'details': item.details,
        }


__all__ = ['JsonFormatter']
