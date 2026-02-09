#!/usr/bin/env python3
# Path: mat_acc/debug_hierarchy.py
"""
Debug script to diagnose why hierarchies only have 1 node.
Shows the actual structure of the hierarchy field in mapper output.
"""

import json
import sys
from pathlib import Path


def debug_file(json_path: Path) -> None:
    """Debug a single statement JSON file."""
    print(f"\n{'='*70}")
    print(f"DEBUG: {json_path.name}")
    print('='*70)

    with open(json_path) as f:
        data = json.load(f)

    # Show top-level keys
    print(f"\nTop-level keys: {list(data.keys())}")
    print(f"statement_type: {data.get('statement_type', 'NOT FOUND')}")

    # Check hierarchy field
    hierarchy = data.get('hierarchy')
    if hierarchy is None:
        print("\n[ISSUE] No 'hierarchy' key found!")
        print("Checking for alternative data structures...")

        # Check for alternatives
        for alt_key in ['line_items', 'items', 'rows', 'nodes', 'facts', 'elements', 'structure']:
            if alt_key in data:
                val = data[alt_key]
                if isinstance(val, list):
                    print(f"  Found '{alt_key}': list with {len(val)} items")
                    if val:
                        print(f"    First item keys: {list(val[0].keys()) if isinstance(val[0], dict) else type(val[0])}")
                elif isinstance(val, dict):
                    print(f"  Found '{alt_key}': dict with {len(val)} keys")
                    print(f"    Keys: {list(val.keys())[:5]}")
        return

    print(f"\n'hierarchy' field found!")
    print(f"  Type: {type(hierarchy).__name__}")

    if isinstance(hierarchy, dict):
        print(f"  Keys: {list(hierarchy.keys())}")

        # Check for expected keys
        roots = hierarchy.get('roots', [])
        nodes = hierarchy.get('nodes', {})
        arcs = hierarchy.get('arcs', [])

        print(f"\n  Expected structure check:")
        print(f"    roots: {len(roots)} items" if isinstance(roots, list) else f"    roots: {type(roots)} (expected list)")
        print(f"    nodes: {len(nodes)} items" if isinstance(nodes, dict) else f"    nodes: {type(nodes)} (expected dict)")
        print(f"    arcs: {len(arcs)} items" if isinstance(arcs, list) else f"    arcs: {type(arcs)} (expected list)")

        if roots:
            print(f"\n  Sample roots:")
            for r in roots[:3]:
                print(f"    - {r}")

        if nodes:
            print(f"\n  Sample nodes (first 2):")
            for i, (concept, node_data) in enumerate(list(nodes.items())[:2]):
                print(f"    [{i+1}] {concept}")
                print(f"        Data keys: {list(node_data.keys())}")
                print(f"        label: {node_data.get('label', 'N/A')}")

        if arcs:
            print(f"\n  Sample arcs (first 3):")
            for i, arc in enumerate(arcs[:3]):
                print(f"    [{i+1}] {arc}")

        # Check if there's alternative hierarchy structure
        if not roots and not nodes and not arcs:
            print("\n  [ISSUE] hierarchy dict has no roots/nodes/arcs!")
            print(f"  Actual keys: {list(hierarchy.keys())}")
            print("\n  Sample of actual content:")
            for k, v in list(hierarchy.items())[:3]:
                if isinstance(v, dict):
                    print(f"    {k}: dict[{len(v)}] - keys: {list(v.keys())[:3]}")
                elif isinstance(v, list):
                    print(f"    {k}: list[{len(v)}]")
                    if v and isinstance(v[0], dict):
                        print(f"      First item keys: {list(v[0].keys())}")
                else:
                    print(f"    {k}: {type(v).__name__} = {str(v)[:50]}")

    elif isinstance(hierarchy, list):
        print(f"  [ISSUE] hierarchy is a LIST, not dict!")
        print(f"  Length: {len(hierarchy)}")
        if hierarchy:
            print(f"  First item type: {type(hierarchy[0]).__name__}")
            if isinstance(hierarchy[0], dict):
                print(f"  First item keys: {list(hierarchy[0].keys())}")
                print(f"  First item sample: {json.dumps(hierarchy[0], indent=4)[:300]}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python debug_hierarchy.py /path/to/statement.json")
        print("  python debug_hierarchy.py /path/to/mapped_filing_folder")
        return

    path = Path(sys.argv[1])

    if path.is_file():
        debug_file(path)
    elif path.is_dir():
        # Find statement files
        json_folder = path / 'json'
        if not json_folder.exists():
            json_folder = path

        for subfolder in ['core_statements', 'details', 'other']:
            sub = json_folder / subfolder
            if sub.exists():
                files = list(sub.glob('*.json'))
                if files:
                    print(f"\n{subfolder}/: {len(files)} files")
                    # Debug first file
                    debug_file(files[0])
                    break
    else:
        print(f"Path not found: {path}")


if __name__ == '__main__':
    main()
