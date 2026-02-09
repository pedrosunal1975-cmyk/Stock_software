# Path: core/logger/logger.py
"""
Logging Configuration

Simple centralized logging setup for XBRL parser.
Uses standard Python logging throughout.

Example:
    from parser.core.logger import setup_logging, get_logger
    from pathlib import Path

    # Configure once at startup
    setup_logging(log_level="INFO", log_file=Path("/mnt/map_pro/parser/logs/parser.log"))

    # Use in any module
    logger = get_logger(__name__)
    logger.info("Processing started")
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from ..config_loader import ConfigLoader


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    log_format: Optional[str] = None,
    config: Optional[ConfigLoader] = None
) -> None:
    """
    Configure logging for XBRL parser.
    
    This should be called once at application startup.
    All modules will then use logging.getLogger(__name__).
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        log_format: Optional custom log format
        config: Optional configuration loader (for reading settings)
        
    Example:
        setup_logging(
            log_level="DEBUG",
            log_file=Path("/mnt/map_pro/parser/logs/parser.log")
        )
    """
    # Load from config if provided
    if config:
        log_level = config.get('log_level', log_level)
        log_file_path = config.get('log_file')
        if log_file_path and not log_file:
            log_file = Path(log_file_path)
    
    # Default format
    if log_format is None:
        log_format = (
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Convert log level string to constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Add file handler if specified
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)
        
        logging.info(f"Logging to file: {log_file}")
    
    logging.info(f"Logging configured: level={log_level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get logger for module.
    
    This is a convenience wrapper around logging.getLogger().
    
    Args:
        name: Module name (use __name__)
        
    Returns:
        Logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Processing started")
        logger.debug("Detail: %s", detail)
        logger.warning("Issue detected: %s", issue)
        logger.error("Failed: %s", error)
    """
    return logging.getLogger(name)


def configure_parser_logging(config: ConfigLoader) -> None:
    """
    Configure logging for parser from config.
    
    Convenience function that reads settings from config
    and calls setup_logging().
    
    Args:
        config: Configuration loader
        
    Example:
        config = ConfigLoader()
        configure_parser_logging(config)
    """
    setup_logging(
        log_level=config.get('log_level', 'INFO'),
        log_file=Path(config.get('log_file')) if config.get('log_file') else None,
        config=config
    )


__all__ = ['setup_logging', 'get_logger', 'configure_parser_logging']