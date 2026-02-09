# Path: mat_acc/database/integration/hierarchy_storage.py
"""
Hierarchy Storage Integration

Connects the hierarchy builder with database storage.
When hierarchies are built, they are automatically stored in the database.

This creates the bridge between:
- process.hierarchy.HierarchyBuilder (builds hierarchies)
- database.operations.HierarchyOperations (stores hierarchies)

Database: PostgreSQL (default) or SQLite (testing only)

Example:
    storage = HierarchyStorage()

    # Process a filing folder and store hierarchies
    result = storage.process_filing_folder(
        folder_path=Path('/mnt/map_pro/mapper/mapped_statements/sec/Apple_Inc/10_K/2024-09-30'),
        market='sec',
        company_name='Apple Inc',
        form_type='10-K',
        filing_date=date(2024, 9, 30)
    )

    print(f"Stored {result['statement_count']} statements with {result['total_nodes']} nodes")
"""

import logging
from datetime import date
from pathlib import Path
from typing import Optional

from database.models.base import (
    initialize_engine,
    create_all_tables,
    session_scope,
    get_connection_info,
)
from database.models.processed_filings import ProcessedFiling
from database.operations.filing_ops import FilingOperations
from database.operations.hierarchy_ops import HierarchyOperations
from process.hierarchy.tree_builder import HierarchyBuilder
from process.hierarchy.fact_merger import FactMerger


logger = logging.getLogger(__name__)


