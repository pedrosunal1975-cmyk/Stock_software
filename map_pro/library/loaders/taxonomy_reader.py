# Path: library/loaders/taxonomy_reader.py
"""
Taxonomy Reader

Verifies physical existence and completeness of taxonomy libraries.
Uses TaxonomyLoader to find directories, then verifies content.

Architecture:
- Uses taxonomy_loader.py to discover directories
- Counts files in each directory
- Verifies against MIN_FILES_THRESHOLD
- Returns verification status
- Informs engine to update database
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from library.core.config_loader import LibraryConfig
from library.core.logger import get_logger
from library.loaders.taxonomy_loader import TaxonomyLoader, TaxonomyLocation
from library.constants import (
    LOG_INPUT,
    LOG_PROCESS,
    LOG_OUTPUT,
    MIN_FILES_THRESHOLD,
)

logger = get_logger(__name__, 'loaders')


@dataclass
class TaxonomyVerification:
    """Verification result for a taxonomy directory."""
    taxonomy_path: Path
    directory_name: str
    source_type: str
    file_count: int
    is_complete: bool
    meets_threshold: bool
    verification_status: str
    error: Optional[str] = None


class TaxonomyReader:
    """
    Verifies physical existence of taxonomy libraries.
    
    Uses TaxonomyLoader for discovery, focuses on verification.
    """
    
    def __init__(self, config: Optional[LibraryConfig] = None):
        """Initialize taxonomy reader."""
        self.config = config if config else LibraryConfig()
        self.loader = TaxonomyLoader(self.config)
        self.min_files_threshold = self.config.get('library_min_files_threshold')
        
        logger.info(
            f"{LOG_INPUT} TaxonomyReader initialized "
            f"(threshold={self.min_files_threshold} files)"
        )
    
    def verify_all(self) -> List[TaxonomyVerification]:
        """
        Verify all taxonomy directories in both sources.
        
        Returns:
            List of TaxonomyVerification objects
        """
        logger.info(f"{LOG_PROCESS} Verifying all taxonomy directories")
        
        # Discover directories
        locations = self.loader.discover_all()
        
        # Verify each directory
        results = []
        for location in locations:
            verification = self.verify_directory(location)
            results.append(verification)
        
        complete_count = sum(1 for r in results if r.is_complete)
        logger.info(
            f"{LOG_OUTPUT} Verified {complete_count}/{len(results)} "
            f"taxonomies are complete"
        )
        
        return results
    
    def verify_libraries(self) -> List[TaxonomyVerification]:
        """
        Verify taxonomies in libraries/ directory only.
        
        Returns:
            List of TaxonomyVerification objects
        """
        logger.info(f"{LOG_PROCESS} Verifying libraries/ directory")
        
        locations = self.loader.discover_libraries()
        
        results = []
        for location in locations:
            verification = self.verify_directory(location)
            results.append(verification)
        
        logger.info(f"{LOG_OUTPUT} Verified {len(results)} libraries")
        
        return results
    
    def verify_manual_downloads(self) -> List[TaxonomyVerification]:
        """
        Verify files in manual_downloads/ directory.
        
        Returns:
            List of TaxonomyVerification objects
        """
        logger.info(f"{LOG_PROCESS} Verifying manual_downloads/ directory")
        
        locations = self.loader.discover_manual_downloads()
        
        results = []
        for location in locations:
            verification = self.verify_directory(location)
            results.append(verification)
        
        logger.info(f"{LOG_OUTPUT} Verified {len(results)} manual downloads")
        
        return results
    
    def verify_directory(self, location: TaxonomyLocation) -> TaxonomyVerification:
        """
        Verify single taxonomy directory.
        
        Args:
            location: TaxonomyLocation object
            
        Returns:
            TaxonomyVerification object
        """
        logger.debug(f"{LOG_INPUT} Verifying: {location.taxonomy_path}")
        
        try:
            # Count files recursively
            file_count = self._count_files(location.taxonomy_path)
            
            # Check against threshold
            meets_threshold = file_count > self.min_files_threshold
            
            # Determine verification status
            if file_count == 0:
                status = "empty"
                is_complete = False
            elif not meets_threshold:
                status = "incomplete"
                is_complete = False
            else:
                status = "complete"
                is_complete = True
            
            logger.debug(
                f"{LOG_OUTPUT} {location.directory_name}: "
                f"{file_count} files, status={status}"
            )
            
            return TaxonomyVerification(
                taxonomy_path=location.taxonomy_path,
                directory_name=location.directory_name,
                source_type=location.source_type,
                file_count=file_count,
                is_complete=is_complete,
                meets_threshold=meets_threshold,
                verification_status=status,
                error=None
            )
            
        except Exception as e:
            logger.error(f"Error verifying {location.taxonomy_path}: {e}")
            
            return TaxonomyVerification(
                taxonomy_path=location.taxonomy_path,
                directory_name=location.directory_name,
                source_type=location.source_type,
                file_count=0,
                is_complete=False,
                meets_threshold=False,
                verification_status="error",
                error=str(e)
            )
    
    def _count_files(self, directory: Path) -> int:
        """
        Count files recursively in directory.
        
        Args:
            directory: Directory to scan
            
        Returns:
            Number of files found
        """
        try:
            file_count = sum(1 for _ in directory.rglob('*') if _.is_file())
            return file_count
        except Exception as e:
            logger.error(f"Error counting files in {directory}: {e}")
            return 0
    
    def get_complete_taxonomies(self) -> List[str]:
        """
        Get list of complete taxonomy directory names.
        
        Returns:
            List of directory names that are complete
        """
        logger.info(f"{LOG_PROCESS} Getting complete taxonomies")
        
        verifications = self.verify_all()
        
        complete = [
            v.directory_name
            for v in verifications
            if v.is_complete
        ]
        
        logger.info(f"{LOG_OUTPUT} Found {len(complete)} complete taxonomies")
        
        return complete
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of taxonomy verification.
        
        Returns:
            Dictionary with summary statistics
        """
        logger.info(f"{LOG_PROCESS} Generating verification summary")
        
        verifications = self.verify_all()
        
        total = len(verifications)
        complete = sum(1 for v in verifications if v.is_complete)
        incomplete = sum(1 for v in verifications if not v.is_complete)
        
        by_source = {}
        for v in verifications:
            source = v.source_type
            if source not in by_source:
                by_source[source] = {'total': 0, 'complete': 0}
            by_source[source]['total'] += 1
            if v.is_complete:
                by_source[source]['complete'] += 1
        
        summary = {
            'total_taxonomies': total,
            'complete': complete,
            'incomplete': incomplete,
            'by_source': by_source,
            'threshold': self.min_files_threshold,
        }
        
        logger.info(f"{LOG_OUTPUT} Summary: {complete}/{total} complete")
        
        return summary


__all__ = ['TaxonomyReader', 'TaxonomyVerification']