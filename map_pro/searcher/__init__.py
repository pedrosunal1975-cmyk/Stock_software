# Path: searcher/__init__.py
"""
Map Pro Searcher Module

Interactive and programmatic filing search across multiple markets.
Supports SEC, ESMA, and FCA markets.
"""

__version__ = '2.0.0'

from .core import ConfigLoader, get_logger, configure_logging
from .markets import get_searcher, get_available_markets

__all__ = [
    'ConfigLoader',
    'get_logger',
    'configure_logging',
    'get_searcher',
    'get_available_markets',
]