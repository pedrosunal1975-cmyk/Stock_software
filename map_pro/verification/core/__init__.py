# Path: verification/core/__init__.py
"""
Verification Core Package

Configuration, data paths, and logging for the verification module.
"""

from .config_loader import ConfigLoader
from .data_paths import DataPathsManager, ensure_data_paths, validate_paths

__all__ = [
    'ConfigLoader',
    'DataPathsManager',
    'ensure_data_paths',
    'validate_paths',
]
