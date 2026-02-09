# Path: downloader/engine/__init__.py
"""
Downloader Engine Module

Main download orchestration components.
Exports public APIs for download workflow execution.

Architecture:
- DownloadCoordinator: Main orchestrator
- DistributionProcessor: Routes by distribution type
- ArchiveDownloader: Handles ZIP/TAR downloads
- DistributionDetector: Auto-detects distribution types
"""

from downloader.engine.coordinator import DownloadCoordinator
from downloader.engine.distribution_processor import DistributionProcessor
from downloader.engine.archive_downloader import ArchiveDownloader
from downloader.engine.distribution_detector import DistributionDetector
from downloader.engine.protocol_handlers import HTTPHandler
from downloader.engine.stream_handler import StreamHandler, ChunkIterator
from downloader.engine.retry_manager import RetryManager, with_retry
from downloader.engine.validator import Validator
from downloader.engine.db_operations import DatabaseRepository
from downloader.engine.path_resolver import PathResolver
from downloader.engine.failure_handler import FailureHandler
from downloader.engine.result import (
    DownloadResult,
    ExtractionResult,
    ValidationResult,
    ProcessingResult,
)

__all__ = [
    # Main coordinator
    'DownloadCoordinator',
    
    # Distribution handling
    'DistributionProcessor',
    'ArchiveDownloader',
    'DistributionDetector',
    
    # Protocol handlers
    'HTTPHandler',
    'StreamHandler',
    'ChunkIterator',
    
    # Workflow components
    'RetryManager',
    'with_retry',
    'Validator',
    'DatabaseRepository',
    
    # Helper components
    'PathResolver',
    'FailureHandler',
    
    # Result objects
    'DownloadResult',
    'ExtractionResult',
    'ValidationResult',
    'ProcessingResult',
]