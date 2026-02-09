# Path: library/core/logger.py
"""
Library Module Logger

Centralized logging for library module.
Designed to work standalone but compatible with multi-module system.

Architecture:
- IPO (Input-Process-Output) pattern
- Component-based logging (core, engine, cli)
- File and console output
- Ready for integration with system-wide logger

Usage:
    from library.core.logger import get_logger
    
    logger = get_logger(__name__, 'engine')
    logger.info(f"{LOG_INPUT} Processing file...")
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Try to import from parent system logger if available
try:
    from system_logger import get_logger as get_system_logger
    SYSTEM_LOGGER_AVAILABLE = True
except ImportError:
    SYSTEM_LOGGER_AVAILABLE = False


def get_logger(name: str, component: str = 'library') -> logging.Logger:
    """
    Get logger instance for library module.
    
    If system logger is available, uses it. Otherwise creates standalone logger.
    
    Args:
        name: Logger name (usually __name__)
        component: Component name ('core', 'engine', 'cli', 'patterns', 'models')
        
    Returns:
        Logger instance configured for library module
    """
    if SYSTEM_LOGGER_AVAILABLE:
        # Use system-wide logger if available
        return get_system_logger(f"library.{component}.{name}", component)
    else:
        # Use standalone library logger
        return _create_standalone_logger(name, component)


def _create_standalone_logger(name: str, component: str) -> logging.Logger:
    """
    Create standalone logger for library module.
    
    Args:
        name: Logger name
        component: Component name
        
    Returns:
        Configured logger instance
    """
    logger_name = f"library.{component}.{name}"
    logger = logging.getLogger(logger_name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Get log directory from environment or use default
        log_dir = _get_log_directory()
        
        # Create log directory if it doesn't exist
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create file handler
        log_file = log_dir / f"library_{component}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger


def _get_log_directory() -> Path:
    """
    Get log directory from environment or use default.
    
    Returns:
        Path to log directory
    """
    import os
    from dotenv import load_dotenv
    
    # Load .env file if it exists
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    # Get log directory from environment
    log_dir_str = os.getenv('LIBRARY_LOG_DIR', '/mnt/map_pro/taxonomies/logs')
    
    return Path(log_dir_str)


__all__ = ['get_logger']