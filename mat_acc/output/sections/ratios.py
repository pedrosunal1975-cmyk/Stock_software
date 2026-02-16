# Path: mat_acc/output/sections/ratios.py
"""
Ratios Section Producer

Creates one ReportSection per ratio category (liquidity, leverage,
profitability, efficiency, plus any future categories).

Groups ratios by category from their definitions. Unknown categories
are collected into an 'other' section.
"""

from typing import Dict, List

from ..report_models import ReportSection, SectionItem
from .base_section import BaseSection

# Category display names and order
CATEGORY_ORDER = [
    'liquidity', 'leverage', 'profitability', 'efficiency',
]
CATEGORY_TITLES = {
    'liquidity': 'Liquidity Ratios',
    'leverage': 'Leverage Ratios',
    'profitability': 'Profitability Ratios',
    'efficiency': 'Efficiency Ratios',
}


class RatiosSection(BaseSection):
    """Produces ratio sections grouped by category."""

    @property
    def section_type(self) -> str:
        return 'ratios'

    def produce(self, analysis_result, **kwargs) -> List[ReportSection]:
        """Build one section per ratio category."""
        ratio_defs = kwargs.get('ratio_definitions', [])
        category_map = self._build_category_map(ratio_defs)
        sections = []

        # Group ratios by category
        grouped = self._group_ratios(
            analysis_result.ratios, category_map,
        )

        # Emit sections in standard order, then any extras
        emitted = set()
        for cat in CATEGORY_ORDER:
            if cat in grouped:
                sections.append(
                    self._build_category_section(cat, grouped[cat])
                )
                emitted.add(cat)

        # Any categories not in standard order
        for cat in sorted(grouped.keys()):
            if cat not in emitted:
                sections.append(
                    self._build_category_section(cat, grouped[cat])
                )

        return sections

    def _build_category_map(
        self, ratio_defs: list,
    ) -> Dict[str, str]:
        """Map ratio_name -> category from definitions."""
        mapping = {}
        for rd in ratio_defs:
            name = rd.get('name', '')
            category = rd.get('category', 'other')
            mapping[name] = category
        return mapping

    def _group_ratios(
        self, ratios: list, category_map: Dict[str, str],
    ) -> Dict[str, list]:
        """Group ratio results by category."""
        grouped: Dict[str, list] = {}
        for r in ratios:
            cat = category_map.get(r.ratio_name, 'other')
            grouped.setdefault(cat, []).append(r)
        return grouped

    def _build_category_section(
        self, category: str, ratios: list,
    ) -> ReportSection:
        """Build a section for one ratio category."""
        title = CATEGORY_TITLES.get(
            category, category.replace('_', ' ').title() + ' Ratios',
        )

        items = []
        for r in ratios:
            status = 'ok' if r.valid else 'error'
            items.append(SectionItem(
                key=r.ratio_name.lower().replace(' ', '_'),
                label=r.ratio_name,
                value=r.value,
                status=status,
                details={
                    'formula': r.formula,
                    'numerator': r.numerator,
                    'denominator': r.denominator,
                    'numerator_value': r.numerator_value,
                    'denominator_value': r.denominator_value,
                    'valid': r.valid,
                    'error': r.error,
                },
            ))

        valid_count = sum(1 for r in ratios if r.valid)
        return ReportSection(
            section_id=f"{category}_ratios",
            title=title,
            section_type='ratio_group',
            items=items,
            metadata={
                'category': category,
                'valid_count': valid_count,
                'total_count': len(ratios),
            },
        )


__all__ = ['RatiosSection']
