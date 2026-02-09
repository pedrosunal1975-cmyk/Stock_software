# Path: mat_acc/core/logger/ipo_logging.py
"""
IPO-Aware Logging for mat_acc (Mathematical Accountancy)

Input-Process-Output separated logging for financial analysis.

This module sets up logging with separate files for:
- INPUT layer (loaders, CLI, user input)
- PROCESS layer (calculations, ratio engine, hierarchy builder)
- OUTPUT layer (reporters, exporters, graph generators)
- Full activity (everything combined)
"""

import logging
import sys
from pathlib import Path


class IPOFilter(logging.Filter):
    """Filter logs by IPO layer prefix."""

    def __init__(self, layer: str):
        """
        Initialize filter for specific IPO layer.

        Args:
            layer: 'input', 'process', or 'output'
        """
        super().__init__()
        self.layer = layer

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter records by logger name prefix."""
        return record.name.startswith(self.layer)


def setup_ipo_logging(
    log_dir: Path,
    log_level: str = 'INFO',
    console_output: bool = True
) -> None:
    """
    Set up IPO-aware logging for mat_acc.

    Creates separate log files for:
    - input_activity.log (INPUT layer)
    - process_activity.log (PROCESS/calculation layer)
    - output_activity.log (OUTPUT layer)
    - full_activity.log (all activities combined)

    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Whether to also output to console

    Example:
        setup_ipo_logging(
            log_dir=Path('/mnt/mat_acc/logs'),
            log_level='INFO',
            console_output=True
        )
    """
    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Standard format
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Full activity log (everything)
    full_handler = logging.FileHandler(log_dir / 'full_activity.log')
    full_handler.setLevel(logging.DEBUG)
    full_handler.setFormatter(formatter)
    root_logger.addHandler(full_handler)

    # INPUT layer log
    input_handler = logging.FileHandler(log_dir / 'input_activity.log')
    input_handler.setLevel(logging.DEBUG)
    input_handler.setFormatter(formatter)
    input_handler.addFilter(IPOFilter('input'))
    root_logger.addHandler(input_handler)

    # PROCESS layer log (calculation engine)
    process_handler = logging.FileHandler(log_dir / 'process_activity.log')
    process_handler.setLevel(logging.DEBUG)
    process_handler.setFormatter(formatter)
    process_handler.addFilter(IPOFilter('process'))
    root_logger.addHandler(process_handler)

    # OUTPUT layer log
    output_handler = logging.FileHandler(log_dir / 'output_activity.log')
    output_handler.setLevel(logging.DEBUG)
    output_handler.setFormatter(formatter)
    output_handler.addFilter(IPOFilter('output'))
    root_logger.addHandler(output_handler)

    # Console output (optional)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        # Simpler format for console
        console_formatter = logging.Formatter(
            '[%(levelname)s] %(name)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)


def get_input_logger(name: str) -> logging.Logger:
    """
    Get logger for INPUT layer.

    Args:
        name: Logger name (e.g., 'verification_loader', 'user_input')

    Returns:
        Logger configured for INPUT layer

    Example:
        logger = get_input_logger('verification_loader')
        logger.info("Loading verification reports")
    """
    return logging.getLogger(f'input.{name}')


def get_process_logger(name: str) -> logging.Logger:
    """
    Get logger for PROCESS layer (calculation engine).

    Args:
        name: Logger name (e.g., 'ratio_calculator', 'hierarchy_builder')

    Returns:
        Logger configured for PROCESS layer

    Example:
        logger = get_process_logger('ratio_calculator')
        logger.info("Calculating financial ratios")
    """
    return logging.getLogger(f'process.{name}')


def get_output_logger(name: str) -> logging.Logger:
    """
    Get logger for OUTPUT layer.

    Args:
        name: Logger name (e.g., 'report_generator', 'excel_exporter')

    Returns:
        Logger configured for OUTPUT layer

    Example:
        logger = get_output_logger('report_generator')
        logger.info("Generating analysis report")
    """
    return logging.getLogger(f'output.{name}')


__all__ = [
    'setup_ipo_logging',
    'get_input_logger',
    'get_process_logger',
    'get_output_logger',
]
