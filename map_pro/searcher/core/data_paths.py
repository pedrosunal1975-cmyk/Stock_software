# Path: searcher/core/data_paths.py
"""
Searcher Data Paths Manager

Automatic directory creation and validation for searcher module.
Ensures all required directories exist and are writable.

Architecture:
- Minimal directory creation (only what's needed)
- Create on first use pattern
- Health checks for directory accessibility
"""

from pathlib import Path
from typing import Optional

from .config_loader import ConfigLoader


class DataPathsManager:
    """
    Manages directory creation and validation for searcher module.
    
    Creates required directories and validates permissions.
    Follows minimal creation principle - only creates what's needed.
    
    Example:
        manager = DataPathsManager()
        manager.ensure_all_directories()
        health = manager.health_check()
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize data paths manager.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self._created_dirs: list[Path] = []
        self._existing_dirs: list[Path] = []
        self._failed_dirs: list[tuple[Path, str]] = []
    
    def ensure_all_directories(self) -> dict:
        """
        Create all required directories for searcher module.
        
        Only creates essential directories:
        - Log directory
        - Cache directory (if caching enabled)
        - Export directory (if configured)
        
        Returns:
            Dictionary with creation statistics
        """
        self._created_dirs = []
        self._existing_dirs = []
        self._failed_dirs = []
        
        # Essential directories
        required_dirs = [
            self.config.get('searcher_log_dir'),
        ]
        
        # Optional directories
        if self.config.get('enable_cache'):
            cache_dir = self.config.get('searcher_cache_dir')
            if cache_dir:
                required_dirs.append(cache_dir)
        
        export_dir = self.config.get('searcher_export_dir')
        if export_dir:
            required_dirs.append(export_dir)
        
        # Filter out None values
        required_dirs = [d for d in required_dirs if d is not None]
        
        # Create each directory
        for directory in required_dirs:
            self._ensure_directory(directory)
        
        return {
            'created': self._created_dirs,
            'existing': self._existing_dirs,
            'failed': self._failed_dirs,
            'total_required': len(required_dirs),
            'success_rate': self._calculate_success_rate(),
        }
    
    def _ensure_directory(self, path: Path) -> bool:
        """
        Ensure a single directory exists.
        
        Args:
            path: Path to directory
            
        Returns:
            True if directory exists or was created, False if failed
        """
        try:
            if path.exists():
                if path.is_dir():
                    self._existing_dirs.append(path)
                    return True
                else:
                    error_msg = f"Path exists but is not a directory: {path}"
                    self._failed_dirs.append((path, error_msg))
                    return False
            
            # Create directory with parents
            path.mkdir(parents=True, exist_ok=True)
            self._created_dirs.append(path)
            return True
            
        except PermissionError as e:
            error_msg = f"Permission denied: {e}"
            self._failed_dirs.append((path, error_msg))
            return False
        except OSError as e:
            error_msg = f"OS error: {e}"
            self._failed_dirs.append((path, error_msg))
            return False
    
    def _calculate_success_rate(self) -> float:
        """
        Calculate success rate of directory creation.
        
        Returns:
            Success rate as percentage (0.0 to 100.0)
        """
        total = len(self._created_dirs) + len(self._existing_dirs) + len(self._failed_dirs)
        if total == 0:
            return 100.0
        
        successful = len(self._created_dirs) + len(self._existing_dirs)
        return (successful / total) * 100.0
    
    def validate_paths(self) -> dict:
        """
        Validate that all required paths exist and are accessible.
        
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        # Check log directory
        log_dir = self.config.get('searcher_log_dir')
        results['log_dir'] = self._validate_directory(log_dir, writable=True)
        
        # Check cache directory
        cache_dir = self.config.get('searcher_cache_dir')
        if cache_dir:
            results['cache_dir'] = self._validate_directory(cache_dir, writable=True)
        
        # Check export directory
        export_dir = self.config.get('searcher_export_dir')
        if export_dir:
            results['export_dir'] = self._validate_directory(export_dir, writable=True)
        
        # Check shared data directories (read-only validation)
        entities_dir = self.config.get('data_entities_dir')
        results['entities_dir'] = self._validate_directory(
            entities_dir,
            writable=False
        )
        
        taxonomies_dir = self.config.get('data_taxonomies_dir')
        results['taxonomies_dir'] = self._validate_directory(
            taxonomies_dir,
            writable=False
        )
        
        return results
    
    def _validate_directory(
        self,
        path: Optional[Path],
        writable: bool = False
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a single directory.
        
        Args:
            path: Path to validate
            writable: Whether to check write permissions
            
        Returns:
            Tuple of (valid, error_message)
        """
        if path is None:
            return (False, "Path not configured")
        
        if not path.exists():
            return (False, f"Path does not exist: {path}")
        
        if not path.is_dir():
            return (False, f"Path is not a directory: {path}")
        
        # Test read access
        try:
            list(path.iterdir())
        except PermissionError:
            return (False, "Permission denied - not readable")
        except OSError as e:
            return (False, f"OS error: {e}")
        
        # Test write access if required
        if writable:
            test_file = path / '.write_test'
            try:
                test_file.touch()
                test_file.unlink()
            except PermissionError:
                return (False, "Permission denied - not writable")
            except OSError as e:
                return (False, f"OS error: {e}")
        
        return (True, None)
    
    def health_check(self) -> dict:
        """
        Perform comprehensive health check of all paths.
        
        Returns:
            Dictionary with health check results
        """
        issues = []
        
        # Validate all paths
        path_validation = self.validate_paths()
        
        for path_name, (valid, error) in path_validation.items():
            if not valid:
                issues.append(f"{path_name}: {error}")
        
        # Determine overall status
        if len(issues) == 0:
            status = 'healthy'
        elif len(issues) <= 2:
            status = 'degraded'
        else:
            status = 'critical'
        
        return {
            'status': status,
            'path_validation': path_validation,
            'issues': issues,
            'total_issues': len(issues),
        }


def ensure_data_paths() -> dict:
    """
    Convenience function to ensure all data paths exist.
    
    Returns:
        Dictionary with creation results
    """
    manager = DataPathsManager()
    return manager.ensure_all_directories()


def validate_paths() -> dict:
    """
    Convenience function to validate all paths.
    
    Returns:
        Dictionary with validation results
    """
    manager = DataPathsManager()
    return manager.health_check()


__all__ = ['DataPathsManager', 'ensure_data_paths', 'validate_paths']