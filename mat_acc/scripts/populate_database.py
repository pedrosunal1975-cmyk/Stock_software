#!/usr/bin/env python3
# Path: mat_acc/scripts/populate_database.py
"""
Populate Database Script

Scans the mapper output directory for mapped statements and populates
the database with hierarchies built by mat_acc's hierarchy builder.

Usage:
    python scripts/populate_database.py [--limit N] [--dry-run]

Options:
    --limit N    Process only N filings (default: all)
    --dry-run    Show what would be processed without writing to database
    --market X   Only process filings from market X (e.g., 'sec')
    --skip-taxonomy  Skip taxonomy availability check

The script will:
    1. Ensure taxonomy libraries are available (scan, process-manual, download)
    2. Scan mapper output directory for filing folders
    3. Use mat_acc's HierarchyBuilder to build hierarchies from each filing
    4. Store hierarchies in PostgreSQL database
    5. Report progress and statistics

Expected directory structure:
    {mapper_output_dir}/{market}/{company}/{form}/{date}/json/core_statements/*.json
"""

import os
import subprocess
import sys
import argparse
from pathlib import Path
from datetime import date
from typing import Optional

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_library_py() -> Optional[Path]:
    """Find the map_pro library.py script from config."""
    config = ConfigLoader()

    # Get library path from config
    library_path = config.get('library_script_path')
    if library_path and library_path.exists():
        logger.info(f"Found library.py at: {library_path}")
        return library_path

    # Fallback: relative to this file's location
    relative_path = Path(__file__).parent.parent.parent / 'library/library.py'
    if relative_path.exists():
        logger.info(f"Found library.py at: {relative_path}")
        return relative_path

    logger.warning("library.py not found. Check MAT_ACC_LIBRARY_SCRIPT_PATH in .env")
    return None


def get_library_env() -> dict:
    """
    Build environment dict for library.py subprocess.

    Loads mat_acc's .env file and converts MAP_PRO_* variables
    to the format expected by the library module.

    Returns:
        Environment dictionary for subprocess
    """
    # Load mat_acc's .env file
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)

    # Start with current environment
    env = os.environ.copy()

    # Map MAT_ACC/MAP_PRO prefixed variables to library module format
    mappings = {
        # Database configuration
        'MAP_PRO_DB_HOST': 'DB_HOST',
        'MAP_PRO_DB_PORT': 'DB_PORT',
        'MAP_PRO_DB_NAME': 'DB_NAME',
        'MAP_PRO_DB_USER': 'DB_USER',
        'MAP_PRO_DB_PASSWORD': 'DB_PASSWORD',
        'MAP_PRO_DB_ROOT_DIR': 'DB_ROOT_DIR',
        'MAP_PRO_DB_LOG_DIR': 'DB_LOG_DIR',
        'MAP_PRO_DB_POSTGRESQL_DATA_DIR': 'DB_POSTGRESQL_DATA_DIR',
        'MAP_PRO_DB_LOG_LEVEL': 'DB_LOG_LEVEL',
        'MAP_PRO_DB_LOG_CONSOLE': 'DB_LOG_CONSOLE',
        'MAP_PRO_DB_POOL_SIZE': 'DB_POOL_SIZE',
        'MAP_PRO_DB_POOL_MAX_OVERFLOW': 'DB_POOL_MAX_OVERFLOW',
        'MAP_PRO_DB_POOL_TIMEOUT': 'DB_POOL_TIMEOUT',
        'MAP_PRO_DB_POOL_RECYCLE': 'DB_POOL_RECYCLE',
        # Shared data paths
        'MAP_PRO_DATA_ENTITIES_DIR': 'DATA_ENTITIES_DIR',
        'MAP_PRO_DATA_TAXONOMIES_DIR': 'DATA_TAXONOMIES_DIR',
        # Library module
        'MAP_PRO_LIBRARY_TAXONOMIES_ROOT': 'LIBRARY_TAXONOMIES_ROOT',
        'MAP_PRO_LIBRARY_TAXONOMIES_LIBRARIES': 'LIBRARY_TAXONOMIES_LIBRARIES',
        'MAP_PRO_LIBRARY_MANUAL_DOWNLOADS': 'LIBRARY_MANUAL_DOWNLOADS',
        'MAP_PRO_LIBRARY_PARSED_FILES_DIR': 'LIBRARY_PARSED_FILES_DIR',
        'MAP_PRO_LIBRARY_CACHE_DIR': 'LIBRARY_CACHE_DIR',
        'MAP_PRO_LIBRARY_TEMP_DIR': 'LIBRARY_TEMP_DIR',
        'MAP_PRO_LIBRARY_LOG_DIR': 'LIBRARY_LOG_DIR',
        'MAP_PRO_LIBRARY_MONITOR_INTERVAL': 'LIBRARY_MONITOR_INTERVAL',
        'MAP_PRO_LIBRARY_AUTO_CREATE': 'LIBRARY_AUTO_CREATE',
        'MAP_PRO_LIBRARY_MIN_FILES_THRESHOLD': 'LIBRARY_MIN_FILES_THRESHOLD',
        'MAP_PRO_LIBRARY_CACHE_TTL': 'LIBRARY_CACHE_TTL',
        'MAP_PRO_LIBRARY_MAX_RETRIES': 'LIBRARY_MAX_RETRIES',
        # Downloader module
        'MAP_PRO_DOWNLOADER_ROOT_DIR': 'DOWNLOADER_ROOT_DIR',
        'MAP_PRO_DOWNLOADER_ENTITIES_DIR': 'DOWNLOADER_ENTITIES_DIR',
        'MAP_PRO_DOWNLOADER_TEMP_DIR': 'DOWNLOADER_TEMP_DIR',
        'MAP_PRO_DOWNLOADER_LOG_DIR': 'DOWNLOADER_LOG_DIR',
        'MAP_PRO_DOWNLOADER_CACHE_DIR': 'DOWNLOADER_CACHE_DIR',
    }

    for src_key, dst_key in mappings.items():
        value = os.getenv(src_key)
        if value:
            env[dst_key] = value

    return env


