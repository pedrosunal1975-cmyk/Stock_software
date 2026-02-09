# Path: database/core/logger.py
"""
Database Module Logger

Centralized logging configuration for the database module.
Future integration point for system-wide logging.

Architecture:
- Component-based logging (core, models, migrations)
- File and console output
- Configurable log levels
- Structured log format
"""

import logging
from pathlib import Path
from typing import Optional

from database.core.config_loader import ConfigLoader
from database.constants import (
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOGGER_CORE,
    LOGGER_MODELS,
    LOGGER_MIGRATIONS,
)


class DatabaseLogger:
    """
    Centralized logger for database module.
    
    Provides component-specific loggers with unified configuration.
    Future integration point for system-wide logging consolidation.
    
    Example:
        logger = get_logger(__name__, 'core')
        logger.info("Database operation completed")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize database logger.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self._configured = False
    
    def configure(self) -> None:
        """Configure logging system for database module."""
        if self._configured:
            return
        
        # Get configuration
        log_dir = self.config.get('db_log_dir')
        log_level = self.config.get('log_level', 'INFO')
        console_output = self.config.get('log_console', True)
        
        # Create log directory if needed
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger for database module
        logger = logging.getLogger('database')
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # File handler for all database logs
        if log_dir:
            log_file = log_dir / 'database_activity.log'
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
            )
            logger.addHandler(file_handler)
        
        # Console handler (optional)
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, log_level.upper()))
            console_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
            )
            logger.addHandler(console_handler)
        
        self._configured = True
    
    def get_logger(self, name: str, component: str = 'core') -> logging.Logger:
        """
        Get logger for specific component.
        
        Args:
            name: Module name (typically __name__)
            component: Component type ('core', 'models', 'migrations')
            
        Returns:
            Configured logger instance
        """
        # Ensure logging is configured
        if not self._configured:
            self.configure()
        
        # Build logger name
        if component == 'core':
            logger_name = f"{LOGGER_CORE}.{name}"
        elif component == 'models':
            logger_name = f"{LOGGER_MODELS}.{name}"
        elif component == 'migrations':
            logger_name = f"{LOGGER_MIGRATIONS}.{name}"
        else:
            logger_name = f"database.{name}"
        
        return logging.getLogger(logger_name)


# Global logger instance
_database_logger = DatabaseLogger()


def get_logger(name: str, component: str = 'core') -> logging.Logger:
    """
    Get logger for database module component.
    
    Convenience function for obtaining configured loggers.
    
    Args:
        name: Module name (typically __name__)
        component: Component type ('core', 'models', 'migrations')
        
    Returns:
        Configured logger instance
        
    Example:
        from database.core.logger import get_logger
        
        logger = get_logger(__name__, 'models')
        logger.info("Entity created successfully")
    """
    return _database_logger.get_logger(name, component)


def configure_logging(config: Optional[ConfigLoader] = None) -> None:
    """
    Configure database logging system.
    
    Call this once at module initialization.
    
    Args:
        config: Optional ConfigLoader instance
        
    Example:
        from database.core.logger import configure_logging
        
        configure_logging()  # Uses default config
    """
    global _database_logger
    
    if config:
        _database_logger = DatabaseLogger(config)
    
    _database_logger.configure()


__all__ = ['get_logger', 'configure_logging', 'DatabaseLogger']