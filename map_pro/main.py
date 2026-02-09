#!/usr/bin/env python3
"""
Map Pro - Main CLI Entry Point

Complete end-to-end workflow for XBRL filing processing:
Input: Company specifications (market, identifier, form type)
Output: Mapped financial statements (JSON, CSV, Excel)

Workflow:
1. Search   - Find filings via market APIs
2. Download - Retrieve and extract archives
3. Parse    - Extract XBRL facts and structure
4. Map      - Build financial statements

Usage:
    python main.py

    # Or with direct execution
    ./main.py
"""

import sys
import asyncio
import logging
from typing import Optional
from pathlib import Path

# =============================================================================
# CORE INITIALIZATION - Must happen before any other imports
# =============================================================================

# Step 1: Load configuration and ensure core paths exist
from core.config_loader import get_core_config
from core.data_paths import ensure_core_paths, ensure_postgresql_ready

# Step 2: Configure logging using core logger
from core.logger import (
    configure_logging,
    get_app_logger,
    get_startup_logger,
    log_startup_complete,
    log_shutdown,
)

# Initialize logging
configure_logging(log_level='INFO', console=True)

# Step 3: Ensure essential directories exist (PostgreSQL data dir)
startup_logger = get_startup_logger()
startup_logger.info("Initializing core paths...")

path_results = ensure_core_paths()
if path_results['all_success']:
    startup_logger.info(
        f"Core paths ready: {path_results['summary']['created']} created, "
        f"{path_results['summary']['existing']} existing"
    )
else:
    startup_logger.warning(
        f"Some paths failed: {path_results['summary']['failed']} failures"
    )

# Step 4: Initialize PostgreSQL (initdb, start service, seed markets)
startup_logger.info("Initializing PostgreSQL...")
from database.postgre_initialize import initialize_postgresql, check_postgresql_status

pg_status = check_postgresql_status()
if not pg_status['postgresql_running']:
    startup_logger.info("PostgreSQL not running - starting initialization...")
    pg_result = initialize_postgresql(seed_markets=True)
    if pg_result['success']:
        startup_logger.info("PostgreSQL initialized successfully")
    else:
        startup_logger.error(f"PostgreSQL initialization failed: {pg_result['message']}")
        print(f"\n[ERROR] PostgreSQL initialization failed: {pg_result['message']}")
        print("Please check the error above and try again.")
        sys.exit(1)
else:
    startup_logger.info("PostgreSQL already running")

# =============================================================================
# APPLICATION IMPORTS
# =============================================================================

# Core workflow
from core.workflow_orchestrator import WorkflowOrchestrator

# Import constants from searcher module (single source of truth)
from searcher.constants import (
    MARKET_SEC,
    MARKET_UK_FRC,
    MARKET_ESEF,
    MARKET_NAMES,
    MIN_RESULTS,
    MAX_RESULTS,
)


