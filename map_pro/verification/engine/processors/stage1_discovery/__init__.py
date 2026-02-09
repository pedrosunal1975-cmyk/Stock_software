# Path: verification/engine/checks_v2/processors/stage1_discovery/__init__.py
"""
Stage 1: Discovery Processor

Scans XBRL files to discover and extract raw data.
No transformation or validation - just extraction.
"""

from .discovery_processor import DiscoveryProcessor

__all__ = ['DiscoveryProcessor']
