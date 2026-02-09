# Path: downloader/engine/failure_handler.py
"""
Failure Handler

Centralized failure handling and error reporting.
Extracts error messages and updates database status.

Architecture:
- Error message extraction from ProcessingResult
- Database status updates
- Structured error logging
"""

from downloader.core.logger import get_logger
from downloader.engine.db_operations import DatabaseRepository
from downloader.engine.result import ProcessingResult
from downloader.constants import STATUS_FAILED, LOG_OUTPUT

logger = get_logger(__name__, 'engine')


class FailureHandler:
    """
    Handles download failures and database updates.
    
    Responsibilities:
    - Extract error messages from ProcessingResult
    - Update database status to 'failed'
    - Log structured error information
    
    Example:
        handler = FailureHandler(db_repo)
        
        # Handle filing failure
        await handler.handle_failure(
            record=filing,
            result=processing_result,
            download_type='filing'
        )
        
        # Handle taxonomy failure
        await handler.handle_failure(
            record=taxonomy,
            result=processing_result,
            download_type='taxonomy'
        )
    """
    
    def __init__(self, db_repo: DatabaseRepository):
        """
        Initialize failure handler.
        
        Args:
            db_repo: Database repository for status updates
        """
        self.db_repo = db_repo
    
    async def handle_failure(
        self,
        record,
        result: ProcessingResult,
        download_type: str
    ):
        """
        Handle download failure.
        
        Workflow:
        1. Extract error message from ProcessingResult
        2. Build complete error message
        3. Update database status to 'failed'
        4. Log error details
        
        Args:
            record: FilingSearch or TaxonomyLibrary record
            result: ProcessingResult with error information
            download_type: 'filing' or 'taxonomy'
        """
        # Extract error message from appropriate sub-result
        error_details = self._extract_error_details(result)
        
        # Build complete error message
        error_msg = f"Failed at {result.error_stage}: {error_details}"
        
        # Log error
        logger.error(f"{LOG_OUTPUT} Download FAILED: {error_msg}")
        logger.error(f"{LOG_OUTPUT} Failed at {result.error_stage}")
        
        # Update database status
        if download_type == 'filing':
            self.db_repo.update_download_status(
                str(record.search_id),
                STATUS_FAILED,
                error_message=error_msg
            )
        else:
            self.db_repo.update_taxonomy_status(
                str(record.library_id),
                STATUS_FAILED,
                error_message=error_msg
            )
    
    def _extract_error_details(self, result: ProcessingResult) -> str:
        """
        Extract error details from ProcessingResult.
        
        Checks error_stage to determine which sub-result contains
        the actual error message.
        
        Args:
            result: ProcessingResult with error information
            
        Returns:
            Human-readable error message
        """
        if result.error_stage == 'detection':
            # Use error_message if available, otherwise generic message
            return result.error_message or "Distribution detection failed"
        
        elif result.error_stage == 'download' and result.download_result:
            return result.download_result.error_message or "Download failed"
        
        elif result.error_stage == 'extraction' and result.extraction_result:
            return result.extraction_result.error_message or "Extraction failed"
        
        elif result.error_stage == 'validation':
            return "Validation failed - no files found"
        
        elif result.error_stage == 'verification':
            return "File verification failed"
        
        elif result.error_stage == 'database':
            return "Database update failed"
        
        elif result.error_stage == 'unexpected':
            return "Unexpected error occurred"
        
        else:
            return "Unknown error"


__all__ = ['FailureHandler']