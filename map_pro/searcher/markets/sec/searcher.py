# Path: searcher/markets/sec/searcher.py
"""
SEC Searcher

Main searcher implementation for SEC EDGAR filings.
Implements BaseSearcher interface with async operations.
"""

from typing import Optional
from datetime import datetime

from searcher.engine.base_searcher import BaseSearcher
from searcher.core.logger import get_logger
from searcher.constants import (
    LOG_INPUT,
    LOG_PROCESS,
    LOG_OUTPUT,
    MARKET_SEC,
    KEY_FILING_URL,
    KEY_FORM_TYPE,
    KEY_FILING_DATE,
    KEY_COMPANY_NAME,
    KEY_ENTITY_ID,
    KEY_ACCESSION_NUMBER,
    KEY_MARKET_ID,
)
from searcher.markets.sec.constants import (
    FORM_TYPE_ALIASES,
    ERROR_NO_FILINGS,
    ERROR_NO_ZIP,
)
from searcher.markets.sec.api_client import SECAPIClient
from searcher.markets.sec.company_lookup import SECCompanyLookup
from searcher.markets.sec.url_builder import SECURLBuilder
from searcher.markets.sec.zip_finder import SECZIPFinder

logger = get_logger(__name__, 'markets')


class SECSearcher(BaseSearcher):
    """
    SEC EDGAR searcher implementation.
    
    Workflow:
    1. Resolve identifier → CIK (via company_lookup)
    2. Fetch submissions.json (via api_client)
    3. Filter filings by form type and date
    4. For each filing:
       - Fetch index.json
       - Find XBRL ZIP file
       - Build result dictionary
    5. Return results
    """
    
    def __init__(self):
        """Initialize SEC searcher with all components."""
        self.api_client = SECAPIClient()
        self.company_lookup = SECCompanyLookup(self.api_client)
        self.url_builder = SECURLBuilder()
        self.zip_finder = SECZIPFinder(self.url_builder)
    
    async def search_by_identifier(
        self,
        identifier: str,
        form_type: str,
        max_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict]:
        """
        Search SEC filings by company identifier.
        
        Args:
            identifier: Ticker, CIK, or company name
            form_type: Filing form type (10-K, 10-Q, etc.)
            max_results: Maximum results to return
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            
        Returns:
            List of filing dictionaries
        """
        logger.info(f"{LOG_INPUT} SEC search: {identifier} / {form_type} / max={max_results}")
        
        # Normalize form type
        form_type_normalized = self._normalize_form_type(form_type)
        
        # Resolve identifier to CIK
        logger.info(f"{LOG_PROCESS} Resolving identifier: {identifier}")
        cik = await self.company_lookup.resolve_identifier(identifier)
        logger.info(f"{LOG_OUTPUT} Resolved to CIK: {cik}")
        
        # Fetch submissions.json
        logger.info(f"{LOG_PROCESS} Fetching submissions.json for CIK: {cik}")
        submissions_url = self.url_builder.build_submissions_url(cik)
        submissions_data = await self.api_client.get_json(submissions_url)
        
        # Extract company name (SEC API contract - stable field name)
        company_name = submissions_data.get('name', identifier)
        
        # Get recent filings (SEC API contract - stable field names)
        filings = submissions_data.get('filings', {})
        recent = filings.get('recent', {})
        
        if not recent:
            logger.warning(f"{ERROR_NO_FILINGS} for {identifier}")
            return []
        
        # Extract filing arrays (SEC API contract - stable field names)
        accession_numbers = recent.get('accessionNumber', [])
        filing_dates = recent.get('filingDate', [])
        form_types = recent.get('form', [])

        # Process filings and build results
        results = await self._process_filings(
            cik=cik,
            company_name=company_name,
            accession_numbers=accession_numbers,
            filing_dates=filing_dates,
            form_types=form_types,
            form_type_normalized=form_type_normalized,
            max_results=max_results,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"{LOG_OUTPUT} SEC search complete: {len(results)} results")

        return results
    
    async def search_by_company_name(
        self,
        company_name: str,
        form_type: str,
        max_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict]:
        """
        Search SEC filings by company name.
        
        Delegates to search_by_identifier (company_lookup handles name resolution).
        
        Args:
            company_name: Company name or partial name
            form_type: Filing form type
            max_results: Maximum results
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            List of filing dictionaries
        """
        return await self.search_by_identifier(
            identifier=company_name,
            form_type=form_type,
            max_results=max_results,
            start_date=start_date,
            end_date=end_date
        )
    
    async def _process_filings(
        self,
        cik: str,
        company_name: str,
        accession_numbers: list,
        filing_dates: list,
        form_types: list,
        form_type_normalized: str,
        max_results: int,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> list[dict]:
        """
        Process filings and build result list.

        Args:
            cik: Company CIK
            company_name: Company name
            accession_numbers: List of accession numbers
            filing_dates: List of filing dates
            form_types: List of form types
            form_type_normalized: Normalized form type to match
            max_results: Maximum results to return
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of filing dictionaries
        """
        results = []

        for i, (accession, date, form) in enumerate(zip(accession_numbers, filing_dates, form_types)):
            # Stop if we have enough results
            if len(results) >= max_results:
                break

            # Filter by form type
            if form != form_type_normalized:
                continue

            # Filter by date range
            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue

            logger.info(f"{LOG_PROCESS} Processing filing {i+1}: {form} / {date} / {accession}")

            # Try to get XBRL ZIP URL
            try:
                zip_url = await self._find_zip_url(cik, accession)

                if not zip_url:
                    logger.info(f"No XBRL ZIP found for {accession}, skipping")
                    continue

                # Build result dictionary
                result = self._build_result_dict(
                    filing_url=zip_url,
                    form_type=form,
                    filing_date=date,
                    company_name=company_name,
                    entity_id=cik,
                    accession_number=accession,
                    market_id=MARKET_SEC
                )

                results.append(result)
                logger.info(f"{LOG_OUTPUT} Added filing: {form} / {date}")

            except Exception as e:
                logger.error(f"Failed to process filing {accession}: {e}")
                continue

        return results

    def _normalize_form_type(self, form_type: str) -> str:
        """
        Normalize form type to official SEC format.
        
        Args:
            form_type: User input (e.g., '10K', '10-K', '10_K')
            
        Returns:
            Official form type (e.g., '10-K')
        """
        form_type_clean = form_type.strip().lower().replace(' ', '')
        
        # Check aliases
        if form_type_clean in FORM_TYPE_ALIASES:
            normalized = FORM_TYPE_ALIASES[form_type_clean]
            logger.debug(f"Normalized form type: {form_type} → {normalized}")
            return normalized
        
        # Return as-is if no alias found (might be already normalized)
        return form_type.strip()
    
    async def _find_zip_url(self, cik: str, accession_number: str) -> Optional[str]:
        """
        Find XBRL ZIP URL using index.json or pattern matching.
        
        Strategy:
        1. Try index.json (if it exists)
        2. Fallback to pattern matching with HEAD validation
        
        Args:
            cik: Company CIK
            accession_number: Filing accession number
            
        Returns:
            ZIP URL or None if not found
        """
        # Strategy 1: Try index.json
        logger.debug(f"Trying index.json for {accession_number}")
        index_data = await self.api_client.get_filing_index(cik, accession_number)
        
        if index_data:
            # Use index.json to find ZIP
            zip_url = self.zip_finder.find_xbrl_zip(index_data, cik, accession_number)
            if zip_url:
                return zip_url
        
        # Strategy 2: Pattern matching with HEAD validation
        logger.debug(f"No index.json, trying URL patterns for {accession_number}")
        return await self._find_zip_by_patterns(cik, accession_number)
    
    async def _find_zip_by_patterns(self, cik: str, accession_number: str) -> Optional[str]:
        """
        Find ZIP URL using multiple URL patterns with HEAD validation.
        
        Args:
            cik: Company CIK
            accession_number: Filing accession number
            
        Returns:
            ZIP URL or None if not found
        """
        from searcher.core.config_loader import ConfigLoader
        
        config = ConfigLoader()
        archives_base = config.get('sec_archives_base_url')
        
        # Prepare URL components
        cik_no_zeros = str(int(cik))
        accession_no_dashes = accession_number.replace('-', '')
        accession_underscore = accession_number.replace('-', '_')
        
        # Generate potential ZIP URLs (priority order)
        potential_urls = [
            f"{archives_base}{cik_no_zeros}/{accession_no_dashes}/{accession_number}-xbrl.zip",
            f"{archives_base}{cik_no_zeros}/{accession_no_dashes}/{accession_underscore}_htm.zip",
            f"{archives_base}{cik_no_zeros}/{accession_no_dashes}/{accession_no_dashes}-xbrl.zip",
            f"{archives_base}{cik_no_zeros}/{accession_no_dashes}/{accession_underscore}_xbrl.zip",
        ]
        
        # Validate each URL until we find one that exists
        for url in potential_urls:
            if await self.api_client.check_url_exists(url):
                zip_filename = url.split('/')[-1]
                logger.info(f"Found ZIP via URL validation: {zip_filename}")
                return url
        
        logger.info(f"No XBRL ZIP found for {accession_number} after checking all patterns")
        return None
    
    async def close(self) -> None:
        """Close API client session."""
        await self.api_client.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


__all__ = ['SECSearcher']