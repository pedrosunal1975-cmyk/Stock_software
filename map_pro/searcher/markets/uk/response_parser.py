# Path: searcher/markets/uk/response_parser.py
"""
UK Companies House Response Parser

Parses Companies House API responses and extracts relevant data.
"""

from typing import Optional
from datetime import datetime

from searcher.core.logger import get_logger
from searcher.constants import LOG_PROCESS

logger = get_logger(__name__, 'markets')


class UKResponseParser:
    """
    Parses Companies House API responses.

    Handles:
    - Company profile parsing
    - Filing history parsing
    - Document metadata parsing
    - Date parsing and normalization
    """

    @staticmethod
    def parse_company_profile(data: dict) -> dict:
        """
        Parse company profile response.

        Args:
            data: Company profile API response

        Returns:
            dict: Parsed company data
        """
        return {
            'company_number': data.get('company_number'),
            'company_name': data.get('company_name'),
            'company_status': data.get('company_status'),
            'company_type': data.get('type'),
            'jurisdiction': data.get('jurisdiction'),
            'date_of_creation': data.get('date_of_creation'),
            'registered_office_address': data.get('registered_office_address'),
            'sic_codes': data.get('sic_codes', []),
            'has_been_liquidated': data.get('has_been_liquidated', False),
            'has_insolvency_history': data.get('has_insolvency_history', False),
        }

    @staticmethod
    def parse_filing_item(item: dict) -> dict:
        """
        Parse single filing history item.

        Args:
            item: Filing item from filing history response

        Returns:
            dict: Parsed filing data
        """
        return {
            'transaction_id': item.get('transaction_id'),
            'type': item.get('type'),
            'description': item.get('description'),
            'category': item.get('category'),
            'date': item.get('date'),
            'action_date': item.get('action_date'),
            'barcode': item.get('barcode'),
            'subcategory': item.get('subcategory', []),
            'links': item.get('links', {}),
            'pages': item.get('pages'),
            'paper_filed': item.get('paper_filed', False),
        }

    @staticmethod
    def parse_filing_history(data: dict) -> dict:
        """
        Parse filing history response.

        Args:
            data: Filing history API response

        Returns:
            dict: Parsed filing history
        """
        items = data.get('items', [])

        return {
            'total_count': data.get('total_count', len(items)),
            'items_per_page': data.get('items_per_page', len(items)),
            'start_index': data.get('start_index', 0),
            'filing_history_status': data.get('filing_history_status'),
            'items': [UKResponseParser.parse_filing_item(item) for item in items],
        }

    @staticmethod
    def parse_document_metadata(data: dict) -> dict:
        """
        Parse document metadata response.

        Args:
            data: Document metadata API response

        Returns:
            dict: Parsed metadata
        """
        resources = data.get('resources', {})

        # Extract available formats
        available_formats = list(resources.keys())

        return {
            'document_id': data.get('etag'),  # Unique document identifier
            'company_number': data.get('company_number'),
            'barcode': data.get('barcode'),
            'significant_date': data.get('significant_date'),
            'significant_date_type': data.get('significant_date_type'),
            'category': data.get('category'),
            'pages': data.get('pages'),
            'filename': data.get('filename'),
            'available_formats': available_formats,
            'resources': resources,
        }

    @staticmethod
    def extract_document_id_from_url(url: str) -> Optional[str]:
        """
        Extract document ID from metadata URL.

        Args:
            url: Document metadata URL (e.g., /document/{id}/metadata)

        Returns:
            str: Document ID or None
        """
        if not url:
            return None

        # URL format: /document/{document_id}/metadata
        parts = url.split('/')
        if len(parts) >= 3 and parts[1] == 'document':
            return parts[2]

        return None

    @staticmethod
    def parse_date(date_str: str, format_str: str = '%Y-%m-%d') -> Optional[datetime]:
        """
        Parse date string.

        Args:
            date_str: Date string
            format_str: Date format

        Returns:
            datetime: Parsed datetime or None
        """
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, format_str)
        except Exception as e:
            logger.warning(
                f"Failed to parse date '{date_str}': {e}",
                extra={LOG_PROCESS: 'date_parse_error'}
            )
            return None

    @staticmethod
    def format_date(dt: datetime, format_str: str = '%Y-%m-%d') -> str:
        """
        Format datetime to string.

        Args:
            dt: Datetime object
            format_str: Output format

        Returns:
            str: Formatted date string
        """
        if not dt:
            return ''

        return dt.strftime(format_str)
