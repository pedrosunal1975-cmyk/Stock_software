# Path: library/models/library_status.py
"""
Library Status Model

Data structure for taxonomy library availability status.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class LibraryStatus:
    """
    Status of a single taxonomy library.
    
    Used for availability checking and reporting.
    
    Attributes:
        taxonomy_name: Taxonomy name (e.g., 'us-gaap')
        version: Taxonomy version (e.g., '2024')
        available_in_db: Whether record exists in database
        available_on_disk: Whether files exist on disk
        file_count: Number of files in library directory
        is_ready: Whether library is ready for use
        requires_download: Whether library needs to be downloaded
        requires_reindex: Whether library needs re-indexing
    """
    taxonomy_name: str
    version: str
    available_in_db: bool
    available_on_disk: bool
    file_count: int
    is_ready: bool
    requires_download: bool
    requires_reindex: bool
    
    @property
    def status_summary(self) -> str:
        """Human-readable status summary."""
        if self.is_ready:
            return "Ready"
        elif self.requires_download:
            return "Needs Download"
        elif self.requires_reindex:
            return "Needs Re-index"
        else:
            return "Unknown"


__all__ = ['LibraryStatus']