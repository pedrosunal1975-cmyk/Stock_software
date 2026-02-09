# Path: mapping/models/parsed_filing.py
"""
Parsed Filing Model

Complete parsed filing with intelligence (already defined in loaders).

This model is imported from loaders.parser_output for consistency.
"""

# Re-export from loaders to keep models centralized
from ...loaders.parser_output import ParsedFiling, FilingCharacteristics

__all__ = ['ParsedFiling', 'FilingCharacteristics']
