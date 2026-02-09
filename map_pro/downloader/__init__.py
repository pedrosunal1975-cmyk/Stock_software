# Path: downloader/__init__.py
"""
MAP PRO Downloader Module

XBRL filing download system with streaming, retry logic, and database integration.
"""

from .engine.coordinator import DownloadCoordinator
from .cli.download_cli import DownloadCLI, main

__version__ = '1.0.0'

__all__ = ['DownloadCoordinator', 'DownloadCLI', 'main']