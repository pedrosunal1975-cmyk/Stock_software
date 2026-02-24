# Path: mat_acc/output/sections/plausibility.py
"""
Plausibility Audit Section Producer

Converts PlausibilityReport findings into ReportSection instances
for the output pipeline. Formatters render these alongside other
sections without knowing plausibility logic.
"""

from typing import List

from ..report_models import ReportSection, SectionItem
from .base_section import BaseSection


class PlausibilitySection(BaseSection):
    """Produces plausibility audit section for reports."""

    @property
    def section_type(self) -> str:
        return 'plausibility'

    def produce(self, analysis_result, **kwargs) -> List[ReportSection]:
        """Build plausibility section from analysis result."""
        plausibility = getattr(analysis_result, 'plausibility', None)
        if not plausibility or not plausibility.findings:
            return []

        items = []
        for f in plausibility.findings:
            items.append(SectionItem(
                key=f.target,
                label=f.target.replace('_', ' ').title(),
                value=f.actual_value,
                status=self._map_status(f.severity.value),
                details={
                    'severity': f.severity.value,
                    'severity_tag': f.severity_tag,
                    'category': f.category,
                    'message': f.message,
                    'source': f.source_tag,
                    'expectation_basis': f.expectation_basis,
                    'expected_range': f.expected_range,
                    'declared_value': f.declared_value,
                },
            ))

        counts = plausibility.summary_counts
        return [ReportSection(
            section_id='plausibility_audit',
            title='Plausibility Audit',
            section_type='plausibility_audit',
            items=items,
            metadata={
                'total': len(plausibility.findings),
                'warnings': (
                    counts.get('warning', 0)
                    + counts.get('alert', 0)
                ),
                'advisories': counts.get('advisory', 0),
                'infos': counts.get('info', 0),
            },
        )]

    def _map_status(self, severity: str) -> str:
        """Map severity to SectionItem status."""
        mapping = {
            'alert': 'error',
            'warning': 'warning',
            'advisory': 'info',
            'info': 'ok',
        }
        return mapping.get(severity, 'info')


__all__ = ['PlausibilitySection']
