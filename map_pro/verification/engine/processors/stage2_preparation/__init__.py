# Path: verification/engine/checks_v2/processors/stage2_preparation/__init__.py
"""
Stage 2: Preparation Processor

Transforms discovered data using specialized tools.
Normalizes, classifies, groups, and prepares for verification.
"""

from .preparation_processor import PreparationProcessor

__all__ = ['PreparationProcessor']
