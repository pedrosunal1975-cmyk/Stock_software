# Path: searcher/cli/search_cli.py
"""
Interactive Search CLI

Market-specific interactive prompts for searching filings.
Adapts to selected market (SEC, ESMA, FCA).
"""

import asyncio
from typing import Optional

from searcher.core.logger import get_logger
from searcher.constants import (
    MARKET_SEC,
    MARKET_ESMA,
    MARKET_FCA,
    MARKET_NAMES,
    MIN_RESULTS,
    MAX_RESULTS,
)
from searcher.markets.sec.constants import (
    CLI_COMPANY_PROMPT,
    CLI_FORM_TYPE_PROMPT,
)

logger = get_logger(__name__, 'cli')


class SearchCLI:
    """
    Interactive search CLI with market-specific prompts.
    
    Features:
    - Market selection (SEC, ESMA, FCA)
    - Market-specific company identifier input
    - Market-specific form type selection
    - Flexible input parsing
    - Confirmation screen
    """
    
    def __init__(self):
        """Initialize CLI."""
        self.market_id: Optional[str] = None
        self.company_identifier: Optional[str] = None
        self.form_type: Optional[str] = None
        self.num_filings: int = 1
    
    async def run(self) -> None:
        """Run interactive CLI."""
        print("\n" + "=" * 70)
        print("MAP PRO - FILING SEARCHER")
        print("=" * 70 + "\n")
        
        while True:
            # Step 1: Select market
            self.market_id = self._select_market()
            
            if not self.market_id:
                print("\nExiting...")
                break
            
            # Step 2: Company identifier (market-specific)
            self.company_identifier = self._get_company_identifier()
            
            if not self.company_identifier:
                continue
            
            # Step 3: Form type (market-specific)
            self.form_type = self._get_form_type()
            
            if not self.form_type:
                continue
            
            # Step 4: Number of filings
            self.num_filings = self._get_num_filings()
            
            # Step 5: Confirmation
            if not self._confirm_parameters():
                continue
            
            # Execute search
            await self._execute_search()
            
            # Ask to continue
            if not self._continue_searching():
                break
    
    def _select_market(self) -> Optional[str]:
        """Select market interactively."""
        print("Select Market:")
        print("  1. SEC (United States)")
        print("  2. ESMA (European Union)")
        print("  3. FCA (United Kingdom)")
        print("  0. Exit\n")
        
        while True:
            choice = input("Enter market number: ").strip()
            
            if choice == '0':
                return None
            elif choice == '1':
                return MARKET_SEC
            elif choice == '2':
                return MARKET_ESMA
            elif choice == '3':
                return MARKET_FCA
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 0.\n")
    
    def _get_company_identifier(self) -> Optional[str]:
        """Get company identifier (market-specific)."""
        print()
        
        if self.market_id == MARKET_SEC:
            print(CLI_COMPANY_PROMPT)
        elif self.market_id == MARKET_ESMA:
            print("ESMA Company Identifier:")
            print("  Enter LEI code (e.g., 549300VVMHHWQ3GKKD56)\n")
        elif self.market_id == MARKET_FCA:
            print("FCA Company Identifier:")
            print("  Enter company number (e.g., 00445790)\n")
        
        identifier = input("Enter company identifier: ").strip()
        
        if not identifier:
            print("Error: Identifier cannot be empty\n")
            return None
        
        return identifier
    
    def _get_form_type(self) -> Optional[str]:
        """Get form type (market-specific)."""
        print()
        
        if self.market_id == MARKET_SEC:
            print(CLI_FORM_TYPE_PROMPT)
        elif self.market_id == MARKET_ESMA:
            print("ESMA Report Types:")
            print("  ESEF  = European Single Electronic Format")
            print("  UKSEF = UK Single Electronic Format\n")
        elif self.market_id == MARKET_FCA:
            print("FCA Filing Types:")
            print("  AA    = Annual accounts")
            print("  CS01  = Confirmation statement\n")
        
        form_type = input("Enter filing type: ").strip()
        
        if not form_type:
            print("Error: Filing type cannot be empty\n")
            return None
        
        return form_type
    
    def _get_num_filings(self) -> int:
        """Get number of filings to process."""
        print()
        
        while True:
            try:
                num = input(f"Number of historical filings to process ({MIN_RESULTS}-{MAX_RESULTS}): ").strip()
                num_int = int(num)
                
                if MIN_RESULTS <= num_int <= MAX_RESULTS:
                    return num_int
                else:
                    print(f"Please enter a number between {MIN_RESULTS} and {MAX_RESULTS}.\n")
            
            except ValueError:
                print("Please enter a valid number.\n")
    
    def _confirm_parameters(self) -> bool:
        """Show confirmation screen."""
        print("\n" + "=" * 70)
        print("WORKFLOW PARAMETERS")
        print("=" * 70)
        print(f"  Market:             {MARKET_NAMES[self.market_id]}")
        print(f"  Company:            {self.company_identifier}")
        print(f"  Filing Type:        {self.form_type}")
        print(f"  Filings to Process: {self.num_filings}")
        print("=" * 70)
        
        while True:
            choice = input("\nProceed with workflow? (y/n): ").strip().lower()
            
            if choice == 'y':
                return True
            elif choice == 'n':
                return False
            else:
                print("Please enter 'y' or 'n'.")
    
    async def _execute_search(self) -> None:
        """Execute search with selected parameters and save to database."""
        print("\n" + "=" * 70)
        print("SEARCH IN PROGRESS")
        print("=" * 70 + "\n")
        
        try:
            # Initialize database first
            from database import initialize_database
            initialize_database()
            
            # Use orchestrator to search and save to database
            from searcher.engine.orchestrator import SearchOrchestrator
            
            orchestrator = SearchOrchestrator()
            
            # Execute search and save to database
            saved_count = await orchestrator.search_and_save(
                market_id=self.market_id,
                identifier=self.company_identifier,
                form_type=self.form_type,
                max_results=self.num_filings
            )
            
            # Display results
            print(f"\n{'=' * 70}")
            print(f"SEARCH COMPLETE: {saved_count} filings saved to database")
            print('=' * 70 + '\n')
            
            # Query database to show what was saved
            if saved_count > 0:
                from database import session_scope
                from database.models import FilingSearch, Entity
                
                with session_scope() as session:
                    # Get the most recently created filings (just saved)
                    filings = session.query(FilingSearch, Entity).join(
                        Entity, FilingSearch.entity_id == Entity.entity_id
                    ).filter(
                        FilingSearch.market_type == self.market_id,
                        FilingSearch.form_type == self.form_type
                    ).order_by(
                        FilingSearch.created_at.desc()
                    ).limit(saved_count).all()
                    
                    for i, (filing, entity) in enumerate(filings, 1):
                        print(f"{i}. {filing.form_type} - {filing.filing_date}")
                        print(f"   Company: {entity.company_name} (CIK: {entity.market_entity_id})")
                        print(f"   Accession: {filing.accession_number}")
                        print(f"   Status: {filing.download_status}")
                        print()
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            print(f"\nError: Search failed - {e}\n")
            import traceback
            traceback.print_exc()
    
    def _continue_searching(self) -> bool:
        """Ask if user wants to continue."""
        print()
        while True:
            choice = input("Search again? (y/n): ").strip().lower()
            
            if choice == 'y':
                return True
            elif choice == 'n':
                return False
            else:
                print("Please enter 'y' or 'n'.")


async def main():
    """Main entry point for CLI."""
    cli = SearchCLI()
    await cli.run()


if __name__ == '__main__':
    asyncio.run(main())