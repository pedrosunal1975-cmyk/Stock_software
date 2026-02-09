# Path: searcher/markets/sec/zip_finder.py
"""
SEC XBRL ZIP Finder

Identifies XBRL ZIP files from SEC filing index.json data.
Uses priority-based pattern matching.
"""

from typing import Optional

from searcher.core.logger import get_logger
from searcher.markets.sec.constants import XBRL_ZIP_SUFFIXES

logger = get_logger(__name__, 'markets')


class SECZIPFinder:
    """
    Finds XBRL ZIP files in SEC filing directories.
    
    Parses index.json and identifies XBRL ZIP files using
    priority-based suffix matching.
    """
    
    def __init__(self, url_builder=None):
        """
        Initialize ZIP finder.
        
        Args:
            url_builder: Optional SECURLBuilder instance
        """
        self.url_builder = url_builder
    
    def find_xbrl_zip(
        self,
        index_data: dict,
        cik: str,
        accession: str
    ) -> Optional[str]:
        """
        Find XBRL ZIP file URL from index.json data.
        
        Args:
            index_data: Parsed index.json data
            cik: CIK number
            accession: Accession number
            
        Returns:
            Full URL to XBRL ZIP file, or None if not found
        """
        # Get directory listing from index.json (SEC API contract - stable field names)
        directory = index_data.get('directory', {})
        items = directory.get('item', [])
        
        if not items:
            logger.warning(f"No items found in index.json for {accession}")
            return None
        
        # Extract filenames
        filenames = [item.get('name') for item in items if item.get('name')]
        
        # Find XBRL ZIP using priority matching
        zip_filename = self._find_zip_by_priority(filenames)
        
        if not zip_filename:
            logger.warning(f"No XBRL ZIP found for {accession}")
            return None
        
        # Build full download URL
        if self.url_builder:
            return self.url_builder.build_file_download_url(
                cik=cik,
                accession=accession,
                filename=zip_filename
            )
        else:
            # Fallback if no URL builder provided
            from searcher.markets.sec.url_builder import SECURLBuilder
            builder = SECURLBuilder()
            return builder.build_file_download_url(
                cik=cik,
                accession=accession,
                filename=zip_filename
            )
    
    def _find_zip_by_priority(self, filenames: list[str]) -> Optional[str]:
        """
        Find XBRL ZIP file using priority-based matching.
        
        Tries suffixes in priority order:
        1. -xbrl.zip (highest priority)
        2. _htm.xml.zip
        3. .zip (fallback)
        
        Args:
            filenames: List of filenames from index.json
            
        Returns:
            XBRL ZIP filename, or None if not found
        """
        for suffix in XBRL_ZIP_SUFFIXES:
            for filename in filenames:
                if filename.endswith(suffix):
                    logger.debug(f"Found XBRL ZIP: {filename} (suffix: {suffix})")
                    return filename
        
        return None
    
    def get_all_zip_files(self, index_data: dict) -> list[str]:
        """
        Get all ZIP files from index.json (for debugging).
        
        Args:
            index_data: Parsed index.json data
            
        Returns:
            List of ZIP filenames
        """
        # SEC API contract - stable field names
        directory = index_data.get('directory', {})
        items = directory.get('item', [])
        
        zip_files = [
            item.get('name')
            for item in items
            if item.get('name', '').endswith('.zip')
        ]
        
        return zip_files


__all__ = ['SECZIPFinder']