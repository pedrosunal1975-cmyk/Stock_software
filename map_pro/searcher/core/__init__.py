# Path: searcher/core/__init__.py
"""Core Module - Configuration, Logging, Path Management, and Metadata Extraction"""

from .config_loader import ConfigLoader
from .logger import get_logger, configure_logging
from .data_paths import DataPathsManager, ensure_data_paths, validate_paths
from .metadata_extractor import BaseMetadataExtractor

__all__ = [
    'ConfigLoader',
    'get_logger',
    'configure_logging',
    'DataPathsManager',
    'ensure_data_paths',
    'validate_paths',
    'BaseMetadataExtractor',
]