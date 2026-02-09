# Path: downloader/engine/path_resolver.py
"""
Path Resolver

Handles path construction and download type detection.
Separates path logic from coordination logic.

Architecture:
- Type-based routing (filing vs taxonomy)
- Market-agnostic path building
- Clean directory structure generation
"""

from pathlib import Path
from typing import Union

from downloader.core.logger import get_logger
from downloader.constants import LOG_PROCESS, LOG_OUTPUT
from downloader.engine.constants import (
    UNKNOWN_COMPANY_NAME,
    FILINGS_SUBDIRECTORY,
    UNSAFE_PATH_CHARS,
    PATH_REPLACEMENT_CHAR,
)

logger = get_logger(__name__, 'engine')


class PathResolver:
    """
    Resolves download paths and determines download types.
    
    Responsibilities:
    - Determine if record is filing or taxonomy
    - Build correct directory paths based on type
    - Normalize company names for filesystem
    
    Example:
        resolver = PathResolver(
            entities_dir=Path('/mnt/map_pro/downloader/entities'),
            taxonomies_dir=Path('/mnt/map_pro/taxonomies')
        )
        
        # Detect type
        download_type = resolver.determine_type(record)
        
        # Build path
        if download_type == 'filing':
            path = resolver.build_filing_path(record)
        else:
            path = resolver.build_taxonomy_path(record)
    """
    
    def __init__(self, entities_dir: Path, taxonomies_dir: Path):
        """
        Initialize path resolver.
        
        Args:
            entities_dir: Base directory for filing downloads
            taxonomies_dir: Base directory for taxonomy downloads
        """
        self.entities_dir = entities_dir
        self.taxonomies_dir = taxonomies_dir
    
    def determine_type(self, record) -> str:
        """
        Determine if record is a filing or taxonomy download.
        
        Uses attribute inspection:
        - TaxonomyLibrary has 'taxonomy_name'
        - FilingSearch has 'form_type'
        
        Args:
            record: Database record (FilingSearch or TaxonomyLibrary)
            
        Returns:
            'filing' or 'taxonomy'
        """
        if hasattr(record, 'taxonomy_name'):
            return 'taxonomy'
        else:
            return 'filing'
    
    def build_filing_path(self, filing) -> Path:
        """
        Build directory path for filing download.
        
        Structure: {entities_dir}/{market}/{company}/filings/{form}/{accession}
        Example: /mnt/map_pro/downloader/entities/sec/Apple_Inc/filings/10-K/0001234567-24-000123
        
        Args:
            filing: FilingSearch record with pre-loaded entity data
            
        Returns:
            Path object for filing directory
        """
        # Get pre-loaded company name (from db_operations session handling)
        company_name = getattr(filing, '_company_name', UNKNOWN_COMPANY_NAME)
        market = filing.market_type.lower()
        
        # Normalize company name for filesystem
        safe_company_name = self._normalize_company_name(company_name)
        
        logger.info(
            f"{LOG_PROCESS} Building filing path: "
            f"entities_dir={self.entities_dir}, "
            f"market={market}, company={safe_company_name}, "
            f"form={filing.form_type}, accession={filing.accession_number}"
        )
        
        target_dir = (
            self.entities_dir /
            market /
            safe_company_name /
            FILINGS_SUBDIRECTORY /
            filing.form_type /
            filing.accession_number
        )
        
        logger.info(f"{LOG_OUTPUT} Built filing directory path: {target_dir}")
        
        return target_dir
    
    def build_taxonomy_path(self, taxonomy) -> Path:
        """
        Build directory path for taxonomy download.
        
        Structure: {taxonomies_dir}/{taxonomy_name}/{version}/
        Example: /mnt/map_pro/taxonomies/us-gaap/2024/
        
        Args:
            taxonomy: TaxonomyLibrary record
            
        Returns:
            Path object for taxonomy directory
        """
        logger.info(
            f"{LOG_PROCESS} Building taxonomy path: "
            f"taxonomies_dir={self.taxonomies_dir}, "
            f"name={taxonomy.taxonomy_name}, "
            f"version={taxonomy.taxonomy_version}"
        )
        
        target_dir = (
            self.taxonomies_dir /
            taxonomy.taxonomy_name /
            taxonomy.taxonomy_version
        )
        
        logger.info(f"{LOG_OUTPUT} Built taxonomy directory path: {target_dir}")
        
        return target_dir
    
    def _normalize_company_name(self, company_name: str) -> str:
        """
        Normalize company name for safe filesystem usage.
        
        Rules:
        - Remove unsafe characters (/, \\)
        - Replace spaces with underscores
        - Keep only alphanumeric and underscores
        
        Args:
            company_name: Raw company name
            
        Returns:
            Filesystem-safe company name
        """
        # Remove unsafe path characters
        safe_name = company_name
        for unsafe_char in UNSAFE_PATH_CHARS:
            safe_name = safe_name.replace(unsafe_char, PATH_REPLACEMENT_CHAR)
        
        # Replace spaces with underscores
        safe_name = safe_name.replace(' ', PATH_REPLACEMENT_CHAR)
        
        # Keep only alphanumeric and underscores
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c == PATH_REPLACEMENT_CHAR)
        
        return safe_name


__all__ = ['PathResolver']