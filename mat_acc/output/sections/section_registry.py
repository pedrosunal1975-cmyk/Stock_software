# Path: mat_acc/output/sections/section_registry.py
"""
Section Registry

Central registry for section producers. New calculation types
register here to be automatically included in report generation.

Usage:
    SectionRegistry.register(MyNewSection)
    sections = SectionRegistry.build_all(analysis_result)
"""

from typing import Dict, List, Type

from ..report_models import ReportSection
from .base_section import BaseSection


class SectionRegistry:
    """
    Registry of section producers.

    Maintains an ordered list of producers. When build_all() is
    called, each registered producer creates its sections from
    the analysis result.

    Class-level registry shared across all instances.
    """

    _producers: Dict[str, Type[BaseSection]] = {}
    _order: List[str] = []

    @classmethod
    def register(cls, producer_class: Type[BaseSection]) -> None:
        """
        Register a section producer.

        Args:
            producer_class: BaseSection subclass to register
        """
        instance = producer_class()
        key = instance.section_type
        if key not in cls._producers:
            cls._producers[key] = producer_class
            cls._order.append(key)

    @classmethod
    def unregister(cls, section_type: str) -> None:
        """Remove a registered producer."""
        cls._producers.pop(section_type, None)
        if section_type in cls._order:
            cls._order.remove(section_type)

    @classmethod
    def build_all(cls, analysis_result, **kwargs) -> List[ReportSection]:
        """
        Run all registered producers in order.

        Args:
            analysis_result: AnalysisResult from ratio_check
            **kwargs: Additional context passed to each producer

        Returns:
            Ordered list of ReportSection instances
        """
        sections = []
        for key in cls._order:
            producer_class = cls._producers[key]
            producer = producer_class()
            produced = producer.produce(analysis_result, **kwargs)
            sections.extend(produced)
        return sections

    @classmethod
    def get_registered(cls) -> List[str]:
        """Return list of registered section type names."""
        return list(cls._order)

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations (for testing)."""
        cls._producers.clear()
        cls._order.clear()


__all__ = ['SectionRegistry']
