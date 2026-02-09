# Path: xbrl_parser/observability/profiler.py
"""
Code Profiling System

Detailed profiling of parser code execution for performance optimization.

This module provides:
- Function-level timing
- Memory profiling
- Call stack analysis
- Profile export formats
- Integration with standard profilers

Example:
    from ..observability import Profiler
    
    profiler = Profiler()
    
    # Profile code execution
    with profiler.profile('parsing'):
        # Code to profile
        parse_filing(filing_path)
    
    # Get results
    stats = profiler.get_stats()
    
    # Save profile
    profiler.save_profile('/path/to/profile.json')
"""

import logging
import cProfile
import pstats
import io
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
import time

from ..observability.constants import (
    ProfilingMode,
    PROFILING_SAMPLE_INTERVAL,
    PROFILING_MAX_DEPTH,
    PROFILING_MIN_DURATION,
    PROFILE_SORT_BY
)


@dataclass
class ProfileEntry:
    """
    A single profiling entry.
    
    Attributes:
        function_name: Name of function
        filename: Source file
        line_number: Line number
        call_count: Number of calls
        total_time: Total time spent
        cumulative_time: Cumulative time including sub-calls
        per_call_time: Average time per call
    """
    function_name: str
    filename: str
    line_number: int
    call_count: int
    total_time: float
    cumulative_time: float
    per_call_time: float = 0.0
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'function': self.function_name,
            'file': self.filename,
            'line': self.line_number,
            'calls': self.call_count,
            'total_time': round(self.total_time, 6),
            'cumulative_time': round(self.cumulative_time, 6),
            'per_call_time': round(self.per_call_time, 6)
        }


