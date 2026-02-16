# Path: mat_acc/output/formatters/base_formatter.py
"""
Base Formatter and Formatter Registry

Abstract base class for output formatters and a registry
to look them up by format name.

To add a new format (e.g., HTML, PDF, Excel):
1. Subclass BaseFormatter
2. Implement format_report() and write_report()
3. Register via FormatterRegistry.register()
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Type

from ..report_models import ReportData


class BaseFormatter(ABC):
    """
    Abstract base for report formatters.

    Each subclass renders ReportData into a specific format.
    Formatters iterate over sections and items generically,
    so new section types are handled automatically.
    """

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Short name for this format (e.g., 'json', 'text')."""

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension including dot (e.g., '.json', '.txt')."""

    @abstractmethod
    def format_report(self, report: ReportData) -> str:
        """
        Render report to string.

        Args:
            report: ReportData to render

        Returns:
            Formatted string representation
        """

    def write_report(self, report: ReportData, output_path: Path) -> Path:
        """
        Write report to file.

        Args:
            report: ReportData to render
            output_path: Directory to write into

        Returns:
            Path to the written file
        """
        output_path.mkdir(parents=True, exist_ok=True)
        filename = self._build_filename(report)
        filepath = output_path / filename

        content = self.format_report(report)
        filepath.write_text(content, encoding='utf-8')
        return filepath

    def _build_filename(self, report: ReportData) -> str:
        """Build output filename from report metadata."""
        company = report.company.replace(' ', '_')
        date = report.date
        return f"analysis_{company}_{date}{self.file_extension}"


class FormatterRegistry:
    """
    Registry of available formatters.

    Lookup by format name. The ReportGenerator uses this to
    find the right formatter for each requested output format.
    """

    _formatters: Dict[str, Type[BaseFormatter]] = {}

    @classmethod
    def register(cls, formatter_class: Type[BaseFormatter]) -> None:
        """Register a formatter class."""
        instance = formatter_class()
        name = instance.format_name
        cls._formatters[name] = formatter_class

    @classmethod
    def get(cls, format_name: str) -> Optional[BaseFormatter]:
        """Get a formatter instance by name."""
        formatter_class = cls._formatters.get(format_name)
        if formatter_class:
            return formatter_class()
        return None

    @classmethod
    def get_available(cls) -> list[str]:
        """Return list of registered format names."""
        return list(cls._formatters.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations (for testing)."""
        cls._formatters.clear()


__all__ = ['BaseFormatter', 'FormatterRegistry']
