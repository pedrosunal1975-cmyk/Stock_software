#!/usr/bin/env python3
# Path: mat_acc/test_hierarchy_real.py
"""
Test Hierarchy Builder with real mapped statement data.

This script tests the HierarchyBuilder with actual mapper output,
which has the following structure:

  /mnt/map_pro/mapper/mapped_statements/{market}/{company}/{form}/{date}/
  |-- json/
  |   |-- _catalog.json
  |   |-- MAIN_FINANCIAL_STATEMENTS.json
  |   |-- core_statements/
  |   |   |-- statement1.json
  |   |   |-- statement2.json
  |   |-- details/
  |   |   |-- detail1.json
  |   |-- other/
  |       |-- other1.json

Each statement JSON contains:
  - statement_type: The type (e.g., "INCOME_STATEMENT")
  - hierarchy:
      - roots: List of root concept names
      - nodes: Dict mapping concepts to node data
      - arcs: List of parent-child relationships

Usage:
    python test_hierarchy_real.py
    python test_hierarchy_real.py /path/to/mapped_filing_folder
"""

import json
import sys
from pathlib import Path

# Add mat_acc to path
sys.path.insert(0, str(Path(__file__).parent))

from process.hierarchy import HierarchyBuilder, StatementHierarchy


def find_mapped_filings(base_dir: Path) -> list[Path]:
    """Find all mapped filing folders by looking for json/ subdirectories."""
    filings = []

    # Look for directories containing json/core_statements
    for json_folder in base_dir.rglob('json'):
        if not json_folder.is_dir():
            continue

        # Check if it has core_statements, details, or other
        has_statements = any(
            (json_folder / folder).exists()
            for folder in ['core_statements', 'details', 'other']
        )

        if has_statements:
            filings.append(json_folder.parent)

    return filings


def test_with_filing_folder(filing_folder: Path) -> None:
    """Test hierarchy building with a mapped filing folder."""
    print(f"\n{'='*70}")
    print(f"Testing with: {filing_folder}")
    print('='*70)

    # Check folder structure
    json_folder = filing_folder / 'json'
    if not json_folder.exists():
        print(f"[WARN] No json/ folder found in {filing_folder}")
        return

    # List statement folders
    for folder_name in ['core_statements', 'details', 'other']:
        folder_path = json_folder / folder_name
        if folder_path.exists():
            files = list(folder_path.glob('*.json'))
            print(f"  {folder_name}/: {len(files)} files")

    # Build hierarchies
    builder = HierarchyBuilder()
    hierarchies = builder.build_from_filing_folder(filing_folder)

    if not hierarchies:
        print("[WARN] No hierarchies built")
        if builder.last_error:
            print(f"Last error: {builder.last_error}")
        return

    print(f"\n[OK] Built {len(hierarchies)} hierarchies")
    print(f"Discovered statement types: {builder.discovered_types}")

    # Group by statement type
    by_type: dict[str, list] = {}
    for name, root in hierarchies.items():
        stmt_type = root.metadata.get('statement_type', 'UNKNOWN')
        if stmt_type not in by_type:
            by_type[stmt_type] = []
        by_type[stmt_type].append((name, root))

    # Print summary by type
    print("\n--- Statements by Type ---")
    for stmt_type, statements in sorted(by_type.items()):
        print(f"\n  {stmt_type}:")
        for name, root in statements[:5]:  # First 5 of each type
            print(f"    - {name}: {root.descendant_count + 1} nodes")

    # Detailed view of first few hierarchies
    print("\n--- Detailed View (first 3 hierarchies) ---")
    for i, (name, root) in enumerate(list(hierarchies.items())[:3]):
        print(f"\n  [{i+1}] {name}")
        print(f"      Type: {root.metadata.get('statement_type', 'UNKNOWN')}")
        print(f"      Nodes: {root.descendant_count + 1}")
        print(f"      Max depth: {root.max_depth}")

        # Show first 2 levels
        print("      Structure (first 2 levels):")
        for node in root.iter_preorder():
            if node.depth <= 2:
                indent = "        " + "  " * node.depth
                value_str = f" = {node.value:,.0f}" if node.has_value else ""
                type_str = f" [{node.node_type.value}]"
                print(f"{indent}{node.label}{value_str}{type_str}")


def test_single_statement_file(json_path: Path) -> None:
    """Test building from a single statement JSON file."""
    print(f"\n{'='*70}")
    print(f"Testing single file: {json_path}")
    print('='*70)

    # Show file content structure
    with open(json_path) as f:
        data = json.load(f)

    print(f"\nTop-level keys: {list(data.keys())}")
    print(f"statement_type: {data.get('statement_type', 'NOT FOUND')}")

    hierarchy_data = data.get('hierarchy', {})
    if hierarchy_data:
        print(f"hierarchy.roots: {len(hierarchy_data.get('roots', []))} items")
        print(f"hierarchy.nodes: {len(hierarchy_data.get('nodes', {}))} items")
        print(f"hierarchy.arcs: {len(hierarchy_data.get('arcs', []))} items")
    else:
        print("No hierarchy field found!")
        return

    # Build hierarchy
    builder = HierarchyBuilder()
    root = builder.build_from_statement_file(json_path)

    if not root:
        print(f"[FAIL] Build failed: {builder.last_error}")
        return

    print(f"\n[OK] Built hierarchy: {root.descendant_count + 1} nodes")
    print(f"Statement type: {root.metadata.get('statement_type', 'UNKNOWN')}")

    # Create StatementHierarchy wrapper for analysis
    hierarchy = StatementHierarchy(root=root)
    stats = hierarchy.get_statistics()

    print(f"\nStatistics:")
    print(f"  Node count: {stats['node_count']}")
    print(f"  Line items: {stats['line_item_count']}")
    print(f"  Abstracts: {stats['abstract_count']}")
    print(f"  Totals: {stats['total_count']}")
    print(f"  Max depth: {stats['max_depth']}")

    # Print structure
    print(f"\nStructure (first 4 levels):")
    for node in hierarchy:
        if node.depth <= 4:
            indent = "  " + "  " * node.depth
            value_str = f" = {node.value:,.0f}" if node.has_value else ""
            print(f"{indent}{node.label}{value_str}")


def main():
    # Check for command line argument
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.is_file() and path.suffix == '.json':
            test_single_statement_file(path)
        elif path.is_dir():
            test_with_filing_folder(path)
        else:
            print(f"[ERROR] Invalid path: {path}")
        return

    # Default: Search for mapped statements
    mapper_dir = Path('/mnt/map_pro/mapper/mapped_statements')

    if not mapper_dir.exists():
        print(f"[ERROR] Mapper output directory not found: {mapper_dir}")
        print("\nTry running with a specific path:")
        print("  python test_hierarchy_real.py /path/to/mapped_filing_folder")
        print("  python test_hierarchy_real.py /path/to/statement.json")
        return

    print(f"Searching for mapped filings in: {mapper_dir}")

    filings = find_mapped_filings(mapper_dir)

    if not filings:
        print("[WARN] No mapped filing folders found")
        print("\nTry running with a specific path:")
        print("  python test_hierarchy_real.py /path/to/mapped_filing_folder")
        return

    print(f"Found {len(filings)} mapped filing folders")

    # Test with first few filings
    for filing_folder in filings[:3]:
        try:
            test_with_filing_folder(filing_folder)
        except Exception as e:
            print(f"[ERROR] Failed to process {filing_folder}: {e}")


if __name__ == '__main__':
    main()
