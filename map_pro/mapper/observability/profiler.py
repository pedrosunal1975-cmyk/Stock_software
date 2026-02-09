# Path: observability/profiler.py
"""
Profiler

Performance profiling for mapper operations.
"""

import logging
import time
import functools
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class ProfileData:
    """Profile data for a function."""
    function_name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    
    def update(self, duration: float):
        """Update with new call duration."""
        self.call_count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.avg_time = self.total_time / self.call_count


class Profiler:
    """
    Function profiler.
    
    Profiles function execution time and call counts.
    
    Example:
        profiler = Profiler()
        
        @profiler.profile
        def my_function():
            # ... do work ...
            pass
        
        # Get profile report
        report = profiler.get_report()
    """
    
    def __init__(self):
        """Initialize profiler."""
        self.logger = logging.getLogger('observability.profiler')
        self._profiles: dict[str, ProfileData] = {}
        self._enabled = True
    
    def enable(self):
        """Enable profiling."""
        self._enabled = True
    
    def disable(self):
        """Disable profiling."""
        self._enabled = False
    
    def profile(self, func: Callable) -> Callable:
        """
        Decorator to profile function.
        
        Args:
            func: Function to profile
            
        Returns:
            Wrapped function
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self._enabled:
                return func(*args, **kwargs)
            
            func_name = f"{func.__module__}.{func.__name__}"
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                
                if func_name not in self._profiles:
                    self._profiles[func_name] = ProfileData(func_name)
                
                self._profiles[func_name].update(duration)
        
        return wrapper
    
    def get_report(self) -> dict[str, dict]:
        """
        Get profiling report.

        Returns:
            Dictionary mapping function names to profile data
        """
        return {
            name: {
                'call_count': profile.call_count,
                'total_time': profile.total_time,
                'avg_time': profile.avg_time,
                'min_time': profile.min_time,
                'max_time': profile.max_time
            }
            for name, profile in self._profiles.items()
        }
    
    def get_top_functions(self, n: int = 10, by: str = 'total_time') -> list:
        """
        Get top N functions by metric.
        
        Args:
            n: Number of functions
            by: Metric to sort by (total_time, avg_time, call_count)
            
        Returns:
            List of (function_name, metric_value) tuples
        """
        if by == 'total_time':
            key_func = lambda x: x[1].total_time
        elif by == 'avg_time':
            key_func = lambda x: x[1].avg_time
        elif by == 'call_count':
            key_func = lambda x: x[1].call_count
        else:
            raise ValueError(f"Unknown metric: {by}")
        
        sorted_profiles = sorted(
            self._profiles.items(),
            key=key_func,
            reverse=True
        )
        
        return [
            (name, getattr(profile, by))
            for name, profile in sorted_profiles[:n]
        ]
    
    def reset(self):
        """Reset all profile data."""
        self._profiles.clear()


__all__ = ['Profiler', 'ProfileData']