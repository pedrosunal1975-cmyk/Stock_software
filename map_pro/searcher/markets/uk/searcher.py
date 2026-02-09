# Path: searcher/markets/uk/searcher.py
"""
UK Companies House Searcher

Main searcher implementation for UK Companies House market.
Implements BaseSearcher interface for standardized search operations.
"""

from typing import Optional

from searcher.engine.base_searcher import BaseSearcher
from searcher.core.config_loader import ConfigLoader
from searcher.core.logger import get_logger
from searcher.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT

from searcher.markets.uk.api_client import UKAPIClient
from searcher.markets.uk.url_builder import UKURLBuilder
from searcher.markets.uk.company_lookup import UKCompanyLookup
from searcher.markets.uk.filing_finder import UKFilingFinder
from searcher.markets.uk.response_parser import UKResponseParser
from searcher.markets.uk.validators import UKValidators
from searcher.markets.uk.data_builder import UKDataBuilder
from searcher.markets.uk.constants import (
    MARKET_ID,
    CATEGORY_ACCOUNTS,
    MSG_COMPANY_NOT_FOUND,
    ERR_COMPANY_NOT_FOUND,
    ERR_INVALID_COMPANY_NUMBER,
)

logger = get_logger(__name__, 'markets')


class UKSearcher(BaseSearcher):
    """
    UK Companies House searcher implementation.

    Searches for company XBRL filings in UK Companies House.

    Features:
    - Company number validation and resolution
    - Accounts filing search
    - iXBRL document identification
    - Standardized output format
    """

    def __init__(self, config: ConfigLoader = None):
        """
        Initialize UK searcher.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()

        # Initialize components
        self.api_client = UKAPIClient(self.config)
        self.url_builder = UKURLBuilder(self.config)
        self.company_lookup = UKCompanyLookup(self.api_client, self.url_builder)
        self.filing_finder = UKFilingFinder(self.api_client, self.url_builder)
        self.response_parser = UKResponseParser()
        self.validators = UKValidators()
        self.data_builder = UKDataBuilder()

        logger.info(
            f"UK searcher initialized (market: {MARKET_ID})",
            extra={LOG_PROCESS: 'init'}
        )

    async def search_by_identifier(
        self,
        identifier: str,
        form_type: str,
        max_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict]:
        """
        Search for filings by company number.

        Args:
            identifier: UK company number (e.g., "00000006", "SC123456")
            form_type: Filing type (e.g., "AA" for Full Accounts, "AC" for Abridged)
            max_results: Maximum results to return
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            list[dict]: Standardized filing results
        """
        logger.info(
            f"Searching UK filings: {identifier}, form_type={form_type}",
            extra={
                LOG_INPUT: 'search',
                'identifier': identifier,
                'form_type': form_type,
                'max_results': max_results
            }
        )

        # Parse form types (allow comma-separated)
        filing_types = None
        if form_type and form_type != 'ALL':
            filing_types = [ft.strip() for ft in form_type.split(',')]

        # Validate inputs
        valid, error = self.validators.validate_search_params(
            identifier=identifier,
            filing_types=filing_types,
            start_date=start_date,
            end_date=end_date,
            limit=max_results
        )

        if not valid:
            logger.error(
                f"Validation error: {error}",
                extra={LOG_OUTPUT: 'error', 'error': error}
            )
            return [self.data_builder.build_error_result(
                identifier=identifier,
                error_code=ERR_INVALID_COMPANY_NUMBER,
                error_message=error
            )]

        try:
            # Resolve company number and get company data
            company_number, company_data = await self.company_lookup.resolve(identifier)

            if not company_data:
                logger.warning(
                    f"{MSG_COMPANY_NOT_FOUND}: {identifier}",
                    extra={LOG_OUTPUT: 'not_found'}
                )
                return [self.data_builder.build_error_result(
                    identifier=identifier,
                    error_code=ERR_COMPANY_NOT_FOUND,
                    error_message=MSG_COMPANY_NOT_FOUND
                )]

            logger.debug(
                f"Company found: {company_data.get('company_name')}",
                extra={LOG_PROCESS: 'company_resolved', 'company_number': company_number}
            )

            # Find filings
            filings = await self.filing_finder.find_accounts_filings(
                company_number=company_number,
                filing_types=filing_types,
                start_date=start_date,
                end_date=end_date,
                limit=max_results
            )

            if not filings:
                logger.info(
                    f"No filings found for {company_number}",
                    extra={LOG_OUTPUT: 'no_results'}
                )
                return []

            # Build standardized results
            results = []
            for filing in filings:
                # Get document ID and download URL
                document_id = filing.get('document_id')
                download_url = filing.get('document_download_url')  # Use pre-constructed URL

                if not download_url:
                    # Fallback: use self link from filing if no document available
                    # This satisfies database NOT NULL constraint for filing_url
                    links = filing.get('links', {})
                    self_link = links.get('self')
                    if self_link:
                        # Construct full URL from relative link using base URL from config
                        base_url = self.url_builder.base_url
                        download_url = f"{base_url}{self_link}"

                # Build result
                result = self.data_builder.build_filing_result(
                    filing_item=filing,
                    company_data=company_data,
                    document_id=document_id,
                    download_url=download_url
                )

                results.append(result)

            logger.info(
                f"Found {len(results)} filings for {company_number}",
                extra={LOG_OUTPUT: 'results', 'count': len(results)}
            )

            return results

        except Exception as e:
            logger.error(
                f"Search failed: {e}",
                extra={LOG_OUTPUT: 'error', 'error': str(e)}
            )
            return [self.data_builder.build_error_result(
                identifier=identifier,
                error_code='UK999',
                error_message=f"Search failed: {str(e)}"
            )]

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

        Note: Company name search not yet implemented.
        UK Companies House requires company number for direct lookups.

        Args:
            company_name: Company name
            form_type: Filing type
            max_results: Maximum results
            start_date: Start date filter
            end_date: End date filter

        Returns:
            list[dict]: Error result (not implemented)
        """
        logger.warning(
            "Company name search not implemented for UK market",
            extra={LOG_PROCESS: 'not_implemented'}
        )

        return [self.data_builder.build_error_result(
            identifier=company_name,
            error_code='UK998',
            error_message="Company name search not yet implemented for UK market. Please use company number."
        )]

    async def close(self):
        """Close resources."""
        await self.api_client.close()
        logger.debug("UK searcher closed", extra={LOG_PROCESS: 'cleanup'})

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


__all__ = ['UKSearcher']
