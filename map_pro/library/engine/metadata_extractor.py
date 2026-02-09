# Path: library/engine/metadata_extractor.py
"""
Metadata Extractor

Extracts business metadata from parsed filing folder structures.
Uses loaders/parsed_loader.py for file discovery, focuses on metadata interpretation.

Architecture:
- Delegates discovery to parsed_loader.py
- Extracts metadata from folder structure (company, form, accession, market)
- Creates FilingEntry objects with business context
- Structure-agnostic: extracts from END of path
"""

from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

from library.core.config_loader import LibraryConfig
from library.core.logger import get_logger
from library.loaders.parsed_loader import ParsedLoader, ParsedFileLocation
from library.models.filing_entry import FilingEntry
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'engine')


class MetadataExtractor:
    """
    Extracts business metadata from folder structure.
    
    Uses ParsedLoader for discovery, interprets folder structure.
    
    Example:
        extractor = MetadataExtractor()
        
        # Get all filings with metadata
        filings = extractor.extract_all()
        
        for filing in filings:
            print(f"{filing.market}/{filing.company}/{filing.form}")
    """
    
    def __init__(self, config: Optional[LibraryConfig] = None):
        """
        Initialize metadata extractor.
        
        Args:
            config: Optional LibraryConfig instance
        """
        self.config = config if config else LibraryConfig()
        self.loader = ParsedLoader(self.config)
        
        logger.info(f"{LOG_INPUT} MetadataExtractor initialized")
    
    def extract_all(self) -> List[FilingEntry]:
        """
        Extract metadata for all discovered filings.
        
        Returns:
            List of FilingEntry objects with metadata
        """
        logger.info(f"{LOG_PROCESS} Extracting metadata from all filings")
        
        # Discover files using loader
        locations = self.loader.discover_all()
        
        # Extract metadata from each
        entries = []
        for location in locations:
            entry = self._extract_metadata(location)
            if entry:
                entries.append(entry)
        
        logger.info(f"{LOG_OUTPUT} Extracted metadata from {len(entries)} filings")
        
        # Sort by market, company, form, accession
        entries.sort(key=lambda e: (e.market, e.company, e.form, e.accession))
        
        return entries
    
    def extract_by_market(self, market: str) -> List[FilingEntry]:
        """
        Extract metadata for filings from specific market.
        
        Args:
            market: Market identifier (e.g., 'sec', 'fca')
            
        Returns:
            List of FilingEntry objects for that market
        """
        logger.info(f"{LOG_PROCESS} Extracting metadata for market: {market}")
        
        all_entries = self.extract_all()
        
        market_entries = [
            entry for entry in all_entries
            if entry.market.lower() == market.lower()
        ]
        
        logger.info(f"{LOG_OUTPUT} Found {len(market_entries)} filings for {market}")
        
        return market_entries
    
    def extract_by_company(self, company: str) -> List[FilingEntry]:
        """
        Extract metadata for filings from specific company.
        
        Args:
            company: Company name
            
        Returns:
            List of FilingEntry objects for that company
        """
        logger.info(f"{LOG_PROCESS} Extracting metadata for company: {company}")
        
        all_entries = self.extract_all()
        
        company_entries = [
            entry for entry in all_entries
            if company.lower() in entry.company.lower()
        ]
        
        logger.info(f"{LOG_OUTPUT} Found {len(company_entries)} filings for {company}")
        
        return company_entries
    
    def _extract_metadata(
        self,
        location: ParsedFileLocation
    ) -> Optional[FilingEntry]:
        """
        Extract business metadata from folder structure.
        
        STRUCTURE-AGNOSTIC: Extracts from END of path.
        Minimum 3 parts required: company/form/accession
        
        Args:
            location: ParsedFileLocation from loader
            
        Returns:
            FilingEntry with metadata or None if invalid
        """
        try:
            parts = location.relative_path.parts
            
            # Minimum 3 parts required: company/form/accession
            if len(parts) < 3:
                logger.debug(
                    f"Path too shallow (need 3+ parts, got {len(parts)}): "
                    f"{location.relative_path}"
                )
                return None
            
            # STRUCTURE-AGNOSTIC: Extract from END of path
            # Don't care about intermediate folder names
            accession = parts[-1]      # Innermost directory
            form = parts[-2]           # Parent directory
            company = parts[-3]        # Grandparent directory
            
            # Try to detect market from first part if available
            # Default to 'unknown' if path is shallow
            market = parts[0] if len(parts) >= 4 else 'unknown'
            
            # Discover all available files in folder
            available_files = self._discover_files(location.filing_folder)
            
            if not available_files:
                logger.warning(f"No files found in {location.filing_folder}")
                return None
            
            # Create FilingEntry with metadata
            entry = FilingEntry(
                market=market,
                company=company,
                form=form,
                accession=accession,
                filing_folder=location.filing_folder,
                parsed_json_path=location.parsed_json_path,
                available_files=available_files
            )
            
            logger.debug(f"{LOG_OUTPUT} Extracted metadata: {entry.filing_id}")
            
            return entry
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {location.relative_path}: {e}")
            return None
    
    def _discover_files(self, filing_folder: Path) -> Dict[str, Path]:
        """
        Discover all files in filing folder.
        
        Args:
            filing_folder: Path to filing folder
            
        Returns:
            Dictionary mapping file extension to path
        """
        files = {}
        
        try:
            for file_path in filing_folder.iterdir():
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    # Store by extension (without dot)
                    key = ext[1:] if ext.startswith('.') else ext
                    files[key] = file_path
        except Exception as e:
            logger.error(f"Error discovering files in {filing_folder}: {e}")
        
        return files
    
    def count_by_market(self) -> Dict[str, int]:
        """
        Count filings by market.
        
        Returns:
            Dictionary mapping market to count
        """
        logger.info(f"{LOG_PROCESS} Counting filings by market")
        
        entries = self.extract_all()
        
        counts = {}
        for entry in entries:
            market = entry.market
            counts[market] = counts.get(market, 0) + 1
        
        logger.info(f"{LOG_OUTPUT} Found {len(counts)} markets")
        
        return counts
    
    def count_by_form(self) -> Dict[str, int]:
        """
        Count filings by form type.
        
        Returns:
            Dictionary mapping form to count
        """
        logger.info(f"{LOG_PROCESS} Counting filings by form")
        
        entries = self.extract_all()
        
        counts = {}
        for entry in entries:
            form = entry.form
            counts[form] = counts.get(form, 0) + 1
        
        logger.info(f"{LOG_OUTPUT} Found {len(counts)} form types")
        
        return counts


__all__ = ['MetadataExtractor']