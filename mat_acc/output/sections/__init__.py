# Path: mat_acc/output/sections/__init__.py
"""
Report Sections

Each section producer converts part of AnalysisResult into
ReportSection instances. New calculation types add new producers
here without changing formatters or the generator.
"""

from .base_section import BaseSection
from .section_registry import SectionRegistry
from .overview import OverviewSection
from .components import ComponentsSection
from .ratios import RatiosSection

__all__ = [
    'BaseSection',
    'SectionRegistry',
    'OverviewSection',
    'ComponentsSection',
    'RatiosSection',
]
