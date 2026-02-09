# Path: library/core/__init__.py
"""
Library Core Module

Core infrastructure for library module.
Provides configuration, paths, and logging.
"""

from .config_loader import LibraryConfig
from .data_paths import LibraryPaths
from .logger import get_logger

__all__ = [
    'LibraryConfig',
    'LibraryPaths',
    'get_logger',
]