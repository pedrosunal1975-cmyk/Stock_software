# Path: mat_acc/core/logger/__init__.py
"""
mat_acc Logger Package

IPO-aware logging for the Mathematical Accountancy system.

Provides separate log streams for:
- INPUT layer (loaders, user input)
- PROCESS layer (calculations, analysis)
- OUTPUT layer (reports, exports)
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
