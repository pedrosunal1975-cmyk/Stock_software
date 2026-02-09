# Path: mat_acc/core/data_paths.py
"""
Data Paths Manager for mat_acc (Mathematical Accountancy)

Automatic directory creation and path validation for the analysis system.
Ensures all required directories exist and are writable.

Creates directories in data partition only (/mnt/mat_acc/):
- output/ (general output)
- reports/ (analysis reports)
- ratios/ (calculated ratios)
- normalized/ (normalized statements)
- graphs/ (CSV, Excel, visualization data)
- audit/ (audit trails)
- logs/ (IPO logging)
- cache/ (optional caching)
- database/ (SQLite database files)

Note: Does NOT create directories in input paths (map_pro directories).
Those are READ-ONLY and should already exist.
"""

import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_loader import ConfigLoader


# ==============================================================================
# CONSTANTS
# ==============================================================================
BYTES_TO_KB: int = 1024
BYTES_TO_MB: int = 1024 * 1024


class DataPathsManager:
    """
    Manages directory creation and validation for mat_acc data directories.

    Creates all required directories on the data partition,
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
        Create all required directories for mat_acc operation.

        Creates directories on data partition only. Program files
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
        # DATA PARTITION DIRECTORIES (Auto-create these)
        # ================================================================

        data_dirs = [
            # Base data root
            self.config.get('data_root'),

            # Output directories
            self.config.get('output_dir'),
            self.config.get('reports_dir'),
            self.config.get('ratios_dir'),
            self.config.get('normalized_dir'),
            self.config.get('graphs_dir'),
            self.config.get('audit_dir'),

            # Logging directory
            self.config.get('log_dir'),

            # Cache directory (optional)
            self.config.get('cache_dir'),

            # Database directory (for SQLite database files)
            self.config.get('database_dir'),
        ]

        # Filter out None values (optional paths)
        data_dirs = [d for d in data_dirs if d is not None]

        # Create each directory
        for directory in data_dirs:
            self._ensure_directory(directory)

        return {
            'created': self._created_dirs,
            'existing': self._existing_dirs,
            'failed': self._failed_dirs,
            'total_required': len(data_dirs),
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

    def validate_input_paths(self, required_only: bool = True) -> dict:
        """
        Validate that required input paths exist and are readable.

        Input paths are READ-ONLY external data sources from map_pro:
        - Verification reports directory (REQUIRED - primary input)
        - Mapper output directory (mapped statements)
        - Parser output directory (parsed.json files)
        - XBRL filings directory
        - Taxonomy directory (OPTIONAL - created by library.py)

        These should already exist and are NOT created by this module.

        Args:
            required_only: If True, only check verification_reports_dir.
                          Other paths are created by library.py workflow.

        Returns:
            Dictionary with validation results
        """
        # Required paths that must exist before mat_acc can run
        required_paths = {
            'verification_reports_dir': self.config.get('verification_reports_dir'),
        }

        # Optional paths - created by library.py or other map_pro modules
        optional_paths = {
            'mapper_output_dir': self.config.get('mapper_output_dir'),
            'parser_output_dir': self.config.get('parser_output_dir'),
            'xbrl_filings_dir': self.config.get('xbrl_filings_dir'),
            'taxonomy_dir': self.config.get('taxonomy_dir'),
        }

        # Choose which paths to validate
        input_paths = required_paths if required_only else {**required_paths, **optional_paths}

        results = {
            'valid': [],
            'missing': [],
            'not_directory': [],
            'not_readable': [],
        }

        for name, path in input_paths.items():
            if path is None:
                results['missing'].append(name)
                continue

            if not path.exists():
                results['missing'].append((name, str(path)))
                continue

            if not path.is_dir():
                results['not_directory'].append((name, str(path)))
                continue

            # Check if readable
            try:
                list(path.iterdir())
                results['valid'].append((name, str(path)))
            except PermissionError:
                results['not_readable'].append((name, str(path)))

        return results

    def health_check(self) -> dict:
        """
        Perform comprehensive health check of all paths.

        Returns:
            Dictionary with health status:
                - status: 'healthy', 'degraded', or 'critical'
                - output_paths: Output directory validation results
                - input_paths: Input directory validation results
                - disk_space: Available disk space info
        """
        # Check output directories
        output_result = self.ensure_all_directories()

        # Check input directories
        input_result = self.validate_input_paths()

        # Determine overall status
        if output_result['failed'] or input_result['missing']:
            if len(output_result['failed']) > 2 or len(input_result['missing']) > 2:
                status = 'critical'
            else:
                status = 'degraded'
        else:
            status = 'healthy'

        # Check disk space
        data_root = self.config.get('data_root')
        disk_info = self._get_disk_space(data_root) if data_root else None

        return {
            'status': status,
            'output_paths': output_result,
            'input_paths': input_result,
            'disk_space': disk_info,
        }

    def _get_disk_space(self, path: Path) -> Optional[dict]:
        """
        Get disk space information for a path.

        Args:
            path: Path to check

        Returns:
            Dictionary with disk space info or None if unavailable
        """
        try:
            import shutil
            total, used, free = shutil.disk_usage(path)
            return {
                'total_gb': round(total / (1024 ** 3), 2),
                'used_gb': round(used / (1024 ** 3), 2),
                'free_gb': round(free / (1024 ** 3), 2),
                'percent_used': round((used / total) * 100, 1),
            }
        except Exception:
            return None

    def get_output_path(
        self,
        market: str,
        company: str,
        form: str,
        date: str,
        output_type: str = 'reports'
    ) -> Path:
        """
        Build output path following standard structure.

        Args:
            market: Market identifier (e.g., 'sec')
            company: Company name
            form: Form type (e.g., '10_K')
            date: Filing date (e.g., '2025-10-13')
            output_type: One of 'reports', 'ratios', 'normalized', 'graphs', 'audit'

        Returns:
            Path to output directory
        """
        type_dirs = {
            'reports': self.config.get('reports_dir'),
            'ratios': self.config.get('ratios_dir'),
            'normalized': self.config.get('normalized_dir'),
            'graphs': self.config.get('graphs_dir'),
            'audit': self.config.get('audit_dir'),
        }

        base_dir = type_dirs.get(output_type, self.config.get('output_dir'))

        if base_dir is None:
            raise ValueError(f"Output directory not configured for type: {output_type}")

        return base_dir / market / company / form / date


def ensure_mat_acc_directories() -> dict:
    """
    Convenience function to ensure all mat_acc directories exist.

    Returns:
        Dictionary with directory creation results
    """
    manager = DataPathsManager()
    return manager.ensure_all_directories()


__all__ = [
    'DataPathsManager',
    'ensure_mat_acc_directories',
]
