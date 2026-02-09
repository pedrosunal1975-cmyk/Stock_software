# Path: loaders/taxonomy.py
"""
Taxonomy Library Loader

Simple recursive file accessor for taxonomy library files.

DESIGN PRINCIPLES:
- Uses ConfigLoader for path resolution (NO hardcoded paths)
- Recursive file discovery (up to 25 levels deep)
- NO hardcoded file types or patterns
- NO parsing or processing - just file access
- Market-agnostic

RESPONSIBILITY: Provide access to taxonomy files. That's it.
Calling mechanisms decide what to do with the files.
"""

from pathlib import Path
from typing import Optional
from ..core.config_loader import ConfigLoader
import logging 

class TaxonomyLoader:
    """
    Provides recursive access to taxonomy library files.
    NO processing, NO filtering - just discovers and lists files.
    Calling code decides what to do with them.
    """
    MAX_DEPTH = 25
    MAX_FILE_SIZE = 500 * 1024 * 1024

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize taxonomy library loader.
        Args:
            config: Optional ConfigLoader instance (creates new if not provided)
        """
        self.config = config if config else ConfigLoader()
        self.taxonomy_path = self.config.get('taxonomy_path')
        if not self.taxonomy_path:
            raise ValueError(
                "taxonomy_path not configured. "
                "Check .env for 'PARSER_TAXONOMY_PATH'"
            )
        self.logger = logging.getLogger('input.taxonomy')
        self.logger.info(f"TaxonomyLoader initialized: {self.taxonomy_path}") 
    
    def get_taxonomy_directory(self, taxonomy_id: str) -> Path:
        """
        Get taxonomy library directory path.
        
        Args:
            taxonomy_id: Taxonomy identifier (subdirectory name)
            
        Returns:
            Path to taxonomy library directory
            
        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        taxonomy_dir = self.taxonomy_path / taxonomy_id
        
        if not taxonomy_dir.exists():
            raise FileNotFoundError(
                f"Taxonomy library not found: {taxonomy_dir}\n"
                f"Searched in: {self.taxonomy_path}"
            )
        
        if not taxonomy_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {taxonomy_dir}")
        
        return taxonomy_dir
    
    def discover_all_files(
        self,
        taxonomy_id: str = None,
        max_depth: int = None
    ) -> list[Path]:
        """
        Recursively discover ALL files in taxonomy library.
        
        NO filtering - returns everything. Caller decides what to use.
        
        Args:
            taxonomy_id: Optional taxonomy identifier (subdirectory)
            max_depth: Optional depth limit (default: 25)
            
        Returns:
            list of all file paths found
        """
        if taxonomy_id:
            search_dir = self.get_taxonomy_directory(taxonomy_id)
        else:
            search_dir = self.taxonomy_path
        
        depth = max_depth if max_depth is not None else self.MAX_DEPTH
        
        self.logger.info(f"File discovery started: {search_dir, depth}")
        
        files = self._recursive_discover(search_dir, current_depth=0, max_depth=depth)
        
        self.logger.info(f"File discovery completed: {len(files)} files found")
        
        return files
    
    def list_taxonomies(self) -> list[Path]:
        """
        list available taxonomy directories (non-recursive).
        
        Returns:
            list of taxonomy directory paths
        """
        if not self.taxonomy_path.exists():
            raise FileNotFoundError(f"Taxonomy root not found: {self.taxonomy_path}")
        
        taxonomies = [
            item for item in self.taxonomy_path.iterdir()
            if item.is_dir() and not item.is_symlink()
        ]
        
        return sorted(taxonomies)
    
    def _recursive_discover(
        self,
        directory: Path,
        current_depth: int,
        max_depth: int
    ) -> list[Path]:
        """
        Recursively discover files with depth limit.
        
        Args:
            directory: Directory to search
            current_depth: Current recursion depth
            max_depth: Maximum recursion depth
            
        Returns:
            list of file paths
        """
        if current_depth > max_depth:
            self.logger.debug(f"Max depth {max_depth} reached at: {directory}")
            return []
        
        discovered = []
        
        try:
            for item in directory.iterdir():
                if item.is_symlink():
                    continue
                
                if item.is_dir():
                    discovered.extend(
                        self._recursive_discover(item, current_depth + 1, max_depth)
                    )
                
                elif item.is_file():
                    try:
                        if item.stat().st_size > self.MAX_FILE_SIZE:
                            self.logger.warning('file_discovery', f"Skipping large file: {item}")
                            continue
                    except OSError:
                        continue
                    
                    discovered.append(item)
        
        except PermissionError:
            self.logger.warning('file_discovery', f"Permission denied: {directory}")
        except Exception as e:
            self.logger.error('file_discovery', f"Error in {directory}: {e}")
        
        return discovered


__all__ = ['TaxonomyLoader']