# Path: mat_acc/ratio_check/check_parsed_json.py
"""
Quick diagnostic: Check what's inside parsed.json files.

Usage:
    cd mat_acc_files
    python -m ratio_check.check_parsed_json
"""

import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_loader import ConfigLoader
from loaders import ParsedDataLoader


def check_parsed_json():
    """Check the structure of parsed.json files."""
    config = ConfigLoader()
    loader = ParsedDataLoader(config)

    filings = loader.discover_all_parsed_filings()
    print(f"Found {len(filings)} parsed filings\n")

    for filing in filings:
        print("=" * 80)
        print(f"Filing: {filing.company}/{filing.form}/{filing.date}")
        print(f"Folder: {filing.filing_folder}")

        json_path = filing.available_files.get('json')
        if not json_path or not json_path.exists():
            print("[ERROR] No parsed.json found!")
            continue

        print(f"JSON path: {json_path}")
        print(f"File size: {json_path.stat().st_size:,} bytes")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            print(f"\nTop-level keys: {list(data.keys())}")

            # Check facts at top level
            facts = data.get('facts', [])
            print(f"Facts key type: {type(facts).__name__}")
            print(f"Facts count: {len(facts) if isinstance(facts, list) else 'N/A (not a list)'}")

            # Check inside 'instance' - this is where facts actually are!
            instance = data.get('instance', {})
            if instance:
                print(f"\n*** INSTANCE structure (where facts likely are):")
                print(f"    instance keys: {list(instance.keys())}")

                # Check for facts inside instance
                inst_facts = instance.get('facts', [])
                print(f"    instance.facts: {len(inst_facts) if isinstance(inst_facts, list) else type(inst_facts).__name__}")

                if isinstance(inst_facts, list) and inst_facts:
                    print(f"\n    First fact from instance.facts:")
                    print(f"    {json.dumps(inst_facts[0], indent=2)[:600]}")

                # Check contexts inside instance
                inst_contexts = instance.get('contexts', {})
                print(f"\n    instance.contexts: {len(inst_contexts) if isinstance(inst_contexts, (dict, list)) else type(inst_contexts).__name__}")

                # Check units inside instance
                inst_units = instance.get('units', {})
                print(f"    instance.units: {len(inst_units) if isinstance(inst_units, (dict, list)) else type(inst_units).__name__}")

            # Check for alternative fact structures
            if 'fact_table' in data:
                print(f"\nfact_table found: {len(data['fact_table'])} entries")
            if 'factTable' in data:
                print(f"\nfactTable found: {len(data['factTable'])} entries")

            # Check contexts at top level
            contexts = data.get('contexts', {})
            print(f"\nContexts (top level): {len(contexts) if isinstance(contexts, (dict, list)) else 'N/A'}")

            # Check units at top level
            units = data.get('units', {})
            print(f"Units (top level): {len(units) if isinstance(units, (dict, list)) else 'N/A'}")

            # Show full structure at high level
            print(f"\nFull structure overview:")
            for key, value in data.items():
                if isinstance(value, dict):
                    print(f"  {key}: dict with {len(value)} keys")
                elif isinstance(value, list):
                    print(f"  {key}: list with {len(value)} items")
                else:
                    val_str = str(value)[:50]
                    print(f"  {key}: {type(value).__name__} = {val_str}")

        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON decode error: {e}")
        except Exception as e:
            print(f"[ERROR] {e}")

        print()


if __name__ == '__main__':
    check_parsed_json()
