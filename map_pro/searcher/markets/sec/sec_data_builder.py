# Path: searcher/markets/sec/sec_data_builder.py
"""
SEC Data Structure Builders.

Builds standardized data structures for companies and filings.
"""

from typing import Optional
from datetime import datetime, timezone, date

from searcher.markets.sec.constants import (
    FORM_10K,
    FORM_10Q,
    FORM_8K,
    FORM_20F,
    MAJOR_FILING_TYPES,
)


# Build SEC_FILING_TYPES for the builder
SEC_FILING_TYPES = {
    FORM_10K: 'Annual Report',
    FORM_10Q: 'Quarterly Report',
    FORM_8K: 'Current Report',
    FORM_20F: 'Annual Report (Foreign)',
}


class CompanyDataBuilder:
    """
    Builds standardized company information structures.
    
    Static methods for building company data dictionaries
    in the format expected by the market-agnostic interface.
    """
    
    @staticmethod
    def build_company_info(cik: str, submissions_data: dict[str, any]) -> dict[str, any]:
        """
        Build standardized company information dictionary.
        
        Args:
            cik: Company CIK
            submissions_data: Raw submissions data from SEC API
            
        Returns:
            Standardized company information
        """
        return {
            'market_entity_id': cik,
            'name': submissions_data.get('name'),
            'ticker': CompanyDataBuilder._get_primary_ticker(submissions_data),
            'identifiers': CompanyDataBuilder._build_identifiers(cik, submissions_data),
            'jurisdiction': submissions_data.get('stateOfIncorporation'),
            'entity_type': submissions_data.get('entityType'),
            'status': 'active',
            'discovered_at': datetime.now(timezone.utc),
            'source_url': CompanyDataBuilder._build_company_url(cik),
            'additional_info': CompanyDataBuilder._build_additional_info(submissions_data)
        }
    
    @staticmethod
    def _get_primary_ticker(submissions_data: dict[str, any]) -> Optional[str]:
        """Get primary ticker symbol from submissions data."""
        tickers = submissions_data.get('tickers', [])
        if tickers:
            return tickers[0]
        return None
    
    @staticmethod
    def _build_identifiers(cik: str, submissions_data: dict[str, any]) -> dict[str, any]:
        """Build identifiers dictionary."""
        return {
            'cik': cik,
            'ein': submissions_data.get('ein'),
            'tickers': submissions_data.get('tickers', [])
        }
    
    @staticmethod
    def _build_company_url(cik: str) -> str:
        """Build SEC company URL."""
        return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
    
    @staticmethod
    def _build_additional_info(submissions_data: dict[str, any]) -> dict[str, any]:
        """Build additional company information."""
        return {
            'sic': submissions_data.get('sic'),
            'sic_description': submissions_data.get('sicDescription'),
            'fiscal_year_end': submissions_data.get('fiscalYearEnd'),
            'business_address': submissions_data.get('addresses', {}).get('business'),
            'mailing_address': submissions_data.get('addresses', {}).get('mailing'),
            'former_names': submissions_data.get('formerNames', [])
        }


class FilingDataBuilder:
    """
    Builds standardized filing information structures.
    
    Static methods for building filing data dictionaries
    in the format expected by the market-agnostic interface.
    """
    
    @staticmethod
    def build_filing_info(
        cik: str,
        accession_number: str,
        filing_type: str,
        filing_date: date,
        zip_url: str
    ) -> dict[str, any]:
        """
        Build standardized filing information dictionary.
        
        Args:
            cik: Company CIK
            accession_number: Filing accession number
            filing_type: Filing type code
            filing_date: Filing date
            zip_url: ZIP file URL
            
        Returns:
            Standardized filing information
        """
        return {
            'market_filing_id': accession_number,
            'filing_type': filing_type,
            'filing_date': filing_date,
            'title': SEC_FILING_TYPES.get(filing_type, filing_type),
            'url': zip_url,
            'format': '.zip',
            'source_url': FilingDataBuilder._build_filing_source_url(cik, filing_type),
            'additional_info': {
                'accession_number': accession_number,
                'filing_type_description': SEC_FILING_TYPES.get(filing_type, 'Other'),
                'has_xbrl_zip': True
            }
        }
    
    @staticmethod
    def _build_filing_source_url(cik: str, filing_type: str) -> str:
        """Build SEC filing source URL."""
        return (
            f"https://www.sec.gov/cgi-bin/browse-edgar?"
            f"action=getcompany&CIK={cik}&type={filing_type}"
            f"&dateb=&owner=exclude&count=100"
        )


__all__ = ['CompanyDataBuilder', 'FilingDataBuilder']