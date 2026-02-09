# Path: xbrl_parser/observability/performance.py
"""
Performance Monitoring System

Tracks parser performance metrics including timing, memory, and IO statistics.
Identifies bottlenecks and provides performance insights.

Design:
- Phase-based timing breakdown
- Memory tracking per component
- IO statistics (files, bytes, cache hits)
- Bottleneck identification
- Context manager for automatic timing
"""

import time
import psutil
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Phase(str, Enum):
    """Parser execution phases."""
    DISCOVERY = "discovery"
    TAXONOMY_LOADING = "taxonomy_loading"
    INSTANCE_PARSING = "instance_parsing"
    VALIDATION = "validation"
    INDEXING = "indexing"
    SERIALIZATION = "serialization"
    TOTAL = "total"


@dataclass
class PhaseMetrics:
    """Metrics for a single phase."""
    phase: Phase
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    memory_start_mb: float = 0.0
    memory_end_mb: float = 0.0
    memory_peak_mb: float = 0.0
    memory_delta_mb: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'phase': self.phase,
            'duration': round(self.duration, 3),
            'memory_start_mb': round(self.memory_start_mb, 2),
            'memory_end_mb': round(self.memory_end_mb, 2),
            'memory_peak_mb': round(self.memory_peak_mb, 2),
            'memory_delta_mb': round(self.memory_delta_mb, 2),
        }


@dataclass
class IOStatistics:
    """IO operation statistics."""
    files_read: int = 0
    files_written: int = 0
    bytes_read: int = 0
    bytes_written: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    network_requests: int = 0
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100.0
    
    @property
    def total_files(self) -> int:
        """Total files accessed."""
        return self.files_read + self.files_written
    
    @property
    def total_bytes(self) -> int:
        """Total bytes transferred."""
        return self.bytes_read + self.bytes_written
    
    @property
    def total_bytes_mb(self) -> float:
        """Total bytes in megabytes."""
        return self.total_bytes / (1024 * 1024)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'files_read': self.files_read,
            'files_written': self.files_written,
            'bytes_read': self.bytes_read,
            'bytes_written': self.bytes_written,
            'total_bytes_mb': round(self.total_bytes_mb, 2),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': round(self.cache_hit_rate, 2),
            'network_requests': self.network_requests,
        }


@dataclass
class Bottleneck:
    """Identified performance bottleneck."""
    phase: Phase
    metric: str
    value: float
    threshold: float
    severity: str  # 'critical', 'warning', 'info'
    recommendation: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'phase': self.phase,
            'metric': self.metric,
            'value': value,
            'threshold': self.threshold,
            'severity': self.severity,
            'recommendation': self.recommendation,
        }


