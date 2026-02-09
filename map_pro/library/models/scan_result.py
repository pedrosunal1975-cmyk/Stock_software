# Path: library/models/scan_result.py
"""
Scan Result Model

Data structure for namespace scanning results.
"""

from dataclasses import dataclass, field
from typing import Set, List, Dict, Any, Optional


@dataclass
class ScanResult:
    """
    Result of scanning a filing for namespace requirements.
    
    Attributes:
        filing_id: Unique filing identifier
        namespaces_detected: Set of namespace URIs found
        required_libraries: List of library metadata dictionaries
        market_type: Market type (sec, fca, esma, etc.)
        success: Whether scan completed successfully
        error: Error message if scan failed
    """
    filing_id: str
    namespaces_detected: Set[str]
    required_libraries: List[Dict[str, Any]]
    market_type: str
    success: bool
    error: Optional[str] = None
    
    @property
    def namespace_count(self) -> int:
        """Number of namespaces detected."""
        return len(self.namespaces_detected)
    
    @property
    def library_count(self) -> int:
        """Number of required libraries."""
        return len(self.required_libraries)


__all__ = ['ScanResult']