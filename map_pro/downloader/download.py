# Path: downloader/download.py
"""
MAP PRO Downloader - Main Entry Point

Standalone download module for XBRL filing downloads.
Run from downloader root: python download.py

Architecture:
- Query database for pending downloads
- Interactive CLI for user selection
- Download coordinator handles workflow
- Files saved to /mnt/map_pro/downloader/entities/

Usage:
    cd downloader/
    python download.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure downloader module is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from downloader.cli.download_cli import main


if __name__ == '__main__':
    """
    Main entry point for downloader module.
    
    Runs interactive CLI for downloading XBRL filings.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)