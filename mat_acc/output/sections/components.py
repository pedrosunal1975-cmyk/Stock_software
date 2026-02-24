# Path: mat_acc/output/sections/components.py
"""
Components Section Producer

Creates sections showing component matching results.
Splits into matched and unmatched sub-sections.
"""

from typing import List

from ..report_models import ReportSection, SectionItem
from .base_section import BaseSection


class ComponentsSection(BaseSection):
    """Produces component matching sections."""

    @property
    def section_type(self) -> str:
        return 'components'

    def produce(self, analysis_result, **kwargs) -> List[ReportSection]:
        """Build matched/uncertain/unmatched component sections."""
        sections = []
        matches = analysis_result.component_matches

        confident = [m for m in matches if m.matched and m.match_quality != 'uncertain']
        uncertain = [m for m in matches if m.matched and m.match_quality == 'uncertain']
        unmatched = [m for m in matches if not m.matched]

        if confident:
            sections.append(self._build_matched(confident))
        if uncertain:
            sections.append(self._build_uncertain(uncertain))
        if unmatched:
            sections.append(self._build_unmatched(unmatched))

        return sections

    def _build_matched(self, matched: list) -> ReportSection:
        """Build section for matched components."""
        items = []
        for m in matched:
            label = m.label or ''
            if not label and m.matched_concept:
                label = m.matched_concept

            items.append(SectionItem(
                key=m.component_name,
                label=m.component_name.replace('_', ' ').title(),
                value=m.value,
                status='ok',
                details={
                    'concept': m.matched_concept,
                    'concept_label': label,
                    'confidence': m.confidence,
                    'match_quality': m.match_quality,
                    'fallback_formula': m.fallback_formula,
                },
            ))

        return ReportSection(
            section_id='matched_components',
            title='Matched Components',
            section_type='component_table',
            items=items,
            metadata={'count': len(items)},
        )

    def _build_uncertain(self, uncertain: list) -> ReportSection:
        """Build section for uncertain matches (value blocked)."""
        items = []
        for m in uncertain:
            label = m.label or ''
            if not label and m.matched_concept:
                label = m.matched_concept
            items.append(SectionItem(
                key=m.component_name,
                label=m.component_name.replace('_', ' ').title(),
                value=None,
                status='warning',
                details={
                    'concept': m.matched_concept,
                    'concept_label': label,
                    'confidence': m.confidence,
                    'match_quality': 'uncertain',
                },
            ))
        return ReportSection(
            section_id='uncertain_components',
            title='Uncertain Components (value blocked)',
            section_type='component_table',
            items=items,
            metadata={'count': len(items)},
        )

    def _build_unmatched(self, unmatched: list) -> ReportSection:
        """Build section for unmatched components."""
        items = []
        for m in unmatched:
            items.append(SectionItem(
                key=m.component_name,
                label=m.component_name.replace('_', ' ').title(),
                value=None,
                status='error',
                details={
                    'fallback_formula': m.fallback_formula,
                },
            ))

        return ReportSection(
            section_id='unmatched_components',
            title='Unmatched Components',
            section_type='component_table',
            items=items,
            metadata={'count': len(items)},
        )


__all__ = ['ComponentsSection']
