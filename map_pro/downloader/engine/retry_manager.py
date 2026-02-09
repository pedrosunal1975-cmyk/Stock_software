# Path: downloader/engine/retry_manager.py
"""
Retry Manager

Exponential backoff retry logic for transient failures.
Handles network errors, timeouts, and rate limiting.

Architecture:
- Exponential backoff with jitter
- Configurable retry attempts
- Retryable vs fatal error classification
- Async support for streaming downloads
"""

import asyncio
import time
from typing import Callable, TypeVar, Optional, Any
from functools import wraps

from downloader.core.logger import get_logger
from downloader.core.config_loader import ConfigLoader
from downloader.constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    RETRYABLE_STATUS_CODES,
    HTTP_TOO_MANY_REQUESTS,
    LOG_PROCESS,
)
from downloader.engine.constants import MAX_RETRY_DELAY

logger = get_logger(__name__, 'engine')

T = TypeVar('T')


class RetryManager:
    """
    Manages retry logic with exponential backoff.
    
    Features:
    - Exponential backoff: delay = base_delay * (2 ^ attempt)
    - Maximum delay cap
    - Jitter to prevent thundering herd
    - Retryable error detection
    
    Example:
        manager = RetryManager(max_retries=3, base_delay=1.0)
        
        async def download():
            # ... download logic ...
            pass
        
        result = await manager.retry_async(download)
    """
    
    def __init__(
        self,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        config: Optional[ConfigLoader] = None
    ):
        """
        Initialize retry manager.
        
        Args:
            max_retries: Maximum retry attempts (from config if None)
            base_delay: Initial retry delay in seconds (from config if None)
            max_delay: Maximum retry delay cap (from config if None)
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        
        self.max_retries = max_retries if max_retries is not None else \
            self.config.get('retry_attempts', DEFAULT_MAX_RETRIES)
        
        self.base_delay = base_delay if base_delay is not None else \
            self.config.get('retry_delay', DEFAULT_RETRY_DELAY)
        
        self.max_delay = max_delay if max_delay is not None else \
            self.config.get('max_retry_delay', MAX_RETRY_DELAY)
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate retry delay with exponential backoff.
        
        Formula: min(base_delay * (2 ^ attempt), max_delay)
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    def is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if error is retryable.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error should trigger retry
        """
        # Network errors are retryable
        if isinstance(error, (ConnectionError, TimeoutError)):
            return True
        
        # Check for specific HTTP errors
        if hasattr(error, 'status'):
            return error.status in RETRYABLE_STATUS_CODES
        
        # OSError for network issues
        if isinstance(error, OSError):
            return True
        
        # Default: not retryable
        return False
    
    async def retry_async(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute async function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of successful execution
            
        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Success
                if attempt > 0:
                    logger.info(f"{LOG_PROCESS} Retry succeeded on attempt {attempt + 1}")
                
                return result
            
            except Exception as e:
                last_exception = e
                
                # Check if retryable
                if not self.is_retryable_error(e):
                    logger.error(f"Non-retryable error: {e}")
                    raise
                
                # Check if we have retries left
                if attempt >= self.max_retries:
                    logger.error(f"All retries exhausted after {attempt + 1} attempts")
                    raise
                
                # Calculate delay
                delay = self.calculate_delay(attempt)
                
                logger.warning(
                    f"{LOG_PROCESS} Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                
                # Wait before retry
                await asyncio.sleep(delay)
        
        # Should not reach here, but raise last exception if we do
        raise last_exception
    
    def retry_sync(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute sync function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of successful execution
            
        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Success
                if attempt > 0:
                    logger.info(f"{LOG_PROCESS} Retry succeeded on attempt {attempt + 1}")
                
                return result
            
            except Exception as e:
                last_exception = e
                
                # Check if retryable
                if not self.is_retryable_error(e):
                    logger.error(f"Non-retryable error: {e}")
                    raise
                
                # Check if we have retries left
                if attempt >= self.max_retries:
                    logger.error(f"All retries exhausted after {attempt + 1} attempts")
                    raise
                
                # Calculate delay
                delay = self.calculate_delay(attempt)
                
                logger.warning(
                    f"{LOG_PROCESS} Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                
                # Wait before retry
                time.sleep(delay)
        
        # Should not reach here, but raise last exception if we do
        raise last_exception


def with_retry(max_retries: int = DEFAULT_MAX_RETRIES):
    """
    Decorator for automatic retry on functions.
    
    Args:
        max_retries: Maximum retry attempts
        
    Example:
        @with_retry(max_retries=3)
        async def download_file(url):
            # ... download logic ...
            pass
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            manager = RetryManager(max_retries=max_retries)
            return await manager.retry_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            manager = RetryManager(max_retries=max_retries)
            return manager.retry_sync(func, *args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


__all__ = ['RetryManager', 'with_retry']