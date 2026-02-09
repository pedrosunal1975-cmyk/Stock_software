# Path: observability/alerting.py
"""
Alerting System

Generates alerts for issues and anomalies.
"""

import logging
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data."""
    severity: AlertSeverity
    message: str
    component: str
    timestamp: datetime
    metadata: dict


class AlertingSystem:
    """
    Alerting system.
    
    Generates alerts for:
    - Low mapping coverage
    - High error rates
    - Low confidence scores
    - Performance issues
    - System health problems
    
    Example:
        alerting = AlertingSystem()
        
        # Register alert handler
        alerting.register_handler(lambda alert: print(alert.message))
        
        # Generate alert
        alerting.alert(
            AlertSeverity.WARNING,
            "Low mapping coverage: 45%",
            "mapper"
        )
    """
    
    def __init__(self):
        """Initialize alerting system."""
        self.logger = logging.getLogger('observability.alerting')
        self._alerts: list[Alert] = []
        self._handlers: list[Callable] = []
    
    def register_handler(self, handler: Callable[[Alert], None]):
        """
        Register alert handler.
        
        Args:
            handler: Function that receives Alert objects
        """
        self._handlers.append(handler)
    
    def alert(
        self,
        severity: AlertSeverity,
        message: str,
        component: str,
        metadata: Optional[dict] = None
    ):
        """
        Generate alert.
        
        Args:
            severity: Alert severity
            message: Alert message
            component: Component that generated alert
            metadata: Optional metadata
        """
        alert = Alert(
            severity=severity,
            message=message,
            component=component,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self._alerts.append(alert)
        
        # Log alert
        log_func = {
            AlertSeverity.INFO: self.logger.info,
            AlertSeverity.WARNING: self.logger.warning,
            AlertSeverity.ERROR: self.logger.error,
            AlertSeverity.CRITICAL: self.logger.critical
        }[severity]
        
        log_func(f"[{component}] {message}")
        
        # Call handlers
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")
    
    def check_mapping_result(self, mapping_result):
        """
        Check mapping result and generate alerts.
        
        Args:
            mapping_result: MappingResult to check
        """
        stats = mapping_result.statistics
        
        # Check coverage
        coverage = (stats.facts_mapped / stats.total_facts * 100) if stats.total_facts > 0 else 0
        
        if coverage < 50:
            self.alert(
                AlertSeverity.CRITICAL,
                f"Very low mapping coverage: {coverage:.1f}%",
                "mapper",
                {'coverage': coverage}
            )
        elif coverage < 75:
            self.alert(
                AlertSeverity.WARNING,
                f"Low mapping coverage: {coverage:.1f}%",
                "mapper",
                {'coverage': coverage}
            )
        
        # Check failure rate
        attempted = stats.facts_mapped + stats.facts_failed
        if attempted > 0:
            failure_rate = (stats.facts_failed / attempted * 100)
            
            if failure_rate > 10:
                self.alert(
                    AlertSeverity.ERROR,
                    f"High failure rate: {failure_rate:.1f}%",
                    "mapper",
                    {'failure_rate': failure_rate}
                )
        
        # Check confidence
        if stats.average_confidence < 0.70:
            self.alert(
                AlertSeverity.WARNING,
                f"Low average confidence: {stats.average_confidence:.2f}",
                "mapper",
                {'avg_confidence': stats.average_confidence}
            )
        
        # Check errors
        if mapping_result.errors:
            self.alert(
                AlertSeverity.ERROR,
                f"{len(mapping_result.errors)} errors occurred during mapping",
                "mapper",
                {'error_count': len(mapping_result.errors)}
            )
    
    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None
    ) -> list[Alert]:
        """
        Get alerts.
        
        Args:
            severity: Optional filter by severity
            
        Returns:
            List of alerts
        """
        if severity:
            return [a for a in self._alerts if a.severity == severity]
        return self._alerts.copy()
    
    def clear_alerts(self):
        """Clear all alerts."""
        self._alerts.clear()


__all__ = ['AlertingSystem', 'Alert', 'AlertSeverity']