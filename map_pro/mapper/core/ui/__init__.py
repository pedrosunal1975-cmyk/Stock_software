# Path: core/ui/__init__.py
"""
User Interface Module

Interactive command-line interface for the mapper.

This module provides:
- CLI for selecting parsed filings
- Interactive filing selection

Example:
    from ...core.ui import MappingCLI
    
    cli = MappingCLI()
    parsed_filing = cli.run()
"""

from ...core.ui.cli import MappingCLI, ParsedFilingEntry

__all__ = ['MappingCLI', 'ParsedFilingEntry']
