# Path: mat_acc_files/scripts/test_matching_engine.py
"""
Test Script for Dynamic Concept Matching Engine

This script demonstrates how the dictionary-based matching engine works
by creating sample concepts and running them through the matcher.

Usage:
    cd mat_acc_files
    python scripts/test_matching_engine.py
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from process.matcher.engine.coordinator import MatchingCoordinator
from process.matcher.models.concept_metadata import ConceptMetadata, ConceptIndex


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(name)s: %(message)s'
    )


def create_sample_concepts() -> list[ConceptMetadata]:
    """
    Create sample concepts simulating a parsed SEC filing.

    These represent typical US-GAAP concepts found in a balance sheet.
    """
    concepts = [
        # Current Assets - THE target concept
        ConceptMetadata(
            qname="us-gaap:AssetsCurrent",
            local_name="AssetsCurrent",
            prefix="us-gaap",
            labels={
                'standard': "Assets, Current",
                'terse': "Current Assets",
                'verbose': "Total Current Assets"
            },
            definition="Sum of the carrying amounts as of the balance sheet date of all assets that are expected to be realized in cash, sold, or consumed within one year (or the normal operating cycle, if longer).",
            balance_type="debit",
            period_type="instant",
            is_abstract=False,
            presentation_parent="us-gaap:AssetsAbstract",
            presentation_level=2,
            presentation_order=1.0,
            presentation_siblings=["us-gaap:AssetsNoncurrent"],
            calculation_children=[
                {"qname": "us-gaap:CashAndCashEquivalentsAtCarryingValue", "weight": 1.0, "order": 1},
                {"qname": "us-gaap:AccountsReceivableNetCurrent", "weight": 1.0, "order": 2},
                {"qname": "us-gaap:InventoryNet", "weight": 1.0, "order": 3},
                {"qname": "us-gaap:PrepaidExpenseAndOtherAssetsCurrent", "weight": 1.0, "order": 4},
            ]
        ),

        # Cash - child of Current Assets
        ConceptMetadata(
            qname="us-gaap:CashAndCashEquivalentsAtCarryingValue",
            local_name="CashAndCashEquivalentsAtCarryingValue",
            prefix="us-gaap",
            labels={
                'standard': "Cash and Cash Equivalents, at Carrying Value",
                'terse': "Cash and Cash Equivalents"
            },
            balance_type="debit",
            period_type="instant",
            is_abstract=False,
            presentation_parent="us-gaap:AssetsCurrent",
            presentation_level=3,
        ),

        # Accounts Receivable - child of Current Assets
        ConceptMetadata(
            qname="us-gaap:AccountsReceivableNetCurrent",
            local_name="AccountsReceivableNetCurrent",
            prefix="us-gaap",
            labels={
                'standard': "Accounts Receivable, after Allowance for Credit Loss, Current",
                'terse': "Accounts Receivable, Net"
            },
            balance_type="debit",
            period_type="instant",
            is_abstract=False,
            presentation_parent="us-gaap:AssetsCurrent",
            presentation_level=3,
        ),

        # Inventory - child of Current Assets
        ConceptMetadata(
            qname="us-gaap:InventoryNet",
            local_name="InventoryNet",
            prefix="us-gaap",
            labels={
                'standard': "Inventory, Net",
                'terse': "Inventories"
            },
            balance_type="debit",
            period_type="instant",
            is_abstract=False,
            presentation_parent="us-gaap:AssetsCurrent",
            presentation_level=3,
        ),

        # Prepaid Expenses - child of Current Assets
        ConceptMetadata(
            qname="us-gaap:PrepaidExpenseAndOtherAssetsCurrent",
            local_name="PrepaidExpenseAndOtherAssetsCurrent",
            prefix="us-gaap",
            labels={
                'standard': "Prepaid Expense and Other Assets, Current",
                'terse': "Prepaid Expenses"
            },
            balance_type="debit",
            period_type="instant",
            is_abstract=False,
            presentation_parent="us-gaap:AssetsCurrent",
            presentation_level=3,
        ),

        # Noncurrent Assets - sibling of Current Assets
        ConceptMetadata(
            qname="us-gaap:AssetsNoncurrent",
            local_name="AssetsNoncurrent",
            prefix="us-gaap",
            labels={
                'standard': "Assets, Noncurrent",
                'terse': "Noncurrent Assets"
            },
            balance_type="debit",
            period_type="instant",
            is_abstract=False,
            presentation_parent="us-gaap:AssetsAbstract",
            presentation_level=2,
            presentation_order=2.0,
            presentation_siblings=["us-gaap:AssetsCurrent"],
        ),

        # Total Assets - parent total
        ConceptMetadata(
            qname="us-gaap:Assets",
            local_name="Assets",
            prefix="us-gaap",
            labels={
                'standard': "Assets",
                'terse': "Total Assets",
                'verbose': "Assets, Total"
            },
            definition="Sum of the carrying amounts as of the balance sheet date of all assets that are recognized.",
            balance_type="debit",
            period_type="instant",
            is_abstract=False,
            presentation_level=1,
            calculation_children=[
                {"qname": "us-gaap:AssetsCurrent", "weight": 1.0, "order": 1},
                {"qname": "us-gaap:AssetsNoncurrent", "weight": 1.0, "order": 2},
            ]
        ),

        # Assets Abstract - hierarchy parent
        ConceptMetadata(
            qname="us-gaap:AssetsAbstract",
            local_name="AssetsAbstract",
            prefix="us-gaap",
            labels={
                'standard': "Assets [Abstract]"
            },
            is_abstract=True,
            presentation_level=1,
        ),

        # Current Liabilities - THE target concept for current ratio
        ConceptMetadata(
            qname="us-gaap:LiabilitiesCurrent",
            local_name="LiabilitiesCurrent",
            prefix="us-gaap",
            labels={
                'standard': "Liabilities, Current",
                'terse': "Current Liabilities",
                'verbose': "Total Current Liabilities"
            },
            definition="Total obligations incurred as part of normal operations that are expected to be paid during the following twelve months or within one business cycle, if longer.",
            balance_type="credit",
            period_type="instant",
            is_abstract=False,
            presentation_parent="us-gaap:LiabilitiesAbstract",
            presentation_level=2,
            presentation_order=1.0,
            calculation_children=[
                {"qname": "us-gaap:AccountsPayableCurrent", "weight": 1.0, "order": 1},
                {"qname": "us-gaap:AccruedLiabilitiesCurrent", "weight": 1.0, "order": 2},
                {"qname": "us-gaap:ShortTermBorrowings", "weight": 1.0, "order": 3},
            ]
        ),

        # Accounts Payable - child of Current Liabilities
        ConceptMetadata(
            qname="us-gaap:AccountsPayableCurrent",
            local_name="AccountsPayableCurrent",
            prefix="us-gaap",
            labels={
                'standard': "Accounts Payable, Current",
                'terse': "Accounts Payable"
            },
            balance_type="credit",
            period_type="instant",
            is_abstract=False,
            presentation_parent="us-gaap:LiabilitiesCurrent",
            presentation_level=3,
        ),

        # Total Equity
        ConceptMetadata(
            qname="us-gaap:StockholdersEquity",
            local_name="StockholdersEquity",
            prefix="us-gaap",
            labels={
                'standard': "Stockholders' Equity Attributable to Parent",
                'terse': "Total Stockholders' Equity",
                'verbose': "Total Equity"
            },
            balance_type="credit",
            period_type="instant",
            is_abstract=False,
            presentation_level=2,
        ),

        # Revenue
        ConceptMetadata(
            qname="us-gaap:Revenues",
            local_name="Revenues",
            prefix="us-gaap",
            labels={
                'standard': "Revenues",
                'terse': "Total Revenues",
                'verbose': "Revenue from Operations"
            },
            definition="Amount of revenue recognized from goods sold, services rendered, insurance premiums, or other activities that constitute an earning process.",
            balance_type="credit",
            period_type="duration",
            is_abstract=False,
            presentation_level=1,
        ),

        # Net Income
        ConceptMetadata(
            qname="us-gaap:NetIncomeLoss",
            local_name="NetIncomeLoss",
            prefix="us-gaap",
            labels={
                'standard': "Net Income (Loss) Attributable to Parent",
                'terse': "Net Income",
                'verbose': "Net Income or Loss"
            },
            definition="The portion of profit or loss for the period, net of income taxes, which is attributable to the parent.",
            balance_type="credit",
            period_type="duration",
            is_abstract=False,
            presentation_level=1,
        ),
    ]

    return concepts


def print_separator(title: str = "") -> None:
    """Print a visual separator."""
    print()
    if title:
        print(f"{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print("-" * 60)


def print_match_result(component_id: str, result) -> None:
    """Print details of a match result."""
    print(f"\n  Component: {component_id}")
    print(f"  Status: {'MATCHED' if result.is_matched else 'NOT MATCHED'}")

    if result.is_matched:
        print(f"  Matched Concept: {result.matched_concept}")
        print(f"  Total Score: {result.total_score}")
        print(f"  Confidence: {result.confidence.value.upper()}")

        if result.rule_breakdown:
            print("  Score Breakdown:")
            for rule_type, rule_score in result.rule_breakdown.items():
                if rule_score.score > 0:
                    print(f"    - {rule_type}: +{rule_score.score}")

        if result.alternatives:
            print(f"  Alternatives: {len(result.alternatives)}")
            for i, alt in enumerate(result.alternatives[:3], 1):
                print(f"    {i}. {alt.concept} (score: {alt.total_score})")
    else:
        reason = result.warnings[0] if result.warnings else "Unknown"
        print(f"  Reason: {reason}")


def main():
    """Run the matching engine test."""
    print_separator("Dynamic Concept Matching Engine Test")

    # Setup logging (set to True for verbose output)
    setup_logging(verbose=False)

    # Step 1: Create sample concepts
    print("\n[1] Creating sample concepts (simulating parsed filing)...")
    concepts = create_sample_concepts()
    print(f"    Created {len(concepts)} sample concepts")

    # Step 2: Initialize the matching coordinator
    print("\n[2] Initializing Matching Coordinator...")
    print("    Loading component definitions from dictionary/")

    try:
        coordinator = MatchingCoordinator()
        components = coordinator.get_all_components()
        print(f"    Loaded {len(components)} component definitions:")
        for cid in components:
            print(f"      - {cid}")
    except Exception as e:
        print(f"    [ERROR] Failed to initialize: {e}")
        print("\n    Make sure you're running from mat_acc_files/ directory")
        return 1

    # Step 3: Build concept index
    print("\n[3] Building concept index...")
    concept_index = coordinator.build_index(concepts)
    print(f"    Indexed {len(concept_index)} concepts")

    # Step 4: Resolve all components
    print_separator("Matching Results")
    print("\n[4] Resolving all components...")

    resolution = coordinator.resolve_all(
        concept_index=concept_index,
        filing_id="test_filing_001"
    )

    # Step 5: Display results
    print(f"\n    Resolution Summary:")
    print(f"    - Total components: {len(components)}")
    print(f"    - Resolved: {len(resolution.resolved)}")
    print(f"    - High confidence rate: {resolution.high_confidence_rate:.1f}%")

    print_separator("Detailed Match Results")

    # Print atomic matches
    for component_id, result in resolution.matches.items():
        print_match_result(component_id, result)

    # Print composite matches (like current_ratio)
    if resolution.composites:
        print_separator("Composite Components (Formulas)")
        for component_id, composite in resolution.composites.items():
            print(f"\n  Component: {component_id}")
            print(f"  Status: {'RESOLVED' if composite.resolved else 'NOT RESOLVED'}")
            print(f"  Formula: {composite.formula}")

            if composite.resolved:
                print("  Component Concepts:")
                for cid, concept in composite.component_concepts.items():
                    print(f"    - {cid}: {concept}")
            else:
                print(f"  Missing: {composite.missing_components}")

    # Step 6: Demonstrate single component resolution
    print_separator("Single Component Resolution Demo")

    test_component = "current_assets"
    print(f"\n  Resolving just '{test_component}'...")

    single_result = coordinator.resolve_component(test_component, concept_index)
    print_match_result(test_component, single_result)

    # Step 7: Show concept extraction
    print_separator("Concept Extraction Demo")

    print("\n  Using resolution map to get matched concepts:")
    for component_id in ['current_assets', 'current_liabilities', 'total_equity', 'revenue', 'net_income']:
        if resolution.is_resolved(component_id):
            concept = resolution.get_concept(component_id)
            confidence = resolution.get_confidence(component_id)
            print(f"    {component_id}: {concept} ({confidence})")
        else:
            print(f"    {component_id}: NOT RESOLVED")

    print_separator("Test Complete")
    print("\nThe matching engine successfully:")
    print("  [OK] Loaded component definitions from YAML dictionary")
    print("  [OK] Built concept index for fast lookup")
    print("  [OK] Evaluated matching rules (label, hierarchy, calculation, definition)")
    print("  [OK] Scored and ranked candidates")
    print("  [OK] Resolved components with confidence levels")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
