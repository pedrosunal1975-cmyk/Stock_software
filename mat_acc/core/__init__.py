# Path: mat_acc/core/__init__.py
"""
mat_acc Core Package

Core utilities for the Mathematical Accountancy system.

Submodules:
    - logger: IPO-aware logging system
    - ui: User input and interaction
    - data_paths: Directory management
"""

from .data_paths import DataPathsManager

__all__ = [
    'DataPathsManager',
]
