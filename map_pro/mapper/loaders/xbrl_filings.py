# Path: loaders/xbrl_filings.py
"""
XBRL Filings Loader

Simple recursive file accessor for XBRL filing files.

DESIGN PRINCIPLES:
- Uses ConfigLoader for path resolution (NO hardcoded paths)
- Recursive file discovery (up to 25 levels deep)
- NO hardcoded file types or patterns
- NO parsing or processing - just file access
- Market-agnostic

RESPONSIBILITY: Provide access to XBRL files. That's it.
Calling mechanisms decide what to do with the files.

DOORKEEPER: Single entry point for XBRL filing file access.
"""

import logging
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader


class XBRLFilingsLoader:
    """
    Provides recursive access to XBRL filing files.
    
    NO processing, NO filtering - just discovers and lists files.
    Calling code decides what to do with them.
    
    DOORKEEPER: All XBRL filing file access must go through this class.
    """
    
    MAX_DEPTH = 25
    MAX_FILE_SIZE = 500 * 1024 * 1024
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize XBRL filings loader.
        
        Args:
            config: Optional ConfigLoader instance (creates new if not provided)
        """
        self.config = config if config else ConfigLoader()
        self.xbrl_path = self.config.get('xbrl_filings_path')
        
        if not self.xbrl_path:
            raise ValueError(
                "xbrl_filings_path not configured. "
                "Check .env for 'MAPPER_XBRL_FILINGS_PATH'"
            )
        
        self.logger = logging.getLogger('input.xbrl_filings')
        self.logger.info(f"XBRLFilingsLoader initialized: {self.xbrl_path}")
    
    def discover_all_files(
        self,
        subdirectory: str = None,
        max_depth: int = None
    ) -> list[Path]:
        """
        Recursively discover ALL files in XBRL filing directory.
        
        NO filtering - returns everything. Caller decides what to use.
        
        Args:
            subdirectory: Optional subdirectory to search in
            max_depth: Optional depth limit (default: 25)
            
        Returns:
            List of all file paths found
        """
        search_dir = self.xbrl_path / subdirectory if subdirectory else self.xbrl_path
        
        if not search_dir.exists():
            raise FileNotFoundError(f"Directory not found: {search_dir}")
        
        depth = max_depth if max_depth is not None else self.MAX_DEPTH
        
        self.logger.info(f"File discovery started: {search_dir} (max depth: {depth})")
        
        files = self._recursive_discover(search_dir, current_depth=0, max_depth=depth)
        
        self.logger.info(f"File discovery completed: {len(files)} files found")
        
        return files
    
    def get_filing_directory(self, relative_path: str) -> Path:
        """
        Get filing directory path.
        
        Args:
            relative_path: Path relative to XBRL filings root
            
        Returns:
            Absolute Path to filing directory
            
        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        filing_dir = self.xbrl_path / relative_path
        
        if not filing_dir.exists():
            raise FileNotFoundError(f"Filing directory not found: {filing_dir}")
        
        if not filing_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {filing_dir}")
        
        return filing_dir
    
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
            List of file paths
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
                            self.logger.warning(f"Skipping large file: {item}")
                            continue
                    except OSError:
                        continue
                    
                    discovered.append(item)
        
        except PermissionError:
            self.logger.warning(f"Permission denied: {directory}")
        except Exception as e:
            self.logger.error(f"Error in {directory}: {e}")
        
        return discovered


__all__ = ['XBRLFilingsLoader']
