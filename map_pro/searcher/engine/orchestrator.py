# Path: searcher/engine/orchestrator.py
"""
Search Orchestrator

Coordinates search operations and database persistence.
Converts searcher results (dictionaries) to database models.

Architecture:
- Searchers return raw dictionaries (not database models)
- Orchestrator handles database persistence
- Clean separation between search and storage
- Handles both filing searches and taxonomy library metadata
"""

from typing import Optional

from ..core.logger import get_logger
from ..constants import (
    LOG_INPUT,
    LOG_PROCESS,
    LOG_OUTPUT,
    KEY_FILING_URL,
    KEY_FORM_TYPE,
    KEY_FILING_DATE,
    KEY_COMPANY_NAME,
    KEY_ENTITY_ID,
    KEY_ACCESSION_NUMBER,
    KEY_MARKET_ID,
    STATUS_PENDING,
)

logger = get_logger(__name__, 'engine')


class SearchOrchestrator:
    """
    Orchestrates search operations and database persistence.
    
    Responsibilities:
    - Execute searches via market searchers
    - Convert results to database models
    - Save filings to FilingSearch table
    - Save taxonomies to TaxonomyLibrary table
    - Handle errors and logging
    
    Example:
        orchestrator = SearchOrchestrator()
        
        # For filing searches
        saved_count = await orchestrator.search_and_save(
            market_id='sec',
            identifier='AAPL',
            form_type='10-K',
            max_results=5
        )
        
        # For taxonomy metadata (called by library module)
        success = orchestrator.save_taxonomy_to_database(
            taxonomy_name='us-gaap',
            taxonomy_version='2024',
            taxonomy_namespace='http://fasb.org/us-gaap/2024',
            source_url='https://xbrl.sec.gov/us-gaap/2024/us-gaap-2024.zip',
            market_type='sec'
        )
    """
    
    def __init__(self):
        """Initialize orchestrator."""
        self.results_saved: int = 0
        self.results_failed: int = 0
    
    async def search_and_save(
        self,
        market_id: str,
        identifier: str,
        form_type: str,
        max_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        Execute search and save results to database.
        
        Args:
            market_id: Market identifier (sec, esma, fca)
            identifier: Company identifier
            form_type: Filing form type
            max_results: Maximum results to return
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Number of filings saved to database
        """
        logger.info(f"{LOG_INPUT} Search request: {market_id} / {identifier} / {form_type}")
        
        # Execute search
        results = await self._execute_search(
            market_id=market_id,
            identifier=identifier,
            form_type=form_type,
            max_results=max_results,
            start_date=start_date,
            end_date=end_date
        )
        
        # Save to database
        saved = self._save_results_to_database(results, market_id)
        
        return saved
    
    async def search_by_name_and_save(
        self,
        market_id: str,
        company_name: str,
        form_type: str,
        max_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        Execute search by company name and save results.
        
        Args:
            market_id: Market identifier
            company_name: Company name or partial name
            form_type: Filing form type
            max_results: Maximum results to return
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Number of filings saved to database
        """
        logger.info(f"{LOG_INPUT} Name search: {market_id} / {company_name} / {form_type}")
        
        # Get market searcher
        from ..markets.registry import get_searcher
        
        logger.info(f"{LOG_PROCESS} Getting searcher for market: {market_id}")
        
        searcher = None
        try:
            searcher = get_searcher(market_id)
            
            results = await searcher.search_by_company_name(
                company_name=company_name,
                form_type=form_type,
                max_results=max_results,
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(f"{LOG_OUTPUT} Search returned {len(results)} results")
            
            # Save to database
            saved = self._save_results_to_database(results, market_id)
            
            return saved
        
        except Exception as e:
            logger.error(f"Search by name failed: {e}")
            raise
        
        finally:
            if searcher and hasattr(searcher, 'close'):
                await searcher.close()
    
    async def _execute_search(
        self,
        market_id: str,
        identifier: str,
        form_type: str,
        max_results: int,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> list[dict]:
        """
        Execute search via market searcher.
        
        Args:
            market_id: Market identifier
            identifier: Company identifier
            form_type: Filing form type
            max_results: Maximum results
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            List of filing dictionaries
        """
        from ..markets.registry import get_searcher
        
        logger.info(f"{LOG_PROCESS} Getting searcher for market: {market_id}")
        
        searcher = None
        try:
            searcher = get_searcher(market_id)
            
            results = await searcher.search_by_identifier(
                identifier=identifier,
                form_type=form_type,
                max_results=max_results,
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(f"{LOG_OUTPUT} Search returned {len(results)} results")
            
            return results
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
        
        finally:
            # Clean up searcher resources
            if searcher and hasattr(searcher, 'close'):
                await searcher.close()
    
    def _save_results_to_database(
        self,
        results: list[dict],
        market_id: str
    ) -> int:
        """
        Save search results to database.
        
        Workflow:
        1. Find or create Entity for company
        2. Create FilingSearch records with proper entity UUID
        
        Args:
            results: List of filing dictionaries
            market_id: Market identifier
            
        Returns:
            Number of filings saved
        """
        # Import database modules only when needed
        try:
            from database import session_scope
            from database.models import FilingSearch, Entity
        except ImportError:
            logger.warning(
                "Database module not available. "
                "Results not saved to database."
            )
            return 0
        
        logger.info(f"{LOG_PROCESS} Saving {len(results)} results to database...")
        
        self.results_saved = 0
        self.results_failed = 0
        
        with session_scope() as session:
            for result in results:
                try:
                    # Extract data from result
                    market_entity_id = result.get(KEY_ENTITY_ID)  # CIK for SEC
                    company_name = result.get(KEY_COMPANY_NAME)
                    
                    # Find or create Entity
                    entity = session.query(Entity).filter_by(
                        market_type=market_id,
                        market_entity_id=market_entity_id
                    ).first()
                    
                    if not entity:
                        logger.info(f"{LOG_PROCESS} Creating new entity: {company_name} ({market_entity_id})")
                        
                        entity = Entity(
                            market_type=market_id,
                            market_entity_id=market_entity_id,
                            company_name=company_name,
                            entity_status='active',
                            identifiers={'cik': market_entity_id} if market_id == 'sec' else {}
                        )
                        session.add(entity)
                        session.flush()  # Get entity_id UUID
                    
                    # Create FilingSearch with proper entity UUID
                    filing = FilingSearch(
                        entity_id=entity.entity_id,  # UUID from Entity table
                        market_type=market_id,
                        form_type=result.get(KEY_FORM_TYPE),
                        filing_date=result.get(KEY_FILING_DATE),
                        filing_url=result.get(KEY_FILING_URL),
                        accession_number=result.get(KEY_ACCESSION_NUMBER),
                        search_metadata={
                            'company_name': company_name,
                            'market_entity_id': market_entity_id,
                        },
                        download_status=STATUS_PENDING,
                        extraction_status=STATUS_PENDING
                    )
                    
                    session.add(filing)
                    self.results_saved += 1
                    
                    logger.debug(f"Saved: {company_name} / {result.get(KEY_FORM_TYPE)} / {result.get(KEY_FILING_DATE)}")
                
                except Exception as e:
                    logger.error(f"Failed to save filing: {e}")
                    self.results_failed += 1
                    continue
            
            # Commit all at once
            try:
                session.commit()
                logger.info(
                    f"{LOG_OUTPUT} Database save complete: "
                    f"{self.results_saved} saved, {self.results_failed} failed"
                )
            except Exception as e:
                logger.error(f"Database commit failed: {e}")
                session.rollback()
                self.results_saved = 0
        
        return self.results_saved
    
    def save_taxonomy_to_database(
        self,
        taxonomy_name: str,
        taxonomy_version: str,
        taxonomy_namespace: str,
        source_url: str,
        market_type: str,
        required_by_filing: Optional[str] = None,
        taxonomy_metadata: Optional[dict] = None
    ) -> bool:
        """
        Save taxonomy library metadata to database.
        
        Called by library module after recognizing taxonomy from parsed.json.
        Creates or updates TaxonomyLibrary record.
        
        CRITICAL: Checks for existing record by namespace (unique).
        If exists, updates required_by_filings list.
        If new, creates with status='pending' for downloader.
        
        Args:
            taxonomy_name: Taxonomy name (e.g., 'us-gaap')
            taxonomy_version: Version string (e.g., '2024')
            taxonomy_namespace: Full namespace URI (unique identifier)
            source_url: Download URL
            market_type: Market identifier (sec, esma, fca)
            required_by_filing: Optional filing_search UUID that needs this
            taxonomy_metadata: Optional additional metadata
            
        Returns:
            True if saved successfully, False otherwise
        """
        logger.info(
            f"{LOG_INPUT} Saving taxonomy: {taxonomy_name}/{taxonomy_version} "
            f"to database"
        )
        
        # Import database modules
        try:
            from database import session_scope
            from database.models import TaxonomyLibrary
        except ImportError:
            logger.error("Database module not available")
            return False
        
        try:
            with session_scope() as session:
                # Check if taxonomy already exists (by unique namespace)
                existing = session.query(TaxonomyLibrary).filter_by(
                    taxonomy_namespace=taxonomy_namespace
                ).first()
                
                if existing:
                    logger.info(
                        f"{LOG_PROCESS} Taxonomy already exists: "
                        f"{taxonomy_name}/{taxonomy_version}"
                    )
                    
                    # Update required_by_filings if provided
                    if required_by_filing:
                        existing.add_required_by_filing(required_by_filing)
                        logger.info(
                            f"{LOG_PROCESS} Added filing dependency: "
                            f"{required_by_filing}"
                        )
                    
                    session.commit()
                    logger.info(f"{LOG_OUTPUT} Updated existing taxonomy record")
                    return True
                
                # Create new taxonomy record
                logger.info(
                    f"{LOG_PROCESS} Creating new taxonomy record: "
                    f"{taxonomy_name}/{taxonomy_version}"
                )
                
                taxonomy = TaxonomyLibrary(
                    taxonomy_name=taxonomy_name,
                    taxonomy_version=taxonomy_version,
                    taxonomy_namespace=taxonomy_namespace,
                    source_url=source_url,
                    download_status='pending',
                    required_by_filings=[required_by_filing] if required_by_filing else [],
                    taxonomy_metadata=taxonomy_metadata or {}
                )
                
                session.add(taxonomy)
                session.commit()
                
                logger.info(
                    f"{LOG_OUTPUT} Taxonomy saved successfully: "
                    f"{taxonomy_name}/{taxonomy_version} (status=pending)"
                )
                return True
        
        except Exception as e:
            logger.error(f"Failed to save taxonomy: {e}")
            return False
    
    def get_statistics(self) -> dict:
        """
        Get orchestrator statistics.
        
        Returns:
            Dictionary with save statistics
        """
        return {
            'results_saved': self.results_saved,
            'results_failed': self.results_failed,
            'success_rate': (
                (self.results_saved / (self.results_saved + self.results_failed) * 100)
                if (self.results_saved + self.results_failed) > 0
                else 0.0
            )
        }


__all__ = ['SearchOrchestrator']