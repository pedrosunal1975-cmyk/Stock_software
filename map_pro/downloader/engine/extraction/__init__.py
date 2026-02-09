# Path: downloader/engine/extraction/__init__.py
"""
Extraction Module

Multi-format extraction for XBRL taxonomies.
Supports ZIP archives, individual XSD files, and directory structures.

Use ArchiveHandler for ZIP/TAR files.
Use XSDHandler for individual schema files.
Use DirectoryHandler for directory mirroring.
"""

from downloader.engine.extraction.archive_handler import (
    ArchiveHandler,
    ZipExtractor,
    TarExtractor,
    BaseExtractor,
)
from downloader.engine.extraction.xsd_handler import XSDHandler
from downloader.engine.extraction.directory_handler import DirectoryHandler

__all__ = [
    # Archive extraction
    'ArchiveHandler',
    'ZipExtractor',
    'TarExtractor',
    'BaseExtractor',
    
    # XSD extraction
    'XSDHandler',
    
    # Directory mirroring
    'DirectoryHandler',
]