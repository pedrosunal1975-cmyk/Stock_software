# Path: library/engine/result_cache.py
"""
Result Cache

Simple in-memory cache for analysis results.
Reduces redundant processing of same filings.

Architecture:
- Cache keyed by filing_id
- TTL-based expiration
- Statistics tracking (hits, misses)
- Thread-safe operations

Usage:
    from library.engine.result_cache import ResultCache
    
    cache = ResultCache()
    
    # Check cache first
    result = cache.get_cached_result(filing_id)
    if result:
        return result
    
    # Process and cache
    result = expensive_operation()
    cache.cache_result(filing_id, result)
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from library.core.config_loader import LibraryConfig
from library.core.logger import get_logger
from library.constants import LOG_INPUT, LOG_OUTPUT, CACHE_TTL_SECONDS

logger = get_logger(__name__, 'engine')


class ResultCache:
    """
    Simple in-memory cache for analysis results.
    
    Features:
    - TTL-based expiration
    - Statistics tracking
    - Clear/invalidate operations
    
    Example:
        cache = ResultCache()
        
        # Try cache first
        cached = cache.get_cached_result('filing_123')
        if cached:
            print("Cache hit!")
        else:
            # Process and cache
            result = process_filing()
            cache.cache_result('filing_123', result)
    """
    
    def __init__(self, config: Optional[LibraryConfig] = None):
        """
        Initialize result cache.
        
        Args:
            config: Optional LibraryConfig instance
        """
        self.config = config if config else LibraryConfig()
        self.ttl_seconds = self.config.get('library_cache_ttl')
        
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._hits = 0
        self._misses = 0
        
        logger.debug(f"{LOG_OUTPUT} Result cache initialized (TTL={self.ttl_seconds}s)")
    
    def get_cached_result(self, filing_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result for filing.
        
        Args:
            filing_id: Filing identifier
            
        Returns:
            Cached result or None if not found/expired
        """
        if filing_id not in self._cache:
            self._misses += 1
            logger.debug(f"{LOG_OUTPUT} Cache miss: {filing_id}")
            return None
        
        entry = self._cache[filing_id]
        
        # Check expiration
        if self._is_expired(entry['cached_at']):
            logger.debug(f"{LOG_OUTPUT} Cache expired: {filing_id}")
            del self._cache[filing_id]
            self._misses += 1
            return None
        
        self._hits += 1
        logger.debug(f"{LOG_OUTPUT} Cache hit: {filing_id}")
        
        return entry['result']
    
    def cache_result(self, filing_id: str, result: Dict[str, Any]) -> None:
        """
        Cache analysis result.
        
        Args:
            filing_id: Filing identifier
            result: Analysis result dictionary
        """
        self._cache[filing_id] = {
            'result': result,
            'cached_at': datetime.now(),
        }
        
        logger.debug(f"{LOG_INPUT} Cached result: {filing_id}")
    
    def invalidate_cache(self, filing_id: str) -> None:
        """
        Remove cached result for filing.
        
        Args:
            filing_id: Filing identifier
        """
        if filing_id in self._cache:
            del self._cache[filing_id]
            logger.debug(f"{LOG_OUTPUT} Invalidated cache: {filing_id}")
    
    def clear_cache(self) -> None:
        """Clear all cached results."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"{LOG_OUTPUT} Cleared {count} cached results")
    
    def _is_expired(self, cached_at: datetime) -> bool:
        """
        Check if cache entry is expired.
        
        Args:
            cached_at: Timestamp when entry was cached
            
        Returns:
            True if expired
        """
        age = datetime.now() - cached_at
        return age.total_seconds() > self.ttl_seconds
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = (
            (self._hits / total_requests * 100)
            if total_requests > 0
            else 0.0
        )
        
        return {
            'cache_hits': self._hits,
            'cache_misses': self._misses,
            'total_requests': total_requests,
            'hit_rate_percentage': round(hit_rate, 2),
            'cache_size': len(self._cache),
            'ttl_seconds': self.ttl_seconds,
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        expired_ids = [
            filing_id
            for filing_id, entry in self._cache.items()
            if self._is_expired(entry['cached_at'])
        ]
        
        for filing_id in expired_ids:
            del self._cache[filing_id]
        
        if expired_ids:
            logger.info(f"{LOG_OUTPUT} Cleaned up {len(expired_ids)} expired cache entries")
        
        return len(expired_ids)


__all__ = ['ResultCache']