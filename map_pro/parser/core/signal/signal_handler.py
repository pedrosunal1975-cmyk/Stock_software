# Path: core/signal/signal_handler.py
"""
Signal Handler

Handles system signals for graceful shutdown during long-running operations.

This module provides signal handling for SIGINT (Ctrl+C) and SIGTERM,
allowing the parser to clean up resources and save state before exiting.
"""

import signal
import logging
import sys
from typing import Optional
from types import FrameType


class SignalHandler:
    """
    Signal handler for graceful shutdown.
    
    Intercepts SIGINT and SIGTERM signals to allow cleanup before exit.
    Useful for long-running parsing operations that may be interrupted.
    
    Example:
        handler = SignalHandler(cleanup_func)
        handler.register()
        
        # Long operation here
        
        if handler.interrupted:
            print("Operation was interrupted")
    """
    
    def __init__(self, cleanup_callback: Optional[Callable] = None):
        """
        Initialize signal handler.
        
        Args:
            cleanup_callback: Optional function to call on interrupt
        """
        self.cleanup_callback = cleanup_callback
        self.interrupted = False
        self.original_sigint: any = None
        self.original_sigterm: any = None
        self.logger = logging.getLogger(__name__)
    
    def register(self) -> None:
        """
        Register signal handlers.
        
        Replaces default signal handlers with graceful shutdown handlers.
        Stores original handlers for restoration.
        """
        self.original_sigint = signal.signal(signal.SIGINT, self._handle_signal)
        self.original_sigterm = signal.signal(signal.SIGTERM, self._handle_signal)
        self.logger.debug("Signal handlers registered")
    
    def unregister(self) -> None:
        """
        Restore original signal handlers.
        
        Returns signal handling to original state.
        """
        if self.original_sigint:
            signal.signal(signal.SIGINT, self.original_sigint)
        if self.original_sigterm:
            signal.signal(signal.SIGTERM, self.original_sigterm)
        self.logger.debug("Signal handlers restored")
    
    def _handle_signal(self, signum: int, frame: Optional[FrameType]) -> None:
        """
        Handle interrupt signal.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        self.logger.info(f"Received {signal_name}, initiating graceful shutdown")
        
        # Mark as interrupted
        self.interrupted = True
        
        # Call cleanup callback if provided
        if self.cleanup_callback:
            try:
                self.logger.debug("Executing cleanup callback")
                self.cleanup_callback()
            except Exception as e:
                self.logger.error(f"Cleanup callback failed: {e}")
        
        # Exit gracefully
        self.logger.info("Shutdown complete")
        sys.exit(0)
    
    def check_interrupted(self) -> bool:
        """
        Check if operation was interrupted.
        
        Returns:
            True if interrupt signal received
        """
        return self.interrupted
    
    def __enter__(self):
        """Context manager entry."""
        self.register()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.unregister()
        return False


class InterruptibleOperation:
    """
    Context manager for interruptible long operations.
    
    Automatically registers signal handlers and checks for interruption.
    
    Example:
        with InterruptibleOperation() as op:
            for item in large_dataset:
                if op.interrupted:
                    print("Interrupted, stopping...")
                    break
                # Process item
    """
    
    def __init__(self, cleanup_callback: Optional[Callable] = None):
        """
        Initialize interruptible operation.
        
        Args:
            cleanup_callback: Optional cleanup function
        """
        self.handler = SignalHandler(cleanup_callback)
        self.interrupted = False
    
    def __enter__(self):
        """Enter context and register handlers."""
        self.handler.register()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and unregister handlers."""
        self.handler.unregister()
        self.interrupted = self.handler.interrupted
        return False


def install_signal_handler(cleanup_callback: Optional[Callable] = None) -> SignalHandler:
    """
    Install global signal handler.
    
    Convenience function to register signal handlers for graceful shutdown.
    
    Args:
        cleanup_callback: Optional function to call on interrupt
        
    Returns:
        SignalHandler instance
        
    Example:
        handler = install_signal_handler(lambda: print("Cleaning up..."))
        
        # Long operation
        
        if handler.interrupted:
            print("Was interrupted")
    """
    handler = SignalHandler(cleanup_callback)
    handler.register()
    return handler


__all__ = [
    'SignalHandler',
    'InterruptibleOperation',
    'install_signal_handler',
]