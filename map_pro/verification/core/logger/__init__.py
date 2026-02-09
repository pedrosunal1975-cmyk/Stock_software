# Path: verification/core/logger/__init__.py
"""
Verification Logger Package

IPO-aware logging for the verification module.
"""

from .ipo_logging import (
    setup_ipo_logging,
    get_input_logger,
    get_process_logger,
    get_output_logger,
)

__all__ = [
    'setup_ipo_logging',
    'get_input_logger',
    'get_process_logger',
    'get_output_logger',
]
