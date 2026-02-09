#!/usr/bin/env python3
# Path: mat_acc/main.py
"""
Mathematical Accountancy (mat_acc) - Main Entry Point

Financial analysis software for verified XBRL statements.
Processes only filings that have passed verification checks.

Data Flow:
    INPUT:  /mnt/map_pro/verification/reports/ (verified filings)
    PROCESS: Hierarchy building, ratio calculation, analysis
    OUTPUT: /mnt/mat_acc/ (reports, ratios, graphs)

Usage:
    python main.py              # Interactive mode
    python main.py --list       # List available filings
    python main.py --all        # Process all verified filings
    python main.py --company X  # Process specific company

Prerequisites:
    - Verification reports from map_pro
    - PostgreSQL database (optional)
    - Configured .env file
"""

import argparse
import sys
from pathlib import Path

# Ensure mat_acc root is in path
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import ConfigLoader
from core.data_paths import DataPathsManager
from core.logger import setup_ipo_logging, get_input_logger
from core.ui.user_input import CompanySelector, confirm_action
from loaders.verification_data import VerificationDataLoader
from loaders.verification_reader import VerificationReader
from constants import (
    STATUS_OK, STATUS_FAIL, STATUS_INFO,
    MENU_HEADER, MENU_SEPARATOR,
)


def print_banner() -> None:
    """Print application banner."""
    print()
    print(MENU_HEADER)
    print("  MAT_ACC - Mathematical Accountancy")
    print("  Financial Analysis for Verified XBRL Statements")
    print(MENU_HEADER)
    print()


def print_system_info(config: ConfigLoader) -> None:
    """
    Print system configuration information.

    Args:
        config: ConfigLoader instance
    """
    print(f"  Environment: {config.get('environment')}")
    print(f"  Input:  {config.get('verification_reports_dir')}")
    print(f"  Output: {config.get('output_dir')}")
    print()


def list_filings(loader: VerificationDataLoader, reader: VerificationReader) -> None:
    """
    List all available verified filings.

    Args:
        loader: VerificationDataLoader for path discovery
        reader: VerificationReader for score extraction
    """
    entries = loader.discover_filings()

    if not entries:
        print(f"\n{STATUS_INFO} No verified filings found.")
        print(f"  Check directory: {loader.config.get('verification_reports_dir')}")
        return

    print(f"\n{STATUS_OK} Found {len(entries)} verified filings:\n")
    print(f"  {'#':>3}  {'Market':<8} {'Company':<25} {'Form':<8} {'Date':<12} {'Score':>6}")
    print(f"  {MENU_SEPARATOR}")

    for i, entry in enumerate(entries, 1):
        # Get verification score
        report = reader.load_report(entry)
        score = f"{report.summary.score:.1f}" if report else "N/A"

        print(
            f"  {i:3d}  {entry.market:<8} {entry.company[:25]:<25} "
            f"{entry.form:<8} {entry.date:<12} {score:>6}"
        )

    print()


def run_interactive(config: ConfigLoader, logger) -> int:
    """
    Run in interactive mode.

    Args:
        config: Configuration loader
        logger: Logger instance

    Returns:
        Exit code (0 for success)
    """
    logger.info("Starting interactive mode")

    try:
        selector = CompanySelector(config)
        selection = selector.select_filing()

        if selection is None:
            print("\n[Cancelled]")
            return 0

        # Handle "all filings" selection
        if isinstance(selection, list):
            print(f"\n{STATUS_INFO} Selected ALL {len(selection)} filings for processing.")
            if not confirm_action("Process all filings?"):
                print("[Cancelled]")
                return 0

            # TODO: Process all filings
            print("\n[TODO] Batch processing not yet implemented.")
            print("  This will be added in the Process module.")
            return 0

        # Single filing selected
        print(f"\n{STATUS_OK} Selected: {selection.company} - {selection.form} ({selection.date})")
        print(f"  Report: {selection.report_path}")

        if selection.verification_score:
            print(f"  Score: {selection.verification_score:.1f}/100")

        # TODO: Process single filing
        print("\n[TODO] Single filing processing not yet implemented.")
        print("  This will be added in the Process module.")

        return 0

    except ValueError as e:
        print(f"\n{STATUS_FAIL} Configuration error: {e}")
        logger.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n[Interrupted]")
        return 130


