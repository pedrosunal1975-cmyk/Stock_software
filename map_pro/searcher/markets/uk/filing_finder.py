# Path: searcher/markets/uk/filing_finder.py
"""
UK Filing Finder

Finds and filters UK company filings from Companies House.
Specializes in accounts filings (iXBRL documents).
"""

from typing import Optional
from datetime import datetime, date

from searcher.core.logger import get_logger
from searcher.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT
from searcher.markets.uk.constants import (
    CATEGORY_ACCOUNTS,
    FILING_TYPE_FULL_ACCOUNTS,
    FILING_TYPE_ABRIDGED_ACCOUNTS,
    FILING_TYPE_DORMANT_ACCOUNTS,
    FILING_TYPE_GROUP_ACCOUNTS,
    FORMAT_IXBRL,
    FORMAT_PRIORITY,
    MSG_NO_ACCOUNTS_FOUND,
)
from searcher.markets.uk.api_client import UKAPIClient
from searcher.markets.uk.url_builder import UKURLBuilder

logger = get_logger(__name__, 'markets')


class UKFilingFinder:
    """
    Finds company filings in Companies House.

    Handles:
    - Filing history retrieval
    - Filtering by category (accounts)
    - Filtering by filing type
    - Date range filtering
    - Document format detection (iXBRL)
    """

    def __init__(self, api_client: UKAPIClient, url_builder: UKURLBuilder):
        """
        Initialize filing finder.

        Args:
            api_client: UK API client
            url_builder: UK URL builder
        """
        self.api_client = api_client
        self.url_builder = url_builder

    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse date string to date object.

        Args:
            date_str: Date string (YYYY-MM-DD)

        Returns:
            date: Parsed date or None
        """
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            return None

    def _is_in_date_range(
        self,
        filing_date: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> bool:
        """
        Check if filing date is in specified range.

        Args:
            filing_date: Filing date string
            start_date: Range start date
            end_date: Range end date

        Returns:
            bool: True if in range
        """
        filing_dt = self._parse_date(filing_date)
        if not filing_dt:
            return True  # Include if can't parse

        if start_date:
            start_dt = self._parse_date(start_date)
            if start_dt and filing_dt < start_dt:
                return False

        if end_date:
            end_dt = self._parse_date(end_date)
            if end_dt and filing_dt > end_dt:
                return False

        return True

    async def get_filing_history(
        self,
        company_number: str,
        category: str = CATEGORY_ACCOUNTS,
        items_per_page: int = 100
    ) -> list[dict]:
        """
        Get filing history for company.

        Args:
            company_number: Company number
            category: Filing category filter
            items_per_page: Items per page (max 100)

        Returns:
            list[dict]: Filing items
        """
        logger.debug(
            f"Fetching filing history for {company_number}",
            extra={LOG_INPUT: 'filing_history', 'company_number': company_number}
        )

        # Get filing history URL
        url = self.url_builder.get_filing_history_url(
            company_number=company_number,
            category=category,
            items_per_page=items_per_page
        )

        # Fetch data
        data = await self.api_client.get_json(url)

        if not data:
            logger.warning(
                f"No filing history for {company_number}",
                extra={LOG_OUTPUT: 'no_filings'}
            )
            return []

        # Extract items
        items = data.get('items', [])

        logger.debug(
            f"Found {len(items)} filing items",
            extra={LOG_OUTPUT: 'filing_count', 'count': len(items)}
        )

        return items

    async def get_document_metadata(self, document_id: str) -> Optional[dict]:
        """
        Get document metadata to check available formats.

        Args:
            document_id: Document ID from filing

        Returns:
            dict: Document metadata or None
        """
        try:
            url = self.url_builder.get_document_metadata_url(document_id)
            logger.info(
                f"Fetching document metadata from: {url}",
                extra={LOG_PROCESS: 'metadata_fetch', 'document_id': document_id}
            )
            metadata = await self.api_client.get_json(url)
            logger.info(
                f"Document metadata response: {type(metadata).__name__}, "
                f"content: {str(metadata)[:200] if metadata else 'None'}",
                extra={LOG_OUTPUT: 'metadata_response'}
            )
            return metadata
        except Exception as e:
            logger.error(
                f"Failed to get document metadata: {e}",
                extra={LOG_OUTPUT: 'error', 'document_id': document_id}
            )
            return None

    def _get_preferred_format(self, metadata: dict) -> Optional[tuple[str, dict]]:
        """
        Get preferred document format from metadata.

        Prefers: iXBRL > XML > PDF

        Args:
            metadata: Document metadata

        Returns:
            tuple: (format_type, format_data) or None
        """
        resources = metadata.get('resources', {})

        # Try formats in priority order
        for format_type in FORMAT_PRIORITY:
            if format_type in resources:
                return format_type, resources[format_type]

        return None

    async def find_accounts_filings(
        self,
        company_number: str,
        filing_types: list[str] = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 10
    ) -> list[dict]:
        """
        Find accounts filings for company.

        Args:
            company_number: Company number
            filing_types: List of filing type codes (e.g., ['AA', 'AC'])
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            limit: Maximum results to return

        Returns:
            list[dict]: Filtered filing items with metadata
        """
        logger.debug(
            f"Finding accounts filings for {company_number}",
            extra={
                LOG_INPUT: 'find_filings',
                'company_number': company_number,
                'filing_types': filing_types,
                'date_range': f"{start_date} to {end_date}"
            }
        )

        # Get all accounts filings
        items = await self.get_filing_history(
            company_number=company_number,
            category=CATEGORY_ACCOUNTS
        )

        if not items:
            logger.warning(
                MSG_NO_ACCOUNTS_FOUND,
                extra={LOG_OUTPUT: 'no_accounts', 'company_number': company_number}
            )
            return []

        # Filter by filing type
        if filing_types:
            items = [
                item for item in items
                if item.get('type') in filing_types
            ]

        # Filter by date range
        if start_date or end_date:
            items = [
                item for item in items
                if self._is_in_date_range(item.get('date'), start_date, end_date)
            ]

        # Limit results
        items = items[:limit]

        logger.debug(
            f"After filtering: {len(items)} filings",
            extra={LOG_OUTPUT: 'filtered_count', 'count': len(items)}
        )

        # Enrich with document metadata
        enriched = []
        for item in items:
            links = item.get('links', {})

            # Get document ID from links
            document_metadata_url = links.get('document_metadata')

            if document_metadata_url:
                # Extract document ID from URL
                # Format can be absolute: https://document-api.company-information.service.gov.uk/document/{document_id}
                # Or relative: /document/{document_id}/metadata
                parts = document_metadata_url.split('/')

                # Find the document ID - it comes after '/document/' in the path
                if '/document/' in document_metadata_url:
                    # Get everything after /document/
                    doc_index = parts.index('document') if 'document' in parts else -1
                    if doc_index >= 0 and doc_index + 1 < len(parts):
                        document_id = parts[doc_index + 1]

                    # Get metadata
                    metadata = await self.get_document_metadata(document_id)

                    # Store document_id and construct download URL
                    # The document_metadata_url already has the full path, just need to add /content
                    item['document_id'] = document_id
                    item['document_download_url'] = f"{document_metadata_url}/content"

                    # Log metadata status for debugging
                    logger.info(
                        f"Document {document_id} metadata: {metadata is not None}",
                        extra={LOG_PROCESS: 'metadata_check'}
                    )

                    if metadata:
                        # Log full metadata structure for debugging
                        logger.info(
                            f"Document {document_id} metadata keys: {list(metadata.keys())}",
                            extra={LOG_PROCESS: 'metadata_keys'}
                        )

                        # Log available formats for debugging
                        resources = metadata.get('resources', {})
                        logger.info(
                            f"Document {document_id} available formats: {list(resources.keys())}",
                            extra={LOG_PROCESS: 'format_check', 'formats': list(resources.keys())}
                        )

                        # Get preferred format
                        format_info = self._get_preferred_format(metadata)

                        # Add metadata
                        item['document_metadata'] = metadata

                        if format_info:
                            format_type, format_data = format_info
                            item['preferred_format'] = format_type
                            item['format_data'] = format_data
                        else:
                            item['preferred_format'] = None
                            item['format_data'] = None
                    else:
                        # Even without metadata, we can still download
                        item['document_metadata'] = None
                        item['preferred_format'] = None
                        item['format_data'] = None

            enriched.append(item)

        return enriched

    async def get_document_download_url(self, document_id: str) -> str:
        """
        Get document download URL.

        Args:
            document_id: Document ID

        Returns:
            str: Download URL
        """
        return self.url_builder.get_document_content_url(document_id)
