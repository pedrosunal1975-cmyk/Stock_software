# Path: xbrl_parser/observability/metrics.py
"""
Performance Metrics Collection

Collects and exports performance metrics for monitoring and analysis.

This module provides:
- Metric collection (counters, gauges, histograms, timers)
- Multiple export formats (JSON, Prometheus, CSV)
- Metric aggregation and reporting
- Integration with PerformanceMonitor

Example:
    from ..observability import MetricsCollector
    
    collector = MetricsCollector()
    
    # Record metrics
    collector.increment('files_processed')
    collector.gauge('memory_usage_mb', 512.5)
    collector.timer('parse_duration', 45.2)
    
    # Export
    metrics = collector.export_json()
    collector.save_metrics('/path/to/metrics.json')
"""

import json
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from ..observability.constants import (
    MetricType,
    MetricFormat,
    METRIC_PREFIX_PARSER,
    METRICS_BUFFER_SIZE
)


@dataclass
class Metric:
    """
    A single metric data point.
    
    Attributes:
        name: Metric name
        value: Metric value
        metric_type: Type of metric (counter, gauge, histogram, timer)
        timestamp: When metric was recorded
        labels: Additional labels/tags
    """
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    labels: dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'value': self.value,
            'type': self.metric_type.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels
        }


class MetricsCollector:
    """
    Collect and manage performance metrics.
    
    Tracks various metric types and exports in multiple formats.
    
    Example:
        collector = MetricsCollector()
        
        # Counters (always increase)
        collector.increment('requests_total')
        collector.increment('errors_total', amount=5)
        
        # Gauges (can go up or down)
        collector.gauge('memory_usage_mb', 512.5)
        collector.gauge('active_connections', 10)
        
        # Histograms (distribution of values)
        collector.histogram('response_time_ms', [100, 150, 200, 180])
        
        # Timers (measure duration)
        collector.timer('parse_duration_seconds', 45.2)
        
        # Export
        json_data = collector.export_json()
        collector.save_metrics('metrics.json', MetricFormat.JSON)
    """
    
    def __init__(self, prefix: str = METRIC_PREFIX_PARSER):
        """
        Initialize metrics collector.
        
        Args:
            prefix: Prefix for all metric names
        """
        self.logger = logging.getLogger(__name__)
        self.prefix = prefix
        
        # Metric storage
        self.counters: dict[str, float] = defaultdict(float)
        self.gauges: dict[str, float] = {}
        self.histograms: dict[str, list[float]] = defaultdict(list)
        self.timers: dict[str, list[float]] = defaultdict(list)
        
        # Metric history
        self.metrics: list[Metric] = []
        self.max_metrics = METRICS_BUFFER_SIZE
        
        self.logger.debug("MetricsCollector initialized")
    
    def increment(
        self,
        name: str,
        amount: float = 1.0,
        labels: Optional[dict[str, str]] = None
    ) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Counter name
            amount: Amount to increment by (default: 1.0)
            labels: Optional labels
        """
        full_name = f"{self.prefix}_{name}"
        self.counters[full_name] += amount
        
        metric = Metric(
            name=full_name,
            value=self.counters[full_name],
            metric_type=MetricType.COUNTER,
            labels=labels or {}
        )
        self._add_metric(metric)
        
        self.logger.debug(f"Counter {full_name} incremented to {self.counters[full_name]}")
    
    def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[dict[str, str]] = None
    ) -> None:
        """
        set a gauge metric.
        
        Args:
            name: Gauge name
            value: Current value
            labels: Optional labels
        """
        full_name = f"{self.prefix}_{name}"
        self.gauges[full_name] = value
        
        metric = Metric(
            name=full_name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels or {}
        )
        self._add_metric(metric)
        
        self.logger.debug(f"Gauge {full_name} set to {value}")
    
    def histogram(
        self,
        name: str,
        values: list[float],
        labels: Optional[dict[str, str]] = None
    ) -> None:
        """
        Record histogram values.
        
        Args:
            name: Histogram name
            values: list of values
            labels: Optional labels
        """
        full_name = f"{self.prefix}_{name}"
        self.histograms[full_name].extend(values)
        
        # Calculate statistics
        avg = sum(values) / len(values) if values else 0
        
        metric = Metric(
            name=full_name,
            value=avg,
            metric_type=MetricType.HISTOGRAM,
            labels=labels or {}
        )
        self._add_metric(metric)
        
        self.logger.debug(f"Histogram {full_name} recorded {len(values)} values")
    
    def timer(
        self,
        name: str,
        duration: float,
        labels: Optional[dict[str, str]] = None
    ) -> None:
        """
        Record a timer metric (duration).
        
        Args:
            name: Timer name
            duration: Duration in seconds
            labels: Optional labels
        """
        full_name = f"{self.prefix}_{name}"
        self.timers[full_name].append(duration)
        
        metric = Metric(
            name=full_name,
            value=duration,
            metric_type=MetricType.TIMER,
            labels=labels or {}
        )
        self._add_metric(metric)
        
        self.logger.debug(f"Timer {full_name} recorded {duration}s")
    
    def _add_metric(self, metric: Metric) -> None:
        """Add metric to history with buffer management."""
        self.metrics.append(metric)
        
        # Trim if buffer is full
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
    
    def get_summary(self) -> dict[str, any]:
        """
        Get summary of all metrics.
        
        Returns:
            Dictionary with metric summaries
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'histograms': {
                name: {
                    'count': len(values),
                    'min': min(values) if values else 0,
                    'max': max(values) if values else 0,
                    'avg': sum(values) / len(values) if values else 0
                }
                for name, values in self.histograms.items()
            },
            'timers': {
                name: {
                    'count': len(durations),
                    'min': min(durations) if durations else 0,
                    'max': max(durations) if durations else 0,
                    'avg': sum(durations) / len(durations) if durations else 0,
                    'total': sum(durations)
                }
                for name, durations in self.timers.items()
            }
        }
    
    def export_json(self) -> str:
        """
        Export metrics as JSON.
        
        Returns:
            JSON string
        """
        summary = self.get_summary()
        return json.dumps(summary, indent=2)
    
    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted string
        """
        lines = []
        
        # Counters
        for name, value in self.counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # Gauges
        for name, value in self.gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        # Histograms
        for name, values in self.histograms.items():
            if values:
                lines.append(f"# TYPE {name} histogram")
                lines.append(f"{name}_count {len(values)}")
                lines.append(f"{name}_sum {sum(values)}")
        
        # Timers
        for name, durations in self.timers.items():
            if durations:
                lines.append(f"# TYPE {name} summary")
                lines.append(f"{name}_count {len(durations)}")
                lines.append(f"{name}_sum {sum(durations)}")
        
        return "\n".join(lines)
    
    def save_metrics(
        self,
        output_path: Path,
        format: MetricFormat = MetricFormat.JSON
    ) -> None:
        """
        Save metrics to file.
        
        Args:
            output_path: Output file path
            format: Output format
        """
        output_path = Path(output_path)
        
        if format == MetricFormat.JSON:
            content = self.export_json()
        elif format == MetricFormat.PROMETHEUS:
            content = self.export_prometheus()
        elif format == MetricFormat.TEXT:
            content = str(self.get_summary())
        else:
            self.logger.warning(f"Unsupported format: {format}, using JSON")
            content = self.export_json()
        
        output_path.write_text(content, encoding='utf-8')
        self.logger.info(f"Metrics saved to {output_path}")
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.timers.clear()
        self.metrics.clear()
        
        self.logger.debug("Metrics reset")


__all__ = ['MetricsCollector', 'Metric', 'MetricType', 'MetricFormat']
