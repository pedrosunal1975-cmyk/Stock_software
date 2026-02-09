# Path: library/engine/statistics_reporter.py
"""
Statistics Reporter

Lightweight statistics tracking for library module.
No hardcoded logic - just counts and metrics.

Usage:
    from library.engine.statistics_reporter import StatisticsReporter
    
    reporter = StatisticsReporter()
    
    # Update stats
    reporter.record_filing_processed(namespaces_count=5, libraries_count=3)
    
    # Get stats
    stats = reporter.get_statistics()
"""

from typing import Dict, Any
from datetime import datetime

from library.core.logger import get_logger
from library.constants import LOG_OUTPUT

logger = get_logger(__name__, 'engine')


class StatisticsReporter:
    """
    Track and report library module statistics.
    
    Tracks:
    - Filings processed
    - Namespaces detected
    - Libraries required/available/downloaded
    - Success rates
    
    Example:
        reporter = StatisticsReporter()
        
        # Record activity
        reporter.record_filing_processed(
            namespaces_count=5,
            libraries_count=3
        )
        
        # Get statistics
        stats = reporter.get_statistics()
    """
    
    def __init__(self):
        """Initialize statistics reporter."""
        self._stats = {
            'filings_processed': 0,
            'namespaces_detected': 0,
            'libraries_required': 0,
            'libraries_available': 0,
            'libraries_downloaded': 0,
            'manual_downloads_needed': 0,
            'processing_errors': 0,
            'started_at': datetime.now().isoformat(),
        }
        
        logger.debug(f"{LOG_OUTPUT} Statistics reporter initialized")
    
    def record_filing_processed(
        self,
        namespaces_count: int,
        libraries_count: int
    ) -> None:
        """
        Record filing processing.
        
        Args:
            namespaces_count: Number of namespaces detected
            libraries_count: Number of libraries required
        """
        self._stats['filings_processed'] += 1
        self._stats['namespaces_detected'] += namespaces_count
        self._stats['libraries_required'] += libraries_count
    
    def record_library_availability(
        self,
        available: int,
        downloaded: int,
        manual: int
    ) -> None:
        """
        Record library availability results.
        
        Args:
            available: Number of libraries already available
            downloaded: Number of libraries downloaded
            manual: Number requiring manual download
        """
        self._stats['libraries_available'] += available
        self._stats['libraries_downloaded'] += downloaded
        self._stats['manual_downloads_needed'] += manual
    
    def record_error(self) -> None:
        """Record processing error."""
        self._stats['processing_errors'] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics.
        
        Returns:
            Dictionary with all statistics including derived metrics
        """
        # Calculate derived metrics
        filings = self._stats['filings_processed']
        
        avg_namespaces = (
            self._stats['namespaces_detected'] / filings
            if filings > 0 else 0.0
        )
        
        avg_libraries = (
            self._stats['libraries_required'] / filings
            if filings > 0 else 0.0
        )
        
        total_processing = filings + self._stats['processing_errors']
        success_rate = (
            (filings / total_processing * 100)
            if total_processing > 0 else 100.0
        )
        
        return {
            **self._stats,
            'average_namespaces_per_filing': round(avg_namespaces, 2),
            'average_libraries_per_filing': round(avg_libraries, 2),
            'success_rate_percentage': round(success_rate, 2),
            'last_updated': datetime.now().isoformat(),
        }
    
    def reset_statistics(self) -> None:
        """Reset all statistics."""
        logger.info(f"{LOG_OUTPUT} Resetting statistics")
        
        self._stats = {
            'filings_processed': 0,
            'namespaces_detected': 0,
            'libraries_required': 0,
            'libraries_available': 0,
            'libraries_downloaded': 0,
            'manual_downloads_needed': 0,
            'processing_errors': 0,
            'started_at': datetime.now().isoformat(),
        }


__all__ = ['StatisticsReporter']