class MapProCLI:
    """
    Interactive CLI for complete Map Pro workflow.

    Guides user through:
    - Market selection
    - Company identification
    - Form type selection
    - Number of filings
    - Confirmation
    - Complete workflow execution
    """

    def __init__(self):
        """Initialize CLI."""
        self.logger = logging.getLogger('map_pro_cli')

        # User inputs
        self.market_id: Optional[str] = None
        self.company_identifier: Optional[str] = None
        self.form_type: Optional[str] = None
        self.num_filings: int = 1

    async def run(self) -> None:
        """Run interactive CLI."""
        self._print_banner()

        while True:
            try:
                # Step 1: Select market
                self.market_id = self._select_market()

                if not self.market_id:
                    print("\nExiting Map Pro...")
                    break

                # Step 2: Get company identifier
                self.company_identifier = self._get_company_identifier()

                if not self.company_identifier:
                    continue

                # Step 3: Get form type
                self.form_type = self._get_form_type()

                if not self.form_type:
                    continue

                # Step 4: Get number of filings
                self.num_filings = self._get_num_filings()

                # Step 5: Confirmation
                if not self._confirm_parameters():
                    continue

                # Step 6: Execute complete workflow
                await self._execute_workflow()

                # Step 7: Ask to continue
                if not self._continue_processing():
                    break

            except KeyboardInterrupt:
                print("\n\nWorkflow interrupted by user.")
                break

            except Exception as e:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
                print(f"\nError: {e}")
                print("Please try again or exit.\n")

        print("\nThank you for using Map Pro!")

    def _print_banner(self) -> None:
        """Print welcome banner."""
        print("\n" + "=" * 80)
        print("MAP PRO - XBRL FILING PROCESSOR")
        print("=" * 80)
        print("\nComplete End-to-End Workflow:")
        print("  1. Search for filings")
        print("  2. Download XBRL archives")
        print("  3. Parse XBRL structure")
        print("  4. Map to financial statements")
        print("\nOutput: JSON, CSV, and Excel financial statements")
        print("=" * 80 + "\n")

    def _select_market(self) -> Optional[str]:
        """Select market interactively."""
        print("\n" + "=" * 80)
        print("STEP 1: SELECT MARKET")
        print("=" * 80)
        print("  1. SEC (United States)")
        print("  2. Companies House (United Kingdom)")
        print("  3. ESEF (European Single Electronic Format)")
        print("  0. Exit\n")

        while True:
            choice = input("Enter market number: ").strip()

            if choice == '0':
                return None
            elif choice == '1':
                return MARKET_SEC
            elif choice == '2':
                return MARKET_UK_FRC
            elif choice == '3':
                return MARKET_ESEF
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 0.\n")

    def _get_company_identifier(self) -> Optional[str]:
        """Get company identifier (market-specific)."""
        print("\n" + "=" * 80)
        print("STEP 2: COMPANY IDENTIFIER")
        print("=" * 80)

        if self.market_id == MARKET_SEC:
            print("\nSEC Company Identifier:")
            print("  Enter CIK (10 digits with leading zeros) or Ticker Symbol")
            print("  Examples:")
            print("    CIK:    0000320193  (Apple Inc.)")
            print("    Ticker: AAPL        (Apple Inc.)")
            print("    CIK:    0001318605  (Tesla Inc.)")
            print("    Ticker: TSLA        (Tesla Inc.)\n")

        elif self.market_id == MARKET_UK_FRC:
            print("\nUK Companies House Identifier:")
            print("  Enter UK company number (6-8 alphanumeric characters)")
            print("  Examples:")
            print("    00445790  (Tesco PLC)")
            print("    00102498  (BP plc)")
            print("    SC123456  (Scottish company - starts with SC)")
            print("    NI012345  (Northern Ireland - starts with NI)\n")

        elif self.market_id == MARKET_ESEF:
            print("\nESEF Company Identifier:")
            print("  Enter LEI (20 characters) or Company Name")
            print("  Examples:")
            print("    LEI:  2138002P5RNKC5W2JZ46  (Tesco PLC)")
            print("    LEI:  213800LH1BZH3DI6G760  (BP P.L.C.)")
            print("    Name: Tesco")
            print("    Name: BP\n")
            print("  Optional: Add country code prefix for better results")
            print("    GB:Tesco  (UK companies)")
            print("    DE:BMW    (German companies)\n")

        identifier = input("Enter company identifier: ").strip()

        if not identifier:
            print("Error: Identifier cannot be empty\n")
            return None

        return identifier

    def _get_form_type(self) -> Optional[str]:
        """Get form type (market-specific)."""
        print("\n" + "=" * 80)
        print("STEP 3: FILING TYPE")
        print("=" * 80)

        if self.market_id == MARKET_SEC:
            print("\nSEC Filing Types:")
            print("  10-K  = Annual report")
            print("  10-Q  = Quarterly report")
            print("  8-K   = Current report")
            print("  20-F  = Annual report (foreign private issuer)")
            print("  S-1   = Registration statement\n")

        elif self.market_id == MARKET_UK_FRC:
            print("\nUK Companies House Filing Types:")
            print("  AA    = Full accounts (Annual accounts)")
            print("  AC    = Abridged accounts")
            print("  AD    = Dormant company accounts")
            print("  AG    = Group accounts")
            print("  ALL   = All accounts types\n")

        elif self.market_id == MARKET_ESEF:
            print("\nNote: filings.xbrl.org API returns ALL filings for an entity.")
            print("Report type filtering is not supported by the API.")
            print("Press Enter to fetch all available filings.\n")
            input("Press Enter to continue...")
            return "ALL"  # ESEF doesn't support report type filtering

        form_type = input("Enter filing type: ").strip().upper()

        if not form_type:
            print("Error: Filing type cannot be empty\n")
            return None

        return form_type

    def _get_num_filings(self) -> int:
        """Get number of filings to process."""
        print("\n" + "=" * 80)
        print("STEP 4: NUMBER OF FILINGS")
        print("=" * 80)

        while True:
            try:
                num = input(
                    f"\nHow many historical filings to process? ({MIN_RESULTS}-{MAX_RESULTS}): "
                ).strip()
                num_int = int(num)

                if MIN_RESULTS <= num_int <= MAX_RESULTS:
                    return num_int
                else:
                    print(f"Please enter a number between {MIN_RESULTS} and {MAX_RESULTS}.")

            except ValueError:
                print("Please enter a valid number.")

    def _confirm_parameters(self) -> bool:
        """Show confirmation screen."""
        print("\n" + "=" * 80)
        print("CONFIRMATION")
        print("=" * 80)
        print(f"\n  Market:             {MARKET_NAMES[self.market_id]}")
        print(f"  Company:            {self.company_identifier}")
        print(f"  Filing Type:        {self.form_type}")
        print(f"  Filings to Process: {self.num_filings}")
        print("\n" + "=" * 80)
        print("\nThis will execute the complete workflow:")
        print("   Search for filings in market database")
        print("   Download XBRL archives")
        print("   Parse XBRL structure and extract facts")
        print("   Map to financial statements")
        print("   Export to JSON, CSV, and Excel")
        print("=" * 80)

        while True:
            choice = input("\nProceed with workflow? (y/n): ").strip().lower()

            if choice == 'y':
                return True
            elif choice == 'n':
                return False
            else:
                print("Please enter 'y' or 'n'.")

    async def _execute_workflow(self) -> None:
        """Execute complete workflow."""
        print("\n" + "=" * 80)
        print("EXECUTING WORKFLOW")
        print("=" * 80)

        try:
            # Initialize orchestrator
            orchestrator = WorkflowOrchestrator()

            # Run workflow
            print("\nStarting workflow...")
            print("This may take several minutes depending on filing size.\n")

            results = await orchestrator.run_complete_workflow(
                market_id=self.market_id,
                company_identifier=self.company_identifier,
                form_type=self.form_type,
                num_filings=self.num_filings
            )

            # Display results
            self._display_results(results)

        except Exception as e:
            self.logger.error(f"Workflow failed: {e}", exc_info=True)
            print(f"\n{'=' * 80}")
            print("WORKFLOW FAILED")
            print('=' * 80)
            print(f"\nError: {e}")
            print("\nPlease check the logs for more details.")
            print('=' * 80)

    def _display_results(self, results: dict) -> None:
        """Display workflow results."""
        print("\n" + "=" * 80)
        print("WORKFLOW COMPLETE")
        print("=" * 80)

        summary = results['summary']

        print("\n Summary:")
        print(f"   Filings Found:      {summary['filings_found']}")
        print(f"   Filings Downloaded:  {summary['filings_downloaded']}")
        print(f"   Filings Parsed:      {summary['filings_parsed']}")
        print(f"   Filings Mapped:      {summary['filings_mapped']}")
        print(f"   Total Time:          {summary['total_time_seconds']:.1f} seconds")

        if results.get('errors'):
            print(f"\n  Errors: {len(results['errors'])}")
            for error in results['errors'][:3]:  # Show first 3 errors
                print(f"      {error['stage']}: {error['message']}")

        if results.get('warnings'):
            print(f"\n  Warnings: {len(results['warnings'])}")

        print("\n" + "=" * 80)

        if summary['filings_mapped'] > 0:
            print("\n Success! Financial statements have been generated.")
            print("\nOutput locations:")
            print(f"   Parsed XBRL: Check database for parsed output paths")
            print(f"   Mapped Statements: Check output_mapped_dir in configuration")
        else:
            print("\n No filings were successfully mapped.")
            print("Please check the errors above and try again.")

        print("\n" + "=" * 80)

    def _continue_processing(self) -> bool:
        """Ask if user wants to continue."""
        print()
        while True:
            choice = input("Process another filing? (y/n): ").strip().lower()

            if choice == 'y':
                return True
            elif choice == 'n':
                return False
            else:
                print("Please enter 'y' or 'n'.")


async def main():
    """Main entry point."""
    # Log startup complete
    log_startup_complete()

    # Run CLI
    cli = MapProCLI()
    await cli.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting Map Pro...")
    finally:
        # Log shutdown
        log_shutdown()
        sys.exit(0)
