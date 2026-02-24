# Path: mat_acc/ratio_check/esef/__init__.py
"""
ESEF Preprocessor Module

Runs AFTER MIU (to reuse its ContextFilter), BEFORE matching.
Fixes ESEF data quality issues without modifying SEC processing.

Key responsibilities:
- Context resolution (period, dimensional filtering)
- Period annotation for facts with missing period info
- Dimensional fact exclusion via is_primary flag
"""
from .esef_preprocessor import preprocess_esef

__all__ = ['preprocess_esef']
