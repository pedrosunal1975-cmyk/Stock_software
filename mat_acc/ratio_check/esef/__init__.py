# Path: mat_acc/ratio_check/esef/__init__.py
"""
ESEF Preprocessor Module

Handles ESEF-specific data preparation that runs BEFORE the
universal analysis pipeline. Fixes data quality issues in
ESEF mapped statements without modifying SEC processing.

Key responsibilities:
- Context resolution (period, dimensional filtering)
- Period annotation for facts with missing period info
- Derived total computation (total_assets, total_liabilities)
"""
from .esef_preprocessor import preprocess_esef

__all__ = ['preprocess_esef']
