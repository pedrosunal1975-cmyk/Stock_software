# Path: library/__init__.py
"""
Library Module

Taxonomy library management for MAP PRO system.
Monitors parsed filings, detects taxonomy requirements,
and ensures required taxonomy libraries are available.

Usage:
    from library import LibraryCoordinator
    
    coordinator = LibraryCoordinator()
    coordinator.start_monitoring()
"""

from library.core.config_loader import LibraryConfig
from library.core.data_paths import LibraryPaths
from library.core.logger import get_logger

__version__ = '1.0.0'

__all__ = [
    'LibraryConfig',
    'LibraryPaths',
    'get_logger',
]