# Path: downloader/engine/extraction/sec_handler.py
"""
SEC Extraction Handler

SEC-specific extraction logic (if needed).
Currently minimal - just inherits from base Extractor.

CRITICAL PRINCIPLE: Extractor ONLY extracts archives.
Instance file discovery is parser's responsibility.

Architecture:
- Inherits from base Extractor
- Placeholder for future SEC-specific extraction rules (if any)
- Does NOT search for instance files
- Does NOT parse content
"""

from pathlib import Path
from typing import Optional

from downloader.core.logger import get_logger
from downloader.engine.extraction.extractor import Extractor
from downloader.engine.result import ExtractionResult

logger = get_logger(__name__, 'extraction')


class SECExtractionHandler(Extractor):
    """
    SEC-specific extraction handler.
    
    Currently identical to base Extractor.
    Exists as placeholder for future SEC-specific extraction rules.
    
    Does NOT search for instance files - parser's responsibility.
    
    Example:
        handler = SECExtractionHandler()
        result = handler.extract_zip(
            zip_path=Path('/mnt/map_pro/downloader/temp/filing.zip'),
            target_dir=Path('/mnt/map_pro/downloader/entities/sec/COMPANY/filings/10-K/000123')
        )
    """
    
    def extract_zip(
        self,
        zip_path: Path,
        target_dir: Path,
        cleanup_zip: bool = True
    ) -> ExtractionResult:
        """
        Extract SEC filing ZIP.
        
        Currently identical to base extraction.
        Future: Could add SEC-specific validation or metadata.
        
        Args:
            zip_path: Path to SEC XBRL ZIP file
            target_dir: Target directory for extraction
            cleanup_zip: Whether to delete ZIP after extraction
            
        Returns:
            ExtractionResult with extraction details
        """
        # Use base extractor (no special SEC logic needed currently)
        return super().extract_zip(zip_path, target_dir, cleanup_zip)


__all__ = ['SECExtractionHandler']