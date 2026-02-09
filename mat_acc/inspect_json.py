#!/usr/bin/env python3
"""Inspect JSON structure to understand mapper output format."""

import json
import sys
from pathlib import Path


def inspect_file(json_path: Path):
    """Inspect a single JSON file."""
    with open(json_path) as f:
        data = json.load(f)

    print(f"File: {json_path.name}")
    print(f"Top-level keys: {list(data.keys())}")

    # Show each top-level key's type and sample
    for key in data.keys():
        val = data[key]
        if isinstance(val, dict):
            print(f"\n  {key}: dict with {len(val)} keys")
            if len(val) <= 10:
                print(f"    Keys: {list(val.keys())}")
            else:
                print(f"    First 10 keys: {list(val.keys())[:10]}")
        elif isinstance(val, list):
            print(f"\n  {key}: list with {len(val)} items")
            if val and isinstance(val[0], dict):
                print(f"    First item keys: {list(val[0].keys())}")
        elif isinstance(val, str):
            print(f"\n  {key}: str = '{val[:100]}{'...' if len(val) > 100 else ''}'")
        else:
            print(f"\n  {key}: {type(val).__name__} = {val}")

    # Check for hierarchy field specifically
    if 'hierarchy' in data:
        print("\n" + "="*60)
        print("HIERARCHY STRUCTURE:")
        print("="*60)
        h = data['hierarchy']
        print(f"Type: {type(h).__name__}")
        if isinstance(h, dict):
            for k, v in h.items():
                if isinstance(v, list):
                    print(f"  {k}: list[{len(v)}]")
                    if v:
                        print(f"    First item: {json.dumps(v[0], indent=4)[:300]}")
                elif isinstance(v, dict):
                    print(f"  {k}: dict[{len(v)}]")
                    keys = list(v.keys())[:3]
                    for key in keys:
                        print(f"    {key}: {json.dumps(v[key], indent=4)[:200]}")
                else:
                    print(f"  {k}: {v}")
    else:
        print("\n[WARN] No 'hierarchy' key found in this file")


def inspect_folder(folder_path: Path):
    """Inspect all JSON files in a folder."""
    files = list(folder_path.glob('*.json'))
    print(f"Found {len(files)} JSON files in {folder_path.name}/")

    if files:
        print("\n" + "="*70)
        print(f"INSPECTING: {files[0].name}")
        print("="*70)
        inspect_file(files[0])


if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.is_file():
            inspect_file(path)
        elif path.is_dir():
            # Check for json subfolder structure
            json_folder = path / 'json'
            if json_folder.exists():
                for subfolder in ['core_statements', 'details', 'other']:
                    sub = json_folder / subfolder
                    if sub.exists():
                        inspect_folder(sub)
                        break
            else:
                inspect_folder(path)
    else:
        print("Usage:")
        print("  python inspect_json.py /path/to/file.json")
        print("  python inspect_json.py /path/to/mapped_filing_folder")
