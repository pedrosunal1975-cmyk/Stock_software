"""
Core Module - Shared Workflow Components

This module provides shared components used across all Map Pro modules.

Components:
- Configuration loading (config_loader)
- Data path management (data_paths)
- Logging system (logger)
- Workflow orchestration (workflow_orchestrator)
- Constants and helpers
"""

# Configuration and initialization (import first)
from .config_loader import CoreConfigLoader, get_core_config
from .data_paths import (
    CoreDataPathsManager,
    ensure_core_paths,
    ensure_postgresql_ready,
)
from .logger import (
    MapProLogger,
    get_map_pro_logger,
    get_app_logger,
    get_startup_logger,
    configure_logging,
    log_startup_complete,
    log_shutdown,
)

# Workflow components
from .workflow_orchestrator import WorkflowOrchestrator, WorkflowState
from .constants import (
    PROGRESS_DATABASE_INIT,
    PROGRESS_SEARCH_START,
    PROGRESS_DOWNLOAD_START,
    PROGRESS_PARSE_START,
    PROGRESS_MAP_START,
    PROGRESS_COMPLETE,
    SEPARATOR_WIDTH,
    SEPARATOR_CHAR,
)

__all__ = [
    # Configuration
    'CoreConfigLoader',
    'get_core_config',
    # Data paths
    'CoreDataPathsManager',
    'ensure_core_paths',
    'ensure_postgresql_ready',
    # Logging
    'MapProLogger',
    'get_map_pro_logger',
    'get_app_logger',
    'get_startup_logger',
    'configure_logging',
    'log_startup_complete',
    'log_shutdown',
    # Workflow
    'WorkflowOrchestrator',
    'WorkflowState',
    # Progress constants
    'PROGRESS_DATABASE_INIT',
    'PROGRESS_SEARCH_START',
    'PROGRESS_DOWNLOAD_START',
    'PROGRESS_PARSE_START',
    'PROGRESS_MAP_START',
    'PROGRESS_COMPLETE',
    # Display constants
    'SEPARATOR_WIDTH',
    'SEPARATOR_CHAR',
]
