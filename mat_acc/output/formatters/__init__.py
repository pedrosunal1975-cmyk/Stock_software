# Path: mat_acc/output/formatters/__init__.py
"""
Report Formatters

Each formatter renders ReportData into a specific output format.
Formatters are format-specific; they know nothing about calculation
logic. New formats add new formatters without changing sections.
"""

from .base_formatter import BaseFormatter, FormatterRegistry
from .json_formatter import JsonFormatter
from .text_formatter import TextFormatter
from .csv_formatter import CsvFormatter

__all__ = [
    'BaseFormatter',
    'FormatterRegistry',
    'JsonFormatter',
    'TextFormatter',
    'CsvFormatter',
]
