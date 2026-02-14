# Path: mat_acc/ratio_check/diagnose_parsed.py
"""
Diagnostic script: Why is parsed.json not being found?

Run this to identify why the FactValueLookup cannot access parsed.json files.

Usage:
    cd mat_acc_files
    python -m ratio_check.diagnose_parsed
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_loader import ConfigLoader
from loaders import (
    ParsedDataLoader,
    MappedDataLoader,
    ParsedReader,
)
from loaders.constants import normalize_name, normalize_form_name, get_form_variations, dates_match_flexible, names_match_flexible


def diagnose():
    """Run full diagnosis of parsed.json access."""
    config = ConfigLoader()

    print("=" * 80)
    print("DIAGNOSIS: Why is parsed.json not being found?")
    print("=" * 80)

    # 1. Check configuration paths
    print("\n1. CONFIGURATION PATHS:")
    parsed_dir = os.getenv('MAT_ACC_PARSER_OUTPUT_DIR', 'NOT SET')
    mapped_dir = os.getenv('MAT_ACC_MAPPER_OUTPUT_DIR', 'NOT SET')
    print(f"   MAT_ACC_PARSER_OUTPUT_DIR: {parsed_dir}")
    print(f"   MAT_ACC_MAPPER_OUTPUT_DIR: {mapped_dir}")
    print(f"   Parsed dir exists: {os.path.exists(parsed_dir) if parsed_dir != 'NOT SET' else 'N/A'}")
    print(f"   Mapped dir exists: {os.path.exists(mapped_dir) if mapped_dir != 'NOT SET' else 'N/A'}")

    # 2. Discover all mapped filings
    print("\n2. MAPPED FILINGS (what ratio_check works with):")
    mapped_loader = MappedDataLoader(config)
    mapped_filings = mapped_loader.discover_all_mapped_filings()
    print(f"   Found {len(mapped_filings)} mapped filings:")
    for m in mapped_filings:
        print(f"      [{m.market}] {m.company} / {m.form} / {m.date}")
        print(f"         folder: {m.filing_folder}")

    # 3. Discover all parsed filings
    print("\n3. PARSED FILINGS (what should be accessible):")
    parsed_loader = ParsedDataLoader(config)
    parsed_filings = parsed_loader.discover_all_parsed_filings()
    print(f"   Found {len(parsed_filings)} parsed filings:")
    for p in parsed_filings:
        json_path = p.available_files.get('json')
        json_exists = json_path.exists() if json_path else False
        print(f"      [{p.market}] {p.company} / {p.form} / {p.date}")
        print(f"         folder: {p.filing_folder}")
        print(f"         JSON: {json_path} (exists={json_exists})")

    # 4. Try to match each mapped filing to a parsed filing
    print("\n4. MATCHING MAPPED -> PARSED (detailed analysis):")
    print("-" * 80)

    for mapped in mapped_filings:
        print(f"\n   MAPPED: {mapped.market}/{mapped.company}/{mapped.form}/{mapped.date}")

        # Show what we're searching for
        mapped_company_norm = normalize_name(mapped.company)
        mapped_form_norm = normalize_form_name(mapped.form)
        form_vars = get_form_variations(mapped.form)

        print(f"   Search criteria:")
        print(f"      company_normalized: '{mapped_company_norm}'")
        print(f"      form_normalized: '{mapped_form_norm}'")
        print(f"      form_variations: {form_vars[:5]}...")

        # Try the find method
        parsed = parsed_loader.find_parsed_filing(
            market=mapped.market,
            company=mapped.company,
            form=mapped.form,
            date=mapped.date,
        )

        if parsed:
            print(f"   [OK] FOUND: {parsed.filing_folder}")
            json_path = parsed.available_files.get('json')
            if json_path and json_path.exists():
                print(f"        JSON exists: {json_path}")
                # Test reading
                reader = ParsedReader()
                result = reader.read_parsed_filing(parsed)
                if result:
                    numeric_facts = [f for f in result.facts if f.value is not None]
                    print(f"        Facts: {len(result.facts)} ({len(numeric_facts)} numeric)")
            else:
                print(f"        [WARN] JSON missing or not in available_files!")
        else:
            print(f"   [FAIL] NOT FOUND!")

            # Debug: check each parsed filing to see why it didn't match
            print(f"\n   [DEBUG] Checking all {len(parsed_filings)} parsed filings:")

            for p in parsed_filings:
                parsed_company_norm = normalize_name(p.company)
                parsed_form_norm = normalize_form_name(p.form)
                form_variations = [f.lower() for f in get_form_variations(mapped.form)]

                # Check each criterion
                market_match = p.market.lower() == mapped.market.lower()

                # Company matching logic (from find_parsed_filing) - now uses flexible matching
                company_match = names_match_flexible(mapped.company, p.company)

                # Form matching logic (from find_parsed_filing)
                form_match = (
                    parsed_form_norm in form_variations or
                    p.form.lower() in form_variations
                )

                # Date matching
                date_match = dates_match_flexible(mapped.date, p.date, 'any')

                # Show ALL parsed filings and their match status
                status = []
                if market_match:
                    status.append("market:OK")
                else:
                    status.append(f"market:FAIL({p.market}!={mapped.market})")

                if company_match:
                    status.append("company:OK")
                else:
                    status.append(f"company:FAIL")

                if form_match:
                    status.append("form:OK")
                else:
                    status.append(f"form:FAIL({parsed_form_norm} not in {form_variations[:3]})")

                if date_match:
                    status.append("date:OK")
                else:
                    status.append(f"date:FAIL")

                all_match = market_match and company_match and form_match and date_match
                marker = "[MATCH]" if all_match else "[     ]"

                print(f"\n      {marker} {p.market}/{p.company}/{p.form}/{p.date}")
                print(f"              company_norm: '{parsed_company_norm}'")
                print(f"              form_norm: '{parsed_form_norm}'")
                print(f"              Status: {', '.join(status)}")

    # 5. Check if ParsedReader can actually read the files
    print("\n5. PARSED READER DIRECT TEST:")
    print("-" * 80)

    if parsed_filings:
        reader = ParsedReader()
        for pf in parsed_filings[:3]:  # Test first 3
            print(f"\n   Testing: {pf.company}/{pf.form}/{pf.date}")
            print(f"   Path: {pf.filing_folder}")

            result = reader.read_parsed_filing(pf)
            if result:
                numeric_facts = [f for f in result.facts if f.value is not None]
                print(f"   [OK] Read successful!")
                print(f"        Facts: {len(result.facts)} ({len(numeric_facts)} numeric)")
                print(f"        Contexts: {len(result.contexts)}")

                if numeric_facts:
                    print(f"        Sample values:")
                    for f in numeric_facts[:3]:
                        print(f"           {f.concept}: {f.value}")
            else:
                print(f"   [FAIL] Read failed!")
    else:
        print("   No parsed filings to test!")

    # 6. Directory structure analysis
    print("\n6. DIRECTORY STRUCTURE ANALYSIS:")
    print("-" * 80)

    if os.path.exists(parsed_dir):
        print(f"   Parsed root: {parsed_dir}")
        for item in sorted(os.listdir(parsed_dir)):
            item_path = os.path.join(parsed_dir, item)
            if os.path.isdir(item_path):
                sub_items = os.listdir(item_path)
                print(f"      /{item}/ ({len(sub_items)} items)")
                # Show all items
                for sub in sorted(sub_items):
                    sub_path = os.path.join(item_path, sub)
                    if os.path.isdir(sub_path):
                        # Check for parsed.json
                        parsed_json = os.path.join(sub_path, 'parsed.json')
                        # Check recursively
                        has_json = False
                        for root, dirs, files in os.walk(sub_path):
                            if 'parsed.json' in files:
                                has_json = True
                                break
                        marker = "[JSON]" if has_json else "[    ]"
                        print(f"         {marker} /{sub}/")
    else:
        print(f"   [ERROR] Parsed directory does not exist: {parsed_dir}")

    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)
    print("\nIf parsed filings exist but aren't being matched:")
    print("  1. Check company name differences (look at 'company_norm' values)")
    print("  2. Check form type differences (look at 'form_norm' values)")
    print("  3. Check directory structure (parsed.json must be in filing folder)")
    print("=" * 80)


if __name__ == '__main__':
    diagnose()
