# Path: core/logger.py
"""
Map Pro Core Logger

Centralized logging system for the Map Pro application.
Designed to be the future head of all module loggers.

Architecture:
- Root logger configuration for entire application
- Component registration system for module loggers
- Unified log format across all modules
- Console and file output with configurable levels
- Future integration point for all module loggers

Current Scope:
- Application startup/shutdown logging
- Core initialization events
- System-wide error capture

Future Vision:
- Central registry for all module loggers
- Unified log aggregation
- Log routing and filtering
- Performance metrics logging
- Structured logging (JSON) support

Note:
    Module-specific logging is currently handled by each module's
    logger.py file. This core logger will eventually coordinate
    all module loggers for unified logging management.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Set

from core.config_loader import CoreConfigLoader, get_core_config


# Log format constants
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Application log file name
APP_LOG_FILE = 'map_pro.log'
STARTUP_LOG_FILE = 'startup.log'

# Logger hierarchy
LOGGER_ROOT = 'map_pro'
LOGGER_CORE = 'map_pro.core'
LOGGER_STARTUP = 'map_pro.startup'


class MapProLogger:
    """
    Central logging manager for Map Pro application.

    Provides unified logging configuration and serves as the
    future integration point for all module loggers.

    Features:
    - Application-wide logging configuration
    - Startup/shutdown event logging
    - Component registration for future module integration
    - File and console output

    Future Features:
    - Module logger registration and coordination
    - Log level management per module
    - Log aggregation and routing
    - Structured logging support

    Example:
        logger = get_app_logger()
        logger.info("Application starting")

        # Component logging
        component_logger = get_component_logger('database')
        component_logger.info("Database initialized")
    """

    def __init__(self, config: Optional[CoreConfigLoader] = None):
        """
        Initialize Map Pro logger.

        Args:
            config: Optional CoreConfigLoader instance
        """
        self.config = config if config else get_core_config()
        self._configured = False
        self._registered_components: Set[str] = set()
        self._startup_time: Optional[datetime] = None

    def configure(self, log_level: str = 'INFO', console: bool = True) -> None:
        """
        Configure the logging system.

        Sets up root logger, file handlers, and console output.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console: Whether to output to console
        """
        if self._configured:
            return

        self._startup_time = datetime.now()

        # Get log directory from config
        log_dir = self.config.get('log_dir')

        # Create log directory if needed
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)

        # Configure root application logger
        root_logger = logging.getLogger(LOGGER_ROOT)
        root_logger.setLevel(getattr(logging, log_level.upper()))

        # Clear any existing handlers
        root_logger.handlers.clear()

        # Prevent propagation to root logger
        root_logger.propagate = False

        # File handler for application logs
        if log_dir:
            app_log_file = log_dir / APP_LOG_FILE
            file_handler = logging.FileHandler(app_log_file)
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
            )
            root_logger.addHandler(file_handler)

            # Separate startup log
            startup_log_file = log_dir / STARTUP_LOG_FILE
            startup_handler = logging.FileHandler(startup_log_file)
            startup_handler.setLevel(logging.INFO)
            startup_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
            )

            startup_logger = logging.getLogger(LOGGER_STARTUP)
            startup_logger.addHandler(startup_handler)
            startup_logger.propagate = True

        # Console handler
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_level.upper()))
            console_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
            )
            root_logger.addHandler(console_handler)

        self._configured = True

        # Log startup
        startup_logger = self.get_startup_logger()
        startup_logger.info("=" * 70)
        startup_logger.info("MAP PRO APPLICATION STARTING")
        startup_logger.info(f"Startup time: {self._startup_time.isoformat()}")
        startup_logger.info("=" * 70)

    def get_logger(self, name: str = '') -> logging.Logger:
        """
        Get application logger.

        Args:
            name: Optional logger name suffix

        Returns:
            Configured logger instance
        """
        if not self._configured:
            self.configure()

        if name:
            return logging.getLogger(f"{LOGGER_ROOT}.{name}")
        return logging.getLogger(LOGGER_ROOT)

    def get_startup_logger(self) -> logging.Logger:
        """
        Get startup-specific logger.

        Returns:
            Logger for startup events
        """
        if not self._configured:
            self.configure()

        return logging.getLogger(LOGGER_STARTUP)

    def get_core_logger(self) -> logging.Logger:
        """
        Get core module logger.

        Returns:
            Logger for core module events
        """
        if not self._configured:
            self.configure()

        return logging.getLogger(LOGGER_CORE)

    def register_component(self, component_name: str) -> logging.Logger:
        """
        Register a component logger.

        Future integration point for module loggers.
        Registers the component and returns a configured logger.

        Args:
            component_name: Name of the component (e.g., 'database', 'searcher')

        Returns:
            Configured logger for the component
        """
        if not self._configured:
            self.configure()

        self._registered_components.add(component_name)

        logger = logging.getLogger(f"{LOGGER_ROOT}.{component_name}")

        # Log registration
        startup_logger = self.get_startup_logger()
        startup_logger.info(f"Component registered: {component_name}")

        return logger

    def get_registered_components(self) -> List[str]:
        """
        Get list of registered components.

        Returns:
            List of registered component names
        """
        return list(self._registered_components)

    def log_startup_complete(self) -> None:
        """Log that startup is complete."""
        if self._startup_time:
            elapsed = datetime.now() - self._startup_time
            startup_logger = self.get_startup_logger()
            startup_logger.info("-" * 70)
            startup_logger.info("STARTUP COMPLETE")
            startup_logger.info(f"Elapsed time: {elapsed.total_seconds():.2f} seconds")
            startup_logger.info(f"Components registered: {len(self._registered_components)}")
            for component in sorted(self._registered_components):
                startup_logger.info(f"  - {component}")
            startup_logger.info("-" * 70)

    def log_shutdown(self) -> None:
        """Log application shutdown."""
        startup_logger = self.get_startup_logger()
        startup_logger.info("=" * 70)
        startup_logger.info("MAP PRO APPLICATION SHUTTING DOWN")
        startup_logger.info(f"Shutdown time: {datetime.now().isoformat()}")
        if self._startup_time:
            uptime = datetime.now() - self._startup_time
            startup_logger.info(f"Total uptime: {uptime}")
        startup_logger.info("=" * 70)


# Global logger instance
_app_logger: Optional[MapProLogger] = None


def get_map_pro_logger() -> MapProLogger:
    """
    Get global Map Pro logger instance.

    Returns:
        MapProLogger instance
    """
    global _app_logger
    if _app_logger is None:
        _app_logger = MapProLogger()
    return _app_logger


def get_app_logger(name: str = '') -> logging.Logger:
    """
    Get application logger.

    Convenience function for obtaining application logger.

    Args:
        name: Optional logger name suffix

    Returns:
        Configured logger instance

    Example:
        from core.logger import get_app_logger

        logger = get_app_logger('my_module')
        logger.info("Module initialized")
    """
    return get_map_pro_logger().get_logger(name)


def get_startup_logger() -> logging.Logger:
    """
    Get startup logger.

    Returns:
        Logger for startup events
    """
    return get_map_pro_logger().get_startup_logger()


def configure_logging(log_level: str = 'INFO', console: bool = True) -> None:
    """
    Configure application logging.

    Call this once at application startup.

    Args:
        log_level: Logging level
        console: Whether to output to console

    Example:
        from core.logger import configure_logging

        configure_logging(log_level='DEBUG', console=True)
    """
    get_map_pro_logger().configure(log_level=log_level, console=console)


def log_startup_complete() -> None:
    """Log that application startup is complete."""
    get_map_pro_logger().log_startup_complete()


def log_shutdown() -> None:
    """Log application shutdown."""
    get_map_pro_logger().log_shutdown()


__all__ = [
    'MapProLogger',
    'get_map_pro_logger',
    'get_app_logger',
    'get_startup_logger',
    'configure_logging',
    'log_startup_complete',
    'log_shutdown',
]
