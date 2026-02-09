# Path: core/signal/__init__.py
"""
Signal Handling Module

Provides graceful shutdown handling for long-running operations.
"""

from ....core.signal.signal_handler import (
    SignalHandler,
    InterruptibleOperation,
    install_signal_handler,
)

__all__ = [
    'SignalHandler',
    'InterruptibleOperation',
    'install_signal_handler',
]