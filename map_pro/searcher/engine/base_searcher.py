# Path: searcher/engine/base_searcher.py
"""
Base Searcher

Abstract base class for all market-specific searchers.
Defines common interface for search operations.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseSearcher(ABC):
    """
    Abstract base class for market-specific searchers.
    
    All market searchers (SEC, ESMA, FCA) must inherit from this
    class and implement the required search methods.
    
    Returns raw dictionaries (not database models) for flexibility.
    Orchestrator handles database persistence.
    """
    
    @abstractmethod
    async def search_by_identifier(
        self,
        identifier: str,
        form_type: str,
        max_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict]:
        """
        Search for filings by company identifier.
        
        Args:
            identifier: Company identifier (ticker, CIK, LEI, etc.)
            form_type: Filing form type (10-K, 10-Q, etc.)
            max_results: Maximum number of results to return
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            
        Returns:
            List of filing dictionaries with keys:
                - filing_url: Direct download URL
                - form_type: Filing form type
                - filing_date: Filing date (YYYY-MM-DD)
                - company_name: Company name
                - entity_id: Entity identifier (CIK, LEI, etc.)
                - accession_number: Filing accession number
                - market_id: Market identifier
        """
        pass
    
    @abstractmethod
    async def search_by_company_name(
        self,
        company_name: str,
        form_type: str,
        max_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict]:
        """
        Search for filings by company name.
        
        Args:
            company_name: Company name or partial name
            form_type: Filing form type
            max_results: Maximum number of results
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            
        Returns:
            List of filing dictionaries (same format as search_by_identifier)
        """
        pass
    
    def _build_result_dict(
        self,
        filing_url: str,
        form_type: str,
        filing_date: str,
        company_name: str,
        entity_id: str,
        accession_number: str,
        market_id: str
    ) -> dict:
        """
        Build standardized result dictionary.
        
        Helper method to ensure consistent result format across markets.
        
        Args:
            filing_url: Direct download URL
            form_type: Filing form type
            filing_date: Filing date (YYYY-MM-DD)
            company_name: Company name
            entity_id: Entity identifier
            accession_number: Filing accession number
            market_id: Market identifier
            
        Returns:
            Standardized result dictionary
        """
        return {
            'filing_url': filing_url,
            'form_type': form_type,
            'filing_date': filing_date,
            'company_name': company_name,
            'entity_id': entity_id,
            'accession_number': accession_number,
            'market_id': market_id,
        }


__all__ = ['BaseSearcher']