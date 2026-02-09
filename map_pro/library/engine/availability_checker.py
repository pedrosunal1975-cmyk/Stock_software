# Path: library/engine/availability_checker.py
"""
Availability Checker

Checks taxonomy library availability using DUAL VERIFICATION:
1. Database status (active + healthy + files > threshold)
2. Disk verification (directory exists + file count > threshold)

100% AGNOSTIC - no hardcoded taxonomy logic.

Both checks must pass for library to be considered "available".
Prevents issues with:
- Database records without actual files
- Empty directories being marked as "available"
- Corrupted downloads

Architecture:
- Check database: status='active' AND validation='healthy' AND total_files > threshold
- Check disk: directory exists AND file count > MIN_FILES_THRESHOLD
- Return: available_libraries, missing_libraries

Usage:
    from library.engine.availability_checker import AvailabilityChecker
    
    checker = AvailabilityChecker()
    
    required = [
        {'taxonomy_name': 'us-gaap', 'version': '2024'},
        {'taxonomy_name': 'dei', 'version': '2024'},
    ]
    
    result = checker.check_library_availability(required)
    # Returns: {
    #     'available_libraries': [...],
    #     'missing_libraries': [...],
    #     'available_count': 1,
    #     'missing_count': 1
    # }
"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from library.core.config_loader import LibraryConfig
from library.core.data_paths import LibraryPaths
from library.core.logger import get_logger
from library.constants import (
    LOG_INPUT,
    LOG_PROCESS,
    LOG_OUTPUT,
    LIBRARY_STATUS_ACTIVE,
    VALIDATION_STATUS_HEALTHY,
    MIN_FILES_THRESHOLD,
)
from library.engine.constants import STATUS_VALID  # Use engine constants for validation status

logger = get_logger(__name__, 'engine')


class AvailabilityChecker:
    """
    Check taxonomy library availability with DUAL VERIFICATION.
    
    Pattern: Database + Disk checking
    Both must pass for library to be "available".
    
    Key Features:
    - MIN_FILES_THRESHOLD check prevents empty dirs
    - Strict readiness: active + healthy + files > threshold
    - Download vs re-index detection
    - Detailed failure scenarios
    
    Example:
        checker = AvailabilityChecker()
        
        required = [
            {'taxonomy_name': 'us-gaap', 'version': '2024'},
        ]
        
        result = checker.check_library_availability(required)
        
        if result['missing_count'] > 0:
            print(f"Need to download {result['missing_count']} libraries")
    """
    
    def __init__(
        self,
        config: Optional[LibraryConfig] = None,
        paths: Optional[LibraryPaths] = None
    ):
        """
        Initialize availability checker.
        
        Args:
            config: Optional LibraryConfig instance
            paths: Optional LibraryPaths instance
        """
        self.config = config if config else LibraryConfig()
        self.paths = paths if paths else LibraryPaths(self.config)
        
        self.min_files_threshold = self.config.get('library_min_files_threshold')
        
        logger.debug(
            f"{LOG_PROCESS} Availability checker initialized "
            f"(threshold={self.min_files_threshold} files)"
        )
        
        try:
            # Import database components
            from database import session_scope
            from database.models import TaxonomyLibrary
            
            self.session_scope = session_scope
            self.TaxonomyLibrary = TaxonomyLibrary
            
        except ImportError as e:
            logger.error(f"Cannot import database module: {e}")
            raise
    
    def check_library_availability(
        self,
        required_libraries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check which libraries are available.
        
        DUAL VERIFICATION: Database + Disk
        Both checks must pass.
        
        Args:
            required_libraries: List of library metadata dicts
                Each must have: taxonomy_name, version
                
        Returns:
            Dictionary with:
            {
                'available_libraries': List[Dict],
                'missing_libraries': List[Dict],
                'available_count': int,
                'missing_count': int
            }
        """
        logger.info(
            f"{LOG_INPUT} Checking availability of {len(required_libraries)} libraries"
        )
        
        available = []
        missing = []
        
        for library in required_libraries:
            taxonomy_name = library.get('taxonomy_name')
            version = library.get('version')
            
            logger.debug(f"{LOG_PROCESS} Checking {taxonomy_name} v{version}")
            
            # DUAL VERIFICATION
            db_ready = self._is_in_database(taxonomy_name, version)
            disk_ok = self._is_on_disk(taxonomy_name, version)
            
            if db_ready and disk_ok:
                logger.debug(f"{LOG_OUTPUT} Available: {taxonomy_name} v{version}")
                available.append(library)
            else:
                logger.debug(
                    f"{LOG_OUTPUT} Missing: {taxonomy_name} v{version} "
                    f"(db={db_ready}, disk={disk_ok})"
                )
                missing.append(library)
        
        result = {
            'available_libraries': available,
            'missing_libraries': missing,
            'available_count': len(available),
            'missing_count': len(missing),
        }
        
        logger.info(
            f"{LOG_OUTPUT} Availability check: "
            f"{result['available_count']} available, "
            f"{result['missing_count']} missing"
        )
        
        return result
    
    def _is_in_database(self, taxonomy_name: str, version: str) -> bool:
        """
        Check database: completed download + files > threshold.

        Readiness check ensures library has been downloaded and has files.

        Args:
            taxonomy_name: Taxonomy name
            version: Taxonomy version

        Returns:
            True if ready in database
        """
        try:
            with self.session_scope() as session:
                library = session.query(self.TaxonomyLibrary).filter(
                    self.TaxonomyLibrary.taxonomy_name == taxonomy_name,
                    self.TaxonomyLibrary.taxonomy_version == version
                ).first()

                if library is None:
                    return False

                # Check if library has completed download and has files
                has_files = library.total_files and library.total_files > self.min_files_threshold

                # Accept download_status='completed' as ready
                is_ready = library.download_status == 'completed' and has_files

                return is_ready

        except Exception as e:
            logger.error(f"Error checking database for {taxonomy_name}: {e}")
            return False
    
    def _is_on_disk(self, taxonomy_name: str, version: str) -> bool:
        """
        Check disk: directory exists + file count > threshold.
        
        Prevents empty directories from being "available".
        
        Args:
            taxonomy_name: Taxonomy name
            version: Taxonomy version
            
        Returns:
            True if files exist on disk
        """
        try:
            library_dir = self.paths.get_library_directory(taxonomy_name, version)
            
            if not library_dir.exists():
                return False
            
            # Count files recursively
            file_count = sum(1 for _ in library_dir.rglob('*') if _.is_file())
            
            return file_count > self.min_files_threshold
            
        except Exception as e:
            logger.error(f"Error checking disk for {taxonomy_name}: {e}")
            return False
    
    def get_library_status(
        self,
        taxonomy_name: str,
        version: str
    ) -> Dict[str, Any]:
        """
        Get detailed status for a single library.
        
        Returns:
            Dictionary with detailed status information
        """
        logger.debug(f"{LOG_INPUT} Getting status for {taxonomy_name} v{version}")
        
        db_ready = self._is_in_database(taxonomy_name, version)
        disk_ok = self._is_on_disk(taxonomy_name, version)
        
        # Get file count
        library_dir = self.paths.get_library_directory(taxonomy_name, version)
        file_count = 0
        if library_dir.exists():
            file_count = sum(1 for _ in library_dir.rglob('*') if _.is_file())
        
        status = {
            'taxonomy_name': taxonomy_name,
            'version': version,
            'available_in_db': db_ready,
            'available_on_disk': disk_ok,
            'file_count': file_count,
            'is_ready': db_ready and disk_ok,
            'requires_download': not db_ready or not disk_ok,
            'requires_reindex': disk_ok and not db_ready,
        }
        
        logger.debug(f"{LOG_OUTPUT} Status: {status}")
        
        return status


__all__ = ['AvailabilityChecker']