class Profiler:
    """
    Profile code execution.
    
    Provides detailed timing and memory profiling for performance optimization.
    
    Example:
        profiler = Profiler(mode=ProfilingMode.TIME)
        
        # Context manager
        with profiler.profile('taxonomy_loading'):
            load_taxonomy(schema_url)
        
        # Manual profiling
        profiler.start()
        # ... code ...
        profiler.stop()
        
        # Get statistics
        stats = profiler.get_stats()
        print(f"Top functions by time: {stats['top_functions'][:5]}")
        
        # Export profile
        profiler.save_profile('profile.json')
        profiler.export_text('profile.txt')
    """
    
    def __init__(self, mode: ProfilingMode = ProfilingMode.TIME):
        """
        Initialize profiler.
        
        Args:
            mode: Profiling mode (time, memory, full)
        """
        self.logger = logging.getLogger(__name__)
        self.mode = mode
        
        # Profiler state
        self.profiler: Optional[cProfile.Profile] = None
        self.is_profiling = False
        self.start_time = 0.0
        self.end_time = 0.0
        
        # Profile data
        self.profiles: dict[str, pstats.Stats] = {}
        self.current_profile_name: Optional[str] = None
        
        self.logger.debug(f"Profiler initialized in {mode} mode")
    
    def start(self, profile_name: str = "default") -> None:
        """
        Start profiling.
        
        Args:
            profile_name: Name for this profiling session
        """
        if self.is_profiling:
            self.logger.warning("Profiler already running")
            return
        
        self.current_profile_name = profile_name
        self.profiler = cProfile.Profile()
        
        # Try to enable profiler, handling case where another is active
        try:
            self.profiler.enable()
        except ValueError as e:
            if "Another profiling tool is already active" in str(e):
                # Clear any existing profiler and try again
                self.logger.warning("Clearing existing profiler before starting new one")
                import sys
                sys.setprofile(None)
                self.profiler.enable()
            else:
                raise
        
        self.start_time = time.time()
        self.is_profiling = True
        
        self.logger.debug(f"Profiling started: {profile_name}")
    
    def stop(self) -> None:
        """Stop profiling."""
        if not self.is_profiling or not self.profiler:
            self.logger.warning("Profiler not running")
            return
        
        self.profiler.disable()
        self.end_time = time.time()
        self.is_profiling = False
        
        # Store profile stats
        stream = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stream)
        stats.sort_stats(PROFILE_SORT_BY)
        
        if self.current_profile_name:
            self.profiles[self.current_profile_name] = stats
        
        duration = self.end_time - self.start_time
        self.logger.debug(f"Profiling stopped: {self.current_profile_name} ({duration:.3f}s)")
    
    @contextmanager
    def profile(self, name: str):
        """
        Context manager for profiling code blocks.
        
        Args:
            name: Profile name
            
        Example:
            with profiler.profile('taxonomy_loading'):
                load_taxonomy(schema_url)
        """
        self.start(name)
        try:
            yield
        finally:
            self.stop()
    
    def get_stats(self, profile_name: Optional[str] = None) -> dict[str, any]:
        """
        Get profiling statistics.
        
        Args:
            profile_name: Specific profile name (latest if None)
            
        Returns:
            Dictionary with profiling statistics
        """
        if profile_name is None:
            profile_name = self.current_profile_name
        
        if not profile_name or profile_name not in self.profiles:
            self.logger.warning(f"No profile found: {profile_name}")
            return {}
        
        stats = self.profiles[profile_name]
        
        # Extract top functions
        entries = []
        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            filename, line, func_name = func
            
            # Filter by minimum duration
            if tt < PROFILING_MIN_DURATION:
                continue
            
            entry = ProfileEntry(
                function_name=func_name,
                filename=filename,
                line_number=line,
                call_count=nc,
                total_time=tt,
                cumulative_time=ct,
                per_call_time=tt / nc if nc > 0 else 0
            )
            entries.append(entry)
        
        # Sort by total time
        entries.sort(key=lambda e: e.total_time, reverse=True)
        
        # Limit to max depth
        entries = entries[:PROFILING_MAX_DEPTH]
        
        return {
            'profile_name': profile_name,
            'duration': self.end_time - self.start_time if self.end_time else 0,
            'total_functions': len(stats.stats),
            'profiled_functions': len(entries),
            'top_functions': [e.to_dict() for e in entries]
        }
    
    def export_text(self, output_path: Path, profile_name: Optional[str] = None) -> None:
        """
        Export profile as text.
        
        Args:
            output_path: Output file path
            profile_name: Profile name (latest if None)
        """
        if profile_name is None:
            profile_name = self.current_profile_name
        
        if not profile_name or profile_name not in self.profiles:
            self.logger.warning(f"No profile found: {profile_name}")
            return
        
        stats = self.profiles[profile_name]
        
        output_path = Path(output_path)
        with output_path.open('w', encoding='utf-8') as f:
            stream = io.StringIO()
            stats.stream = stream
            stats.print_stats()
            f.write(stream.getvalue())
        
        self.logger.info(f"Text profile saved to {output_path}")
    
    def save_profile(self, output_path: Path, profile_name: Optional[str] = None) -> None:
        """
        Save profile as JSON.
        
        Args:
            output_path: Output file path
            profile_name: Profile name (latest if None)
        """
        import json
        
        stats = self.get_stats(profile_name)
        
        output_path = Path(output_path)
        output_path.write_text(json.dumps(stats, indent=2), encoding='utf-8')
        
        self.logger.info(f"Profile saved to {output_path}")
    
    def get_profile_summary(self) -> dict[str, any]:
        """
        Get summary of all profiles.
        
        Returns:
            Summary dictionary
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'mode': self.mode.value,
            'profiles': list(self.profiles.keys()),
            'total_profiles': len(self.profiles)
        }
    
    def reset(self) -> None:
        """Reset all profiles."""
        self.profiles.clear()
        self.current_profile_name = None
        self.is_profiling = False
        
        self.logger.debug("Profiler reset")


__all__ = ['Profiler', 'ProfileEntry', 'ProfilingMode']
