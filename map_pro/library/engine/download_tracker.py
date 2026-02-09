# Path: library/engine/download_tracker.py
"""
Download Tracker

Tracks download attempts, failures, and alternative URLs.
Separate from db_connector for cleaner code organization.

Responsibilities:
- Record download/extraction attempts
- Track failure reasons
- Manage alternative URLs
- Determine retry strategies
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from library.core.logger import get_logger
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'engine')

# Constants
MAX_DOWNLOAD_ATTEMPTS = 3
MAX_EXTRACTION_ATTEMPTS = 3
MAX_TOTAL_ATTEMPTS = 6


class DownloadTracker:
    """
    Tracks download status and implements retry logic.
    
    Works with DatabaseConnector to update download tracking fields.
    """
    
    def __init__(self, db_connector):
        """
        Initialize download tracker.
        
        Args:
            db_connector: DatabaseConnector instance
        """
        self.db = db_connector
        logger.info(f"{LOG_INPUT} DownloadTracker initialized")
    
    def record_download_attempt(
        self,
        taxonomy_name: str,
        version: str,
        attempt_type: str = 'download'
    ) -> Dict[str, Any]:
        """
        Record a download or extraction attempt.
        
        Args:
            taxonomy_name: Taxonomy name
            version: Version
            attempt_type: 'download' or 'extraction'
            
        Returns:
            Updated library record
        """
        from database.models import session_scope, TaxonomyLibrary
        
        with session_scope() as session:
            library = session.query(TaxonomyLibrary).filter_by(
                taxonomy_name=taxonomy_name,
                version=version
            ).first()
            
            if not library:
                return {'success': False, 'error': 'Library not found'}
            
            # Increment counters
            library.total_attempts += 1
            library.last_attempt_date = datetime.utcnow()
            
            if attempt_type == 'download':
                library.download_attempts += 1
                library.download_status = 'downloading'
            elif attempt_type == 'extraction':
                library.extraction_attempts += 1
                library.download_status = 'extracting'
            
            session.commit()
            
            logger.info(
                f"{LOG_OUTPUT} Recorded {attempt_type} attempt for {taxonomy_name} v{version} "
                f"(total: {library.total_attempts})"
            )
            
            return {
                'success': True,
                'download_attempts': library.download_attempts,
                'extraction_attempts': library.extraction_attempts,
                'total_attempts': library.total_attempts,
            }
    
    def record_download_success(
        self,
        taxonomy_name: str,
        version: str,
        downloaded_file_path: str,
        file_size: int
    ) -> Dict[str, Any]:
        """
        Record successful download (before extraction).
        
        Args:
            taxonomy_name: Taxonomy name
            version: Version
            downloaded_file_path: Path to downloaded ZIP
            file_size: Size in bytes
            
        Returns:
            Result dictionary
        """
        from database.models import session_scope, TaxonomyLibrary
        
        with session_scope() as session:
            library = session.query(TaxonomyLibrary).filter_by(
                taxonomy_name=taxonomy_name,
                version=version
            ).first()
            
            if not library:
                return {'success': False, 'error': 'Library not found'}
            
            library.download_status = 'downloaded'
            library.downloaded_file_path = downloaded_file_path
            library.downloaded_file_size = file_size
            library.failure_stage = None
            library.failure_reason = None
            
            session.commit()
            
            logger.info(
                f"{LOG_OUTPUT} Download successful: {taxonomy_name} v{version} "
                f"({file_size} bytes)"
            )
            
            return {'success': True}
    
    def record_extraction_success(
        self,
        taxonomy_name: str,
        version: str,
        extraction_path: str,
        file_count: int
    ) -> Dict[str, Any]:
        """
        Record successful extraction.
        
        Args:
            taxonomy_name: Taxonomy name
            version: Version
            extraction_path: Path where files extracted
            file_count: Number of files extracted
            
        Returns:
            Result dictionary
        """
        from database.models import session_scope, TaxonomyLibrary
        
        with session_scope() as session:
            library = session.query(TaxonomyLibrary).filter_by(
                taxonomy_name=taxonomy_name,
                version=version
            ).first()
            
            if not library:
                return {'success': False, 'error': 'Library not found'}
            
            library.download_status = 'ready'
            library.status = 'active'
            library.extraction_path = extraction_path
            library.file_count = file_count
            library.last_success_date = datetime.utcnow()
            library.failure_stage = None
            library.failure_reason = None
            library.validation_status = 'valid'
            
            session.commit()
            
            logger.info(
                f"{LOG_OUTPUT} Extraction successful: {taxonomy_name} v{version} "
                f"({file_count} files)"
            )
            
            return {'success': True}
    
    def record_download_failure(
        self,
        taxonomy_name: str,
        version: str,
        failure_stage: str,
        failure_reason: str,
        failure_details: str
    ) -> Dict[str, Any]:
        """
        Record download or extraction failure with specific reason.
        
        Args:
            taxonomy_name: Taxonomy name
            version: Version
            failure_stage: 'download' or 'extraction'
            failure_reason: Specific reason code
            failure_details: Full error message
            
        Returns:
            Result with retry recommendation
        """
        from database.models import session_scope, TaxonomyLibrary
        
        with session_scope() as session:
            library = session.query(TaxonomyLibrary).filter_by(
                taxonomy_name=taxonomy_name,
                version=version
            ).first()
            
            if not library:
                return {'success': False, 'error': 'Library not found'}
            
            library.download_status = 'failed'
            library.failure_stage = failure_stage
            library.failure_reason = failure_reason
            library.failure_details = failure_details
            
            # Determine if should retry
            should_retry = library.total_attempts < MAX_TOTAL_ATTEMPTS
            
            # Determine retry strategy based on failure reason
            retry_strategy = self._determine_retry_strategy(
                failure_reason,
                library.download_attempts,
                library.extraction_attempts
            )
            
            # Check if exceeded max attempts
            if library.total_attempts >= MAX_TOTAL_ATTEMPTS:
                library.status = 'failed'
            
            session.commit()
            
            logger.warning(
                f"{LOG_OUTPUT} Download failed: {taxonomy_name} v{version} "
                f"({failure_stage}: {failure_reason})"
            )
            
            return {
                'success': True,
                'should_retry': should_retry,
                'retry_strategy': retry_strategy,
                'attempts_remaining': MAX_TOTAL_ATTEMPTS - library.total_attempts,
            }
    
    def _determine_retry_strategy(
        self,
        failure_reason: str,
        download_attempts: int,
        extraction_attempts: int
    ) -> str:
        """
        Determine retry strategy based on failure reason.
        
        Returns:
            'retry_same_url', 'try_alternative_url', 'manual_intervention', 'no_retry'
        """
        # URL-related failures → try alternative URL after 3 attempts
        url_failures = {'invalid_url', 'url_404', 'url_403', 'dns_error'}
        if failure_reason in url_failures:
            if download_attempts >= MAX_DOWNLOAD_ATTEMPTS:
                return 'try_alternative_url'
            else:
                return 'retry_same_url'
        
        # Network/temporary failures → retry same URL
        temporary_failures = {'network_error', 'timeout', 'incomplete_download'}
        if failure_reason in temporary_failures:
            if download_attempts >= MAX_DOWNLOAD_ATTEMPTS:
                return 'try_alternative_url'  # Escalate after max attempts
            else:
                return 'retry_same_url'
        
        # Extraction failures → might need alternative source
        extraction_failures = {'corrupted_zip', 'invalid_archive'}
        if failure_reason in extraction_failures:
            if extraction_attempts >= 2:
                return 'try_alternative_url'  # Try different source
            else:
                return 'retry_same_url'  # Try re-downloading first
        
        # Permission/system issues → need manual intervention
        system_failures = {'permission_denied', 'disk_full', 'extraction_error'}
        if failure_reason in system_failures:
            return 'manual_intervention'
        
        # Default: retry same URL
        return 'retry_same_url'
    
    def try_alternative_url(
        self,
        taxonomy_name: str,
        version: str,
        new_url: str
    ) -> Dict[str, Any]:
        """
        Switch to alternative URL for download.
        
        Args:
            taxonomy_name: Taxonomy name
            version: Version
            new_url: New URL to try
            
        Returns:
            Result dictionary
        """
        from database.models import session_scope, TaxonomyLibrary
        
        with session_scope() as session:
            library = session.query(TaxonomyLibrary).filter_by(
                taxonomy_name=taxonomy_name,
                version=version
            ).first()
            
            if not library:
                return {'success': False, 'error': 'Library not found'}
            
            # Record previous URL
            if library.current_url and library.current_url not in (library.alternative_urls_tried or []):
                urls_tried = library.alternative_urls_tried or []
                urls_tried.append(library.current_url)
                library.alternative_urls_tried = urls_tried
            
            # Switch to new URL
            library.current_url = new_url
            library.download_status = 'pending'
            library.failure_stage = None
            library.failure_reason = None
            
            session.commit()
            
            logger.info(
                f"{LOG_OUTPUT} Switched {taxonomy_name} v{version} to alternative URL: {new_url}"
            )
            
            return {
                'success': True,
                'new_url': new_url,
                'urls_tried_count': len(library.alternative_urls_tried or []),
            }
    
    def get_download_status(
        self,
        taxonomy_name: str,
        version: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive download status for a library.
        
        Returns:
            Status dictionary or None
        """
        from database.models import session_scope, TaxonomyLibrary
        
        with session_scope() as session:
            library = session.query(TaxonomyLibrary).filter_by(
                taxonomy_name=taxonomy_name,
                version=version
            ).first()
            
            if not library:
                return None
            
            return {
                'taxonomy_name': library.taxonomy_name,
                'version': library.version,
                'download_status': library.download_status,
                'status': library.status,
                'download_attempts': library.download_attempts,
                'extraction_attempts': library.extraction_attempts,
                'total_attempts': library.total_attempts,
                'failure_stage': library.failure_stage,
                'failure_reason': library.failure_reason,
                'failure_details': library.failure_details,
                'current_url': library.current_url,
                'urls_tried': library.alternative_urls_tried or [],
                'file_count': library.file_count,
                'last_attempt': library.last_attempt_date,
                'last_success': library.last_success_date,
                'namespace': library.namespace,
            }
    
    def get_failed_downloads(self) -> List[Dict[str, Any]]:
        """
        Get all libraries that have failed download after max attempts.
        
        Returns:
            List of failed library records
        """
        from database.models import session_scope, TaxonomyLibrary
        
        with session_scope() as session:
            failed_libraries = session.query(TaxonomyLibrary).filter(
                TaxonomyLibrary.status == 'failed',
                TaxonomyLibrary.total_attempts >= MAX_TOTAL_ATTEMPTS
            ).all()
            
            return [
                {
                    'taxonomy_name': lib.taxonomy_name,
                    'version': lib.version,
                    'failure_stage': lib.failure_stage,
                    'failure_reason': lib.failure_reason,
                    'total_attempts': lib.total_attempts,
                    'urls_tried': lib.alternative_urls_tried or [],
                }
                for lib in failed_libraries
            ]
    
    def get_pending_retries(self) -> List[Dict[str, Any]]:
        """
        Get libraries that need retry (failed but not exceeded max attempts).
        
        Returns:
            List of libraries awaiting retry
        """
        from database.models import session_scope, TaxonomyLibrary
        
        with session_scope() as session:
            retry_libraries = session.query(TaxonomyLibrary).filter(
                TaxonomyLibrary.download_status == 'failed',
                TaxonomyLibrary.total_attempts < MAX_TOTAL_ATTEMPTS
            ).all()
            
            return [
                {
                    'taxonomy_name': lib.taxonomy_name,
                    'version': lib.version,
                    'failure_reason': lib.failure_reason,
                    'current_url': lib.current_url,
                    'attempts': lib.total_attempts,
                    'retry_strategy': self._determine_retry_strategy(
                        lib.failure_reason,
                        lib.download_attempts,
                        lib.extraction_attempts
                    ),
                }
                for lib in retry_libraries
            ]


__all__ = ['DownloadTracker', 'MAX_DOWNLOAD_ATTEMPTS', 'MAX_EXTRACTION_ATTEMPTS', 'MAX_TOTAL_ATTEMPTS']