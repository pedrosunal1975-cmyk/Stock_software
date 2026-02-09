# Path: core/__init__.py
"""
Core Module

Core infrastructure components for the XBRL Mapper.

This module provides:
- Configuration management (ConfigLoader)
- Data paths management (DataPathsManager)
- Mapper-specific configuration (MapperConfig)

Example:
    from ..core import ConfigLoader, ensure_data_paths
    
    # Load configuration
    config = ConfigLoader()
    data_root = config.get('data_root')
    
    # Ensure all directories exist
    result = ensure_data_paths()
    print(f"Created {len(result['created'])} directories")
"""

from .config_loader import ConfigLoader
from .data_paths import (
    DataPathsManager,
    ensure_data_paths,
    validate_paths
)

__all__ = [
    'ConfigLoader',
    'DataPathsManager',
    'ensure_data_paths',
    'validate_paths',
]
