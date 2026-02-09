# Path: observability/metrics.py
"""
Metrics Collector

Collects performance and operational metrics.
"""

import logging
import time
from typing import Optional
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class OperationMetric:
    """Single operation metric."""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    metadata: dict = field(default_factory=dict)


class MetricsCollector:
    """
    Collects operational metrics.
    
    Tracks:
    - Operation durations
    - Success/failure rates
    - Throughput
    - Resource usage
    
    Example:
        metrics = MetricsCollector()
        
        # Time an operation
        metrics.start_operation('mapping')
        # ... do work ...
        metrics.end_operation('mapping', success=True)
        
        # Get summary
        summary = metrics.get_summary()
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.logger = logging.getLogger('observability.metrics')
        
        # Active operations
        self._active: dict[str, OperationMetric] = {}
        
        # Completed operations
        self._completed: list[OperationMetric] = []
        
        # Counters
        self._counters: dict[str, int] = defaultdict(int)
        
        # Start time
        self._start_time = time.time()
    
    def start_operation(
        self,
        operation: str,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Start timing an operation.
        
        Args:
            operation: Operation name
            metadata: Optional metadata
        """
        metric = OperationMetric(
            operation=operation,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        self._active[operation] = metric
        self.logger.debug(f"Started operation: {operation}")
    
    def end_operation(
        self,
        operation: str,
        success: bool = True,
        metadata: Optional[dict] = None
    ) -> float:
        """
        End timing an operation.
        
        Args:
            operation: Operation name
            success: Whether operation succeeded
            metadata: Optional additional metadata
            
        Returns:
            Operation duration in seconds
        """
        if operation not in self._active:
            self.logger.warning(f"Operation not started: {operation}")
            return 0.0
        
        metric = self._active.pop(operation)
        metric.end_time = time.time()
        metric.duration = metric.end_time - metric.start_time
        metric.success = success
        
        if metadata:
            metric.metadata.update(metadata)
        
        self._completed.append(metric)
        
        self.logger.debug(
            f"Completed operation: {operation} "
            f"({metric.duration:.2f}s, success={success})"
        )
        
        return metric.duration
    
    def increment(self, counter: str, value: int = 1) -> None:
        """Increment counter."""
        self._counters[counter] += value
    
    def get_counter(self, counter: str) -> int:
        """Get counter value."""
        return self._counters.get(counter, 0)
    
    def get_operation_stats(self, operation: str) -> dict:
        """Get statistics for specific operation."""
        ops = [m for m in self._completed if m.operation == operation]
        
        if not ops:
            return {'count': 0}
        
        durations = [m.duration for m in ops if m.duration]
        successes = sum(1 for m in ops if m.success)
        
        return {
            'count': len(ops),
            'success_count': successes,
            'failure_count': len(ops) - successes,
            'success_rate': successes / len(ops) if ops else 0,
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'total_duration': sum(durations) if durations else 0
        }
    
    def get_summary(self) -> dict:
        """Get overall metrics summary."""
        total_duration = time.time() - self._start_time
        
        # Group by operation
        operations = set(m.operation for m in self._completed)
        operation_stats = {
            op: self.get_operation_stats(op)
            for op in operations
        }
        
        return {
            'total_duration': total_duration,
            'operations_completed': len(self._completed),
            'operations_active': len(self._active),
            'operation_stats': operation_stats,
            'counters': dict(self._counters)
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._active.clear()
        self._completed.clear()
        self._counters.clear()
        self._start_time = time.time()
        self.logger.info("Metrics reset")


__all__ = ['MetricsCollector', 'OperationMetric']
