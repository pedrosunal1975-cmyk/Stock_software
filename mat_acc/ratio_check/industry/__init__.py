# Path: mat_acc/ratio_check/industry/__init__.py
"""Industry detection and classification."""

from .detector import IndustryDetector
from .registry import IndustryRegistry

__all__ = [
    'IndustryDetector',
    'IndustryRegistry',
]
