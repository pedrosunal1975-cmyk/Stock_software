# Path: mat_acc/output/report_models.py
"""
Report Data Models

Format-agnostic data structures for report generation.
Sections produce these models; formatters consume them.

Design: Any new calculation type (detailed analysis, comparisons,
component breakdowns) creates ReportSection instances with SectionItem
rows. Formatters render them without knowing the calculation logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SectionItem:
    """
    Single data row within a report section.

    Attributes:
        key: Machine identifier (e.g., 'current_ratio')
        label: Human-readable name (e.g., 'Current Ratio')
        value: Primary display value (number, string, etc.)
        status: Rendering hint ('ok', 'warning', 'error', 'info', 'skip')
        details: Extra context (formula, sub-values, interpretation)
    """
    key: str
    label: str
    value: Any = None
    status: str = 'info'
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportSection:
    """
    A logical section of the report.

    Each section represents one block of analysis output.
    Section types are open-ended: new calculation types register
    new section_type values without changing existing code.

    Attributes:
        section_id: Unique identifier (e.g., 'liquidity_ratios')
        title: Display title (e.g., 'Liquidity Ratios')
        section_type: Category hint for formatters
        items: Ordered list of data rows
        metadata: Section-level context (category, notes, totals)
    """
    section_id: str
    title: str
    section_type: str
    items: List[SectionItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportData:
    """
    Complete report ready for formatting.

    Produced by ReportGenerator from AnalysisResult.
    Consumed by any formatter (JSON, text, CSV, HTML, etc.).

    Attributes:
        company: Company name
        market: Market identifier
        form: Filing form type
        date: Filing date
        generated_at: ISO timestamp of report generation
        sections: Ordered list of report sections
        summary: Top-level summary statistics
    """
    company: str
    market: str
    form: str
    date: str
    generated_at: str = ''
    sections: List[ReportSection] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def get_section(self, section_id: str) -> Optional[ReportSection]:
        """Find a section by ID."""
        for section in self.sections:
            if section.section_id == section_id:
                return section
        return None

    def get_sections_by_type(self, section_type: str) -> List[ReportSection]:
        """Get all sections of a given type."""
        return [s for s in self.sections if s.section_type == section_type]


__all__ = ['SectionItem', 'ReportSection', 'ReportData']
