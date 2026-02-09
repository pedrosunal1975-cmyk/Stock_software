# Path: core/data_paths.py
"""
Data Paths Manager

Automatic directory creation and path validation for the XBRL Mapper.
Ensures all required directories exist and are writable.

Creates two main directories:
- logs/ (for logging output)
- mapped_statements/ (for statement exports)
"""

from pathlib import Path
from typing import Optional
from ..core.config_loader import ConfigLoader

# ============================================================================
# CONSTANTS
# ============================================================================
BYTES_TO_KB: int = 1024  # Conversion factor from bytes to kilobytes
BYTES_TO_MB: int = 1024 * 1024  # Conversion factor from bytes to megabytes


class DataPathsManager:
    """
    Manages directory creation and validation for mapper data directories.
    
    Creates all required directories on the data centre partition,
    validates permissions, and provides health checks.
    
    Example:
        manager = DataPathsManager()
        manager.ensure_all_directories()
        health = manager.health_check()
    """
    
    def __init__(self):
        """Initialize the data paths manager with configuration."""
        self.config = ConfigLoader()
        self._created_dirs: list[Path] = []
        self._existing_dirs: list[Path] = []
        self._failed_dirs: list[tuple[Path, str]] = []
    
    def ensure_all_directories(self) -> dict:
        """
        Create all required directories for mapper operation.
        
        Creates directories on data centre partition only. Program files
        directories are not created (they should exist from git clone).
        
        Returns:
            Dictionary with statistics:
                - created: List of newly created directories
                - existing: List of directories that already existed
                - failed: List of (path, error) tuples for failed creations
        """
        # Reset tracking lists
        self._created_dirs = []
        self._existing_dirs = []
        self._failed_dirs = []
        
        # ================================================================
        # DATA CENTRE DIRECTORIES (Auto-create these)
        # ================================================================
        
        data_centre_dirs = [
            # Output directory for mapped statements
            self.config.get('output_mapped_dir'),
            
            # Logging directory
            self.config.get('log_dir'),
        ]
        
        # Filter out None values (optional paths)
        data_centre_dirs = [d for d in data_centre_dirs if d is not None]
        
        # Create each directory
        for directory in data_centre_dirs:
            self._ensure_directory(directory)
        
        return {
            'created': self._created_dirs,
            'existing': self._existing_dirs,
            'failed': self._failed_dirs,
            'total_required': len(data_centre_dirs),
            'success_rate': self._calculate_success_rate(),
        }
    
    def _ensure_directory(self, path: Path) -> bool:
        """
        Ensure a single directory exists, creating it if necessary.
        
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
        """Calculate success rate of directory creation."""
        total = len(self._created_dirs) + len(self._existing_dirs) + len(self._failed_dirs)
        if total == 0:
            return 100.0
        
        successful = len(self._created_dirs) + len(self._existing_dirs)
        return (successful / total) * 100.0
    
    def validate_input_paths(self) -> dict:
        """
        Validate that required input paths exist and are readable.
        
        Input paths are READ-ONLY external data sources:
        - XBRL filings directory (shared with parser)
        - Taxonomy directory (shared with parser)
        - Parser output directory (parsed.json files)
        - Taxonomy cache directory (parser's cache, read-only)
        
        These should already exist and are NOT created by this module.
        
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        # Check XBRL filings path
        filings_path = self.config.get('xbrl_filings_path')
        results['xbrl_filings'] = self._validate_input_path(filings_path)
        
        # Check taxonomy path
        taxonomy_path = self.config.get('taxonomy_path')
        results['taxonomies'] = self._validate_input_path(taxonomy_path)
        
        # Check parser output path (mapper's primary input)
        parser_output = self.config.get('parser_output_dir')
        results['parser_output'] = self._validate_input_path(parser_output)
        
        # Check taxonomy cache (reuse parser's cache)
        taxonomy_cache = self.config.get('taxonomy_cache_dir')
        results['taxonomy_cache'] = self._validate_input_path(taxonomy_cache)
        
        return results
    
    def _validate_input_path(self, path: Optional[Path]) -> tuple[bool, bool, Optional[str]]:
        """
        Validate a single input path.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple of (exists, readable, error_message)
        """
        if path is None:
            return (False, False, "Path not configured")
        
        if not path.exists():
            return (False, False, f"Path does not exist: {path}")
        
        if not path.is_dir():
            return (False, False, f"Path is not a directory: {path}")
        
        # Test read access
        try:
            list(path.iterdir())
            return (True, True, None)
        except PermissionError:
            return (True, False, "Permission denied - not readable")
        except OSError as e:
            return (True, False, f"OS error: {e}")
    
    def validate_output_paths(self) -> dict:
        """
        Validate that output paths are writable.
        
        Tests write permissions by attempting to create a temporary file.
        
        Returns:
            Dictionary with validation results for each output directory
        """
        results = {}
        
        output_dirs = {
            'output_mapped': self.config.get('output_mapped_dir'),
            'logs': self.config.get('log_dir'),
        }
        
        for name, path in output_dirs.items():
            results[name] = self._validate_output_path(path)
        
        return results
    
    def _validate_output_path(self, path: Optional[Path]) -> tuple[bool, Optional[str]]:
        """
        Validate a single output path is writable.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple of (writable, error_message)
        """
        if path is None:
            return (False, "Path not configured")
        
        if not path.exists():
            return (False, f"Path does not exist: {path}")
        
        if not path.is_dir():
            return (False, f"Path is not a directory: {path}")
        
        # Test write access
        test_file = path / '.write_test'
        try:
            test_file.touch()
            test_file.unlink()
            return (True, None)
        except PermissionError:
            return (False, "Permission denied - not writable")
        except OSError as e:
            return (False, f"OS error: {e}")
    
    def health_check(self) -> dict:
        """
        Perform comprehensive health check of all paths.
        
        Checks:
        1. Input paths exist and are readable
        2. Output paths exist and are writable
        3. Cache directories accessible
        4. Temporary directory writable
        5. Log directory writable
        
        Returns:
            Dictionary with health check results:
                - status: 'healthy', 'degraded', or 'critical'
                - input_paths: Validation results
                - output_paths: Validation results
                - issues: List of issues found
        """
        issues = []
        
        # Check input paths
        input_validation = self.validate_input_paths()
        for name, (exists, readable, error) in input_validation.items():
            if not exists or not readable:
                issues.append(f"Input path '{name}': {error}")
        
        # Check output paths
        output_validation = self.validate_output_paths()
        for name, (writable, error) in output_validation.items():
            if not writable:
                issues.append(f"Output path '{name}': {error}")
        
        # Determine overall status
        if len(issues) == 0:
            status = 'healthy'
        elif len(issues) <= 2:
            status = 'degraded'
        else:
            status = 'critical'
        
        return {
            'status': status,
            'input_paths': input_validation,
            'output_paths': output_validation,
            'issues': issues,
            'total_issues': len(issues),
        }
    
    def get_directory_stats(self) -> dict:
        """
        Get statistics about directory sizes and file counts.
        
        Returns:
            Dictionary with stats for each directory
        """
        stats = {}
        
        dirs_to_check = {
            'output_mapped': self.config.get('output_mapped_dir'),
            'logs': self.config.get('log_dir'),
        }
        
        for name, path in dirs_to_check.items():
            if path and path.exists():
                stats[name] = self._get_directory_stats(path)
            else:
                stats[name] = {'size_mb': 0, 'file_count': 0, 'subdirectory_count': 0}
        
        return stats
    
    def _get_directory_stats(self, path: Path) -> dict:
        """Get statistics for a single directory."""
        try:
            total_size = 0
            file_count = 0
            subdir_count = 0
            
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    subdir_count += 1
            
            return {
                'size_mb': round(total_size / BYTES_TO_MB, 2),
                'file_count': file_count,
                'subdirectory_count': subdir_count,
            }
        except (PermissionError, OSError):
            return {'size_mb': 0, 'file_count': 0, 'subdirectory_count': 0}
    
    def cleanup_temp_directory(self) -> dict:
        """
        Clean up temporary directory.
        
        Removes all files from temp directory but keeps the
        directory structure intact.
        
        Returns:
            Dictionary with cleanup results
        """
        files_removed = 0
        space_freed = 0
        errors = []
        
        temp_dir = self.config.get('temp_dir')
        
        if temp_dir is None or not temp_dir.exists():
            return {
                'files_removed': 0,
                'space_freed_mb': 0.0,
                'errors': ['Temp directory does not exist'],
            }
        
        try:
            for item in temp_dir.rglob('*'):
                if item.is_file():
                    try:
                        size = item.stat().st_size
                        item.unlink()
                        files_removed += 1
                        space_freed += size
                    except (PermissionError, OSError) as e:
                        errors.append(f"Failed to remove {item}: {e}")
        except (PermissionError, OSError) as e:
            errors.append(f"Failed to access {temp_dir}: {e}")
        
        return {
            'files_removed': files_removed,
            'space_freed_mb': round(space_freed / BYTES_TO_MB, 2),
            'errors': errors,
        }


def ensure_data_paths() -> dict:
    """
    Convenience function to ensure all data paths exist.
    
    This is the main entry point for directory setup.
    Call this at mapper startup to ensure all directories are ready.
    
    Returns:
        Dictionary with creation results
        
    Example:
        from ..core.data_paths import ensure_data_paths
        
        result = ensure_data_paths()
        if result['failed']:
            print("Failed to create some directories:")
            for path, error in result['failed']:
                print(f"  {path}: {error}")
    """
    manager = DataPathsManager()
    return manager.ensure_all_directories()


def validate_paths() -> dict:
    """
    Convenience function to validate all paths.
    
    Returns:
        Dictionary with validation results
        
    Example:
        from ..core.data_paths import validate_paths
        
        validation = validate_paths()
        if validation['status'] != 'healthy':
            print(f"Path issues: {validation['issues']}")
    """
    manager = DataPathsManager()
    return manager.health_check()


__all__ = ['DataPathsManager', 'ensure_data_paths', 'validate_paths']