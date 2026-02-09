# Path: xbrl_parser/__init__.py
"""
XBRL Parser Package

Main package for parsing and validating XBRL financial filings.

This package provides:
- XBRLParser: Main orchestrator for parsing XBRL filings
- ParsingMode: Different parsing modes (FULL, FACTS_ONLY, etc.)
- ParsedFiling: Complete parsed filing data model
- EntryPointDetector: Universal entry point detection for any market
- Validation: Structural and market-specific validation
- Serialization: JSON and other output formats

Example:
    from xbrl_parser import XBRLParser
    from .parser_modes import ParsingMode
    
    # Parse filing
    parser = XBRLParser()
    result = parser.parse('/path/to/filing.xml')
    
    # With mode selection
    parser = XBRLParser(mode=ParsingMode.FACTS_ONLY)
    result = parser.parse('/path/to/filing.xml')
    
    # Direct entry point detection
    from xbrl_parser import detect_entry_point
    from pathlib import Path
    
    files = list(Path('/filing/').glob('**/*'))
    instance = detect_entry_point(files)
"""

# Main orchestrator
from .orchestrator import XBRLParser, ParsingProgress

# Parsing modes
from .parser_modes import (
    ParsingMode,
    ModeConfiguration,
    get_mode_config,
    list_modes
)

# Entry point detection
from .entry_point_detector import (
    EntryPointDetector,
    EntryPointCandidate,
    detect_entry_point
)

# Version info
__version__ = '1.0.0'
__author__ = 'XBRL Parser Team'


__all__ = [
    # Main orchestrator
    'XBRLParser',
    'ParsingProgress',
    
    # Parsing modes
    'ParsingMode',
    'ModeConfiguration',
    'get_mode_config',
    'list_modes',
    
    # Entry point detection
    'EntryPointDetector',
    'EntryPointCandidate',
    'detect_entry_point',
    
    # Version
    '__version__',
]
