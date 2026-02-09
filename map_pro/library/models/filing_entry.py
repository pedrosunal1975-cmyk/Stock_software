# Path: library/models/filing_entry.py
"""
Filing Entry Model

Lightweight data structure for discovered parsed filings.
Contains only paths and folder-derived metadata.
Does NOT contain file contents.

Architecture:
- Discovered by ParsedLoader (loaders)
- Metadata extracted by MetadataExtractor (engine)
- Used by TaxonomyDetector to locate parsed.json
- Minimal metadata extraction (from folder structure only)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class FilingEntry:
    """
    Entry for a discovered parsed filing.
    
    Contains only paths and folder-derived metadata.
    File contents are loaded on-demand by other components.
    
    Attributes:
        market: Market type (e.g., 'sec', 'fca') - from folder structure
        company: Company name (normalized) - from folder structure
        form: Form type (e.g., '10-K') - from folder structure
        accession: Accession number or unique identifier - from folder structure
        filing_folder: Path to filing folder
        parsed_json_path: Path to parsed.json file
        available_files: Dict of file types to paths
    """
    market: str
    company: str
    form: str
    accession: str
    filing_folder: Path
    parsed_json_path: Path
    available_files: Dict[str, Path]
    
    @property
    def filing_id(self) -> str:
        """
        Generate unique filing identifier.
        
        Returns:
            String identifier: market/company/form/accession
        """
        return f"{self.market}/{self.company}/{self.form}/{self.accession}"
    
    @property
    def has_parsed_json(self) -> bool:
        """
        Check if parsed.json file exists.
        
        Returns:
            True if parsed.json exists
        """
        return self.parsed_json_path.exists()
    
    def get_file_path(self, file_type: str) -> Optional[Path]:
        """
        Get path to specific file type.
        
        Args:
            file_type: File extension (json, csv, xlsx, etc.)
            
        Returns:
            Path to file or None if not found
        """
        return self.available_files.get(file_type)
    
    def list_available_files(self) -> list:
        """
        List all available file types.
        
        Returns:
            List of file extensions
        """
        return list(self.available_files.keys())


__all__ = ['FilingEntry']