def ensure_taxonomies_available() -> bool:
    """
    Trigger library.py to ensure taxonomy libraries are available.

    Runs:
    1. library.py --scan (scan parsed filings for taxonomy requirements)
    2. library.py --process-manual (process any manually downloaded ZIPs)
    3. library.py --download (download any missing taxonomies)

    Returns:
        True if successful, False otherwise
    """
    library_py = find_library_py()

    if not library_py:
        print("[WARN] library.py not found - taxonomies may not be available")
        return False

    # Get environment with library module configuration from mat_acc .env
    library_env = get_library_env()

    try:
        print("\n[INFO] Scanning for taxonomy requirements...")
        logger.info("Running library.py --scan")

        result_scan = subprocess.run(
            [sys.executable, str(library_py), '--scan'],
            env=library_env,
            timeout=120
        )

        if result_scan.returncode != 0:
            logger.warning(f"library.py --scan returned {result_scan.returncode}")
        else:
            logger.info("library.py --scan completed successfully")

        print("[INFO] Processing manual taxonomy downloads...")
        logger.info("Running library.py --process-manual")

        result_manual = subprocess.run(
            [sys.executable, str(library_py), '--process-manual'],
            env=library_env,
            timeout=300
        )

        if result_manual.returncode != 0:
            logger.warning(f"library.py --process-manual returned {result_manual.returncode}")
        else:
            logger.info("library.py --process-manual completed successfully")

        print("[INFO] Downloading required taxonomies...")
        logger.info("Running library.py --download")

        result_download = subprocess.run(
            [sys.executable, str(library_py), '--download'],
            env=library_env,
            timeout=300
        )

        if result_download.returncode != 0:
            logger.warning(f"library.py --download returned {result_download.returncode}")
            return False
        else:
            logger.info("library.py --download completed successfully")
            print("[OK] Taxonomy libraries ready")
            return True

    except subprocess.TimeoutExpired:
        logger.error("library.py timed out")
        print("[FAIL] Taxonomy operations timed out")
        return False
    except Exception as e:
        logger.error(f"Failed to run library.py: {e}")
        print(f"[FAIL] Could not run library.py: {e}")
        return False


