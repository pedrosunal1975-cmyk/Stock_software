# Path: mat_acc/output/formatters/text_formatter.py
"""
Text Formatter

Renders ReportData as ASCII text suitable for console display
and plain-text file output. Handles all section types generically
with type-specific rendering hints.
"""

from ..report_models import ReportData, ReportSection, SectionItem
from .base_formatter import BaseFormatter

LINE_WIDTH = 70
DIVIDER = '=' * LINE_WIDTH
SUB_DIVIDER = '-' * LINE_WIDTH


class TextFormatter(BaseFormatter):
    """Renders report as ASCII text."""

    @property
    def format_name(self) -> str:
        return 'text'

    @property
    def file_extension(self) -> str:
        return '.txt'

    def format_report(self, report: ReportData) -> str:
        """Render full report as text."""
        lines = []
        lines.append('')
        lines.append(DIVIDER)
        lines.append(f"  FINANCIAL ANALYSIS: {report.company}")
        lines.append(
            f"  {report.market.upper()} | {report.form} | {report.date}"
        )
        lines.append(DIVIDER)

        for section in report.sections:
            section_lines = self._render_section(section)
            lines.extend(section_lines)

        lines.append('')
        lines.append(DIVIDER)
        if report.generated_at:
            lines.append(f"  Generated: {report.generated_at}")
        lines.append('')
        return '\n'.join(lines)

    def _render_section(self, section: ReportSection) -> list[str]:
        """Dispatch to type-specific renderer."""
        renderers = {
            'overview': self._render_overview,
            'component_table': self._render_components,
            'ratio_group': self._render_ratio_group,
        }
        renderer = renderers.get(
            section.section_type, self._render_generic,
        )
        return renderer(section)

    def _render_overview(self, section: ReportSection) -> list[str]:
        """Render overview section."""
        lines = []
        lines.append('')
        lines.append(f"  {section.title.upper()}:")
        lines.append(SUB_DIVIDER)
        for item in section.items:
            display = item.details.get('display', item.value)
            lines.append(f"    {item.label:25s}  {display}")
        return lines

    def _render_components(self, section: ReportSection) -> list[str]:
        """Render component matching table."""
        lines = []
        lines.append('')
        lines.append(f"  {section.title.upper()} ({len(section.items)}):")
        lines.append(SUB_DIVIDER)

        for item in section.items:
            if item.status == 'ok':
                lines.extend(self._render_matched_component(item))
            else:
                lines.append(f"    [--] {item.key}")

        return lines

    def _render_matched_component(self, item: SectionItem) -> list[str]:
        """Render a single matched component line."""
        d = item.details
        label = d.get('concept_label', '')[:35]
        conf = d.get('confidence', 0)
        conf_str = f"{conf:.2f}" if conf else 'N/A'

        if item.value is not None:
            val = f"{item.value:>15,.0f}"
        else:
            val = f"{'[no value]':>15}"

        return [f"    [OK] {item.key:22s} -> {label:35s} {val} ({conf_str})"]

    def _render_ratio_group(self, section: ReportSection) -> list[str]:
        """Render a ratio category section."""
        lines = []
        lines.append('')
        lines.append(f"  {section.title.upper()}:")
        lines.append(SUB_DIVIDER)

        for item in section.items:
            lines.extend(self._render_ratio_item(item))

        meta = section.metadata
        vc = meta.get('valid_count', 0)
        tc = meta.get('total_count', 0)
        lines.append(f"    ({vc}/{tc} calculated)")
        return lines

    def _render_ratio_item(self, item: SectionItem) -> list[str]:
        """Render a single ratio item."""
        d = item.details
        lines = []

        if item.status == 'ok' and item.value is not None:
            lines.append(
                f"    [OK] {item.label:25s} = {item.value:10.4f}"
            )
            lines.append(f"         {d.get('formula', '')}")
            num = d.get('numerator_value')
            den = d.get('denominator_value')
            num_s = f"{num:,.0f}" if num is not None else 'N/A'
            den_s = f"{den:,.0f}" if den is not None else 'N/A'
            lines.append(f"         ({num_s} / {den_s})")
        else:
            error = d.get('error', 'Not calculated')
            lines.append(
                f"    [--] {item.label:25s} - {error}"
            )
            num = d.get('numerator_value')
            den = d.get('denominator_value')
            if num is not None or den is not None:
                num_s = f"{num:,.0f}" if num is not None else '[missing]'
                den_s = f"{den:,.0f}" if den is not None else '[missing]'
                lines.append(f"         Values: {num_s} / {den_s}")

        return lines

    def _render_generic(self, section: ReportSection) -> list[str]:
        """Fallback renderer for unknown section types."""
        lines = []
        lines.append('')
        lines.append(f"  {section.title.upper()}:")
        lines.append(SUB_DIVIDER)

        for item in section.items:
            status_tag = {'ok': '[OK]', 'error': '[--]', 'warning': '[!!]'}
            tag = status_tag.get(item.status, '[  ]')
            if item.value is not None:
                lines.append(
                    f"    {tag} {item.label:30s}  {item.value}"
                )
            else:
                lines.append(f"    {tag} {item.label}")

        return lines


__all__ = ['TextFormatter']
