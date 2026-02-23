# Path: mat_acc/core/__init__.py
"""
mat_acc Core Package

Core utilities for the Mathematical Accountancy system.

Submodules:
    - logger: IPO-aware logging system
    - ui: User input and interaction
    - data_paths: Directory management
    - qname: Shared QName parsing and manipulation
"""

from .data_paths import DataPathsManager
from .qname import (
    parse_qname,
    get_local_name,
    alternate_qname,
    normalize_qname,
)

__all__ = [
    'DataPathsManager',
    'parse_qname',
    'get_local_name',
    'alternate_qname',
    'normalize_qname',
]