def find_mapped_filing_folders(
    base_dir: Path,
    parser_output_dir: Optional[Path] = None,
    market_filter: Optional[str] = None
) -> list[dict]:
    """
    Find all mapped filing folders in the mapper output directory.

    Expected structure:
        base_dir/{market}/{company}/{form}/{date}/json/core_statements/

    Args:
        base_dir: Base directory for mapped statements
        parser_output_dir: Base directory for parser output (to find parsed.json)
        market_filter: Optional market to filter by

    Returns:
        List of dictionaries with filing info
    """
    filings = []

    if not base_dir.exists():
        logger.warning(f"Base directory does not exist: {base_dir}")
        return filings

    for market_dir in base_dir.iterdir():
        if not market_dir.is_dir():
            continue

        market = market_dir.name

        # Apply market filter if specified
        if market_filter and market != market_filter:
            continue

        for company_dir in market_dir.iterdir():
            if not company_dir.is_dir():
                continue

            company_name = company_dir.name.replace('_', ' ')

            for form_dir in company_dir.iterdir():
                if not form_dir.is_dir():
                    continue

                form_type = form_dir.name.replace('_', '-')

                for date_dir in form_dir.iterdir():
                    if not date_dir.is_dir():
                        continue

                    # Check for proper mapped statement structure
                    # HierarchyBuilder expects: json/core_statements/*.json
                    json_folder = date_dir / 'json'
                    core_statements = json_folder / 'core_statements'

                    # Count statement files
                    statement_count = 0
                    if core_statements.exists():
                        statement_count += len(list(core_statements.glob('*.json')))

                    # Also check details and other folders
                    details_folder = json_folder / 'details'
                    if details_folder.exists():
                        statement_count += len(list(details_folder.glob('*.json')))

                    other_folder = json_folder / 'other'
                    if other_folder.exists():
                        statement_count += len(list(other_folder.glob('*.json')))

                    if statement_count == 0:
                        # No mapped statements found
                        continue

                    # Parse date
                    try:
                        filing_date = date.fromisoformat(date_dir.name)
                    except ValueError:
                        logger.warning(f"Invalid date format: {date_dir.name}")
                        continue

                    # Find corresponding parsed.json path
                    # Structure: parser_output_dir/{market}/{company}/{form}/{date}/parsed.json
                    parsed_json_path = None
                    if parser_output_dir:
                        # Construct path using same relative structure
                        parsed_json_path = (
                            parser_output_dir /
                            market_dir.name /
                            company_dir.name /
                            form_dir.name /
                            date_dir.name /
                            'parsed.json'
                        )
                        if not parsed_json_path.exists():
                            logger.debug(f"parsed.json not found at {parsed_json_path}")
                            parsed_json_path = None

                    filings.append({
                        'path': date_dir,
                        'market': market,
                        'company_name': company_name,
                        'form_type': form_type,
                        'filing_date': filing_date,
                        'statement_count': statement_count,
                        'parsed_json_path': parsed_json_path,
                    })

    return filings


