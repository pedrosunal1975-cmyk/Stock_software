# Path: xbrl_parser/observability/constants.py
"""
Observability Constants

Central repository for observability-related constants.

This module provides:
- Metrics collection settings
- Health check thresholds
- Profiling configurations
- Status definitions
"""

from enum import Enum

# ==============================================================================
# HEALTH CHECK CONSTANTS
# ==============================================================================

class HealthStatus(str, Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


# Health check thresholds
HEALTH_CHECK_TIMEOUT = 30  # Seconds
HEALTH_CHECK_RETRY_ATTEMPTS = 3
HEALTH_CHECK_RETRY_DELAY = 1  # Seconds

# Resource thresholds
MEMORY_WARNING_THRESHOLD_PERCENT = 80
MEMORY_CRITICAL_THRESHOLD_PERCENT = 95
DISK_WARNING_THRESHOLD_PERCENT = 85
DISK_CRITICAL_THRESHOLD_PERCENT = 95
CPU_WARNING_THRESHOLD_PERCENT = 85
CPU_CRITICAL_THRESHOLD_PERCENT = 95

# Component health
COMPONENT_TIMEOUT = 5  # Seconds per component check


# ==============================================================================
# METRICS CONSTANTS
# ==============================================================================

class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class MetricFormat(str, Enum):
    """Metric output formats."""
    JSON = "json"
    PROMETHEUS = "prometheus"
    CSV = "csv"
    TEXT = "text"


# Metric collection
METRICS_COLLECTION_INTERVAL = 60  # Seconds
METRICS_BUFFER_SIZE = 1000  # Maximum buffered metrics
METRICS_FLUSH_INTERVAL = 300  # Seconds
METRICS_RETENTION_DAYS = 30  # Days to keep metrics

# Metric prefixes
METRIC_PREFIX_PARSER = "xbrl_parser"
METRIC_PREFIX_TAXONOMY = "taxonomy"
METRIC_PREFIX_VALIDATION = "validation"
METRIC_PREFIX_SERIALIZATION = "serialization"

# Common metric names
METRIC_PARSE_DURATION = "parse_duration_seconds"
METRIC_PARSE_ERRORS = "parse_errors_total"
METRIC_FILES_PROCESSED = "files_processed_total"
METRIC_MEMORY_USAGE = "memory_usage_bytes"
METRIC_CACHE_HITS = "cache_hits_total"
METRIC_CACHE_MISSES = "cache_misses_total"


# ==============================================================================
# PROFILING CONSTANTS
# ==============================================================================

class ProfilingMode(str, Enum):
    """Profiling modes."""
    DISABLED = "disabled"
    TIME = "time"
    MEMORY = "memory"
    FULL = "full"


# Profiling settings
PROFILING_SAMPLE_INTERVAL = 0.001  # Seconds (1ms)
PROFILING_MAX_DEPTH = 50  # Maximum call stack depth
PROFILING_MIN_DURATION = 0.001  # Minimum function duration to record (seconds)

# Memory profiling
MEMORY_PROFILING_INTERVAL = 0.1  # Seconds
MEMORY_SNAPSHOT_INTERVAL = 10  # Seconds
MEMORY_SNAPSHOT_MAX_COUNT = 100  # Maximum snapshots to keep

# Profile output
PROFILE_OUTPUT_FORMAT = "json"  # Default format
PROFILE_INCLUDE_STDLIB = False  # Include standard library in profiles
PROFILE_SORT_BY = "cumulative"  # Sort key for profiles


# ==============================================================================
# PERFORMANCE THRESHOLDS
# ==============================================================================

# Phase duration thresholds (seconds)
PHASE_DURATION_WARNING = {
    'discovery': 5.0,
    'taxonomy_loading': 30.0,
    'instance_parsing': 60.0,
    'validation': 45.0,
    'indexing': 20.0,
    'serialization': 15.0,
}

PHASE_DURATION_CRITICAL = {
    'discovery': 10.0,
    'taxonomy_loading': 60.0,
    'instance_parsing': 120.0,
    'validation': 90.0,
    'indexing': 40.0,
    'serialization': 30.0,
}

# Memory usage thresholds (MB)
PHASE_MEMORY_WARNING = {
    'discovery': 100,
    'taxonomy_loading': 500,
    'instance_parsing': 1000,
    'validation': 800,
    'indexing': 600,
    'serialization': 400,
}

PHASE_MEMORY_CRITICAL = {
    'discovery': 200,
    'taxonomy_loading': 1000,
    'instance_parsing': 2000,
    'validation': 1500,
    'indexing': 1200,
    'serialization': 800,
}


# ==============================================================================
# BOTTLENECK DETECTION
# ==============================================================================

class BottleneckSeverity(str, Enum):
    """Bottleneck severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# Bottleneck thresholds
SLOW_FUNCTION_THRESHOLD = 1.0  # Seconds
HIGH_MEMORY_FUNCTION_THRESHOLD = 100  # MB
CACHE_MISS_RATE_THRESHOLD = 20  # Percent
IO_WAIT_THRESHOLD = 30  # Percent of total time


# ==============================================================================
# ALERTING
# ==============================================================================

class AlertLevel(str, Enum):
    """Alert severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Alert settings
ALERT_THROTTLE_SECONDS = 300  # Minimum time between duplicate alerts
ALERT_MAX_QUEUE_SIZE = 100  # Maximum queued alerts
ALERT_RETENTION_HOURS = 24  # Hours to keep alert history


# ==============================================================================
# LOGGING
# ==============================================================================

# Log levels for different scenarios
LOG_LEVEL_HEALTH_CHECK = "INFO"
LOG_LEVEL_METRICS = "DEBUG"
LOG_LEVEL_PROFILING = "DEBUG"
LOG_LEVEL_BOTTLENECK = "WARNING"


# ==============================================================================
# OUTPUT FILENAMES
# ==============================================================================

# Metrics output
METRICS_FILENAME_PATTERN = "metrics_{timestamp}.{format}"
METRICS_SUMMARY_FILENAME = "metrics_summary.json"

# Health check output
HEALTH_CHECK_FILENAME_PATTERN = "health_{timestamp}.json"
HEALTH_CHECK_LATEST = "health_latest.json"

# Profile output
PROFILE_FILENAME_PATTERN = "profile_{filing_id}_{timestamp}.{format}"
PROFILE_STATS_FILENAME = "profile_stats.txt"
PROFILE_FLAMEGRAPH_FILENAME = "flamegraph.svg"

# Debug artifacts
DEBUG_BUNDLE_FILENAME_PATTERN = "debug_bundle_{filing_id}_{timestamp}.zip"


# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    # Status enums
    'HealthStatus',
    'MetricType',
    'MetricFormat',
    'ProfilingMode',
    'BottleneckSeverity',
    'AlertLevel',
    
    # Health thresholds
    'HEALTH_CHECK_TIMEOUT',
    'MEMORY_WARNING_THRESHOLD_PERCENT',
    'MEMORY_CRITICAL_THRESHOLD_PERCENT',
    'DISK_WARNING_THRESHOLD_PERCENT',
    'DISK_CRITICAL_THRESHOLD_PERCENT',
    'CPU_WARNING_THRESHOLD_PERCENT',
    'CPU_CRITICAL_THRESHOLD_PERCENT',
    
    # Metrics
    'METRICS_COLLECTION_INTERVAL',
    'METRICS_BUFFER_SIZE',
    'METRIC_PREFIX_PARSER',
    'METRIC_PARSE_DURATION',
    
    # Profiling
    'PROFILING_SAMPLE_INTERVAL',
    'PROFILING_MAX_DEPTH',
    'MEMORY_PROFILING_INTERVAL',
    
    # Thresholds
    'PHASE_DURATION_WARNING',
    'PHASE_DURATION_CRITICAL',
    'PHASE_MEMORY_WARNING',
    'PHASE_MEMORY_CRITICAL',
    
    # Bottlenecks
    'SLOW_FUNCTION_THRESHOLD',
    'HIGH_MEMORY_FUNCTION_THRESHOLD',
    'CACHE_MISS_RATE_THRESHOLD',
    
    # Filenames
    'METRICS_FILENAME_PATTERN',
    'HEALTH_CHECK_FILENAME_PATTERN',
    'PROFILE_FILENAME_PATTERN',
]