def run_batch(config: ConfigLoader, logger, company_filter: str = None) -> int:
    """
    Run in batch mode (non-interactive).

    Args:
        config: Configuration loader
        logger: Logger instance
        company_filter: Optional company name filter

    Returns:
        Exit code (0 for success)
    """
    logger.info(f"Starting batch mode (filter: {company_filter or 'all'})")

    loader = VerificationDataLoader(config)
    reader = VerificationReader(config)

    entries = loader.discover_filings()

    if company_filter:
        entries = [e for e in entries if company_filter.lower() in e.company.lower()]

    if not entries:
        print(f"\n{STATUS_INFO} No matching filings found.")
        return 0

    print(f"\n{STATUS_OK} Found {len(entries)} filings to process.\n")

    # Filter by minimum verification score
    min_score = config.get('min_verification_score', 95.0)
    qualified = []

    for entry in entries:
        report = reader.load_report(entry)
        if report and reader.is_verified(report, min_score):
            qualified.append((entry, report))

    print(f"{STATUS_INFO} {len(qualified)}/{len(entries)} meet minimum score ({min_score})")

    if not qualified:
        print(f"\n{STATUS_FAIL} No filings meet the verification threshold.")
        return 0

    # TODO: Process qualified filings
    print("\n[TODO] Batch processing not yet implemented.")
    print("  This will be added in the Process module.")

    for entry, report in qualified:
        print(f"  - {entry.company}: {entry.form} ({entry.date}) - Score: {report.summary.score:.1f}")

    return 0


def initialize_system() -> tuple[ConfigLoader, DataPathsManager]:
    """
    Initialize mat_acc system components.

    Returns:
        Tuple of (ConfigLoader, DataPathsManager)

    Raises:
        ValueError: If configuration is invalid
    """
    # Load configuration
    config = ConfigLoader()

    # Set up logging
    setup_ipo_logging(
        log_dir=config.get('log_dir'),
        log_level=config.get('log_level', 'INFO'),
        console_output=not config.get('debug', False)
    )

    # Initialize data paths
    paths = DataPathsManager()

    # Validate only required input paths (verification_reports_dir)
    # Other paths (taxonomy_dir, etc.) are handled by user_input.py via library.py
    validation = paths.validate_input_paths(required_only=True)
    missing_paths = validation.get('missing', [])
    not_readable = validation.get('not_readable', [])

    if missing_paths or not_readable:
        print(f"\n{STATUS_FAIL} Verification reports directory not found:")
        for item in missing_paths:
            if isinstance(item, tuple):
                name, path = item
                print(f"  - {path}")
            else:
                print(f"  - {item} (not configured in .env)")
        for name, path in not_readable:
            print(f"  - Not readable: {path}")
        print("\nTo fix this:")
        print("  1. Run map_pro verification module to generate reports")
        print("  2. Check MAT_ACC_VERIFICATION_REPORTS_DIR in .env")
        raise ValueError("Verification reports directory not found")

    # Create output directories
    paths.ensure_all_directories()

    return config, paths


def main() -> int:
    """
    Main entry point for mat_acc.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='mat_acc - Mathematical Accountancy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              Interactive filing selection
  python main.py --list       List all verified filings
  python main.py --all        Process all qualified filings
  python main.py --company "Apple"  Process Apple filings only
        """
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available verified filings'
    )

    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Process all filings meeting verification threshold'
    )

    parser.add_argument(
        '--company', '-c',
        type=str,
        help='Filter by company name (partial match)'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress banner and verbose output'
    )

    args = parser.parse_args()

    # Print banner unless quiet mode
    if not args.quiet:
        print_banner()

    try:
        # Initialize system
        config, paths = initialize_system()
        logger = get_input_logger('main')

        if not args.quiet:
            print_system_info(config)

        # Run appropriate mode
        if args.list:
            loader = VerificationDataLoader(config)
            reader = VerificationReader(config)
            list_filings(loader, reader)
            return 0

        elif args.all or args.company:
            return run_batch(config, logger, args.company)

        else:
            return run_interactive(config, logger)

    except ValueError as e:
        print(f"\n{STATUS_FAIL} Error: {e}")
        return 1

    except KeyboardInterrupt:
        print("\n[Interrupted]")
        return 130

    except Exception as e:
        print(f"\n{STATUS_FAIL} Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
