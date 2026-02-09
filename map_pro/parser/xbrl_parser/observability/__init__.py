# Path: xbrl_parser/observability/__init__.py
"""
Observability Module

Components for monitoring, profiling, and debugging the XBRL parser.

This module provides:
- Performance monitoring and metrics collection
- System health checks
- Code profiling
- Debug artifacts

Example:
    from ..observability import (
        MetricsCollector,
        HealthCheck,
        Profiler
    )
    
    # Collect metrics
    metrics = MetricsCollector()
    metrics.increment('files_processed')
    metrics.timer('parse_duration', 45.2)
    
    # Check health
    health = HealthCheck()
    status = health.check()
    
    # Profile code
    profiler = Profiler()
    with profiler.profile('parsing'):
        parse_filing(path)
"""

from ..observability.metrics import MetricsCollector, Metric
from ..observability.health_check import HealthCheck, ComponentHealth
from ..observability.profiler import Profiler, ProfileEntry
from ..observability import constants


__all__ = [
    # Metrics
    'MetricsCollector',
    'Metric',
    
    # Health
    'HealthCheck',
    'ComponentHealth',
    
    # Profiling
    'Profiler',
    'ProfileEntry',
    
    # Constants
    'constants',
]
