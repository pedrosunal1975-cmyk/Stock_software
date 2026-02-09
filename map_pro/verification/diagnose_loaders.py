#!/usr/bin/env python3
# Path: verification/diagnose_loaders.py
"""
Diagnostic script to verify loader connections.

Run this to check:
1. MappedDataLoader finds mapped filings
2. ParsedDataLoader finds parsed.json files
3. Matching between the two works correctly
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from verification.core.config_loader import ConfigLoader
from verification.loaders.mapped_data import MappedDataLoader
from verification.loaders.parsed_data import ParsedDataLoader
from verification.loaders.constants import normalize_name, normalize_form_name


def diagnose():
    """Run loader diagnostics."""
    sep = '=' * 60

    print(sep)
    print('VERIFICATION_V2 LOADER DIAGNOSTICS')
    print(sep)
    print()

    # Initialize config
    print('[1] Loading configuration...')
    try:
        config = ConfigLoader()
        print('    [OK] ConfigLoader initialized')
        print(f'    parser_output_dir: {config.get("parser_output_dir")}')
        print(f'    mapper_output_dir: {config.get("mapper_output_dir")}')
    except Exception as e:
        print(f'    [ERROR] ConfigLoader failed: {e}')
        return

    print()

    # Check MappedDataLoader
    print('[2] Discovering mapped filings...')
    try:
        mapped_loader = MappedDataLoader(config)
        mapped_filings = mapped_loader.discover_all_mapped_filings()
        print(f'    [OK] Found {len(mapped_filings)} mapped filings')

        for filing in mapped_filings[:5]:
            print(f'        - {filing.market}/{filing.company}/{filing.form}/{filing.date}')

        if len(mapped_filings) > 5:
            print(f'        ... and {len(mapped_filings) - 5} more')

    except Exception as e:
        print(f'    [ERROR] MappedDataLoader failed: {e}')
        mapped_filings = []

    print()

    # Check ParsedDataLoader
    print('[3] Discovering parsed filings...')
    try:
        parsed_loader = ParsedDataLoader(config)
        parsed_filings = parsed_loader.discover_all_parsed_filings()
        print(f'    [OK] Found {len(parsed_filings)} parsed filings')

        for filing in parsed_filings[:5]:
            print(f'        - {filing.market}/{filing.company}/{filing.form}/{filing.date}')
            print(f'          folder: {filing.filing_folder}')

        if len(parsed_filings) > 5:
            print(f'        ... and {len(parsed_filings) - 5} more')

    except Exception as e:
        print(f'    [ERROR] ParsedDataLoader failed: {e}')
        parsed_filings = []

    print()

    # Check matching
    print('[4] Checking matches between mapped and parsed...')
    matches = 0
    no_match = []

    for mapped in mapped_filings:
        # Try to find matching parsed filing
        found = None

        for parsed in parsed_filings:
            # Normalize for comparison
            mapped_company = normalize_name(mapped.company)
            parsed_company = normalize_name(parsed.company)

            # Check if companies match (fuzzy)
            if mapped_company in parsed_company or parsed_company in mapped_company:
                # Check form match
                mapped_form = normalize_form_name(mapped.form)
                parsed_form = normalize_form_name(parsed.form)

                if mapped_form == parsed_form or mapped.form.lower() == parsed.form.lower():
                    found = parsed
                    break

        if found:
            matches += 1
            print(f'    [MATCH] {mapped.company}/{mapped.form} -> {found.filing_folder}')
        else:
            no_match.append(mapped)

    print()
    print(f'    Matches: {matches}/{len(mapped_filings)}')

    if no_match:
        print(f'    No match found for:')
        for m in no_match[:5]:
            print(f'        - {m.company}/{m.form}/{m.date}')

    print()
    print(sep)
    print('DIAGNOSTICS COMPLETE')
    print(sep)


if __name__ == '__main__':
    diagnose()
