# Path: xbrl_parser/observability/health_check.py
"""
System Health Monitoring

Monitors parser system health including resource usage, component status,
and overall system readiness.

This module provides:
- Resource monitoring (CPU, memory, disk)
- Component health checks
- Overall health status assessment
- Health report generation

Example:
    from ..observability import HealthCheck
    
    health = HealthCheck()
    
    # Check health
    status = health.check()
    
    if status['status'] == 'healthy':
        print("System is healthy")
    else:
        print(f"Issues: {status['issues']}")
    
    # Get detailed report
    report = health.get_detailed_report()
"""

import logging
import psutil
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..observability.constants import (
    HealthStatus,
    MEMORY_WARNING_THRESHOLD_PERCENT,
    MEMORY_CRITICAL_THRESHOLD_PERCENT,
    DISK_WARNING_THRESHOLD_PERCENT,
    DISK_CRITICAL_THRESHOLD_PERCENT,
    CPU_WARNING_THRESHOLD_PERCENT,
    CPU_CRITICAL_THRESHOLD_PERCENT,
    COMPONENT_TIMEOUT
)


@dataclass
class ComponentHealth:
    """
    Health status of a single component.
    
    Attributes:
        name: Component name
        status: Health status
        message: Status message
        details: Additional details
        last_check: When last checked
    """
    name: str
    status: HealthStatus
    message: str
    details: dict[str, any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'details': self.details,
            'last_check': self.last_check.isoformat()
        }


