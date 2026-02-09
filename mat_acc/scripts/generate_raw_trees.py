# Path: mat_acc/scripts/generate_raw_trees.py
"""
Generate Raw Tree Outputs

Creates human-readable tree visualizations of statement hierarchies
from the mat_acc database.

Output structure:
    /mnt/mat_acc/output/{market}/{company}/{form}/{period}/
        - raw_tree.txt    (ASCII tree visualization)
        - raw_tree.json   (Machine-readable format)

Usage:
    python scripts/generate_raw_trees.py              # All filings
    python scripts/generate_raw_trees.py --limit 5    # First 5 filings
    python scripts/generate_raw_trees.py --filing-id <uuid>  # Specific filing
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from output.raw_tree import RawTreeGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate raw tree visualizations from mat_acc database'
    )
    parser.add_argument(
        '--filing-id',
        type=str,
        help='Generate for specific filing UUID'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of filings to process'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Override output directory'
    )

    args = parser.parse_args()

    print('=' * 70)
    print('mat_acc Raw Tree Generator')
    print('=' * 70)
    print()

    # Initialize generator
    output_base = Path(args.output_dir) if args.output_dir else None
    generator = RawTreeGenerator(output_base=output_base)

    print(f'Output directory: {generator.output_base}')
    print()

    if args.filing_id:
        # Generate for specific filing
        print(f'Generating for filing: {args.filing_id}')
        try:
            result = generator.generate_for_filing(args.filing_id)
            print_result(result)
        except Exception as e:
            print(f'Error: {e}')
            return 1
    else:
        # Generate for all filings
        results = generator.generate_all()

        if args.limit:
            results = results[:args.limit]

        print(f'Processing {len(results)} filings...')
        print()

        success_count = 0
        error_count = 0

        for result in results:
            print_result(result)
            if result.get('success'):
                success_count += 1
            else:
                error_count += 1

        print()
        print('=' * 70)
        print('Summary')
        print('=' * 70)
        print(f'  Successful: {success_count}')
        print(f'  Errors: {error_count}')
        print(f'  Output: {generator.output_base}')

    return 0


def print_result(result: dict):
    """Print a single result."""
    if result.get('success'):
        print(f"[OK] {result.get('output_dir', 'unknown')}")
        print(f"     Statements: {result.get('statement_count', 0)}")
    else:
        print(f"[ERROR] {result.get('filing_id', 'unknown')}")
        print(f"        {result.get('error', 'Unknown error')}")


if __name__ == '__main__':
    sys.exit(main())
