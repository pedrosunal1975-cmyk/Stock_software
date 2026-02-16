# Path: mat_acc/output/sections/base_section.py
"""
Base Section Producer

Abstract base class for all section producers.
Each subclass converts part of an AnalysisResult into
one or more ReportSection instances.

To add a new calculation type:
1. Subclass BaseSection
2. Implement produce()
3. Register via SectionRegistry.register()
"""

from abc import ABC, abstractmethod
from typing import List

from ..report_models import ReportSection


class BaseSection(ABC):
    """
    Abstract base for section producers.

    Subclasses implement produce() to transform analysis data
    into format-agnostic ReportSection instances.
    """

    @property
    @abstractmethod
    def section_type(self) -> str:
        """Unique type identifier for this section producer."""

    @abstractmethod
    def produce(self, analysis_result, **kwargs) -> List[ReportSection]:
        """
        Produce report sections from analysis data.

        Args:
            analysis_result: AnalysisResult from ratio_check
            **kwargs: Additional context (value_lookup, etc.)

        Returns:
            List of ReportSection instances (may be multiple
            if the producer creates grouped sub-sections)
        """


__all__ = ['BaseSection']
