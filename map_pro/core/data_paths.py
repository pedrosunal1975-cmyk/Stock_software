# Path: core/data_paths.py
"""
Map Pro Core Data Paths Manager

Automatic directory creation for essential application paths.
Ensures PostgreSQL data directory exists before application startup.

Architecture:
- Creates only essential startup directories
- PostgreSQL data directory is critical for database service
- Each module has its own data_paths.py for module-specific directories
- This manager handles root-level directory initialization only

Note:
    Module-specific directory creation is handled by their respective
    data_paths.py files (database/core/, searcher/core/, etc.)
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from core.config_loader import CoreConfigLoader, get_core_config


class CoreDataPathsManager:
    """
    Manages essential directory creation for Map Pro startup.

    Focused on creating the PostgreSQL data directory which is
    required before the database service can start.

    Example:
        manager = CoreDataPathsManager()
        result = manager.ensure_postgresql_data_dir()
        if result['success']:
            print("PostgreSQL data directory ready")
    """

    def __init__(self, config: Optional[CoreConfigLoader] = None):
        """
        Initialize core data paths manager.

        Args:
            config: Optional CoreConfigLoader instance
        """
        self.config = config if config else get_core_config()
        self._results = {
            'created': [],
            'existing': [],
            'failed': [],
        }

    def ensure_postgresql_data_dir(self) -> Dict:
        """
        Ensure PostgreSQL data directory exists.

        This is the primary function - creates the PostgreSQL data
        directory so the database service can start.

        Returns:
            Dictionary with creation result:
                - success: bool
                - path: Path that was checked/created
                - action: 'created', 'exists', or 'failed'
                - message: Human-readable status message
                - needs_init: Whether initdb needs to be run
        """
        pg_data_dir = self.config.get_postgresql_data_dir()

        if pg_data_dir is None:
            return {
                'success': False,
                'path': None,
                'action': 'failed',
                'message': 'PostgreSQL data directory not configured in .env',
                'needs_init': False,
            }

        # Check if directory already exists and has data
        if pg_data_dir.exists():
            # Check if it contains PostgreSQL data (has PG_VERSION file)
            # Use sudo to check since the directory may be owned by postgres
            pg_version_file = pg_data_dir / 'PG_VERSION'
            try:
                is_initialized = pg_version_file.exists()
            except PermissionError:
                # If we can't read, it's likely owned by postgres (initdb ran)
                is_initialized = True

            if is_initialized:
                return {
                    'success': True,
                    'path': pg_data_dir,
                    'action': 'exists',
                    'message': f'PostgreSQL data directory exists and initialized: {pg_data_dir}',
                    'needs_init': False,
                }
            else:
                # Directory exists but empty or not initialized
                return {
                    'success': True,
                    'path': pg_data_dir,
                    'action': 'exists',
                    'message': f'PostgreSQL data directory exists but needs initialization: {pg_data_dir}',
                    'needs_init': True,
                }

        # Create directory
        try:
            pg_data_dir.mkdir(parents=True, exist_ok=True)
            self._results['created'].append(pg_data_dir)

            return {
                'success': True,
                'path': pg_data_dir,
                'action': 'created',
                'message': f'Created PostgreSQL data directory: {pg_data_dir}',
                'needs_init': True,
            }

        except PermissionError as e:
            self._results['failed'].append((pg_data_dir, str(e)))
            return {
                'success': False,
                'path': pg_data_dir,
                'action': 'failed',
                'message': f'Permission denied creating directory: {pg_data_dir}',
                'needs_init': False,
            }

        except OSError as e:
            self._results['failed'].append((pg_data_dir, str(e)))
            return {
                'success': False,
                'path': pg_data_dir,
                'action': 'failed',
                'message': f'Failed to create directory: {e}',
                'needs_init': False,
            }

    def ensure_all_core_directories(self) -> Dict:
        """
        Ensure all essential core directories exist.

        Creates:
        - PostgreSQL data directory
        - Core log directory

        Returns:
            Dictionary with creation statistics
        """
        self._results = {
            'created': [],
            'existing': [],
            'failed': [],
        }

        results = {}

        # PostgreSQL data directory (critical)
        results['postgresql_data'] = self.ensure_postgresql_data_dir()

        # Log directory
        log_dir = self.config.get('log_dir')
        if log_dir:
            results['log_dir'] = self._ensure_directory(log_dir)

        # Database root directory
        db_root = self.config.get('db_root_dir')
        if db_root:
            results['db_root'] = self._ensure_directory(db_root)

        return {
            'directories': results,
            'summary': {
                'created': len(self._results['created']),
                'existing': len(self._results['existing']),
                'failed': len(self._results['failed']),
            },
            'all_success': len(self._results['failed']) == 0,
        }

    def _ensure_directory(self, path: Path) -> Dict:
        """
        Ensure a single directory exists.

        Args:
            path: Path to directory

        Returns:
            Dictionary with result
        """
        try:
            if path.exists():
                if path.is_dir():
                    self._results['existing'].append(path)
                    return {
                        'success': True,
                        'path': path,
                        'action': 'exists',
                        'message': f'Directory exists: {path}',
                    }
                else:
                    self._results['failed'].append((path, 'Path exists but is not a directory'))
                    return {
                        'success': False,
                        'path': path,
                        'action': 'failed',
                        'message': f'Path exists but is not a directory: {path}',
                    }

            # Create directory
            path.mkdir(parents=True, exist_ok=True)
            self._results['created'].append(path)

            return {
                'success': True,
                'path': path,
                'action': 'created',
                'message': f'Created directory: {path}',
            }

        except PermissionError as e:
            self._results['failed'].append((path, str(e)))
            return {
                'success': False,
                'path': path,
                'action': 'failed',
                'message': f'Permission denied: {path}',
            }

        except OSError as e:
            self._results['failed'].append((path, str(e)))
            return {
                'success': False,
                'path': path,
                'action': 'failed',
                'message': f'OS error: {e}',
            }

    def get_initdb_command(self) -> str:
        """
        Get the command to initialize PostgreSQL database.

        Returns:
            Command string for initializing PostgreSQL
        """
        pg_data_dir = self.config.get_postgresql_data_dir()
        return (
            f"sudo -u postgres initdb "
            f"--locale=C.UTF-8 --encoding=UTF8 "
            f"-D '{pg_data_dir}'"
        )

    def print_initialization_instructions(self) -> None:
        """Print instructions for initializing PostgreSQL."""
        pg_data_dir = self.config.get_postgresql_data_dir()

        print("\n" + "=" * 70)
        print("PostgreSQL Initialization Required")
        print("=" * 70)
        print(f"\nThe PostgreSQL data directory has been created at:")
        print(f"  {pg_data_dir}")
        print("\nTo initialize the database, run these commands:")
        print(f"\n  1. Set ownership (if needed):")
        print(f"     sudo chown -R postgres:postgres {pg_data_dir}")
        print(f"\n  2. Initialize the database cluster:")
        print(f"     {self.get_initdb_command()}")
        print(f"\n  3. Start PostgreSQL:")
        print(f"     sudo systemctl start postgresql")
        print("\n" + "=" * 70)


def ensure_core_paths() -> Dict:
    """
    Convenience function to ensure all core paths exist.

    Call this at application startup before initializing modules.

    Returns:
        Dictionary with creation results
    """
    manager = CoreDataPathsManager()
    return manager.ensure_all_core_directories()


def ensure_postgresql_ready() -> Tuple[bool, str]:
    """
    Ensure PostgreSQL data directory is ready.

    Creates the directory if needed and returns status.

    Returns:
        Tuple of (success, message)
    """
    manager = CoreDataPathsManager()
    result = manager.ensure_postgresql_data_dir()

    if not result['success']:
        return (False, result['message'])

    if result['needs_init']:
        manager.print_initialization_instructions()
        return (True, f"Directory ready but needs initialization: {result['path']}")

    return (True, f"PostgreSQL data directory ready: {result['path']}")


__all__ = [
    'CoreDataPathsManager',
    'ensure_core_paths',
    'ensure_postgresql_ready',
]
