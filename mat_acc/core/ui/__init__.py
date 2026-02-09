# Path: mat_acc/core/ui/__init__.py
"""
mat_acc UI Package

User interface components for the Mathematical Accountancy system.

Provides:
- Company selection interface
- Filing selection interface
- Analysis options interface
"""

from .user_input import (
    CompanySelector,
    display_menu,
    get_user_selection,
)

__all__ = [
    'CompanySelector',
    'display_menu',
    'get_user_selection',
]
