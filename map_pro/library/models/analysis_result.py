# Path: library/models/analysis_result.py
"""
Analysis Result Model

Data structure for complete filing analysis results.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class AnalysisResult:
    """
    Result of complete filing analysis workflow.
    
    Contains namespace detection, library requirements,
    availability status, and download results.
    
    Attributes:
        filing_id: Unique filing identifier
        success: Whether analysis completed successfully
        namespaces_detected: List of namespace URIs
        libraries_required: List of required library names
        libraries_ready: Whether all libraries are available
        manual_downloads_needed: Libraries requiring manual download
        analysis_report: Complete analysis report dictionary
        error: Error message if analysis failed
    """
    filing_id: str
    success: bool
    namespaces_detected: List[str]
    libraries_required: List[str]
    libraries_ready: bool
    manual_downloads_needed: List[Dict[str, Any]] = field(default_factory=list)
    analysis_report: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def namespace_count(self) -> int:
        """Number of namespaces detected."""
        return len(self.namespaces_detected)
    
    @property
    def library_count(self) -> int:
        """Number of required libraries."""
        return len(self.libraries_required)
    
    @property
    def manual_count(self) -> int:
        """Number of libraries needing manual download."""
        return len(self.manual_downloads_needed)


# Path: library/models/library_status.py
"""
Library Status Model

Data structure for taxonomy library status.
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


__all__ = ['AnalysisResult', 'LibraryStatus']