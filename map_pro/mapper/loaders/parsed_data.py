# Path: loaders/parsed_data.py
"""
Parsed Data Loader - Universal Doorkeeper

Discovers and provides paths to ALL files in parser output directory.
Does NOT load or parse files - other components decide how to use them.

ARCHITECTURE:
- Discovers all filing folders
- Provides paths to any file within folders
- Extracts metadata from folder names only
- Other components load files themselves
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader


@dataclass
class ParsedFilingEntry:
    """
    Entry for a parsed filing folder.
    
    Contains only paths and folder-derived metadata.
    Does NOT contain file contents.
    
    Attributes:
        market: Market name
        company: Company name (from folder name)
        form: Document type/form (from folder name)
        date: Filing date (from folder name)
        filing_folder: Path to filing folder
        available_files: Dict of file types to paths
    """
    market: str
    company: str
    form: str
    date: str
    filing_folder: Path
    available_files: dict[str, Path]  # {extension: path}


class ParsedDataLoader:
    """
    Universal doorkeeper for parser output directory.
    
    Discovers filing folders and provides paths to all files.
    Does NOT load file contents - that's for other components.
    
    SINGLE ENTRY POINT: All parser output path discovery goes through this class.
    
    Example:
        loader = ParsedDataLoader()
        
        # Discover all filing folders
        filings = loader.discover_all_parsed_filings()
        
        # Get path to specific file
        json_path = loader.get_file_path(filing, 'json')
        
        # Other component loads it how they want
        import json
        with open(json_path) as f:
            data = json.load(f)
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize parsed data loader.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.parser_output_dir = self.config.get('parser_output_dir')
        self.logger = logging.getLogger('input.parsed_data')
        
        if not self.parser_output_dir:
            raise ValueError(
                "Parser output directory not configured. "
                "Check MAPPER_PARSER_OUTPUT_DIR in .env"
            )
        
        self.logger.info(f"ParsedDataLoader initialized: {self.parser_output_dir}")
    
    def discover_all_parsed_filings(self) -> list[ParsedFilingEntry]:
        """
        Discover all filing folders in parser output directory.
        
        Searches recursively for directories containing parsed data files.
        Works with ANY directory structure - finds filing folders at any depth.
        
        Returns:
            List of ParsedFilingEntry objects with paths to all files
            
        Example:
            filings = loader.discover_all_parsed_filings()
            for filing in filings:
                print(f"{filing.company} | Files: {list(filing.available_files.keys())}")
        """
        if not self.parser_output_dir.exists():
            self.logger.warning(f"Parser output directory not found: {self.parser_output_dir}")
            return []
        
        self.logger.info(f"Discovering filing folders in: {self.parser_output_dir}")
        
        # Find all directories containing parsed.json (the marker for a filing folder)
        # This works at ANY depth - parser can change structure without breaking mapper
        entries = []
        max_depth = 25  # Consistent with other loaders
        
        for json_file in self.parser_output_dir.rglob('parsed.json'):
            # Check depth to avoid infinite recursion
            depth = len(json_file.relative_to(self.parser_output_dir).parts)
            if depth > max_depth:
                continue
            
            filing_folder = json_file.parent
            entry = self._build_filing_entry_from_folder(filing_folder)
            if entry:
                entries.append(entry)
        
        self.logger.info(f"Discovered {len(entries)} valid filing entries")
        
        # Sort by company, form, date
        entries.sort(key=lambda e: (e.company, e.form, e.date))
        
        return entries
    
    def _build_filing_entry_from_folder(self, filing_folder: Path) -> Optional[ParsedFilingEntry]:
        try:
            # Extract metadata from path structure
            # Expected: .../market/company/form/date/
            parts = filing_folder.parts
            
            if len(parts) < 4:
                self.logger.warning(f"Path too shallow: {filing_folder}")
                return None
            
            # Extract from end of path
            date = parts[-1]      # Innermost directory
            form = parts[-2]      # Parent directory
            company = parts[-3]   # Grandparent directory
            market = parts[-4]    # Great-grandparent directory
            
            # Discover all files in folder
            available_files = self._discover_files(filing_folder)
            
            if not available_files:
                self.logger.warning(f"No files found in {filing_folder}")
                return None
            
            return ParsedFilingEntry(
                market=market,
                company=company,
                form=form,
                date=date,
                filing_folder=filing_folder,
                available_files=available_files
            )
            
        except Exception as e:
            self.logger.error(f"Error building entry for {filing_folder}: {e}")
            return None
    
    def _build_filing_entry(self, filing_folder: Path) -> Optional[ParsedFilingEntry]:
        """
        DEPRECATED: Old method for flat folder structure.
        
        This method expected flat structure: CompanyName_FormType_Date
        Now using _build_filing_entry_from_folder for nested structure.
        
        Kept for backwards compatibility but should not be called.
        """
        self.logger.warning(
            f"DEPRECATED: _build_filing_entry called for {filing_folder}. "
            "This method is deprecated - use _build_filing_entry_from_folder instead."
        )
        return None
    
    def _discover_files(self, filing_folder: Path) -> dict[str, Path]:
        """
        Discover all files in filing folder.
        
        Args:
            filing_folder: Path to filing folder
            
        Returns:
            Dictionary mapping file extension to path
            {'json': path/to/file.json, 'csv': path/to/file.csv, ...}
        """
        files = {}
        
        for file_path in filing_folder.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                # Store by extension (without the dot for easier lookup)
                key = ext[1:] if ext.startswith('.') else ext
                files[key] = file_path
        
        return files
    
    def get_file_path(self, filing: ParsedFilingEntry, file_type: str) -> Optional[Path]:
        """
        Get path to specific file type.
        
        Args:
            filing: ParsedFilingEntry
            file_type: File extension (json, csv, xlsx, txt, etc.)
            
        Returns:
            Path to file or None if not found
            
        Example:
            json_path = loader.get_file_path(filing, 'json')
            if json_path:
                # Load it yourself
                import json
                data = json.load(open(json_path))
        """
        return filing.available_files.get(file_type)
    
    def list_all_files(self, filing: ParsedFilingEntry) -> list[str]:
        """
        List all files in a filing folder.
        
        Args:
            filing: ParsedFilingEntry
            
        Returns:
            List of filenames
        """
        return [path.name for path in filing.available_files.values()]
    
    def get_file_info(self, file_path: Path) -> dict[str, any]:
        """
        Get file metadata (size, modified time, etc).
        
        Does NOT load file contents - just metadata.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dict with file metadata
        """
        if not file_path.exists():
            return {}
        
        stat = file_path.stat()
        return {
            'size_bytes': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'modified': stat.st_mtime,
            'name': file_path.name,
            'extension': file_path.suffix
        }


__all__ = ['ParsedDataLoader', 'ParsedFilingEntry']