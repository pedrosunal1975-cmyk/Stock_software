# Path: library/loaders/parsed_loader.py
"""
Parsed Loader - Blind Mole for Parsed Files

Discovers parsed.json files at ANY depth in parser output directory.
Structure-agnostic doorkeeper - only returns paths, does NOT read content.

Architecture:
- Recursive search for parsed.json files
- No assumptions about folder structure
- Returns paths only
- Content reading is parsed_reader.py's job
"""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from library.core.config_loader import LibraryConfig
from library.core.logger import get_logger
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT, PARSED_JSON_FILENAME

logger = get_logger(__name__, 'loaders')


@dataclass
class ParsedFileLocation:
    """Location information for a parsed.json file."""
    parsed_json_path: Path
    filing_folder: Path
    relative_path: Path
    depth: int


class ParsedLoader:
    """
    Blind mole for discovering parsed.json files.
    
    NO structure assumptions - finds files at any depth.
    Does NOT read file contents.
    """
    
    def __init__(self, config: Optional[LibraryConfig] = None):
        """Initialize parsed loader."""
        self.config = config if config else LibraryConfig()
        self.parsed_files_dir = self.config.get('library_parsed_files_dir')
        
        if not self.parsed_files_dir:
            raise ValueError(
                "Parsed files directory not configured. "
                "Check LIBRARY_PARSED_FILES_DIR in .env"
            )
        
        logger.info(f"{LOG_INPUT} ParsedLoader initialized: {self.parsed_files_dir}")
    
    def discover_all(self) -> List[ParsedFileLocation]:
        """
        Discover all parsed.json files at any depth.
        
        Returns:
            List of ParsedFileLocation objects
        """
        if not self.parsed_files_dir.exists():
            logger.warning(f"Directory not found: {self.parsed_files_dir}")
            self.parsed_files_dir.mkdir(parents=True, exist_ok=True)
            return []
        
        logger.info(f"{LOG_PROCESS} Discovering parsed.json files in: {self.parsed_files_dir}")
        
        locations = []
        max_depth = 25
        
        for json_file in self.parsed_files_dir.rglob(PARSED_JSON_FILENAME):
            try:
                relative_path = json_file.relative_to(self.parsed_files_dir)
                depth = len(relative_path.parts)
                
                if depth > max_depth:
                    continue
                
                location = ParsedFileLocation(
                    parsed_json_path=json_file,
                    filing_folder=json_file.parent,
                    relative_path=relative_path,
                    depth=depth
                )
                locations.append(location)
                
            except ValueError:
                continue
        
        logger.info(f"{LOG_OUTPUT} Discovered {len(locations)} parsed.json files")
        
        return locations


__all__ = ['ParsedLoader', 'ParsedFileLocation']