# Path: library/engine/db_connector.py
"""
Database Connector

Handles taxonomy_libraries table operations.
100% AGNOSTIC - direct database operations for taxonomy libraries.

NO HARDCODED taxonomy logic.
Saves taxonomy metadata directly to database.

Architecture:
- Query taxonomy_libraries table (read operations)
- Save taxonomy metadata directly (write operations)
- NO hardcoded taxonomy information
- Market-agnostic database operations

Usage:
    from library.engine.db_connector import DatabaseConnector
    
    db = DatabaseConnector()
    
    # Check if library exists
    exists = db.check_taxonomy_exists('http://fasb.org/us-gaap/2024')
    
    # Save taxonomy metadata
    result = db.save_taxonomy(metadata_dict)
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

from library.core.config_loader import LibraryConfig
from library.core.logger import get_logger
from library.constants import (
    LOG_INPUT,
    LOG_PROCESS,
    LOG_OUTPUT,
    LIBRARY_STATUS_PENDING,
    LIBRARY_STATUS_ACTIVE,
    LIBRARY_STATUS_FAILED,
    VALIDATION_STATUS_PENDING,
    VALIDATION_STATUS_HEALTHY,
    VALIDATION_STATUS_CORRUPTED,
)

logger = get_logger(__name__, 'engine')


class DatabaseConnector:
    """
    Database operations for taxonomy_libraries table.
    
    100% AGNOSTIC - no hardcoded taxonomy logic.
    
    Responsibilities:
    - Query taxonomy_libraries table
    - Save taxonomy metadata directly to database
    - Check library availability
    - Update library status
    
    Example:
        db = DatabaseConnector()
        
        # Check if library exists
        if not db.check_taxonomy_exists(namespace):
            # Save to database
            db.save_taxonomy(metadata)
    """
    
    def __init__(self, config: Optional[LibraryConfig] = None):
        """
        Initialize database connector.
        
        Imports required database modules.
        
        Args:
            config: Optional LibraryConfig instance
        """
        self.config = config if config else LibraryConfig()
        
        logger.debug(f"{LOG_PROCESS} Initializing database connector")
        
        try:
            # Import database components
            from database import session_scope
            from database.models import TaxonomyLibrary
            
            self.session_scope = session_scope
            self.TaxonomyLibrary = TaxonomyLibrary
            
            logger.info(f"{LOG_OUTPUT} Database connector initialized")
            
        except ImportError as e:
            logger.error(f"Cannot import database module: {e}")
            logger.error(
                "DatabaseConnector requires database module. "
                "Ensure database module is in Python path."
            )
            raise

        # Get taxonomies destination directory from config
        self.taxonomies_dir = Path(self.config.get('library_taxonomies_libraries'))

    def _check_physical_existence(self, taxonomy_name: str, version: str) -> bool:
        """
        Check if taxonomy library physically exists in destination folder.

        PHYSICAL EXISTENCE IS THE SOURCE OF TRUTH.

        Checks for directory with files (not empty directory).

        Args:
            taxonomy_name: Taxonomy name (e.g., 'us-gaap')
            version: Taxonomy version (e.g., '2024')

        Returns:
            True if directory exists AND contains files
        """
        # Try multiple naming patterns
        patterns = [
            f"{taxonomy_name}-{version}",  # us-gaap-2024
            taxonomy_name,                  # us-gaap
            f"{taxonomy_name}_{version}",  # us-gaap_2024
        ]

        for pattern in patterns:
            lib_dir = self.taxonomies_dir / pattern
            if lib_dir.exists() and lib_dir.is_dir():
                # Check if directory has files (not empty)
                file_count = sum(1 for _ in lib_dir.rglob('*') if _.is_file())
                if file_count > 0:
                    logger.debug(
                        f"{LOG_OUTPUT} Physical check: {pattern} exists with {file_count} files"
                    )
                    return True

        logger.debug(
            f"{LOG_OUTPUT} Physical check: {taxonomy_name} v{version} NOT found"
        )
        return False

    def check_taxonomy_exists(self, namespace: str) -> bool:
        """
        Check if taxonomy exists in database by namespace.
        
        Args:
            namespace: Taxonomy namespace URI
            
        Returns:
            True if exists, False otherwise
        """
        logger.debug(f"{LOG_INPUT} Checking if taxonomy exists: {namespace}")
        
        try:
            with self.session_scope() as session:
                exists = session.query(self.TaxonomyLibrary).filter(
                    self.TaxonomyLibrary.taxonomy_namespace == namespace
                ).first() is not None
                
                logger.debug(f"{LOG_OUTPUT} Taxonomy exists: {exists}")
                return exists
                
        except Exception as e:
            logger.error(f"Error checking taxonomy existence: {e}")
            return False
    
    def get_taxonomy_by_namespace(
        self,
        namespace: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get taxonomy library record by namespace.
        
        Args:
            namespace: Taxonomy namespace URI
            
        Returns:
            Dictionary with taxonomy data or None if not found
        """
        logger.debug(f"{LOG_INPUT} Getting taxonomy by namespace: {namespace}")
        
        try:
            with self.session_scope() as session:
                library = session.query(self.TaxonomyLibrary).filter(
                    self.TaxonomyLibrary.taxonomy_namespace == namespace
                ).first()
                
                if library:
                    logger.debug(f"{LOG_OUTPUT} Found taxonomy: {library.taxonomy_name}")
                    
                    return {
                        'library_id': str(library.library_id),
                        'taxonomy_name': library.taxonomy_name,
                        'version': library.taxonomy_version,
                        'namespace': library.taxonomy_namespace,
                        'download_url': library.source_url,
                        'download_status': library.download_status,
                        'total_files': library.total_files,
                    }
                else:
                    logger.debug(f"{LOG_OUTPUT} Taxonomy not found")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting taxonomy: {e}")
            return None
    
    def save_taxonomy(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save taxonomy metadata to database.
        
        Saves directly to taxonomy_libraries table.
        Pattern: Check existing â†’ update or create
        
        Args:
            metadata: Dictionary with taxonomy metadata
                Required keys: taxonomy_name, version, namespace, download_url
                Optional keys: market_type, authority
                
        Returns:
            Dictionary with result:
            {
                'success': bool,
                'library_id': str,
                'created': bool,  # vs updated
                'error': Optional[str]
            }
        """
        taxonomy_name = metadata.get('taxonomy_name')
        version = metadata.get('version')
        namespace = metadata.get('namespace')
        download_url = metadata.get('download_url')
        
        # CRITICAL FIX: Skip "unknown" taxonomies
        # Multiple unrecognized namespaces would all map to "unknown/unknown"
        # This violates unique constraint on (taxonomy_name, taxonomy_version)
        if taxonomy_name == 'unknown' or version == 'unknown':
            logger.warning(
                f"{LOG_OUTPUT} Skipping unknown taxonomy: {namespace}"
            )
            return {
                'success': True,  # Consider it successful (just skipped)
                'library_id': None,
                'created': False,
                'error': None,
                'skipped': True,
                'reason': 'Unrecognized taxonomy namespace'
            }
        
        logger.info(
            f"{LOG_INPUT} Saving taxonomy: {taxonomy_name} v{version}"
        )
        
        try:
            with self.session_scope() as session:
                # Check if library already exists
                library = session.query(self.TaxonomyLibrary).filter(
                    self.TaxonomyLibrary.taxonomy_namespace == namespace
                ).first()
                
                if library:
                    # PHYSICAL EXISTENCE IS THE SOURCE OF TRUTH
                    # Check if files actually exist in destination folder
                    physically_exists = self._check_physical_existence(taxonomy_name, version)

                    if physically_exists:
                        # Files exist - ensure database reflects this
                        if library.download_status != 'completed':
                            library.download_status = 'completed'
                            session.commit()
                            logger.info(
                                f"{LOG_OUTPUT} Library physically exists, updated status to completed: "
                                f"{taxonomy_name} v{version}"
                            )
                        else:
                            logger.info(
                                f"{LOG_OUTPUT} Library already exists (physical + DB): "
                                f"{taxonomy_name} v{version}"
                            )
                        return {
                            'success': True,
                            'library_id': str(library.library_id),
                            'created': False,
                            'error': None,
                            'already_available': True,
                        }

                    # Files DON'T exist - set to pending for download
                    library.source_url = download_url
                    library.download_status = LIBRARY_STATUS_PENDING

                    session.commit()

                    logger.info(
                        f"{LOG_OUTPUT} Library needs download (no physical files): "
                        f"{taxonomy_name} v{version}"
                    )

                    return {
                        'success': True,
                        'library_id': str(library.library_id),
                        'created': False,
                        'error': None,
                    }
                else:
                    # Create new
                    new_library = self.TaxonomyLibrary(
                        taxonomy_name=taxonomy_name,
                        taxonomy_version=version,
                        taxonomy_namespace=namespace,
                        source_url=download_url,
                        download_status=LIBRARY_STATUS_PENDING,
                    )
                    
                    session.add(new_library)
                    session.commit()
                    
                    logger.info(
                        f"{LOG_OUTPUT} Created new library: {new_library.library_id}"
                    )
                    
                    return {
                        'success': True,
                        'library_id': str(new_library.library_id),
                        'created': True,
                        'error': None,
                    }
                    
        except Exception as e:
            logger.error(f"Error saving taxonomy: {e}")
            return {
                'success': False,
                'library_id': None,
                'created': False,
                'error': str(e),
            }
    
    def get_pending_taxonomies(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get taxonomies with status='pending'.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of pending taxonomy dictionaries
        """
        logger.debug(f"{LOG_INPUT} Getting pending taxonomies (limit={limit})")
        
        try:
            with self.session_scope() as session:
                pending_libraries = session.query(self.TaxonomyLibrary).filter(
                    self.TaxonomyLibrary.download_status == LIBRARY_STATUS_PENDING
                ).limit(limit).all()
                
                result = []
                for library in pending_libraries:
                    result.append({
                        'library_id': str(library.library_id),
                        'taxonomy_name': library.taxonomy_name,
                        'version': library.taxonomy_version,
                        'namespace': library.taxonomy_namespace,
                        'download_url': library.source_url,
                    })
                
                logger.info(f"{LOG_OUTPUT} Found {len(result)} pending taxonomies")
                return result
                
        except Exception as e:
            logger.error(f"Error getting pending taxonomies: {e}")
            return []
    
    def update_library_status(
        self,
        library_id: str,
        status: str
    ) -> bool:
        """
        Update library status.
        
        Args:
            library_id: Library UUID
            status: New status (pending, completed, failed)
            
        Returns:
            True if updated successfully
        """
        logger.debug(f"{LOG_INPUT} Updating library {library_id} status to {status}")
        
        try:
            with self.session_scope() as session:
                library = session.query(self.TaxonomyLibrary).filter(
                    self.TaxonomyLibrary.library_id == uuid.UUID(library_id)
                ).first()
                
                if library:
                    library.download_status = status
                    session.commit()
                    logger.info(f"{LOG_OUTPUT} Status updated successfully")
                    return True
                else:
                    logger.warning(f"{LOG_OUTPUT} Library not found: {library_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating library status: {e}")
            return False
    
    def mark_for_download(self, library_id: str) -> bool:
        """
        Mark library for download (status='pending').
        
        Args:
            library_id: Library UUID
            
        Returns:
            True if marked successfully
        """
        return self.update_library_status(library_id, LIBRARY_STATUS_PENDING)
    
    def count_libraries_by_status(self) -> Dict[str, int]:
        """
        Count libraries grouped by status.
        
        Returns:
            Dictionary mapping status to count
        """
        logger.debug(f"{LOG_INPUT} Counting libraries by status")
        
        try:
            with self.session_scope() as session:
                libraries = session.query(self.TaxonomyLibrary).all()
                
                counts = {}
                for library in libraries:
                    status = library.download_status
                    counts[status] = counts.get(status, 0) + 1
                
                logger.info(f"{LOG_OUTPUT} Status counts: {counts}")
                return counts
                
        except Exception as e:
            logger.error(f"Error counting libraries: {e}")
            return {}


__all__ = ['DatabaseConnector']