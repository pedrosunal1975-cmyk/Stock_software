# Path: core/logger/ipo_logging.py
"""
IPO-Aware Logging Configuration

Separates logs by IPO layer:
- INPUT:   Data loading (loaders, CLI)
- PROCESS: Core parsing (xbrl_parser)
- OUTPUT:  Result generation (output)

This preserves the architectural separation while using standard Python logging.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_ipo_logging(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    console_output: bool = True
) -> None:
    """
    Configure logging with INPUT/PROCESS/OUTPUT separation.
    
    Creates separate log files for each IPO layer while using standard
    Python logging throughout the codebase.
    
    Args:
        log_dir: Directory for log files (creates if doesn't exist)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Whether to also log to console
        
    Example:
        from ....core.logger import setup_ipo_logging
        setup_ipo_logging(Path('/mnt/map_pro/parser/logs'))
    """
    level = getattr(logging, log_level.upper())
    
    # Create log directory
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers
    root_logger.handlers = []
    
    # Standard format
    standard_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # IPO-specific formats
    input_format = logging.Formatter(
        '%(asctime)s - [INPUT] %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    process_format = logging.Formatter(
        '%(asctime)s - [PROCESS] %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    output_format = logging.Formatter(
        '%(asctime)s - [OUTPUT] %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (if enabled)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(standard_format)
        root_logger.addHandler(console_handler)
    
    if not log_dir:
        return  # Console only
    
    # =========================================================================
    # INPUT LAYER HANDLER - Captures input.* loggers
    # =========================================================================
    
    input_handler = logging.FileHandler(log_dir / 'input_activity.log')
    input_handler.setLevel(level)
    input_handler.setFormatter(input_format)
    
    # Filter: Only INPUT layer logs
    input_handler.addFilter(lambda record: record.name.startswith('input.'))
    
    # Attach to input logger hierarchy
    input_logger = logging.getLogger('input')
    input_logger.addHandler(input_handler)
    input_logger.setLevel(level)
    
    # =========================================================================
    # PROCESS LAYER HANDLER - Captures xbrl_parser.* loggers
    # =========================================================================
    
    process_handler = logging.FileHandler(log_dir / 'process_activity.log')
    process_handler.setLevel(level)
    process_handler.setFormatter(process_format)
    
    # Filter: Only PROCESS layer logs
    process_handler.addFilter(lambda record: record.name.startswith('xbrl_parser.'))
    
    # Attach to xbrl_parser logger hierarchy
    process_logger = logging.getLogger('xbrl_parser')
    process_logger.addHandler(process_handler)
    process_logger.setLevel(level)
    
    # =========================================================================
    # OUTPUT LAYER HANDLER - Captures output.* loggers
    # =========================================================================
    
    output_handler = logging.FileHandler(log_dir / 'output_activity.log')
    output_handler.setLevel(level)
    output_handler.setFormatter(output_format)
    
    # Filter: Only OUTPUT layer logs
    output_handler.addFilter(lambda record: record.name.startswith('output.'))
    
    # Attach to output logger hierarchy
    output_logger = logging.getLogger('output')
    output_logger.addHandler(output_handler)
    output_logger.setLevel(level)
    
    # =========================================================================
    # FULL ACTIVITY LOG - Everything combined
    # =========================================================================
    
    full_handler = logging.FileHandler(log_dir / 'full_activity.log')
    full_handler.setLevel(level)
    full_handler.setFormatter(standard_format)
    
    # No filter - captures everything
    root_logger.addHandler(full_handler)
    
    logging.info(f"IPO logging configured: {log_dir}")
    logging.info("  - input_activity.log  : INPUT layer (loaders, CLI)")
    logging.info("  - process_activity.log: PROCESS layer (xbrl_parser)")
    logging.info("  - output_activity.log : OUTPUT layer (output)")
    logging.info("  - full_activity.log   : All layers combined")


def get_input_logger(name: str) -> logging.Logger:
    """
    Get logger for INPUT layer module.
    
    Args:
        name: Module name (without 'input.' prefix)
        
    Returns:
        Logger instance under 'input' hierarchy
        
    Example:
        logger = get_input_logger('xbrl_filings')
        # Creates logger named 'input.xbrl_filings'
    """
    return logging.getLogger(f'input.{name}')


def get_process_logger(name: str) -> logging.Logger:
    """
    Get logger for PROCESS layer module.
    
    Args:
        name: Module name (use __name__ from xbrl_parser module)
        
    Returns:
        Logger instance under 'xbrl_parser' hierarchy
        
    Example:
        logger = get_process_logger(__name__)
        # If __name__ = 'xbrl_parser.instance.fact_extractor'
        # Creates logger with that full path
    """
    return logging.getLogger(name)


def get_output_logger(name: str) -> logging.Logger:
    """
    Get logger for OUTPUT layer module.
    
    Args:
        name: Module name (without 'output.' prefix)
        
    Returns:
        Logger instance under 'output' hierarchy
        
    Example:
        logger = get_output_logger('excel_exporter')
        # Creates logger named 'output.excel_exporter'
    """
    return logging.getLogger(f'output.{name}')


__all__ = [
    'setup_ipo_logging',
    'get_input_logger',
    'get_process_logger',
    'get_output_logger'
]