class PerformanceMonitor:
    """
    Monitor and track parser performance.
    
    Tracks:
    - Phase timing (discovery, loading, parsing, validation, etc.)
    - Memory usage per phase
    - IO statistics (files, bytes, cache)
    - Bottleneck identification
    
    Example:
        monitor = PerformanceMonitor()
        
        # Manual timing
        monitor.start_phase(Phase.TAXONOMY_LOADING)
        # ... do work ...
        monitor.end_phase(Phase.TAXONOMY_LOADING)
        
        # Context manager
        with monitor.phase_context(Phase.VALIDATION):
            # ... do work ...
            pass
        
        # Get results
        report = monitor.get_report()
    """
    
    def __init__(self):
        """Initialize performance monitor."""
        self._phase_metrics: dict[Phase, PhaseMetrics] = {}
        self._current_phase: Optional[Phase] = None
        self._io_stats = IOStatistics()
        self._bottlenecks: list[Bottleneck] = []
        
        # Process for memory tracking
        self._process = psutil.Process()
        
        # Overall tracking
        self._overall_start: Optional[float] = None
        self._overall_end: Optional[float] = None
    
    def start(self) -> None:
        """Start overall performance monitoring."""
        self._overall_start = time.perf_counter()
    
    def end(self) -> None:
        """End overall performance monitoring."""
        self._overall_end = time.perf_counter()
    
    def start_phase(self, phase: Phase) -> None:
        """
        Start timing a phase.
        
        Args:
            phase: Phase to start tracking
        """
        if self._current_phase is not None:
            raise RuntimeError(
                f"Phase {self._current_phase} is still active. "
                f"End it before starting {phase}."
            )
        
        self._current_phase = phase
        
        metrics = PhaseMetrics(phase=phase)
        metrics.start_time = time.perf_counter()
        metrics.memory_start_mb = self._get_memory_mb()
        metrics.memory_peak_mb = metrics.memory_start_mb
        
        self._phase_metrics[phase] = metrics
    
    def end_phase(self, phase: Phase) -> None:
        """
        End timing a phase.
        
        Args:
            phase: Phase to end tracking
        """
        if self._current_phase != phase:
            raise RuntimeError(
                f"Expected phase {self._current_phase} but got {phase}"
            )
        
        metrics = self._phase_metrics[phase]
        metrics.end_time = time.perf_counter()
        metrics.duration = metrics.end_time - metrics.start_time
        metrics.memory_end_mb = self._get_memory_mb()
        metrics.memory_delta_mb = metrics.memory_end_mb - metrics.memory_start_mb
        
        # Update peak if current is higher
        current_memory = self._get_memory_mb()
        if current_memory > metrics.memory_peak_mb:
            metrics.memory_peak_mb = current_memory
        
        self._current_phase = None
    
    def phase_context(self, phase: Phase):
        """
        Context manager for phase timing.
        
        Args:
            phase: Phase to track
            
        Returns:
            Context manager
            
        Example:
            with monitor.phase_context(Phase.VALIDATION):
                validate_filing()
        """
        return PhaseContext(self, phase)
    
    def _get_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        return self._process.memory_info().rss / (1024 * 1024)
    
    def record_file_read(self, file_path: Path) -> None:
        """
        Record file read operation.
        
        Args:
            file_path: Path to file read
        """
        self._io_stats.files_read += 1
        try:
            self._io_stats.bytes_read += file_path.stat().st_size
        except (OSError, FileNotFoundError):
            pass
    
    def record_file_write(self, file_path: Path) -> None:
        """
        Record file write operation.
        
        Args:
            file_path: Path to file written
        """
        self._io_stats.files_written += 1
        try:
            self._io_stats.bytes_written += file_path.stat().st_size
        except (OSError, FileNotFoundError):
            pass
    
    def record_cache_hit(self) -> None:
        """Record cache hit."""
        self._io_stats.cache_hits += 1
    
    def record_cache_miss(self) -> None:
        """Record cache miss."""
        self._io_stats.cache_misses += 1
    
    def record_network_request(self) -> None:
        """Record network request."""
        self._io_stats.network_requests += 1
    
    def get_io_statistics(self) -> IOStatistics:
        """
        Get IO statistics.
        
        Returns:
            IOStatistics object
        """
        return self._io_stats
    
    def get_phase_duration(self, phase: Phase) -> Optional[float]:
        """
        Get duration for a phase.
        
        Args:
            phase: Phase to query
            
        Returns:
            Duration in seconds, or None if phase not recorded
        """
        if phase not in self._phase_metrics:
            return None
        return self._phase_metrics[phase].duration
    
    def get_total_duration(self) -> Optional[float]:
        """
        Get total duration.
        
        Returns:
            Total duration in seconds, or None if not complete
        """
        if self._overall_start is None or self._overall_end is None:
            return None
        return self._overall_end - self._overall_start
    
    def identify_bottlenecks(
        self,
        time_threshold_seconds: float = 5.0,
        memory_threshold_mb: float = 1000.0
    ) -> list[Bottleneck]:
        """
        Identify performance bottlenecks.
        
        Args:
            time_threshold_seconds: Time threshold for slow phases
            memory_threshold_mb: Memory threshold for high-memory phases
            
        Returns:
            list of identified bottlenecks
        """
        bottlenecks = []
        
        for phase, metrics in self._phase_metrics.items():
            # Check timing
            if metrics.duration > time_threshold_seconds:
                severity = 'critical' if metrics.duration > time_threshold_seconds * 2 else 'warning'
                bottlenecks.append(Bottleneck(
                    phase=phase,
                    metric='duration',
                    value=metrics.duration,
                    threshold=time_threshold_seconds,
                    severity=severity,
                    recommendation=f"Phase {phase} took {metrics.duration:.2f}s. Consider optimization."
                ))
            
            # Check memory
            if metrics.memory_delta_mb > memory_threshold_mb:
                severity = 'critical' if metrics.memory_delta_mb > memory_threshold_mb * 2 else 'warning'
                bottlenecks.append(Bottleneck(
                    phase=phase,
                    metric='memory_delta',
                    value=metrics.memory_delta_mb,
                    threshold=memory_threshold_mb,
                    severity=severity,
                    recommendation=f"Phase {phase} used {metrics.memory_delta_mb:.2f}MB. Consider streaming."
                ))
        
        # Check cache efficiency
        if self._io_stats.cache_hit_rate < 50.0 and self._io_stats.cache_misses > 10:
            bottlenecks.append(Bottleneck(
                phase=Phase.TOTAL,
                metric='cache_hit_rate',
                value=self._io_stats.cache_hit_rate,
                threshold=50.0,
                severity='warning',
                recommendation=f"Cache hit rate is {self._io_stats.cache_hit_rate:.1f}%. Increase cache size."
            ))
        
        self._bottlenecks = bottlenecks
        return bottlenecks
    
    def get_report(self) -> dict[str, any]:
        """
        Get comprehensive performance report.
        
        Returns:
            Dictionary with complete performance data
        """
        # Calculate slowest phase
        slowest_phase = None
        slowest_duration = 0.0
        for phase, metrics in self._phase_metrics.items():
            if metrics.duration > slowest_duration:
                slowest_duration = metrics.duration
                slowest_phase = phase
        
        # Calculate memory-intensive phase
        memory_intensive_phase = None
        max_memory_delta = 0.0
        for phase, metrics in self._phase_metrics.items():
            if metrics.memory_delta_mb > max_memory_delta:
                max_memory_delta = metrics.memory_delta_mb
                memory_intensive_phase = phase
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_duration': self.get_total_duration(),
            'phases': {
                phase.value: metrics.to_dict()
                for phase, metrics in self._phase_metrics.items()
            },
            'io_statistics': self._io_stats.to_dict(),
            'bottlenecks': [b.to_dict() for b in self._bottlenecks],
            'insights': {
                'slowest_phase': slowest_phase.value if slowest_phase else None,
                'slowest_phase_duration': slowest_duration,
                'memory_intensive_phase': memory_intensive_phase.value if memory_intensive_phase else None,
                'max_memory_delta_mb': max_memory_delta,
            }
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._phase_metrics.clear()
        self._current_phase = None
        self._io_stats = IOStatistics()
        self._bottlenecks.clear()
        self._overall_start = None
        self._overall_end = None


class PhaseContext:
    """Context manager for phase timing."""
    
    def __init__(self, monitor: PerformanceMonitor, phase: Phase):
        """
        Initialize phase context.
        
        Args:
            monitor: PerformanceMonitor instance
            phase: Phase to track
        """
        self.monitor = monitor
        self.phase = phase
    
    def __enter__(self):
        """Enter phase context."""
        self.monitor.start_phase(self.phase)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit phase context."""
        self.monitor.end_phase(self.phase)
        return False


__all__ = [
    'PerformanceMonitor',
    'Phase',
    'PhaseMetrics',
    'IOStatistics',
    'Bottleneck',
]