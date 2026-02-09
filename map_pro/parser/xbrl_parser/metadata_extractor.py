# Path: xbrl_parser/metadata_extractor.py
"""
Metadata Extractor

Extracts metadata from DEI (Document and Entity Information) facts.
Populates FilingMetadata from parsed XBRL facts.

DEI facts are standard across all XBRL taxonomies and include:
- DocumentType / DocumentFiscalPeriodFocus
- EntityRegistrantName / EntityCommonName
- EntityCentralIndexKey / EntityIdentifier
- DocumentPeriodEndDate
- CurrentFiscalYearEndDate
- DocumentFiscalYearFocus

This extractor is market-agnostic and works with any XBRL taxonomy.
"""

import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from .models.parsed_filing import FilingMetadata, Fact


class MetadataExtractor:
    """
    Extracts metadata from DEI (Document and Entity Information) facts.

    DEI facts are standardized across XBRL taxonomies and contain:
    - Entity information (name, identifier)
    - Document information (type, period)
    - Filing information (dates, fiscal periods)
    """

    # DEI fact search limit (DEI facts are typically at the beginning)
    DEI_SEARCH_LIMIT = 200

    # Common DEI concept patterns (market-agnostic)
    DOCUMENT_TYPE_CONCEPTS = [
        'DocumentType',
        'DocumentFiscalPeriodFocus',
        'FormType',
    ]

    ENTITY_NAME_CONCEPTS = [
        'EntityRegistrantName',
        'EntityCommonName',
        'EntityLegalName',
        'CompanyName',
    ]

    ENTITY_IDENTIFIER_CONCEPTS = [
        'EntityCentralIndexKey',
        'CentralIndexKey',
        'EntityIdentifier',
        'CompanyIdentifier',
    ]

    PERIOD_END_CONCEPTS = [
        'DocumentPeriodEndDate',
        'PeriodEndDate',
        'ReportingPeriodEndDate',
        'BalanceSheetDate',
    ]

    FILING_DATE_CONCEPTS = [
        'DocumentCreationDate',
        'DocumentDate',
        'FilingDate',
        'ReportDate',
    ]

    # Regulatory/Market identification
    REGULATORY_CONCEPTS = [
        'DocumentType',  # Can infer from form type
    ]

    def __init__(self):
        """Initialize metadata extractor."""
        self.logger = logging.getLogger('parser.metadata_extractor')

    def extract(
        self,
        facts: list[Fact],
        contexts: Optional[list] = None,
        entry_point: Optional[Path] = None,
        filing_id: Optional[str] = None
    ) -> FilingMetadata:
        """
        Extract metadata from facts and contexts.

        Args:
            facts: list of all facts from instance document
            contexts: Optional list of contexts (for extracting period dates)
            entry_point: Optional entry point path
            filing_id: Optional filing ID

        Returns:
            FilingMetadata object with populated fields
        """
        metadata = FilingMetadata()

        # set basic fields
        if filing_id:
            metadata.filing_id = filing_id
        if entry_point:
            metadata.entry_point = entry_point
            metadata.source_files = [entry_point]

        # Extract from DEI facts
        search_limit = min(self.DEI_SEARCH_LIMIT, len(facts))

        for fact in facts[:search_limit]:
            fact_name = self._get_fact_name(fact)
            fact_value = self._get_fact_value(fact)

            if not fact_name or not fact_value:
                continue

            # Document type
            if not metadata.document_type:
                for concept in self.DOCUMENT_TYPE_CONCEPTS:
                    if concept in fact_name:
                        metadata.document_type = str(fact_value).strip()
                        self.logger.debug(f"Found document_type: {metadata.document_type}")
                        break

            # Entity name
            if not metadata.company_name:
                for concept in self.ENTITY_NAME_CONCEPTS:
                    if concept in fact_name:
                        metadata.company_name = str(fact_value).strip()
                        self.logger.debug(f"Found company_name: {metadata.company_name}")
                        break

            # Entity identifier
            if not metadata.entity_identifier:
                for concept in self.ENTITY_IDENTIFIER_CONCEPTS:
                    if concept in fact_name:
                        metadata.entity_identifier = str(fact_value).strip()
                        self.logger.debug(f"Found entity_identifier: {metadata.entity_identifier}")
                        break

            # Period end date
            if not metadata.period_end_date:
                for concept in self.PERIOD_END_CONCEPTS:
                    if concept in fact_name:
                        metadata.period_end_date = self._parse_date(fact_value)
                        if metadata.period_end_date:
                            self.logger.debug(f"Found period_end_date: {metadata.period_end_date}")
                        break

            # Filing date
            if not metadata.filing_date:
                for concept in self.FILING_DATE_CONCEPTS:
                    if concept in fact_name:
                        metadata.filing_date = self._parse_date(fact_value)
                        if metadata.filing_date:
                            self.logger.debug(f"Found filing_date: {metadata.filing_date}")
                        break

        # If period_end_date not found in facts, extract from contexts
        if not metadata.period_end_date and contexts:
            metadata.period_end_date = self._extract_period_from_contexts(contexts)

        # Infer market from document type if available
        if metadata.document_type and not metadata.market:
            metadata.market = self._infer_market(metadata.document_type)
            if metadata.market:
                metadata.regulatory_authority = metadata.market.upper()

        # Log extraction results
        self._log_extraction_summary(metadata)

        return metadata

    def _get_fact_name(self, fact: Fact) -> Optional[str]:
        """Get fact name from Fact object."""
        if hasattr(fact, 'name'):
            return fact.name
        elif isinstance(fact, dict):
            return fact.get('name')
        return None

    def _get_fact_value(self, fact: Fact) -> Optional[str]:
        """Get fact value from Fact object."""
        if hasattr(fact, 'value'):
            return fact.value
        elif isinstance(fact, dict):
            return fact.get('value')
        return None

    def _parse_date(self, value: any) -> Optional[datetime]:
        """
        Parse date from various formats.

        Handles:
        - ISO format: 2024-12-31
        - Already datetime objects
        """
        if isinstance(value, datetime):
            return value

        if not value:
            return None

        value_str = str(value).strip()

        # Try ISO format (most common in XBRL)
        try:
            return datetime.fromisoformat(value_str)
        except (ValueError, AttributeError):
            pass

        # Try common date formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y%m%d']:
            try:
                return datetime.strptime(value_str, fmt)
            except (ValueError, AttributeError):
                continue

        self.logger.warning(f"Could not parse date: {value_str}")
        return None

    def _extract_period_from_contexts(self, contexts) -> Optional[datetime]:
        """
        Extract most recent period end date from contexts.

        XBRL contexts define time periods for facts. Many filings don't have
        DocumentPeriodEndDate as a separate fact - the period is in contexts.

        Args:
            contexts: Dictionary of context objects (context_id -> Context) or list

        Returns:
            Most recent period end date found in contexts
        """
        latest_date = None

        try:
            # Handle both dict and list
            if isinstance(contexts, dict):
                context_list = contexts.values()
            else:
                context_list = contexts

            for context in context_list:
                # Handle both object attributes and dict access
                period = None
                if hasattr(context, 'period'):
                    period = context.period
                elif isinstance(context, dict):
                    period = context.get('period')

                if not period:
                    continue

                # Extract end date from period
                end_date = None
                if hasattr(period, 'end_date'):
                    end_date = period.end_date
                elif isinstance(period, dict):
                    end_date = period.get('end_date') or period.get('endDate')

                if end_date:
                    # Parse the date
                    parsed_date = self._parse_date(end_date)
                    if parsed_date:
                        # Keep the latest date
                        if not latest_date or parsed_date > latest_date:
                            latest_date = parsed_date

            if latest_date:
                self.logger.info(f"Extracted period_end_date from contexts: {latest_date.strftime('%Y-%m-%d')}")
            else:
                self.logger.warning("Could not extract period_end_date from contexts")

            return latest_date

        except Exception as e:
            self.logger.warning(f"Error extracting period from contexts: {e}")
            return None

    def _infer_market(self, document_type: str) -> Optional[str]:
        """
        Infer market/regulatory authority from document type.

        This is a best-effort inference and may not always be accurate.
        """
        doc_type_upper = document_type.upper()

        # US SEC forms
        sec_forms = ['10-K', '10-Q', '8-K', '20-F', '40-F', 'S-1', 'S-3', 'DEF 14A']
        for form in sec_forms:
            if form in doc_type_upper:
                return 'sec'

        # UK forms
        if 'ANNUAL REPORT' in doc_type_upper or 'ACCOUNTS' in doc_type_upper:
            # Could be UK, but ambiguous - return None
            return None

        # If contains specific keywords
        if 'ESEF' in doc_type_upper:
            return 'esma'

        return None

    def _log_extraction_summary(self, metadata: FilingMetadata) -> None:
        """Log summary of extracted metadata."""
        extracted = []
        if metadata.document_type:
            extracted.append(f"document_type={metadata.document_type}")
        if metadata.company_name:
            extracted.append(f"company_name={metadata.company_name}")
        if metadata.entity_identifier:
            extracted.append(f"entity_identifier={metadata.entity_identifier}")
        if metadata.period_end_date:
            extracted.append(f"period_end_date={metadata.period_end_date.strftime('%Y-%m-%d')}")
        if metadata.filing_date:
            extracted.append(f"filing_date={metadata.filing_date.strftime('%Y-%m-%d')}")
        if metadata.market:
            extracted.append(f"market={metadata.market}")

        if extracted:
            self.logger.info(f"Metadata extracted: {', '.join(extracted)}")
        else:
            self.logger.warning("No metadata could be extracted from facts")


__all__ = ['MetadataExtractor']
