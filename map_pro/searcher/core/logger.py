# Path: searcher/core/logger.py
"""
Searcher Module Logger

Centralized logging configuration for the searcher module.
Future integration point for system-wide logging.

Architecture:
- Component-based logging (core, engine, markets, cli)
- File and console output
- Configurable log levels
- Structured log format
- IPO (Input-Process-Output) logging support
"""

import logging
from typing import Optional

from .config_loader import ConfigLoader
from ..constants import (
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOGGER_CORE,
    LOGGER_ENGINE,
    LOGGER_MARKETS,
    LOGGER_CLI,
)


class SearcherLogger:
    """
    Centralized logger for searcher module.
    
    Provides component-specific loggers with unified configuration.
    Future integration point for system-wide logging consolidation.
    
    Example:
        logger = get_logger(__name__, 'engine')
        logger.info("[INPUT] Searching for company filings")
        logger.info("[PROCESS] Calling SEC API")
        logger.info("[OUTPUT] Found 15 filings")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize searcher logger.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self._configured = False
    
    def configure(self) -> None:
        """Configure logging system for searcher module."""
        if self._configured:
            return
        
        # Get configuration
        log_dir = self.config.get('searcher_log_dir')
        log_level = self.config.get('log_level', 'INFO')
        console_output = self.config.get('log_console', True)
        
        # Create log directory if needed
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger for searcher module
        logger = logging.getLogger('searcher')
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # File handler for all searcher logs
        if log_dir:
            log_file = log_dir / 'searcher_activity.log'
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
            )
            logger.addHandler(file_handler)
            
            # Additional API-specific log file
            api_log_file = log_dir / 'api_calls.log'
            api_handler = logging.FileHandler(api_log_file)
            api_handler.setLevel(logging.DEBUG)
            api_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
            )
            # Only add to markets logger
            markets_logger = logging.getLogger(LOGGER_MARKETS)
            markets_logger.addHandler(api_handler)
            
            # Error-only log file
            error_log_file = log_dir / 'errors.log'
            error_handler = logging.FileHandler(error_log_file)
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
            )
            logger.addHandler(error_handler)
        
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
            component: Component type ('core', 'engine', 'markets', 'cli')
            
        Returns:
            Configured logger instance
        """
        # Ensure logging is configured
        if not self._configured:
            self.configure()
        
        # Build logger name
        if component == 'core':
            logger_name = f"{LOGGER_CORE}.{name}"
        elif component == 'engine':
            logger_name = f"{LOGGER_ENGINE}.{name}"
        elif component == 'markets':
            logger_name = f"{LOGGER_MARKETS}.{name}"
        elif component == 'cli':
            logger_name = f"{LOGGER_CLI}.{name}"
        else:
            logger_name = f"searcher.{name}"
        
        return logging.getLogger(logger_name)


# Global logger instance
_searcher_logger = SearcherLogger()


def get_logger(name: str, component: str = 'core') -> logging.Logger:
    """
    Get logger for searcher module component.
    
    Convenience function for obtaining configured loggers.
    
    Args:
        name: Module name (typically __name__)
        component: Component type ('core', 'engine', 'markets', 'cli')
        
    Returns:
        Configured logger instance
        
    Example:
        from searcher.core.logger import get_logger
        
        logger = get_logger(__name__, 'engine')
        logger.info("[INPUT] Starting search operation")
        logger.info("[PROCESS] Calling market API")
        logger.info("[OUTPUT] Search completed successfully")
    """
    return _searcher_logger.get_logger(name, component)


def configure_logging(config: Optional[ConfigLoader] = None) -> None:
    """
    Configure searcher logging system.
    
    Call this once at module initialization.
    
    Args:
        config: Optional ConfigLoader instance
        
    Example:
        from searcher.core.logger import configure_logging
        
        configure_logging()  # Uses default config
    """
    global _searcher_logger
    
    if config:
        _searcher_logger = SearcherLogger(config)
    
    _searcher_logger.configure()


__all__ = ['get_logger', 'configure_logging', 'SearcherLogger']