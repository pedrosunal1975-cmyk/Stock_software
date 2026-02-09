# Path: library/core/data_paths.py
"""
Library Data Paths Manager

Manages all filesystem paths for library module.
Automatically creates required directories on initialization.

Usage:
    from library.core.data_paths import LibraryPaths
    
    paths = LibraryPaths()
    paths.ensure_all_directories()
"""

from pathlib import Path
from typing import Optional

from library.core.config_loader import LibraryConfig
from library.core.logger import get_logger
from library.constants import LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'core')


class LibraryPaths:
    """
    Library filesystem paths manager.
    
    Provides centralized access to all library paths
    and ensures required directories exist.
    """
    
    def __init__(self, config: Optional[LibraryConfig] = None):
        """
        Initialize paths manager.
        
        Args:
            config: Optional LibraryConfig instance (creates if not provided)
        """
        self.config = config if config else LibraryConfig()
        
        # Load all paths from configuration
        self.taxonomies_root = self.config.get('library_taxonomies_root')
        self.taxonomies_libraries = self.config.get('library_taxonomies_libraries')
        self.parsed_files_dir = self.config.get('library_parsed_files_dir')
        self.manual_downloads = self.config.get('library_manual_downloads')
        self.cache_dir = self.config.get('library_cache_dir')
        self.temp_dir = self.config.get('library_temp_dir')
        self.log_dir = self.config.get('library_log_dir')
        
        logger.debug(f"{LOG_PROCESS} Paths manager initialized")
    
    def ensure_all_directories(self) -> None:
        """
        Create all required directories if they don't exist.
        
        Creates:
        - Taxonomy root directory
        - Taxonomy libraries storage
        - Manual download directories
        - Cache and temp directories
        - Log directory
        
        Note: Does NOT create parsed_files_dir as that's managed by parser module
        """
        logger.info(f"{LOG_PROCESS} Ensuring all library directories exist")
        
        directories_to_create = [
            ('Taxonomies Root', self.taxonomies_root),
            ('Taxonomy Libraries', self.taxonomies_libraries),
            ('Manual Downloads', self.manual_downloads),
            ('Cache', self.cache_dir),
            ('Temp', self.temp_dir),
            ('Logs', self.log_dir),
        ]
        
        created_count = 0
        for name, path in directories_to_create:
            if self._ensure_directory(path, name):
                created_count += 1
        
        if created_count > 0:
            logger.info(f"{LOG_OUTPUT} Created {created_count} new directories")
        else:
            logger.info(f"{LOG_OUTPUT} All directories already exist")
    
    def _ensure_directory(self, path: Path, name: str) -> bool:
        """
        Create directory if it doesn't exist.
        
        Args:
            path: Directory path
            name: Directory name (for logging)
            
        Returns:
            True if directory was created, False if it already existed
        """
        if path.exists():
            logger.debug(f"{LOG_OUTPUT} {name} directory already exists: {path}")
            return False
        
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"{LOG_OUTPUT} Created {name} directory: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create {name} directory {path}: {e}")
            raise
    
    def get_parsed_json_path(
        self,
        market: str,
        company: str,
        form: str,
        accession: str
    ) -> Path:
        """
        Build path to parsed.json file for a filing.
        
        Args:
            market: Market type (e.g., 'sec', 'fca')
            company: Company name (normalized)
            form: Form type (e.g., '10-K')
            accession: Accession number
            
        Returns:
            Path to parsed.json file
        """
        return (
            self.parsed_files_dir /
            market /
            company /
            'filings' /
            form /
            accession /
            'parsed.json'
        )
    
    def get_library_directory(
        self,
        taxonomy_name: str,
        version: str
    ) -> Path:
        """
        Build path to taxonomy library directory.

        Uses nested structure: taxonomies/libraries/{name}/{version}/
        Example: taxonomies/libraries/ifrs-full/2022/

        Args:
            taxonomy_name: Taxonomy name (e.g., 'us-gaap', 'ifrs-full')
            version: Taxonomy version (e.g., '2024', '2022')

        Returns:
            Path to library directory
        """
        return self.taxonomies_libraries / taxonomy_name / version
    
    def get_manual_file_path(self, filename: str) -> Path:
        """
        Build path to file in manual downloads directory.
        
        Args:
            filename: File name
            
        Returns:
            Path to file in manual downloads directory
        """
        return self.manual_downloads / filename
    
    def get_cache_file_path(self, cache_key: str) -> Path:
        """
        Build path to cache file.
        
        Args:
            cache_key: Cache key (will be sanitized)
            
        Returns:
            Path to cache file
        """
        # Sanitize cache key for filesystem
        safe_key = cache_key.replace('/', '_').replace('\\', '_')
        return self.cache_dir / f"{safe_key}.json"
    
    def get_temp_file_path(self, filename: str) -> Path:
        """
        Build path to temporary file.
        
        Args:
            filename: Temporary file name
            
        Returns:
            Path to temporary file
        """
        return self.temp_dir / filename
    
    def cleanup_temp_directory(self) -> int:
        """
        Clean up temporary directory.
        
        Removes all files in temp directory.
        
        Returns:
            Number of files removed
        """
        if not self.temp_dir.exists():
            return 0
        
        removed_count = 0
        for file_path in self.temp_dir.iterdir():
            if file_path.is_file():
                try:
                    file_path.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {file_path}: {e}")
        
        logger.info(f"{LOG_OUTPUT} Cleaned up {removed_count} temporary files")
        return removed_count
    
    def get_directory_stats(self) -> dict:
        """
        Get statistics about library directories.
        
        Returns:
            Dictionary with directory statistics
        """
        def count_files(directory: Path) -> int:
            """Count files in directory recursively."""
            if not directory.exists():
                return 0
            return sum(1 for _ in directory.rglob('*') if _.is_file())
        
        return {
            'libraries_count': len(list(self.taxonomies_libraries.iterdir())) if self.taxonomies_libraries.exists() else 0,
            'manual_downloads_count': count_files(self.manual_downloads),
            'cache_files_count': count_files(self.cache_dir),
            'temp_files_count': count_files(self.temp_dir),
        }


__all__ = ['LibraryPaths']