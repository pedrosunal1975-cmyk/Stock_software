# Path: loaders/__init__.py
"""
Loaders Package

Simple file access loaders for XBRL filings and taxonomy libraries.

These loaders provide unconditional recursive access to source files.
NO parsing, NO filtering - just file discovery and access.
Calling code decides what to do with the files.
"""

from .xbrl_filings import XBRLFilingsLoader
from .taxonomy import TaxonomyLoader

__all__ = ['XBRLFilingsLoader', 'TaxonomyLoader']