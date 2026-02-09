# Path: downloader/core/logger.py
"""
Downloader Module Logger

Centralized logging configuration for the downloader module.
Future integration point for system-wide logging.

Architecture:
- Component-based logging (core, engine, cli, extraction)
- File and console output
- Configurable log levels
- IPO (Input-Process-Output) structured logging
"""

import logging
from typing import Optional

from downloader.core.config_loader import ConfigLoader
from downloader.constants import (
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOGGER_CORE,
    LOGGER_ENGINE,
    LOGGER_CLI,
    LOGGER_EXTRACTION,
)


class DownloaderLogger:
    """
    Centralized logger for downloader module.
    
    Provides component-specific loggers with unified configuration.
    
    Example:
        logger = get_logger(__name__, 'engine')
        logger.info("[INPUT] Starting download for filing XYZ")
        logger.info("[PROCESS] Downloading chunk 1/100")
        logger.info("[OUTPUT] Download completed: 10MB in 5s")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize downloader logger.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self._configured = False
    
    def configure(self) -> None:
        """Configure logging system for downloader module."""
        if self._configured:
            return
        
        # Get configuration
        log_dir = self.config.get('downloader_log_dir')
        log_level = self.config.get('log_level', 'INFO')
        console_output = self.config.get('log_console', True)
        
        # Create log directory if needed
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger for downloader module
        logger = logging.getLogger('downloader')
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # File handler for all downloader logs
        if log_dir:
            log_file = log_dir / 'downloader_activity.log'
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
            )
            logger.addHandler(file_handler)
            
            # Download-specific log file
            download_log_file = log_dir / 'downloads.log'
            download_handler = logging.FileHandler(download_log_file)
            download_handler.setLevel(logging.DEBUG)
            download_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
            )
            # Add to engine logger
            engine_logger = logging.getLogger(LOGGER_ENGINE)
            engine_logger.addHandler(download_handler)
            
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
            component: Component type ('core', 'engine', 'cli', 'extraction')
            
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
        elif component == 'cli':
            logger_name = f"{LOGGER_CLI}.{name}"
        elif component == 'extraction':
            logger_name = f"{LOGGER_EXTRACTION}.{name}"
        else:
            logger_name = f"downloader.{name}"
        
        return logging.getLogger(logger_name)


# Global logger instance
_downloader_logger = DownloaderLogger()


def get_logger(name: str, component: str = 'core') -> logging.Logger:
    """
    Get logger for downloader module component.
    
    Convenience function for obtaining configured loggers.
    
    Args:
        name: Module name (typically __name__)
        component: Component type ('core', 'engine', 'cli', 'extraction')
        
    Returns:
        Configured logger instance
        
    Example:
        from downloader.core.logger import get_logger
        
        logger = get_logger(__name__, 'engine')
        logger.info("[INPUT] Processing filing download request")
        logger.info("[PROCESS] Downloading ZIP file")
        logger.info("[OUTPUT] Download completed successfully")
    """
    return _downloader_logger.get_logger(name, component)


def configure_logging(config: Optional[ConfigLoader] = None) -> None:
    """
    Configure downloader logging system.
    
    Call this once at module initialization.
    
    Args:
        config: Optional ConfigLoader instance
        
    Example:
        from downloader.core.logger import configure_logging
        
        configure_logging()  # Uses default config
    """
    global _downloader_logger
    
    if config:
        _downloader_logger = DownloaderLogger(config)
    
    _downloader_logger.configure()


__all__ = ['get_logger', 'configure_logging', 'DownloaderLogger']