class HierarchyStorage:
    """
    Integrates hierarchy building with database storage.

    Uses PostgreSQL by default. For testing, pass use_sqlite=True.

    Provides methods to:
    - Build hierarchies from filing folders
    - Store them in the database (PostgreSQL)
    - Track processing status

    Example:
        storage = HierarchyStorage()

        # Initialize database (creates tables if needed)
        storage.initialize()

        # Process a filing
        result = storage.process_filing_folder(
            folder_path=Path('/mnt/map_pro/mapper/mapped_statements/sec/Apple_Inc/10_K/2024-09-30'),
            market='sec',
            company_name='Apple Inc',
            form_type='10-K',
            filing_date=date(2024, 9, 30)
        )
    """

    def __init__(self, db_url: Optional[str] = None, use_sqlite: bool = False):
        """
        Initialize hierarchy storage.

        Args:
            db_url: Optional database URL. If None, uses PostgreSQL from config.
                    Pass ':memory:' for SQLite in-memory (testing).
            use_sqlite: If True, forces SQLite in-memory mode (for testing).
        """
        self._db_url = db_url
        self._use_sqlite = use_sqlite
        self._builder = HierarchyBuilder()
        self._initialized = False

    def initialize(self) -> None:
        """
        Initialize the database connection and create tables.

        Must be called before any storage operations.
        Safe to call multiple times (idempotent).
        """
        if self._initialized:
            return

        initialize_engine(self._db_url, use_sqlite=self._use_sqlite)
        create_all_tables()
        self._initialized = True

        info = get_connection_info()
        logger.info(f"HierarchyStorage initialized: {info.get('type', 'unknown')}")

    def process_filing_folder(
        self,
        folder_path: Path,
        market: str,
        company_name: str,
        form_type: str,
        filing_date: date,
        accession_number: Optional[str] = None,
        cik: Optional[str] = None,
        exclude_details: bool = True,
        parsed_json_path: Optional[Path] = None,
    ) -> dict:
        """
        Build hierarchies from a filing folder and store in database.

        This is the main integration point. It:
        1. Creates or finds the filing record
        2. Builds hierarchies using HierarchyBuilder
        3. Stores all hierarchies in the database

        Args:
            folder_path: Path to the mapped filing folder
            market: Market code (e.g., 'sec', 'frc')
            company_name: Company name
            form_type: Form type (e.g., '10-K')
            filing_date: Filing date
            accession_number: Optional SEC accession number
            cik: Optional CIK or entity ID
            exclude_details: If True, exclude 'Details' statements
            parsed_json_path: Optional path to parsed.json for fact merging.
                              If provided, facts with context_ref will be merged
                              into mat_acc_id (e.g., 'BS-002-001-c4').

        Returns:
            Dictionary with processing results:
                - filing_id: ID of the filing record
                - statement_count: Number of statements stored
                - total_nodes: Total nodes across all statements
                - statements: List of statement names
                - errors: List of any errors encountered
        """
        self.initialize()

        result = {
            'filing_id': None,
            'statement_count': 0,
            'total_nodes': 0,
            'statements': [],
            'errors': [],
        }

        # Validate folder exists
        folder_path = Path(folder_path)
        if not folder_path.exists():
            result['errors'].append(f"Folder not found: {folder_path}")
            return result

        try:
            with session_scope() as session:
                # Get or create filing record
                filing, created = FilingOperations.get_or_create(
                    session,
                    market=market,
                    company_name=company_name,
                    form_type=form_type,
                    filing_date=filing_date,
                    source_path=str(folder_path),
                    accession_number=accession_number,
                    cik=cik,
                )
                result['filing_id'] = filing.filing_id

                if created:
                    logger.info(f"Created new filing record: {filing.filing_key}")
                else:
                    logger.info(f"Using existing filing record: {filing.filing_key}")
                    # If filing already has hierarchies, we could skip or replace
                    # For now, we'll add new hierarchies

                # Build hierarchies from folder
                logger.info(f"Building hierarchies from: {folder_path}")
                hierarchies = self._builder.build_from_filing_folder(
                    folder_path,
                    include_details=not exclude_details,
                )

                if not hierarchies:
                    result['errors'].append("No hierarchies built from folder")
                    return result

                # Load facts from parsed.json if provided
                fact_merger = None
                if parsed_json_path:
                    parsed_json_path = Path(parsed_json_path)
                    if parsed_json_path.exists():
                        fact_merger = FactMerger()
                        if fact_merger.load_from_parsed_json(parsed_json_path):
                            logger.info(
                                f"Loaded {fact_merger.total_facts} facts "
                                f"({fact_merger.numeric_facts_count} numeric) for merging"
                            )
                        else:
                            logger.warning(f"Failed to load facts from {parsed_json_path}")
                            fact_merger = None
                    else:
                        logger.warning(f"parsed.json not found at {parsed_json_path}")

                # Store all hierarchies
                logger.info(f"Storing {len(hierarchies)} hierarchies to database")
                stored_hierarchies = HierarchyOperations.store_all_hierarchies(
                    session,
                    filing_id=filing.filing_id,
                    hierarchies=hierarchies,
                    fact_merger=fact_merger,
                )

                # Update result
                result['statement_count'] = len(stored_hierarchies)
                result['total_nodes'] = sum(h.node_count for h in stored_hierarchies)
                result['statements'] = [h.statement_name for h in stored_hierarchies]

                logger.info(
                    f"Stored {result['statement_count']} statements "
                    f"with {result['total_nodes']} total nodes"
                )

        except Exception as e:
            logger.error(f"Error processing filing folder: {e}")
            result['errors'].append(str(e))

        return result

    def process_xbrl_filing(
        self,
        filing_dir: Path,
        market: str,
        company_name: str,
        form_type: str,
        filing_date: date,
        accession_number: Optional[str] = None,
        cik: Optional[str] = None,
    ) -> dict:
        """
        Build hierarchies from XBRL filing and store in database.

        Uses the presentation linkbase to build hierarchies.

        Args:
            filing_dir: Path to the XBRL filing directory
            market: Market code
            company_name: Company name
            form_type: Form type
            filing_date: Filing date
            accession_number: Optional accession number
            cik: Optional CIK

        Returns:
            Dictionary with processing results
        """
        self.initialize()

        result = {
            'filing_id': None,
            'statement_count': 0,
            'total_nodes': 0,
            'statements': [],
            'errors': [],
        }

        filing_dir = Path(filing_dir)
        if not filing_dir.exists():
            result['errors'].append(f"Filing directory not found: {filing_dir}")
            return result

        try:
            with session_scope() as session:
                # Get or create filing record
                filing, created = FilingOperations.get_or_create(
                    session,
                    market=market,
                    company_name=company_name,
                    form_type=form_type,
                    filing_date=filing_date,
                    source_path=str(filing_dir),
                    accession_number=accession_number,
                    cik=cik,
                )
                result['filing_id'] = filing.filing_id

                # Build hierarchies from XBRL
                logger.info(f"Building hierarchies from XBRL: {filing_dir}")
                hierarchies = self._builder.build_from_xbrl_filing(filing_dir)

                if not hierarchies:
                    result['errors'].append("No hierarchies built from XBRL filing")
                    return result

                # Store hierarchies
                stored_hierarchies = HierarchyOperations.store_all_hierarchies(
                    session,
                    filing_id=filing.filing_id,
                    hierarchies=hierarchies,
                )

                result['statement_count'] = len(stored_hierarchies)
                result['total_nodes'] = sum(h.node_count for h in stored_hierarchies)
                result['statements'] = [h.statement_name for h in stored_hierarchies]

        except Exception as e:
            logger.error(f"Error processing XBRL filing: {e}")
            result['errors'].append(str(e))

        return result

    def get_filing_summary(self, filing_id: str) -> Optional[dict]:
        """
        Get summary of a processed filing.

        Args:
            filing_id: Filing UUID

        Returns:
            Dictionary with filing and hierarchy info, or None
        """
        self.initialize()

        with session_scope() as session:
            filing = FilingOperations.find_by_id(session, filing_id)
            if not filing:
                return None

            hierarchies = HierarchyOperations.find_hierarchies_by_filing(
                session, filing_id
            )

            return {
                'filing': filing.to_dict(),
                'hierarchies': [
                    {
                        'name': h.statement_name,
                        'type': h.statement_type,
                        'code': h.statement_code,
                        'node_count': h.node_count,
                        'max_depth': h.max_depth,
                    }
                    for h in hierarchies
                ],
            }

    def list_processed_filings(
        self,
        market: Optional[str] = None,
        company_name: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        List processed filings.

        Args:
            market: Filter by market
            company_name: Filter by company
            limit: Maximum results

        Returns:
            List of filing dictionaries
        """
        self.initialize()

        with session_scope() as session:
            if company_name:
                filings = FilingOperations.find_by_company(session, company_name)
            elif market:
                filings = FilingOperations.find_by_market(session, market)
            else:
                filings = session.query(ProcessedFiling).limit(limit).all()

            return [f.to_dict() for f in filings[:limit]]

    def get_hierarchy_nodes(
        self,
        hierarchy_id: str
    ) -> Optional[dict]:
        """
        Get hierarchy with all nodes.

        Args:
            hierarchy_id: Hierarchy UUID

        Returns:
            Dictionary with hierarchy data and nodes
        """
        self.initialize()

        with session_scope() as session:
            return HierarchyOperations.get_hierarchy_with_nodes(
                session, hierarchy_id
            )

    def search_nodes_by_concept(
        self,
        concept: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        Search for nodes by XBRL concept.

        Args:
            concept: XBRL concept name (e.g., 'us-gaap:Assets')
            limit: Maximum results

        Returns:
            List of matching node dictionaries
        """
        self.initialize()

        with session_scope() as session:
            nodes = HierarchyOperations.find_nodes_by_concept(session, concept)
            return [n.to_dict() for n in nodes[:limit]]


def process_filing_to_database(
    folder_path: Path,
    market: str,
    company_name: str,
    form_type: str,
    filing_date: date,
    db_url: Optional[str] = None,
    use_sqlite: bool = False,
    parsed_json_path: Optional[Path] = None,
) -> dict:
    """
    Convenience function to process a filing folder and store in database.

    Args:
        folder_path: Path to the mapped filing folder
        market: Market code
        company_name: Company name
        form_type: Form type
        filing_date: Filing date
        db_url: Optional database URL. If None, uses PostgreSQL from config.
        use_sqlite: If True, uses SQLite in-memory (for testing)
        parsed_json_path: Optional path to parsed.json for fact merging

    Returns:
        Processing result dictionary
    """
    storage = HierarchyStorage(db_url=db_url, use_sqlite=use_sqlite)
    return storage.process_filing_folder(
        folder_path=folder_path,
        market=market,
        company_name=company_name,
        form_type=form_type,
        filing_date=filing_date,
        parsed_json_path=parsed_json_path,
    )


__all__ = ['HierarchyStorage', 'process_filing_to_database']
