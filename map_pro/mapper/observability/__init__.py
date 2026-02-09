# Path: observability/__init__.py
"""
Observability Module

Monitoring, profiling, health checks, and debugging for mapper system.

Components:
- HealthCheck: System health monitoring
- MetricsCollector: Performance metrics collection
- Profiler: Performance profiling
- DebugArtifacts: Debug output generation
- AlertingSystem: Alert generation

Example:
    from ..observability import HealthCheck, MetricsCollector
    
    # Check system health
    health = HealthCheck()
    status = health.check_all()
    
    # Collect metrics
    metrics = MetricsCollector()
    metrics.start_operation('mapping')
    # ... do work ...
    metrics.end_operation('mapping')
"""

from .health_check import HealthCheck
from .metrics import MetricsCollector
from .profiler import Profiler
from .debug_artifacts import DebugArtifacts
from .alerting import AlertingSystem

__all__ = [
    'HealthCheck',
    'MetricsCollector',
    'Profiler',
    'DebugArtifacts',
    'AlertingSystem',
]
