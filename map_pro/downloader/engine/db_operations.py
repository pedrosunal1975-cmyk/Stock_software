# Path: downloader/engine/db_operations.py
"""
Database Operations

Repository pattern for database interactions.
Isolates database logic from download orchestration.

Architecture:
- Repository pattern (clean separation)
- Session management
- Entity/filing CRUD operations
- File verification integration
- Database reflects reality principle
"""

from pathlib import Path
from typing import Optional, List
from datetime import datetime

from downloader.core.logger import get_logger
from downloader.constants import (
    STATUS_PENDING,
    STATUS_DOWNLOADING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    LOG_INPUT,
    LOG_PROCESS,
    LOG_OUTPUT,
    is_included_taxonomy,
)

logger = get_logger(__name__, 'engine')


class DatabaseRepository:
    """
    Repository for database operations.
    
    Handles all database interactions with proper session management.
    Follows "database reflects reality" principle.
    
    Example:
        repo = DatabaseRepository()
        
        # Get pending and failed downloads
        downloadable = repo.get_pending_downloads(limit=10)
        
        # Update after download
        repo.update_download_status(filing_id, 'completed', file_path)
    """
    
    def __init__(self):
        """Initialize database repository."""
        # Import database modules only when needed
        try:
            from database import initialize_engine, session_scope
            from database.models import (
                FilingSearch,
                DownloadedFiling,
                Entity
            )
            
            # Initialize the database engine FIRST
            logger.info(f"{LOG_PROCESS} Initializing database engine...")
            initialize_engine()
            
            self.session_scope = session_scope
            self.FilingSearch = FilingSearch
            self.DownloadedFiling = DownloadedFiling
            self.Entity = Entity
            self._db_available = True
            
            logger.info(f"{LOG_OUTPUT} Database engine initialized successfully")
            
        except ImportError as e:
            logger.error(f"Database module not available: {e}")
            self._db_available = False
            raise RuntimeError(
                "Database module required for downloader. "
                "Ensure database module is installed and configured."
            )
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            self._db_available = False
            raise RuntimeError(
                f"Failed to initialize database: {e}"
            )
    
    def get_pending_downloads(self, limit: int = 100) -> List:
        """
        Get downloadable filing downloads (pending OR failed status).
        
        Returns both 'pending' and 'failed' status filings so user can
        retry failed downloads after fixing issues.
        
        Args:
            limit: Maximum number to retrieve
            
        Returns:
            List of FilingSearch records with pre-loaded entity data
        """
        if not self._db_available:
            return []
        
        logger.info(f"{LOG_INPUT} Querying downloadable filings (limit={limit})")
        
        try:
            with self.session_scope() as session:
                # Query for BOTH pending AND failed status
                filings = session.query(self.FilingSearch).filter(
                    self.FilingSearch.download_status.in_([STATUS_PENDING, STATUS_FAILED])
                ).order_by(
                    # Show failed first (to retry), then pending
                    self.FilingSearch.download_status.asc(),
                    self.FilingSearch.filing_date.desc()
                ).limit(limit).all()
                
                # Extract data while session is active
                result = []
                for filing in filings:
                    # Get entity
                    entity = session.query(self.Entity).filter_by(
                        entity_id=filing.entity_id
                    ).first()
                    
                    # Extract needed attributes into filing object while session active
                    # This ensures data is loaded before session closes
                    _ = filing.search_id
                    _ = filing.entity_id
                    _ = filing.market_type
                    _ = filing.form_type
                    _ = filing.filing_date
                    _ = filing.filing_url
                    _ = filing.accession_number
                    _ = filing.download_status
                    
                    # Store entity data as simple attributes (not relationship)
                    if entity:
                        filing._company_name = entity.company_name
                        filing._market_type_full = entity.market_type
                    else:
                        filing._company_name = 'UNKNOWN'
                        filing._market_type_full = filing.market_type
                    
                    result.append(filing)
                
                # Expire objects to allow access outside session
                for filing in result:
                    session.expunge(filing)
                
                # Count by status for logging
                pending_count = sum(1 for f in result if f.download_status == STATUS_PENDING)
                failed_count = sum(1 for f in result if f.download_status == STATUS_FAILED)
                
                logger.info(
                    f"{LOG_OUTPUT} Found {len(result)} downloadable filings "
                    f"({failed_count} failed, {pending_count} pending)"
                )
                
                return result
        
        except Exception as e:
            logger.error(f"Error querying downloadable filings: {e}")
            return []
    
    def get_filing_by_id(self, search_id: str):
        """
        Get filing search record by ID.
        
        Args:
            search_id: Filing search UUID
            
        Returns:
            FilingSearch record or None
        """
        if not self._db_available:
            return None
        
        try:
            with self.session_scope() as session:
                filing = session.query(self.FilingSearch).filter_by(
                    search_id=search_id
                ).first()
                
                return filing
        
        except Exception as e:
            logger.error(f"Error getting filing {search_id}: {e}")
            return None
    
    def update_download_status(
        self,
        search_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update filing download status.
        
        CRITICAL: Only call AFTER physical file verification.
        
        Args:
            search_id: Filing search UUID
            status: New status (downloading, completed, failed)
            error_message: Optional error message if failed
            
        Returns:
            True if update successful
        """
        if not self._db_available:
            return False
        
        logger.info(f"{LOG_PROCESS} Updating download status: {search_id} -> {status}")
        
        try:
            with self.session_scope() as session:
                filing = session.query(self.FilingSearch).filter_by(
                    search_id=search_id
                ).first()
                
                if not filing:
                    logger.error(f"Filing not found: {search_id}")
                    return False
                
                filing.download_status = status
                
                if error_message and status == STATUS_FAILED:
                    # Store error in metadata
                    metadata = filing.search_metadata or {}
                    metadata['download_error'] = error_message
                    metadata['download_failed_at'] = datetime.now().isoformat()
                    filing.search_metadata = metadata
                
                session.commit()
                logger.info(f"{LOG_OUTPUT} Status updated successfully")
                
                return True
        
        except Exception as e:
            logger.error(f"Error updating download status: {e}")
            return False
    
    def create_downloaded_filing(
        self,
        search_id: str,
        entity_id: str,
        download_directory: Path,
        instance_file: Optional[Path] = None
    ) -> bool:
        """
        Create DownloadedFiling record.
        
        CRITICAL: Only call AFTER physical file verification confirms files exist.
        
        Args:
            search_id: FilingSearch UUID
            entity_id: Entity UUID
            download_directory: Path to extracted filing directory
            instance_file: Path to discovered instance file
            
        Returns:
            True if creation successful
        """
        if not self._db_available:
            return False
        
        logger.info(f"{LOG_PROCESS} Creating DownloadedFiling record")
        
        try:
            with self.session_scope() as session:
                # Create record
                downloaded = self.DownloadedFiling(
                    search_id=search_id,
                    entity_id=entity_id,
                    download_directory=str(download_directory),
                    extraction_directory=None,  # Not used in new design
                    instance_file_path=str(instance_file) if instance_file else None,
                    download_completed_at=datetime.now()
                )
                
                session.add(downloaded)
                session.commit()
                
                logger.info(f"{LOG_OUTPUT} DownloadedFiling record created")
                
                return True
        
        except Exception as e:
            logger.error(f"Error creating DownloadedFiling: {e}")
            return False
    
    def get_entity(self, entity_id: str):
        """
        Get entity record by ID.
        
        Args:
            entity_id: Entity UUID
            
        Returns:
            Entity record or None
        """
        if not self._db_available:
            return None
        
        try:
            with self.session_scope() as session:
                entity = session.query(self.Entity).filter_by(
                    entity_id=entity_id
                ).first()
                
                return entity
        
        except Exception as e:
            logger.error(f"Error getting entity {entity_id}: {e}")
            return None
    
    def verify_filing_files_exist(self, filing_id: str) -> bool:
        """
        Verify that downloaded filing files actually exist on disk.
        
        Uses DownloadedFiling model's verification properties.
        
        Args:
            filing_id: DownloadedFiling UUID
            
        Returns:
            True if files exist on disk
        """
        if not self._db_available:
            return False
        
        try:
            with self.session_scope() as session:
                filing = session.query(self.DownloadedFiling).filter_by(
                    filing_id=filing_id
                ).first()
                
                if not filing:
                    return False
                
                # Use model's verification property
                return filing.files_actually_exist
        
        except Exception as e:
            logger.error(f"Error verifying filing files: {e}")
            return False

    
    def get_pending_taxonomies(self, limit: int = 100) -> List:
        """
        Get downloadable taxonomy libraries (pending OR failed status).
        
        Returns both 'pending' and 'failed' status taxonomies so user can
        retry failed downloads after fixing issues.
        
        Args:
            limit: Maximum number to retrieve
            
        Returns:
            List of TaxonomyLibrary records with status='pending' OR 'failed'
        """
        if not self._db_available:
            return []
        
        logger.info(f"{LOG_INPUT} Querying downloadable taxonomies (limit={limit})")
        
        try:
            with self.session_scope() as session:
                # Import TaxonomyLibrary model
                from database.models import TaxonomyLibrary
                
                # Query for BOTH pending AND failed status
                taxonomies = session.query(TaxonomyLibrary).filter(
                    TaxonomyLibrary.download_status.in_([STATUS_PENDING, STATUS_FAILED])
                ).order_by(
                    # Show failed first (to retry), then pending
                    TaxonomyLibrary.download_status.asc(),
                    TaxonomyLibrary.created_at.desc()
                ).limit(limit).all()
                
                # Extract data while session is active, filtering out included taxonomies
                result = []
                skipped_count = 0
                for taxonomy in taxonomies:
                    # Access attributes to load them before session closes
                    _ = taxonomy.library_id
                    _ = taxonomy.taxonomy_name
                    _ = taxonomy.taxonomy_version
                    _ = taxonomy.taxonomy_namespace
                    _ = taxonomy.source_url
                    _ = taxonomy.download_status

                    # Skip included taxonomies (transformation registries, bundled taxonomies)
                    if is_included_taxonomy(taxonomy.taxonomy_name):
                        logger.info(
                            f"{LOG_PROCESS} Skipping included taxonomy: {taxonomy.taxonomy_name} "
                            f"(built-in, not downloadable)"
                        )
                        skipped_count += 1
                        continue

                    result.append(taxonomy)
                
                # Expire objects to allow access outside session
                for taxonomy in result:
                    session.expunge(taxonomy)
                
                # Count by status for logging
                pending_count = sum(1 for t in result if t.download_status == STATUS_PENDING)
                failed_count = sum(1 for t in result if t.download_status == STATUS_FAILED)

                log_msg = (
                    f"{LOG_OUTPUT} Found {len(result)} downloadable taxonomies "
                    f"({failed_count} failed, {pending_count} pending)"
                )
                if skipped_count > 0:
                    log_msg += f" [skipped {skipped_count} included/built-in taxonomies]"
                logger.info(log_msg)

                return result
        
        except Exception as e:
            logger.error(f"Error querying downloadable taxonomies: {e}")
            return []
    
    def update_taxonomy_status(
        self,
        library_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update taxonomy library download status.
        
        Args:
            library_id: TaxonomyLibrary UUID
            status: New status (downloading, completed, failed)
            error_message: Optional error message if failed
            
        Returns:
            True if update successful
        """
        if not self._db_available:
            return False
        
        logger.info(f"{LOG_PROCESS} Updating taxonomy status: {library_id} -> {status}")
        
        try:
            with self.session_scope() as session:
                from database.models import TaxonomyLibrary
                
                taxonomy = session.query(TaxonomyLibrary).filter_by(
                    library_id=library_id
                ).first()
                
                if not taxonomy:
                    logger.error(f"Taxonomy not found: {library_id}")
                    return False
                
                taxonomy.download_status = status
                
                if error_message and status == STATUS_FAILED:
                    taxonomy.download_error = error_message
                    taxonomy.updated_at = datetime.now()
                
                session.commit()
                logger.info(f"{LOG_OUTPUT} Taxonomy status updated successfully")
                
                return True
        
        except Exception as e:
            logger.error(f"Error updating taxonomy status: {e}")
            return False
    
    def update_taxonomy_completion(
        self,
        library_id: str,
        library_directory: Path,
        total_files: int
    ) -> bool:
        """
        Mark taxonomy download as completed with file information.
        
        CRITICAL: Only call AFTER physical file verification.
        
        Args:
            library_id: TaxonomyLibrary UUID
            library_directory: Path to extracted taxonomy directory
            total_files: Number of files extracted
            
        Returns:
            True if update successful
        """
        if not self._db_available:
            return False
        
        logger.info(f"{LOG_PROCESS} Marking taxonomy as completed: {library_id}")
        
        try:
            with self.session_scope() as session:
                from database.models import TaxonomyLibrary
                
                taxonomy = session.query(TaxonomyLibrary).filter_by(
                    library_id=library_id
                ).first()
                
                if not taxonomy:
                    logger.error(f"Taxonomy not found: {library_id}")
                    return False
                
                taxonomy.download_status = STATUS_COMPLETED
                taxonomy.library_directory = str(library_directory)
                taxonomy.total_files = total_files
                taxonomy.download_completed_at = datetime.now()
                taxonomy.last_verified_at = datetime.now()

                # CRITICAL: Also set status and validation_status
                # AvailabilityChecker expects these to determine if library is ready
                taxonomy.status = 'active'
                taxonomy.validation_status = 'valid'
                
                session.commit()
                logger.info(f"{LOG_OUTPUT} Taxonomy completion recorded successfully")
                
                return True
        
        except Exception as e:
            logger.error(f"Error updating taxonomy completion: {e}")
            return False


__all__ = ['DatabaseRepository']