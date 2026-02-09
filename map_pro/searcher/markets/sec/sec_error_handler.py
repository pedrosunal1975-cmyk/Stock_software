# Path: searcher/markets/sec/sec_error_handler.py
"""
SEC API Error Handler

Handles HTTP errors and retry logic for SEC EDGAR API requests.
Separates error handling concerns from HTTP client logic.

Responsibilities:
- Process HTTP error status codes
- Classify and log errors appropriately
- Determine retry-ability of errors
- Generate user-friendly error messages
"""

import asyncio
from typing import Optional
import aiohttp

from searcher.core.logger import get_logger
from searcher.markets.sec.constants import (
    HTTP_BAD_REQUEST,
    HTTP_UNAUTHORIZED,
    HTTP_FORBIDDEN,
    HTTP_NOT_FOUND,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_BAD_GATEWAY,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_GATEWAY_TIMEOUT,
)

logger = get_logger(__name__, 'markets')


class ErrorSeverity:
    """Classification of error severity levels."""
    FATAL = 'fatal'          # Don't retry (404, invalid request)
    TRANSIENT = 'transient'  # Retry possible (network, timeout)
    UNKNOWN = 'unknown'      # Unknown error type


class SECErrorHandler:
    """
    Handler for SEC API HTTP errors and retry logic.
    
    Handles:
    - HTTP status code processing
    - Error classification by severity
    - Error logging and user messaging
    
    Example:
        handler = SECErrorHandler()
        
        try:
            # ... API call ...
        except aiohttp.ClientError as e:
            severity = handler.classify_error_severity(e)
            if severity == ErrorSeverity.FATAL:
                # Don't retry
                pass
            elif severity == ErrorSeverity.TRANSIENT:
                # Retry
                pass
    """
    
    # HTTP status codes (from constants)
    STATUS_NOT_FOUND = HTTP_NOT_FOUND
    STATUS_BAD_REQUEST = HTTP_BAD_REQUEST
    STATUS_UNAUTHORIZED = HTTP_UNAUTHORIZED
    STATUS_FORBIDDEN = HTTP_FORBIDDEN
    STATUS_TOO_MANY_REQUESTS = HTTP_TOO_MANY_REQUESTS
    STATUS_SERVER_ERROR = HTTP_INTERNAL_SERVER_ERROR

    # Error messages
    ERROR_MESSAGES = {
        HTTP_BAD_REQUEST: "Bad Request - Invalid request parameters",
        HTTP_UNAUTHORIZED: "Unauthorized - Authentication required",
        HTTP_FORBIDDEN: "Forbidden - Access denied",
        HTTP_NOT_FOUND: "Not Found - Resource does not exist",
        HTTP_TOO_MANY_REQUESTS: "Too Many Requests - Rate limit exceeded",
        HTTP_INTERNAL_SERVER_ERROR: "Server Error - SEC server error",
        HTTP_BAD_GATEWAY: "Bad Gateway - SEC service unavailable",
        HTTP_SERVICE_UNAVAILABLE: "Service Unavailable - SEC service temporarily unavailable",
    }
    
    def __init__(self):
        """Initialize SEC error handler."""
        self.logger = logger
    
    def get_error_message(self, status_code: int) -> str:
        """
        Get error message for HTTP status code.
        
        Args:
            status_code: HTTP status code
            
        Returns:
            Error message string
        """
        return self.ERROR_MESSAGES.get(
            status_code,
            f"HTTP Error {status_code}"
        )
    
    def is_fatal_error(self, status_code: int) -> bool:
        """
        Check if error is fatal (should not retry).
        
        Args:
            status_code: HTTP status code
            
        Returns:
            True if error is fatal
        """
        fatal_codes = {
            self.STATUS_NOT_FOUND,
            self.STATUS_BAD_REQUEST,
            self.STATUS_UNAUTHORIZED,
            self.STATUS_FORBIDDEN,
        }
        return status_code in fatal_codes
    
    def is_retryable_error(self, status_code: int) -> bool:
        """
        Check if error is retryable.
        
        Args:
            status_code: HTTP status code
            
        Returns:
            True if error can be retried
        """
        retryable_codes = {
            self.STATUS_TOO_MANY_REQUESTS,
            self.STATUS_SERVER_ERROR,
            HTTP_BAD_GATEWAY,
            HTTP_SERVICE_UNAVAILABLE,
            HTTP_GATEWAY_TIMEOUT,
        }
        return status_code in retryable_codes
    
    def classify_error_severity(self, error: Exception) -> str:
        """
        Classify error by severity.
        
        Args:
            error: Exception to classify
            
        Returns:
            Error severity string (ErrorSeverity enum value)
        """
        # File not found errors are fatal
        if isinstance(error, FileNotFoundError):
            return ErrorSeverity.FATAL
        
        # Network and timeout errors are transient
        if isinstance(error, (asyncio.TimeoutError, aiohttp.ClientError)):
            return ErrorSeverity.TRANSIENT
        
        # Unknown error type
        return ErrorSeverity.UNKNOWN
    
    def should_retry_error(self, error: Exception) -> bool:
        """
        Determine if error should be retried.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error should be retried
        """
        severity = self.classify_error_severity(error)
        return severity == ErrorSeverity.TRANSIENT
    
    def log_error(
        self,
        error: Exception,
        context: str,
        severity: Optional[str] = None
    ) -> None:
        """
        Log error with appropriate level and context.
        
        Args:
            error: Exception to log
            context: Context string describing what failed
            severity: Optional severity override
        """
        if severity is None:
            severity = self.classify_error_severity(error)
        
        error_msg = f"{context}: {error}"
        
        if severity == ErrorSeverity.FATAL:
            self.logger.error(error_msg)
        elif severity == ErrorSeverity.TRANSIENT:
            self.logger.warning(error_msg)
        else:
            self.logger.error(error_msg)
    
    def build_error_info(
        self,
        error: Exception,
        context: str
    ) -> dict[str, any]:
        """
        Build structured error information.
        
        Args:
            error: Exception
            context: Context string
            
        Returns:
            Dictionary with error details
        """
        severity = self.classify_error_severity(error)
        retryable = self.should_retry_error(error)
        
        return {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'severity': severity,
            'retryable': retryable,
            'is_fatal': severity == ErrorSeverity.FATAL,
        }
    
    async def handle_api_error(
        self,
        error: Exception,
        context: str,
        log_error: bool = True
    ) -> dict[str, any]:
        """
        Handle API error with logging and classification.
        
        Args:
            error: Exception to handle
            context: Context string
            log_error: Whether to log the error
            
        Returns:
            Error information dictionary
        """
        error_info = self.build_error_info(error, context)
        
        if log_error:
            self.log_error(error, context, error_info['severity'])
        
        return error_info
    
    def handle_status_code_error(
        self,
        status_code: int,
        url: str
    ) -> dict[str, any]:
        """
        Handle HTTP status code error.
        
        Args:
            status_code: HTTP status code
            url: Request URL
            
        Returns:
            Error information dictionary
        """
        error_message = self.get_error_message(status_code)
        is_fatal = self.is_fatal_error(status_code)
        is_retryable = self.is_retryable_error(status_code)
        
        # Log error
        if is_fatal:
            self.logger.error(f"Fatal HTTP error {status_code}: {error_message} - {url}")
        elif is_retryable:
            self.logger.warning(f"Retryable HTTP error {status_code}: {error_message} - {url}")
        else:
            self.logger.error(f"HTTP error {status_code}: {error_message} - {url}")
        
        return {
            'status_code': status_code,
            'error_message': error_message,
            'url': url,
            'is_fatal': is_fatal,
            'is_retryable': is_retryable,
        }


__all__ = ['SECErrorHandler', 'ErrorSeverity']