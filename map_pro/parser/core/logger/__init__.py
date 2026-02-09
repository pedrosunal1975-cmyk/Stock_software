# Path: core/logger/__init__.py
"""
Parser Logging System

Provides two logging configurations:
1. IPO-Aware (setup_ipo_logging): Creates 4 log files (input, process, output, full)
2. Simple (setup_logging): Creates 1 log file (parser.log)

Use IPO-aware for detailed layer separation, or simple for basic logging.

Example (IPO-aware):
    from parser.core.logger import setup_ipo_logging
    from pathlib import Path

    setup_ipo_logging(
        log_dir=Path('/mnt/map_pro/parser/logs'),
        log_level='INFO',
        console_output=True
    )

Example (Simple):
    from parser.core.logger import setup_logging
    from pathlib import Path

    setup_logging(
        log_level='INFO',
        log_file=Path('/mnt/map_pro/parser/logs/parser.log')
    )
"""

# Import from ipo_logging.py (IPO-aware logging)
from .ipo_logging import (
    setup_ipo_logging,
    get_input_logger,
    get_process_logger,
    get_output_logger
)

# Import from logger.py (simple logging)
from .logger import (
    setup_logging,
    get_logger,
    configure_parser_logging
)

__all__ = [
    # IPO-aware logging
    'setup_ipo_logging',
    'get_input_logger',
    'get_process_logger',
    'get_output_logger',
    # Simple logging
    'setup_logging',
    'get_logger',
    'configure_parser_logging'
]