class HealthCheck:
    """
    Monitor system health.
    
    Checks:
    - CPU usage
    - Memory usage
    - Disk space
    - Component availability
    
    Example:
        health = HealthCheck()
        
        # Quick check
        status = health.check()
        print(f"Status: {status['status']}")
        
        # Detailed report
        report = health.get_detailed_report()
        
        # Save report
        health.save_report('/path/to/health.json')
    """
    
    def __init__(self):
        """Initialize health check system."""
        self.logger = logging.getLogger(__name__)
        self.components: dict[str, ComponentHealth] = {}
        
        self.logger.debug("HealthCheck initialized")
    
    def check(self) -> dict[str, any]:
        """
        Perform health check.
        
        Returns:
            Dictionary with health status and issues
        """
        self.logger.info("Performing health check")
        
        issues = []
        overall_status = HealthStatus.HEALTHY
        
        # Check resources
        cpu_status = self._check_cpu()
        memory_status = self._check_memory()
        disk_status = self._check_disk()
        
        # Aggregate issues
        if cpu_status['status'] != HealthStatus.HEALTHY:
            issues.append(cpu_status['message'])
            if cpu_status['status'] == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
            elif overall_status != HealthStatus.CRITICAL:
                overall_status = HealthStatus.DEGRADED
        
        if memory_status['status'] != HealthStatus.HEALTHY:
            issues.append(memory_status['message'])
            if memory_status['status'] == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
            elif overall_status != HealthStatus.CRITICAL:
                overall_status = HealthStatus.DEGRADED
        
        if disk_status['status'] != HealthStatus.HEALTHY:
            issues.append(disk_status['message'])
            if disk_status['status'] == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
            elif overall_status != HealthStatus.CRITICAL:
                overall_status = HealthStatus.DEGRADED
        
        result = {
            'status': overall_status.value,
            'timestamp': datetime.now().isoformat(),
            'issues': issues,
            'checks': {
                'cpu': cpu_status,
                'memory': memory_status,
                'disk': disk_status
            }
        }
        
        self.logger.info(f"Health check completed: {overall_status.value}")
        return result
    
    def _check_cpu(self) -> dict[str, any]:
        """Check CPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent >= CPU_CRITICAL_THRESHOLD_PERCENT:
                status = HealthStatus.CRITICAL
                message = f"CPU usage critical: {cpu_percent}%"
            elif cpu_percent >= CPU_WARNING_THRESHOLD_PERCENT:
                status = HealthStatus.DEGRADED
                message = f"CPU usage high: {cpu_percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"CPU usage normal: {cpu_percent}%"
            
            return {
                'status': status,
                'message': message,
                'cpu_percent': cpu_percent,
                'threshold_warning': CPU_WARNING_THRESHOLD_PERCENT,
                'threshold_critical': CPU_CRITICAL_THRESHOLD_PERCENT
            }
        
        except Exception as e:
            self.logger.error(f"CPU check failed: {e}")
            return {
                'status': HealthStatus.UNKNOWN,
                'message': f"CPU check failed: {e}",
                'error': str(e)
            }
    
    def _check_memory(self) -> dict[str, any]:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent >= MEMORY_CRITICAL_THRESHOLD_PERCENT:
                status = HealthStatus.CRITICAL
                message = f"Memory usage critical: {memory_percent}%"
            elif memory_percent >= MEMORY_WARNING_THRESHOLD_PERCENT:
                status = HealthStatus.DEGRADED
                message = f"Memory usage high: {memory_percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory_percent}%"
            
            return {
                'status': status,
                'message': message,
                'memory_percent': memory_percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'memory_total_mb': memory.total / (1024 * 1024),
                'threshold_warning': MEMORY_WARNING_THRESHOLD_PERCENT,
                'threshold_critical': MEMORY_CRITICAL_THRESHOLD_PERCENT
            }
        
        except Exception as e:
            self.logger.error(f"Memory check failed: {e}")
            return {
                'status': HealthStatus.UNKNOWN,
                'message': f"Memory check failed: {e}",
                'error': str(e)
            }
    
    def _check_disk(self) -> dict[str, any]:
        """Check disk space."""
        try:
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            if disk_percent >= DISK_CRITICAL_THRESHOLD_PERCENT:
                status = HealthStatus.CRITICAL
                message = f"Disk usage critical: {disk_percent}%"
            elif disk_percent >= DISK_WARNING_THRESHOLD_PERCENT:
                status = HealthStatus.DEGRADED
                message = f"Disk usage high: {disk_percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage normal: {disk_percent}%"
            
            return {
                'status': status,
                'message': message,
                'disk_percent': disk_percent,
                'disk_free_gb': disk.free / (1024 * 1024 * 1024),
                'disk_total_gb': disk.total / (1024 * 1024 * 1024),
                'threshold_warning': DISK_WARNING_THRESHOLD_PERCENT,
                'threshold_critical': DISK_CRITICAL_THRESHOLD_PERCENT
            }
        
        except Exception as e:
            self.logger.error(f"Disk check failed: {e}")
            return {
                'status': HealthStatus.UNKNOWN,
                'message': f"Disk check failed: {e}",
                'error': str(e)
            }
    
    def register_component(self, name: str, health: ComponentHealth) -> None:
        """
        Register a component health status.
        
        Args:
            name: Component name
            health: Component health status
        """
        self.components[name] = health
        self.logger.debug(f"Component registered: {name}")
    
    def get_component_health(self, name: str) -> Optional[ComponentHealth]:
        """
        Get health status of a component.
        
        Args:
            name: Component name
            
        Returns:
            Component health or None
        """
        return self.components.get(name)
    
    def get_detailed_report(self) -> dict[str, any]:
        """
        Get detailed health report.
        
        Returns:
            Comprehensive health report
        """
        health_check = self.check()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': health_check['status'],
            'issues': health_check['issues'],
            'system_checks': health_check['checks'],
            'components': {
                name: comp.to_dict()
                for name, comp in self.components.items()
            }
        }
        
        return report
    
    def save_report(self, output_path: Path) -> None:
        """
        Save health report to file.
        
        Args:
            output_path: Output file path
        """
        import json
        
        report = self.get_detailed_report()
        output_path = Path(output_path)
        
        output_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        self.logger.info(f"Health report saved to {output_path}")


__all__ = ['HealthCheck', 'ComponentHealth', 'HealthStatus']
