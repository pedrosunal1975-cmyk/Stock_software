# Path: core/logger/__init__.py
"""
Logging Module

IPO-aware logging system for the XBRL Mapper.

Provides Input-Process-Output separated logging with 4 log files:
- input_activity.log (loaders, CLI)
- process_activity.log (mapping engine)
- output_activity.log (exporters)
- full_activity.log (all combined)

Example:
    from ...core.logger import setup_ipo_logging
    
    # Setup logging
    setup_ipo_logging(
        log_dir=Path('/mnt/map_pro/mapper/logs'),
        log_level='INFO',
        console_output=True
    )
    
    # Use loggers
    logger = logging.getLogger('input.parser_output')
    logger.info("Loading parsed.json file")
"""

from ...core.logger.ipo_logging import (
    setup_ipo_logging,
    get_input_logger,
    get_process_logger,
    get_output_logger
)

__all__ = [
    'setup_ipo_logging',
    'get_input_logger',
    'get_process_logger',
    'get_output_logger',
]