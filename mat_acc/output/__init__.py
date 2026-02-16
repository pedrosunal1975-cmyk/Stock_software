# Path: mat_acc/output/__init__.py
"""
Output Module for mat_acc

Generates human-readable and machine-readable outputs from
financial analysis results and the mat_acc database.

Architecture:
    ReportGenerator  - Main entry point for report generation
    SectionRegistry  - Register new calculation/analysis types
    FormatterRegistry - Register new output formats
    RawTreeGenerator - Existing ASCII tree visualization

Report generation flow:
    AnalysisResult -> [Section Producers] -> ReportData -> [Formatters] -> Files

Extensibility:
    - New calculations: subclass BaseSection, register with SectionRegistry
    - New output formats: subclass BaseFormatter, register with FormatterRegistry

Usage:
    from output import ReportGenerator

    generator = ReportGenerator(config)
    report = generator.generate(analysis_result, ratio_definitions=defs)
    paths = generator.write(report)
    print(generator.to_console(report))
"""

# Existing tree generator
from .raw_tree import RawTreeGenerator, RawTreeFormatter

# Report data models
from .report_models import ReportData, ReportSection, SectionItem

# Report generator
from .report_generator import ReportGenerator

# Section producers and registry
from .sections import (
    BaseSection,
    SectionRegistry,
    OverviewSection,
    ComponentsSection,
    RatiosSection,
)

# Formatters and registry
from .formatters import (
    BaseFormatter,
    FormatterRegistry,
    JsonFormatter,
    TextFormatter,
    CsvFormatter,
)


__all__ = [
    # Existing
    'RawTreeGenerator',
    'RawTreeFormatter',
    # Report models
    'ReportData',
    'ReportSection',
    'SectionItem',
    # Generator
    'ReportGenerator',
    # Sections
    'BaseSection',
    'SectionRegistry',
    'OverviewSection',
    'ComponentsSection',
    'RatiosSection',
    # Formatters
    'BaseFormatter',
    'FormatterRegistry',
    'JsonFormatter',
    'TextFormatter',
    'CsvFormatter',
]