def populate_database(
    limit: Optional[int] = None,
    dry_run: bool = False,
    market_filter: Optional[str] = None,
    skip_taxonomy: bool = False,
):
    """
    Populate the database with hierarchies from mapped statement files.

    Uses mat_acc's HierarchyBuilder to build hierarchies from the
    mapper output directory. If parsed.json files are found, facts with
    context_ref will be merged into mat_acc_id (e.g., 'BS-002-001-c4').

    Args:
        limit: Maximum number of filings to process
        dry_run: If True, show what would be done without making changes
        market_filter: Only process filings from specified market
        skip_taxonomy: If True, skip taxonomy availability check
    """
    from config_loader import ConfigLoader
    from database import HierarchyStorage

    # Ensure taxonomy libraries are available (unless skipped)
    if not skip_taxonomy:
        print("=" * 70)
        print("Checking Taxonomy Libraries")
        print("=" * 70)
        ensure_taxonomies_available()
        print()

    config = ConfigLoader()
    base_dir = config.get('mapper_output_dir')
    parser_output_dir = config.get('parser_output_dir')

    if not base_dir:
        print("[FAIL] mapper_output_dir not configured. Check MAT_ACC_MAPPER_OUTPUT_DIR in .env")
        return 1
    if not parser_output_dir:
        print("[FAIL] parser_output_dir not configured. Check MAT_ACC_PARSER_OUTPUT_DIR in .env")
        return 1

    print("=" * 70)
    print("mat_acc Database Population")
    print("=" * 70)
    print()
    print(f"Scanning: {base_dir}")
    print(f"Parser output: {parser_output_dir}")
    if market_filter:
        print(f"Market filter: {market_filter}")
    if limit:
        print(f"Limit: {limit} filings")
    if dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    print()

    # Find mapped filing folders
    logger.info("Scanning for mapped filing folders...")
    filings = find_mapped_filing_folders(base_dir, parser_output_dir, market_filter)

    if not filings:
        print("No mapped filings found.")
        print()
        print("Expected directory structure:")
        print(f"  {base_dir}/{{market}}/{{company}}/{{form}}/{{date}}/json/core_statements/*.json")
        return

    print(f"Found {len(filings)} mapped filings")
    print()

    # Apply limit
    if limit:
        filings = filings[:limit]
        print(f"Processing {len(filings)} filings (limited)")

    # Initialize storage
    if not dry_run:
        storage = HierarchyStorage()
        storage.initialize()
        print("Database initialized")
        print()

    # Process filings
    success_count = 0
    error_count = 0
    total_statements = 0
    total_nodes = 0

    for i, filing in enumerate(filings, 1):
        print(f"[{i}/{len(filings)}] {filing['company_name']} - "
              f"{filing['form_type']} ({filing['filing_date']})")

        if dry_run:
            print(f"         Path: {filing['path']}")
            print(f"         Statements: {filing['statement_count']} JSON files")
            if filing.get('parsed_json_path'):
                print(f"         Parsed JSON: {filing['parsed_json_path']}")
            else:
                print(f"         Parsed JSON: NOT FOUND (context_ref will be empty)")
            success_count += 1
            continue

        try:
            result = storage.process_filing_folder(
                folder_path=filing['path'],
                market=filing['market'],
                company_name=filing['company_name'],
                form_type=filing['form_type'],
                filing_date=filing['filing_date'],
                parsed_json_path=filing.get('parsed_json_path'),
            )

            if result['errors']:
                print(f"         ERRORS: {result['errors']}")
                error_count += 1
            else:
                print(f"         Stored: {result['statement_count']} statements, "
                      f"{result['total_nodes']} nodes")
                success_count += 1
                total_statements += result['statement_count']
                total_nodes += result['total_nodes']

        except Exception as e:
            print(f"         ERROR: {e}")
            logger.exception("Error processing filing")
            error_count += 1

    # Summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"  Processed: {success_count + error_count} filings")
    print(f"  Successful: {success_count}")
    print(f"  Errors: {error_count}")
    if not dry_run:
        print(f"  Total statements: {total_statements}")
        print(f"  Total nodes: {total_nodes}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Populate mat_acc database with hierarchies from mapped statements'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=None,
        help='Maximum number of filings to process'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--market', '-m',
        type=str,
        default=None,
        help='Only process filings from specified market (e.g., sec)'
    )
    parser.add_argument(
        '--skip-taxonomy',
        action='store_true',
        help='Skip taxonomy availability check (scan, process-manual, download)'
    )

    args = parser.parse_args()

    populate_database(
        limit=args.limit,
        dry_run=args.dry_run,
        market_filter=args.market,
        skip_taxonomy=args.skip_taxonomy,
    )


if __name__ == '__main__':
    main()
