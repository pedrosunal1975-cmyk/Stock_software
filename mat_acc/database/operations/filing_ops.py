# Path: mat_acc/database/operations/filing_ops.py
"""
Filing Operations

CRUD operations for ProcessedFiling records.
Provides methods for creating, finding, and querying filings.
"""

import logging
from datetime import date
from typing import Optional, List

from sqlalchemy.orm import Session

from database.models.processed_filings import ProcessedFiling


logger = logging.getLogger(__name__)


class FilingOperations:
    """
    Operations for ProcessedFiling records.

    Provides static methods for common filing operations.
    All methods require a session to be passed in.

    Example:
        with session_scope() as session:
            # Create filing
            filing = FilingOperations.create_filing(
                session,
                market='sec',
                company_name='Apple Inc',
                form_type='10-K',
                filing_date=date(2024, 9, 30)
            )

            # Find existing
            existing = FilingOperations.find_by_key(
                session,
                market='sec',
                company_name='Apple Inc',
                form_type='10-K',
                filing_date=date(2024, 9, 30)
            )
    """

    @staticmethod
    def create_filing(
        session: Session,
        market: str,
        company_name: str,
        form_type: str,
        filing_date: date,
        source_path: Optional[str] = None,
        accession_number: Optional[str] = None,
        cik: Optional[str] = None,
    ) -> ProcessedFiling:
        """
        Create a new processed filing record.

        Args:
            session: Database session
            market: Market code (sec, frc, esma, etc.)
            company_name: Company name
            form_type: Form type (10-K, 10-Q, etc.)
            filing_date: Filing date
            source_path: Path to source data
            accession_number: SEC accession number or equivalent
            cik: CIK or market entity ID

        Returns:
            Created ProcessedFiling instance
        """
        filing = ProcessedFiling(
            market=market,
            company_name=company_name,
            form_type=form_type,
            filing_date=filing_date,
            source_path=source_path,
            accession_number=accession_number,
            cik=cik,
        )
        session.add(filing)
        session.flush()  # Get the ID

        logger.info(
            f"Created filing: {market}/{company_name}/{form_type}/{filing_date}"
        )
        return filing

    @staticmethod
    def find_by_id(
        session: Session,
        filing_id: str
    ) -> Optional[ProcessedFiling]:
        """
        Find filing by ID.

        Args:
            session: Database session
            filing_id: Filing UUID

        Returns:
            ProcessedFiling or None
        """
        return session.query(ProcessedFiling).filter_by(
            filing_id=filing_id
        ).first()

    @staticmethod
    def find_by_key(
        session: Session,
        market: str,
        company_name: str,
        form_type: str,
        filing_date: date
    ) -> Optional[ProcessedFiling]:
        """
        Find filing by unique key combination.

        Args:
            session: Database session
            market: Market code
            company_name: Company name
            form_type: Form type
            filing_date: Filing date

        Returns:
            ProcessedFiling or None
        """
        return session.query(ProcessedFiling).filter_by(
            market=market,
            company_name=company_name,
            form_type=form_type,
            filing_date=filing_date
        ).first()

    @staticmethod
    def get_or_create(
        session: Session,
        market: str,
        company_name: str,
        form_type: str,
        filing_date: date,
        source_path: Optional[str] = None,
        **kwargs
    ) -> tuple[ProcessedFiling, bool]:
        """
        Get existing filing or create new one.

        Args:
            session: Database session
            market: Market code
            company_name: Company name
            form_type: Form type
            filing_date: Filing date
            source_path: Path to source data
            **kwargs: Additional fields for creation

        Returns:
            Tuple of (filing, created) where created is True if new
        """
        existing = FilingOperations.find_by_key(
            session, market, company_name, form_type, filing_date
        )

        if existing:
            return existing, False

        filing = FilingOperations.create_filing(
            session,
            market=market,
            company_name=company_name,
            form_type=form_type,
            filing_date=filing_date,
            source_path=source_path,
            **kwargs
        )
        return filing, True

    @staticmethod
    def find_by_company(
        session: Session,
        company_name: str,
        market: Optional[str] = None
    ) -> List[ProcessedFiling]:
        """
        Find all filings for a company.

        Args:
            session: Database session
            company_name: Company name
            market: Optional market filter

        Returns:
            List of ProcessedFiling records
        """
        query = session.query(ProcessedFiling).filter_by(
            company_name=company_name
        )
        if market:
            query = query.filter_by(market=market)

        return query.order_by(ProcessedFiling.filing_date.desc()).all()

    @staticmethod
    def find_by_market(
        session: Session,
        market: str,
        limit: int = 100
    ) -> List[ProcessedFiling]:
        """
        Find filings by market.

        Args:
            session: Database session
            market: Market code
            limit: Maximum results

        Returns:
            List of ProcessedFiling records
        """
        return session.query(ProcessedFiling).filter_by(
            market=market
        ).order_by(
            ProcessedFiling.filing_date.desc()
        ).limit(limit).all()

    @staticmethod
    def find_by_form_type(
        session: Session,
        form_type: str,
        market: Optional[str] = None,
        limit: int = 100
    ) -> List[ProcessedFiling]:
        """
        Find filings by form type.

        Args:
            session: Database session
            form_type: Form type (10-K, 10-Q, etc.)
            market: Optional market filter
            limit: Maximum results

        Returns:
            List of ProcessedFiling records
        """
        query = session.query(ProcessedFiling).filter_by(form_type=form_type)
        if market:
            query = query.filter_by(market=market)

        return query.order_by(
            ProcessedFiling.filing_date.desc()
        ).limit(limit).all()

    @staticmethod
    def update_stats(
        session: Session,
        filing: ProcessedFiling,
        statement_count: int,
        total_node_count: int
    ) -> None:
        """
        Update filing statistics.

        Args:
            session: Database session
            filing: Filing to update
            statement_count: Number of statements
            total_node_count: Total nodes across statements
        """
        filing.statement_count = statement_count
        filing.total_node_count = total_node_count
        session.flush()

    @staticmethod
    def delete_filing(
        session: Session,
        filing: ProcessedFiling
    ) -> None:
        """
        Delete a filing and all its hierarchies.

        Args:
            session: Database session
            filing: Filing to delete
        """
        filing_key = filing.filing_key
        session.delete(filing)
        logger.info(f"Deleted filing: {filing_key}")

    @staticmethod
    def get_all(
        session: Session,
        limit: int = 1000
    ) -> List[ProcessedFiling]:
        """
        Get all filings.

        Args:
            session: Database session
            limit: Maximum results

        Returns:
            List of all ProcessedFiling records
        """
        return session.query(ProcessedFiling).order_by(
            ProcessedFiling.filing_date.desc()
        ).limit(limit).all()

    @staticmethod
    def count(session: Session) -> int:
        """
        Count total filings.

        Args:
            session: Database session

        Returns:
            Total count of filings
        """
        return session.query(ProcessedFiling).count()


__all__ = ['FilingOperations']
