# Path: searcher/markets/uk/data_builder.py
"""
UK Search Data Builder

Builds standardized search result format from Companies House data.
Ensures compatibility with rest of map_pro system.
"""

from typing import Optional
from datetime import datetime

from searcher.core.logger import get_logger
from searcher.constants import LOG_PROCESS
from searcher.markets.uk.constants import MARKET_ID, FORMAT_IXBRL

logger = get_logger(__name__, 'markets')


class UKDataBuilder:
    """
    Builds standardized search results from UK data.

    Output format matches other markets (SEC) for consistency.
    """

    @staticmethod
    def build_filing_result(
        filing_item: dict,
        company_data: dict,
        document_id: str = None,
        download_url: str = None
    ) -> dict:
        """
        Build standardized filing result.

        Args:
            filing_item: Filing item from CH API
            company_data: Company profile data
            document_id: Optional document ID
            download_url: Optional download URL

        Returns:
            dict: Standardized filing result
        """
        # Extract key fields
        transaction_id = filing_item.get('transaction_id', '')
        filing_type = filing_item.get('type', '')
        description = filing_item.get('description', '')
        category = filing_item.get('category', '')
        filing_date = filing_item.get('date', '')
        action_date = filing_item.get('action_date', '')

        # Get company info
        company_number = company_data.get('company_number', '')
        company_name = company_data.get('company_name', '')

        # Determine period end date (action_date or filing_date)
        period_end = action_date if action_date else filing_date

        # Get document metadata if available
        preferred_format = filing_item.get('preferred_format')
        format_data = filing_item.get('format_data', {})

        # Build result with standardized field names (matching orchestrator expectations)
        result = {
            # Standardized fields (required by orchestrator)
            'entity_id': company_number,
            'company_name': company_name,
            'form_type': filing_type,
            'filing_date': filing_date,
            'filing_url': download_url,
            'accession_number': transaction_id,
            'market_id': MARKET_ID,

            # Additional UK-specific fields
            'filing_description': description,
            'filing_category': category,
            'period_end': period_end,
            'document_id': document_id,
            'document_format': preferred_format,
            'is_ixbrl': preferred_format == FORMAT_IXBRL,
            'jurisdiction': company_data.get('jurisdiction', 'england-wales'),

            # Additional metadata
            'metadata': {
                'barcode': filing_item.get('barcode'),
                'pages': filing_item.get('pages'),
                'paper_filed': filing_item.get('paper_filed', False),
                'subcategory': filing_item.get('subcategory', []),
                'content_length': format_data.get('content_length') if format_data else None,
                'company_status': company_data.get('company_status'),
                'company_type': company_data.get('type'),
                'sic_codes': company_data.get('sic_codes', []),
            },

            # Links
            'links': filing_item.get('links', {}),
        }

        return result

    @staticmethod
    def build_error_result(
        identifier: str,
        error_code: str,
        error_message: str
    ) -> dict:
        """
        Build standardized error result.

        Args:
            identifier: Company identifier
            error_code: Error code
            error_message: Error message

        Returns:
            dict: Error result
        """
        return {
            'success': False,
            'error_code': error_code,
            'error_message': error_message,
            'identifier': identifier,
            'market': MARKET_ID,
            'timestamp': datetime.utcnow().isoformat(),
        }

    @staticmethod
    def build_search_summary(
        company_number: str,
        company_name: str,
        total_filings: int,
        filtered_filings: int,
        filing_types: list[str] = None,
        date_range: tuple[str, str] = None
    ) -> dict:
        """
        Build search summary metadata.

        Args:
            company_number: Company number
            company_name: Company name
            total_filings: Total filings found
            filtered_filings: Filings after filtering
            filing_types: Filing type filters
            date_range: Date range filter

        Returns:
            dict: Search summary
        """
        start_date, end_date = date_range if date_range else (None, None)

        return {
            'company_number': company_number,
            'company_name': company_name,
            'total_filings': total_filings,
            'filtered_filings': filtered_filings,
            'filters': {
                'filing_types': filing_types if filing_types else [],
                'start_date': start_date,
                'end_date': end_date,
            },
            'market': MARKET_ID,
            'timestamp': datetime.utcnow().isoformat(),
        }
