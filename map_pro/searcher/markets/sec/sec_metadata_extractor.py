# Path: searcher/markets/sec/sec_metadata_extractor.py
"""
SEC Metadata Extractor

Extends BaseMetadataExtractor for SEC-specific metadata.
Builds database-compatible metadata structures for FilingSearch table.

Architecture:
- Inherits universal metadata extraction from BaseMetadataExtractor
- Adds SEC-specific fields (CIK, accession number, form category)
- Returns structure matching database/models/filing_searches.py
"""

from typing import Optional
from datetime import datetime

from searcher.core.metadata_extractor import BaseMetadataExtractor
from searcher.markets.sec.constants import (
    ANNUAL_FILINGS,
    QUARTERLY_FILINGS,
    CURRENT_FILINGS,
)


class SECMetadataExtractor(BaseMetadataExtractor):
    """
    SEC-specific metadata extractor.
    
    Extends base extractor with SEC-specific fields for EDGAR filings.
    Output structure matches FilingSearch database model.
    
    Example:
        metadata = SECMetadataExtractor.extract_full_metadata(
            url='https://www.sec.gov/Archives/.../0001234567-25-000001-xbrl.zip',
            form_type='10-K',
            filing_date='2025-02-06',
            company_name='Trane Technologies',
            cik='0001466258',
            accession_number='0001466258-25-000039'
        )
        # Returns database-ready metadata
    """
    
    @staticmethod
    def extract_full_metadata(
        url: str,
        form_type: str,
        filing_date: str,
        company_name: str,
        cik: str,
        accession_number: str
    ) -> dict[str, any]:
        """
        Extract complete SEC filing metadata.
        
        Builds database-compatible structure for FilingSearch table.
        
        Args:
            url: Full ZIP file URL
            form_type: SEC form type (10-K, 10-Q, etc.)
            filing_date: Filing date (YYYY-MM-DD)
            company_name: Company name from search
            cik: SEC CIK number (padded to 10 digits)
            accession_number: SEC accession number
            
        Returns:
            Complete metadata matching FilingSearch database model
        """
        # Extract core metadata (universal)
        core_metadata = BaseMetadataExtractor.extract_core_metadata(
            url=url,
            form_type=form_type,
            filing_date=filing_date,
            company_name=company_name,
            market_type='sec',
            market_entity_id=cik
        )
        
        # Extract SEC-specific metadata
        sec_specific = SECMetadataExtractor._extract_sec_specific(
            cik=cik,
            accession_number=accession_number,
            form_type=form_type,
            filing_date=filing_date
        )
        
        # Extract URL components
        url_components = BaseMetadataExtractor.extract_url_components(url)
        
        # Classify file type
        file_classification = BaseMetadataExtractor.classify_file_type(
            url_components['filename']
        )
        
        # Build storage structure
        filing_year = filing_date.split('-')[0] if filing_date else ''
        storage_structure = BaseMetadataExtractor.build_storage_structure(
            market_type='sec',
            company_name=company_name,
            market_entity_id=cik,
            filing_year=filing_year,
            form_type=form_type,
            filename=url_components['filename']
        )
        
        # Build SEC-specific identifiers
        identifiers = SECMetadataExtractor._build_sec_identifiers(
            cik=cik,
            accession_number=accession_number
        )
        
        # Build search_metadata JSONB structure (for database)
        search_metadata = {
            'market_specific': sec_specific,
            'file_classification': file_classification,
            'storage_structure': storage_structure,
            'url_components': {
                'domain': url_components['domain'],
                'protocol': url_components['protocol'],
                'path': url_components['path'],
                'filename': url_components['filename'],
            }
        }
        
        # Build complete database-compatible record
        # Structure matches database/models/filing_searches.py
        metadata = {
            # Core fields (map to FilingSearch columns)
            'market_type': 'sec',
            'market_entity_id': cik,
            'company_name': company_name,
            'form_type': form_type,
            'filing_date': filing_date,
            'filing_url': url,
            'accession_number': accession_number,
            
            # JSONB fields
            'search_metadata': search_metadata,
            'identifiers': identifiers,
            
            # Status fields (for database workflow)
            'download_status': 'pending',
            'extraction_status': 'pending',
            
            # Timestamps
            'created_at': datetime.now().isoformat(),
            
            # Additional fields for searcher output
            'filename': url_components['filename'],
            'filing_year': filing_year,
        }
        
        return metadata
    
    @staticmethod
    def _extract_sec_specific(
        cik: str,
        accession_number: str,
        form_type: str,
        filing_date: str
    ) -> dict[str, any]:
        """
        Extract SEC-specific metadata fields.
        
        Args:
            cik: SEC CIK number
            accession_number: SEC accession number
            form_type: Filing form type
            filing_date: Filing date
            
        Returns:
            SEC-specific metadata dictionary
        """
        filing_year = filing_date.split('-')[0] if filing_date else ''
        
        # Determine form category
        form_category = SECMetadataExtractor._classify_form_type(form_type)
        
        # Extract CIK without leading zeros (for URLs)
        cik_no_zeros = str(int(cik)) if cik else ''
        
        # Build accession number variations
        accession_no_dashes = accession_number.replace('-', '')
        accession_underscore = accession_number.replace('-', '_')
        
        return {
            'cik_padded': cik,
            'cik_no_zeros': cik_no_zeros,
            'accession_number': accession_number,
            'accession_no_dashes': accession_no_dashes,
            'accession_underscore': accession_underscore,
            'filing_year': filing_year,
            'form_category': form_category,
            'is_annual': form_type in ANNUAL_FILINGS,
            'is_quarterly': form_type in QUARTERLY_FILINGS,
            'is_current': form_type in CURRENT_FILINGS,
        }
    
    @staticmethod
    def _classify_form_type(form_type: str) -> str:
        """
        Classify SEC form type into category.
        
        Args:
            form_type: SEC form type
            
        Returns:
            Form category (annual, quarterly, current, other)
        """
        if form_type in ANNUAL_FILINGS:
            return 'annual'
        elif form_type in QUARTERLY_FILINGS:
            return 'quarterly'
        elif form_type in CURRENT_FILINGS:
            return 'current'
        else:
            return 'other'
    
    @staticmethod
    def _build_sec_identifiers(
        cik: str,
        accession_number: str
    ) -> dict[str, str]:
        """
        Build SEC-specific identifiers.
        
        Args:
            cik: SEC CIK number
            accession_number: SEC accession number
            
        Returns:
            Identifiers dictionary
        """
        return {
            'cik': cik,
            'accession_number': accession_number,
        }


__all__ = ['SECMetadataExtractor']