# Path: downloader/cli/__init__.py
"""
Downloader CLI Module

Command-line interface for interactive downloads.
"""

from downloader.cli.download_cli import DownloadCLI, main

__all__ = ['DownloadCLI', 'main']