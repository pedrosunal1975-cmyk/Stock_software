# Path: library/loaders/taxonomy_loader.py
"""
Taxonomy Loader - Blind Mole for Taxonomy Files

Discovers taxonomy directories in taxonomies data bank.
Structure-agnostic doorkeeper - only returns paths, does NOT verify content.

Architecture:
- Scans libraries/ and manual_downloads/
- Returns directory paths
- No assumptions about internal structure
- Content verification is taxonomy_reader.py's job
"""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from library.core.config_loader import LibraryConfig
from library.core.logger import get_logger
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'loaders')


@dataclass
class TaxonomyLocation:
    """Location information for a taxonomy directory."""
    taxonomy_path: Path
    source_type: str  # 'libraries' or 'manual_downloads'
    directory_name: str
    relative_path: Path


class TaxonomyLoader:
    """
    Blind mole for discovering taxonomy directories.
    
    Scans libraries/ and manual_downloads/ directories.
    Does NOT verify file contents or completeness.
    """
    
    def __init__(self, config: Optional[LibraryConfig] = None):
        """Initialize taxonomy loader."""
        self.config = config if config else LibraryConfig()
        self.taxonomies_libraries = self.config.get('library_taxonomies_libraries')
        self.manual_downloads = self.config.get('library_manual_downloads')
        
        logger.info(f"{LOG_INPUT} TaxonomyLoader initialized")
    
    def discover_all(self) -> List[TaxonomyLocation]:
        """
        Discover all taxonomy directories in both sources.
        
        Returns:
            List of TaxonomyLocation objects
        """
        logger.info(f"{LOG_PROCESS} Discovering taxonomy directories")
        
        locations = []
        
        # Scan libraries directory
        if self.taxonomies_libraries.exists():
            locations.extend(self._scan_directory(
                self.taxonomies_libraries,
                'libraries'
            ))
        
        # Scan manual downloads directory
        if self.manual_downloads.exists():
            locations.extend(self._scan_directory(
                self.manual_downloads,
                'manual_downloads'
            ))
        
        logger.info(f"{LOG_OUTPUT} Discovered {len(locations)} taxonomy locations")
        
        return locations
    
    def discover_libraries(self) -> List[TaxonomyLocation]:
        """
        Discover taxonomies in libraries/ directory only.
        
        Returns:
            List of TaxonomyLocation objects from libraries/
        """
        logger.info(f"{LOG_PROCESS} Discovering libraries/ directory")
        
        locations = []
        
        if self.taxonomies_libraries.exists():
            locations = self._scan_directory(
                self.taxonomies_libraries,
                'libraries'
            )
        
        logger.info(f"{LOG_OUTPUT} Found {len(locations)} libraries")
        
        return locations
    
    def discover_manual_downloads(self) -> List[TaxonomyLocation]:
        """
        Discover files in manual_downloads/ directory.
        
        Returns:
            List of TaxonomyLocation objects from manual_downloads/
        """
        logger.info(f"{LOG_PROCESS} Discovering manual_downloads/ directory")
        
        locations = []
        
        if self.manual_downloads.exists():
            locations = self._scan_directory(
                self.manual_downloads,
                'manual_downloads'
            )
        
        logger.info(f"{LOG_OUTPUT} Found {len(locations)} manual files")
        
        return locations
    
    def _scan_directory(
        self,
        base_dir: Path,
        source_type: str
    ) -> List[TaxonomyLocation]:
        """
        Scan a directory for taxonomy folders.
        
        Args:
            base_dir: Base directory to scan
            source_type: 'libraries' or 'manual_downloads'
            
        Returns:
            List of TaxonomyLocation objects
        """
        locations = []
        
        try:
            for item in base_dir.iterdir():
                if item.is_dir():
                    try:
                        relative_path = item.relative_to(base_dir)
                        
                        location = TaxonomyLocation(
                            taxonomy_path=item,
                            source_type=source_type,
                            directory_name=item.name,
                            relative_path=relative_path
                        )
                        locations.append(location)
                        
                    except ValueError:
                        continue
                        
        except Exception as e:
            logger.error(f"Error scanning {base_dir}: {e}")
        
        return locations


__all__ = ['TaxonomyLoader', 'TaxonomyLocation']