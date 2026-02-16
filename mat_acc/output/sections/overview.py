# Path: mat_acc/output/sections/overview.py
"""
Overview Section Producer

Creates the report header section with filing identification,
analysis metadata, and top-level summary statistics.
"""

from typing import List

from ..report_models import ReportSection, SectionItem
from .base_section import BaseSection


class OverviewSection(BaseSection):
    """Produces the filing overview / header section."""

    @property
    def section_type(self) -> str:
        return 'overview'

    def produce(self, analysis_result, **kwargs) -> List[ReportSection]:
        """Build overview section from analysis result."""
        r = analysis_result
        s = r.summary

        items = [
            SectionItem(
                key='company', label='Company', value=r.company,
            ),
            SectionItem(
                key='market', label='Market', value=r.market.upper(),
            ),
            SectionItem(
                key='form', label='Form', value=r.form,
            ),
            SectionItem(
                key='date', label='Filing Date', value=r.date,
            ),
        ]

        # Industry if detected
        industry_display = s.get('industry_display', '')
        if industry_display:
            items.append(SectionItem(
                key='industry', label='Industry',
                value=industry_display,
            ))

        # Summary stats
        mc = s.get('matched_components', 0)
        ac = s.get('applicable_components', s.get('total_components', 0))
        rate = s.get('match_rate', 0)
        items.append(SectionItem(
            key='component_match_rate', label='Component Match Rate',
            value=rate,
            details={
                'matched': mc, 'applicable': ac,
                'display': f"{mc}/{ac} ({rate*100:.1f}%)",
            },
        ))

        vr = s.get('valid_ratios', 0)
        tr = s.get('total_ratios', 0)
        items.append(SectionItem(
            key='ratio_completion', label='Ratios Calculated',
            value=vr,
            details={
                'valid': vr, 'total': tr,
                'display': f"{vr}/{tr}",
            },
        ))

        section = ReportSection(
            section_id='overview',
            title='Filing Overview',
            section_type='overview',
            items=items,
            metadata={'summary': s},
        )
        return [section]


__all__ = ['OverviewSection']
