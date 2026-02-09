# Path: mat_acc_files/ratio_check/database_checker.py
"""
Database Checker

Checks if HierarchyNode data exists for a company in the database.
If not, populates it using HierarchyStorage.

Integrates with mat_acc's database module for hierarchy storage.
"""

import logging
from datetime import date
from pathlib import Path
from typing import Optional, List

from config_loader import ConfigLoader

# Import IPO logging (INPUT layer for database retrieval)
from core.logger.ipo_logging import get_input_logger

# Database imports
from database import (
    initialize_engine,
    session_scope,
    ProcessedFiling,
    StatementHierarchy,
    HierarchyNode,
    HierarchyStorage,
    FilingOperations,
    HierarchyOperations,
)


# Use IPO-aware logger (INPUT layer - data retrieval)
logger = get_input_logger('database_checker')


class DatabaseChecker:
    """
    Checks and populates HierarchyNode data in the database.

    Verifies if hierarchy data exists for a company/filing.
    If missing, uses HierarchyStorage to build and store hierarchies.

    Example:
        checker = DatabaseChecker(config)

        if not checker.has_hierarchy_data(company, market, form, date):
            result = checker.populate_hierarchy(
                folder_path=mapped_folder,
                market=market,
                company=company,
                form=form,
                filing_date=filing_date,
                parsed_json_path=parsed_path,
            )
            if result['success']:
                print(f"Created {result['node_count']} nodes")
    """

    def __init__(self, config: ConfigLoader):
        """
        Initialize database checker.

        Args:
            config: ConfigLoader instance
        """
        self.config = config
        self.logger = get_input_logger('database_checker')
        self._initialized = False
        self._storage: Optional[HierarchyStorage] = None

    def initialize(self) -> bool:
        """
        Initialize database connection.

        Returns:
            True if successful, False otherwise
        """
        if self._initialized:
            return True

        try:
            db_url = self.config.get_db_connection_string()
            initialize_engine(db_url)
            self._initialized = True
            self.logger.info("Database connection initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            return False

    def _get_storage(self) -> HierarchyStorage:
        """Get or create HierarchyStorage instance."""
        if self._storage is None:
            self._storage = HierarchyStorage()
            self._storage.initialize()
        return self._storage

    def has_hierarchy_data(
        self,
        company: str,
        market: str,
        form: str,
        filing_date: date
    ) -> bool:
        """
        Check if hierarchy data exists for a filing.

        Args:
            company: Company name
            market: Market identifier
            form: Form type
            filing_date: Filing date

        Returns:
            True if hierarchy data exists, False otherwise
        """
        if not self.initialize():
            return False

        try:
            with session_scope() as session:
                # Find the processed filing
                filing = session.query(ProcessedFiling).filter(
                    ProcessedFiling.company_name.ilike(f"%{company}%"),
                    ProcessedFiling.market == market.lower(),
                ).first()

                if not filing:
                    self.logger.debug(f"No processed filing found for {company}/{market}")
                    return False

                # Check for hierarchies
                hierarchies = session.query(StatementHierarchy).filter_by(
                    filing_id=filing.filing_id
                ).all()

                if not hierarchies:
                    self.logger.debug(f"No hierarchies found for {company}")
                    return False

                # Check for nodes
                node_count = 0
                for hierarchy in hierarchies:
                    count = session.query(HierarchyNode).filter_by(
                        hierarchy_id=hierarchy.hierarchy_id
                    ).count()
                    node_count += count

                has_data = node_count > 0
                self.logger.debug(f"Found {node_count} nodes for {company}")
                return has_data

        except Exception as e:
            self.logger.error(f"Error checking hierarchy data: {e}")
            return False

    def get_filing_info(
        self,
        company: str,
        market: str
    ) -> Optional[dict]:
        """
        Get filing information from database.

        Args:
            company: Company name
            market: Market identifier

        Returns:
            Dictionary with filing info or None
        """
        if not self.initialize():
            return None

        try:
            with session_scope() as session:
                filing = session.query(ProcessedFiling).filter(
                    ProcessedFiling.company_name.ilike(f"%{company}%"),
                    ProcessedFiling.market == market.lower(),
                ).first()

                if not filing:
                    return None

                return {
                    'filing_id': filing.filing_id,
                    'company_name': filing.company_name,
                    'market': filing.market,
                    'form_type': filing.form_type,
                    'filing_date': filing.filing_date,
                    'statement_count': filing.statement_count,
                    'total_node_count': filing.total_node_count,
                }

        except Exception as e:
            self.logger.error(f"Error getting filing info: {e}")
            return None

    def get_hierarchy_nodes(
        self,
        company: str,
        market: str,
        statement_type: Optional[str] = None
    ) -> List[HierarchyNode]:
        """
        Get hierarchy nodes for a company.

        Args:
            company: Company name
            market: Market identifier
            statement_type: Optional filter by statement type

        Returns:
            List of HierarchyNode objects
        """
        if not self.initialize():
            return []

        try:
            with session_scope() as session:
                # Find filing
                filing = session.query(ProcessedFiling).filter(
                    ProcessedFiling.company_name.ilike(f"%{company}%"),
                    ProcessedFiling.market == market.lower(),
                ).first()

                if not filing:
                    return []

                # Get hierarchies
                query = session.query(StatementHierarchy).filter_by(
                    filing_id=filing.filing_id
                )
                if statement_type:
                    query = query.filter_by(statement_type=statement_type)

                hierarchies = query.all()

                # Get all nodes
                nodes = []
                for hierarchy in hierarchies:
                    hierarchy_nodes = session.query(HierarchyNode).filter_by(
                        hierarchy_id=hierarchy.hierarchy_id
                    ).order_by(HierarchyNode.order).all()
                    nodes.extend(hierarchy_nodes)

                return nodes

        except Exception as e:
            self.logger.error(f"Error getting hierarchy nodes: {e}")
            return []

    def populate_hierarchy(
        self,
        folder_path: Path,
        market: str,
        company: str,
        form: str,
        filing_date: date,
        parsed_json_path: Optional[Path] = None,
    ) -> dict:
        """
        Populate hierarchy data for a filing.

        Uses HierarchyStorage to build hierarchies from mapped statements.

        Args:
            folder_path: Path to mapped statement folder
            market: Market identifier
            company: Company name
            form: Form type
            filing_date: Filing date
            parsed_json_path: Optional path to parsed.json for fact merging

        Returns:
            Dictionary with:
                success: True if successful
                statement_count: Number of statements created
                node_count: Number of nodes created
                errors: List of error messages
        """
        result = {
            'success': False,
            'statement_count': 0,
            'node_count': 0,
            'errors': [],
        }

        if not self.initialize():
            result['errors'].append("Database initialization failed")
            return result

        try:
            storage = self._get_storage()

            storage_result = storage.process_filing_folder(
                folder_path=folder_path,
                market=market,
                company_name=company,
                form_type=form,
                filing_date=filing_date,
                parsed_json_path=parsed_json_path,
            )

            if storage_result.get('errors'):
                result['errors'] = storage_result['errors']
            else:
                result['success'] = True
                result['statement_count'] = storage_result.get('statement_count', 0)
                result['node_count'] = storage_result.get('total_nodes', 0)

            self.logger.info(
                f"Populated hierarchy for {company}: "
                f"{result['statement_count']} statements, {result['node_count']} nodes"
            )

        except Exception as e:
            self.logger.error(f"Error populating hierarchy: {e}")
            result['errors'].append(str(e))

        return result

    def get_node_by_concept(
        self,
        company: str,
        market: str,
        concept: str
    ) -> Optional[HierarchyNode]:
        """
        Find a node by concept name.

        Args:
            company: Company name
            market: Market identifier
            concept: XBRL concept name

        Returns:
            HierarchyNode or None
        """
        if not self.initialize():
            return None

        try:
            with session_scope() as session:
                # Find filing
                filing = session.query(ProcessedFiling).filter(
                    ProcessedFiling.company_name.ilike(f"%{company}%"),
                    ProcessedFiling.market == market.lower(),
                ).first()

                if not filing:
                    return None

                # Find node by concept across all hierarchies
                hierarchies = session.query(StatementHierarchy).filter_by(
                    filing_id=filing.filing_id
                ).all()

                for hierarchy in hierarchies:
                    node = session.query(HierarchyNode).filter_by(
                        hierarchy_id=hierarchy.hierarchy_id,
                        concept=concept
                    ).first()
                    if node:
                        return node

                return None

        except Exception as e:
            self.logger.error(f"Error finding node by concept: {e}")
            return None

    def get_statistics(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with counts of filings, hierarchies, nodes
        """
        if not self.initialize():
            return {'error': 'Database not initialized'}

        try:
            with session_scope() as session:
                return {
                    'filings': session.query(ProcessedFiling).count(),
                    'hierarchies': session.query(StatementHierarchy).count(),
                    'nodes': session.query(HierarchyNode).count(),
                }
        except Exception as e:
            return {'error': str(e)}


__all__ = ['DatabaseChecker']
