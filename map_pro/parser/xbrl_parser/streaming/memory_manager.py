# Path: xbrl_parser/streaming/memory_manager.py
"""
Memory Management for Streaming

Monitors and manages memory usage during streaming parse operations.

Provides memory tracking, threshold monitoring, and cleanup strategies
to prevent memory exhaustion when processing large XBRL filings.
"""

import psutil
import logging
import gc
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemorySnapshot:
    """
    Memory usage snapshot.
    
    Attributes:
        timestamp: When snapshot was taken
        rss_mb: Resident set Size in megabytes
        vms_mb: Virtual Memory Size in megabytes
        percent: Memory usage as percentage of total
        available_mb: Available system memory in MB
    """
    timestamp: datetime
    rss_mb: float
    vms_mb: float
    percent: float
    available_mb: float
    
    def __str__(self) -> str:
        """String representation of snapshot."""
        return (
            f"Memory: {self.rss_mb:.1f}MB RSS, "
            f"{self.vms_mb:.1f}MB VMS, "
            f"{self.percent:.1f}% used, "
            f"{self.available_mb:.1f}MB available"
        )


@dataclass
class MemoryThresholds:
    """
    Memory threshold configuration.
    
    Attributes:
        warning_mb: Warn when RSS exceeds this (MB)
        critical_mb: Error when RSS exceeds this (MB)
        max_percent: Maximum memory percentage (0-100)
        cleanup_trigger_mb: Trigger cleanup at this RSS (MB)
    """
    warning_mb: float = 1024.0  # 1GB warning
    critical_mb: float = 4096.0  # 4GB critical
    max_percent: float = 80.0  # 80% of system memory
    cleanup_trigger_mb: float = 512.0  # Cleanup at 512MB


class MemoryManager:
    """
    Memory manager for streaming operations.
    
    Tracks memory usage and triggers cleanup when thresholds are exceeded.
    Used to prevent memory exhaustion during large file processing.
    
    Example:
        manager = MemoryManager(
            thresholds=MemoryThresholds(warning_mb=512)
        )
        
        while parsing:
            manager.check_memory()
            
            if manager.should_cleanup():
                manager.cleanup()
            
            # Process batch
    """
    
    def __init__(
        self,
        thresholds: Optional[MemoryThresholds] = None,
        enable_auto_cleanup: bool = True
    ):
        """
        Initialize memory manager.
        
        Args:
            thresholds: Memory thresholds configuration
            enable_auto_cleanup: Automatically trigger cleanup
        """
        self.thresholds = thresholds or MemoryThresholds()
        self.enable_auto_cleanup = enable_auto_cleanup
        self.logger = logging.getLogger(__name__)
        
        # Tracking
        self.initial_snapshot: Optional[MemorySnapshot] = None
        self.peak_snapshot: Optional[MemorySnapshot] = None
        self.current_snapshot: Optional[MemorySnapshot] = None
        self.snapshots: list[MemorySnapshot] = []
        
        # Statistics
        self.cleanup_count = 0
        self.warning_count = 0
        self.critical_count = 0
        
        # Take initial snapshot
        self.initial_snapshot = self.take_snapshot()
        self.peak_snapshot = self.initial_snapshot
        self.logger.debug(f"Memory manager initialized: {self.initial_snapshot}")
    
    def take_snapshot(self) -> MemorySnapshot:
        """
        Take current memory snapshot.
        
        Returns:
            MemorySnapshot with current memory usage
        """
        process = psutil.Process()
        memory_info = process.memory_info()
        virtual_memory = psutil.virtual_memory()
        
        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=memory_info.rss / (1024 * 1024),
            vms_mb=memory_info.vms / (1024 * 1024),
            percent=virtual_memory.percent,
            available_mb=virtual_memory.available / (1024 * 1024)
        )
        
        self.current_snapshot = snapshot
        self.snapshots.append(snapshot)
        
        # Update peak if necessary
        if not self.peak_snapshot or snapshot.rss_mb > self.peak_snapshot.rss_mb:
            self.peak_snapshot = snapshot
        
        return snapshot
    
    def check_memory(self) -> dict[str, bool]:
        """
        Check memory against thresholds.
        
        Returns:
            Dictionary with threshold status:
                - warning: Warning threshold exceeded
                - critical: Critical threshold exceeded
                - cleanup_needed: Cleanup should be triggered
        """
        snapshot = self.take_snapshot()
        
        status = {
            'warning': False,
            'critical': False,
            'cleanup_needed': False
        }
        
        # Check warning threshold
        if snapshot.rss_mb > self.thresholds.warning_mb:
            status['warning'] = True
            self.warning_count += 1
            self.logger.warning(f"Memory warning: {snapshot}")
        
        # Check critical threshold
        if (snapshot.rss_mb > self.thresholds.critical_mb or 
            snapshot.percent > self.thresholds.max_percent):
            status['critical'] = True
            self.critical_count += 1
            self.logger.error(f"Memory critical: {snapshot}")
        
        # Check cleanup threshold
        if snapshot.rss_mb > self.thresholds.cleanup_trigger_mb:
            status['cleanup_needed'] = True
            
            # Auto cleanup if enabled
            if self.enable_auto_cleanup:
                self.cleanup()
        
        return status
    
    def should_cleanup(self) -> bool:
        """
        Check if cleanup should be triggered.
        
        Returns:
            True if cleanup is recommended
        """
        if not self.current_snapshot:
            return False
        
        return self.current_snapshot.rss_mb > self.thresholds.cleanup_trigger_mb
    
    def cleanup(self) -> MemorySnapshot:
        """
        Trigger garbage collection.
        
        Forces Python garbage collection to free up memory.
        
        Returns:
            MemorySnapshot after cleanup
        """
        before = self.take_snapshot()
        
        self.logger.debug("Triggering garbage collection")
        gc.collect()
        
        after = self.take_snapshot()
        freed_mb = before.rss_mb - after.rss_mb
        
        self.cleanup_count += 1
        self.logger.info(
            f"Memory cleanup #{self.cleanup_count}: "
            f"freed {freed_mb:.1f}MB ({after})"
        )
        
        return after
    
    def get_statistics(self) -> dict[str, any]:
        """
        Get memory usage statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        if not self.current_snapshot or not self.initial_snapshot:
            return {}
        
        return {
            'initial_mb': self.initial_snapshot.rss_mb,
            'current_mb': self.current_snapshot.rss_mb,
            'peak_mb': self.peak_snapshot.rss_mb if self.peak_snapshot else 0.0,
            'delta_mb': self.current_snapshot.rss_mb - self.initial_snapshot.rss_mb,
            'cleanup_count': self.cleanup_count,
            'warning_count': self.warning_count,
            'critical_count': self.critical_count,
            'snapshots_taken': len(self.snapshots)
        }
    
    def reset(self) -> None:
        """Reset memory manager statistics."""
        self.initial_snapshot = self.take_snapshot()
        self.peak_snapshot = self.initial_snapshot
        self.snapshots = [self.initial_snapshot]
        self.cleanup_count = 0
        self.warning_count = 0
        self.critical_count = 0
        self.logger.debug("Memory manager reset")
    
    def __str__(self) -> str:
        """String representation."""
        if not self.current_snapshot:
            return "MemoryManager (no data)"
        
        stats = self.get_statistics()
        return (
            f"MemoryManager("
            f"current={stats.get('current_mb', 0):.1f}MB, "
            f"peak={stats.get('peak_mb', 0):.1f}MB, "
            f"cleanups={stats.get('cleanup_count', 0)})"
        )


__all__ = [
    'MemorySnapshot',
    'MemoryThresholds',
    'MemoryManager',
]