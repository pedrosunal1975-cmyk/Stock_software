# Path: mat_acc_files/scripts/ratio_check.py
"""
Ratio Check Script

Interactive CLI tool to test the Dynamic Concept Matching Engine
on real company data using mat_acc loaders.

Data Sources (checked in order):
1. Mapped Statements (from mapper module)
2. Parsed Filings (from parser module)

Usage:
    cd mat_acc_files
    python scripts/ratio_check.py
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_loader import ConfigLoader

# Import loaders - use full loader package
from loaders import (
    MappedDataLoader, MappedFilingEntry, MappedReader, MappedStatements,
    ParsedDataLoader, ParsedFilingEntry, ParsedReader,
)

from process.matcher.engine.coordinator import MatchingCoordinator
from process.matcher.models.concept_metadata import ConceptMetadata, ConceptIndex
from process.matcher.models.match_result import Confidence


@dataclass
class FilingOption:
    """Unified filing option for menu display."""
    index: int
    source: str  # 'mapped' or 'parsed'
    market: str
    company: str
    form: str
    date: str
    file_count: int
    entry: object  # MappedFilingEntry or ParsedFilingEntry


@dataclass
class RatioResult:
    """Result of a ratio calculation."""
    ratio_id: str
    display_name: str
    value: Optional[float]
    numerator_concept: Optional[str]
    numerator_value: Optional[float]
    denominator_concept: Optional[str]
    denominator_value: Optional[float]
    interpretation: str
    confidence: str


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(name)s: %(message)s'
    )


def print_separator(title: str = "", char: str = "=") -> None:
    """Print a visual separator."""
    print()
    if title:
        print(f"{char*60}")
        print(f"  {title}")
        print(f"{char*60}")
    else:
        print(char * 60)


def discover_all_filings(config: ConfigLoader) -> list[FilingOption]:
    """
    Discover all available filings from multiple data sources.

    Checks mapped statements first, then parsed filings.
    """
    options = []
    index = 1

    # Try mapped statements first
    try:
        mapped_loader = MappedDataLoader(config)
        mapped_filings = mapped_loader.discover_all_mapped_filings()
        for filing in mapped_filings:
            options.append(FilingOption(
                index=index,
                source='mapped',
                market=filing.market,
                company=filing.company,
                form=filing.form,
                date=filing.date,
                file_count=len(filing.available_files.get('json', [])),
                entry=filing,
            ))
            index += 1
    except Exception as e:
        logging.debug(f"Mapped data not available: {e}")

    # Also try parsed filings
    try:
        parsed_loader = ParsedDataLoader(config)
        parsed_filings = parsed_loader.discover_all_parsed_filings()
        for filing in parsed_filings:
            # Skip if we already have a mapped version of same filing
            existing = any(
                o.company == filing.company and
                o.form == filing.form and
                o.date == filing.date
                for o in options
            )
            if not existing:
                options.append(FilingOption(
                    index=index,
                    source='parsed',
                    market=filing.market,
                    company=filing.company,
                    form=filing.form,
                    date=filing.date,
                    file_count=len(filing.available_files),
                    entry=filing,
                ))
                index += 1
    except Exception as e:
        logging.debug(f"Parsed data not available: {e}")

    return options


def display_filing_menu(options: list[FilingOption]) -> None:
    """Display numbered list of filings."""
    print_separator("Available Filings for Ratio Analysis")

    if not options:
        print("\n  No filings found in any data source.")
        config = ConfigLoader()
        print("\n  Checked locations:")
        print(f"    - Mapped: {config.get('mapper_output_dir')}")
        print(f"    - Parsed: {config.get('parser_output_dir')}")
        return

    # Group by company for cleaner display
    companies = {}
    for opt in options:
        key = f"{opt.market}/{opt.company}"
        if key not in companies:
            companies[key] = []
        companies[key].append(opt)

    print(f"\n  Found {len(options)} filings from {len(companies)} companies:\n")

    for company_key, company_opts in sorted(companies.items()):
        print(f"  {company_key}:")
        for opt in company_opts:
            src_tag = "[M]" if opt.source == 'mapped' else "[P]"
            print(f"    [{opt.index:3d}] {src_tag} {opt.form:10s} | {opt.date:12s} | {opt.file_count} files")
        print()

    print("-" * 60)
    print("  [M] = Mapped statements, [P] = Parsed filing")
    print("  Enter number to select, 'd' for demo, 'q' to quit")
    print("-" * 60)


def get_user_selection(options: list[FilingOption]) -> Optional[Union[FilingOption, str]]:
    """Get user's filing selection."""
    while True:
        try:
            choice = input("\n  Select filing number: ").strip().lower()

            if choice == 'q':
                return None

            if choice == 'd':
                return 'demo'

            if choice == 'r':
                return 'refresh'

            idx = int(choice)
            for opt in options:
                if opt.index == idx:
                    return opt

            print(f"  [!] Please enter a valid number")

        except ValueError:
            print("  [!] Invalid input. Enter a number, 'd' for demo, or 'q' to quit.")
        except KeyboardInterrupt:
            print("\n  Interrupted.")
            return None


def convert_facts_to_concepts(
    statements: MappedStatements,
    filing: MappedFilingEntry
) -> list[ConceptMetadata]:
    """
    Convert mapped statement facts to ConceptMetadata for the matching engine.

    This bridges the gap between the mapped data and the matching engine.
    """
    concepts = []
    seen_concepts = set()

    # Build a map of parent-child relationships from statement structure
    parent_map = {}
    level_map = {}

    for stmt in statements.statements:
        for fact in stmt.facts:
            if not fact.concept:
                continue

            qname = fact.concept
            if qname in seen_concepts:
                continue
            seen_concepts.add(qname)

            # Parse concept name
            if ':' in qname:
                prefix, local_name = qname.split(':', 1)
            else:
                prefix = ''
                local_name = qname

            # Build labels from fact data
            labels = {}
            if fact.label:
                labels['standard'] = fact.label
                # Also add variations
                labels['terse'] = fact.label.replace(',', '').strip()

            # Create concept metadata
            concept = ConceptMetadata(
                qname=qname,
                local_name=local_name,
                prefix=prefix,
                labels=labels,
                definition=None,  # Not available in mapped data
                balance_type=None,  # Could be inferred from sign
                period_type='instant' if fact.period_start is None else 'duration',
                is_abstract=fact.is_abstract,
                presentation_level=fact.depth,
                presentation_order=fact.order or 0.0,
            )

            concepts.append(concept)

    return concepts


def find_fact_value(
    statements: MappedStatements,
    concept_qname: str
) -> Optional[float]:
    """Find the numeric value for a concept from statements."""
    for stmt in statements.statements:
        for fact in stmt.facts:
            if fact.concept == concept_qname:
                if fact.value is not None:
                    try:
                        # Handle string numbers with commas
                        if isinstance(fact.value, str):
                            clean_value = fact.value.replace(',', '').replace('$', '')
                            return float(clean_value)
                        return float(fact.value)
                    except (ValueError, TypeError):
                        pass
    return None


def interpret_current_ratio(value: Optional[float]) -> str:
    """Interpret the current ratio value."""
    if value is None:
        return "Cannot calculate - missing data"

    if value < 1.0:
        return f"[CONCERN] Below 1.0 indicates potential liquidity issues"
    elif value < 1.5:
        return f"[CAUTION] Below typical healthy range (1.5-3.0)"
    elif value <= 3.0:
        return f"[HEALTHY] Within typical range (1.5-3.0)"
    elif value <= 4.0:
        return f"[GOOD] Above average liquidity"
    else:
        return f"[HIGH] May indicate inefficient use of assets"


def calculate_ratios(
    resolution,
    statements: MappedStatements
) -> list[RatioResult]:
    """Calculate financial ratios using resolved components."""
    results = []

    # Current Ratio = Current Assets / Current Liabilities
    current_assets_concept = resolution.get_concept('current_assets')
    current_liabilities_concept = resolution.get_concept('current_liabilities')

    current_assets_value = None
    current_liabilities_value = None
    current_ratio_value = None

    if current_assets_concept:
        current_assets_value = find_fact_value(statements, current_assets_concept)

    if current_liabilities_concept:
        current_liabilities_value = find_fact_value(statements, current_liabilities_concept)

    if current_assets_value and current_liabilities_value and current_liabilities_value != 0:
        current_ratio_value = current_assets_value / current_liabilities_value

    # Determine confidence
    assets_conf = resolution.get_confidence('current_assets')
    liab_conf = resolution.get_confidence('current_liabilities')

    if assets_conf == Confidence.HIGH and liab_conf == Confidence.HIGH:
        confidence = "HIGH"
    elif assets_conf == Confidence.NONE or liab_conf == Confidence.NONE:
        confidence = "NONE"
    else:
        confidence = "MEDIUM"

    results.append(RatioResult(
        ratio_id='current_ratio',
        display_name='Current Ratio',
        value=current_ratio_value,
        numerator_concept=current_assets_concept,
        numerator_value=current_assets_value,
        denominator_concept=current_liabilities_concept,
        denominator_value=current_liabilities_value,
        interpretation=interpret_current_ratio(current_ratio_value),
        confidence=confidence,
    ))

    return results


def format_number(value: Optional[float], is_ratio: bool = False) -> str:
    """Format a number for display."""
    if value is None:
        return "N/A"
    if is_ratio:
        return f"{value:.2f}"
    # Format as currency with commas
    if abs(value) >= 1_000_000_000:
        return f"${value/1_000_000_000:,.2f}B"
    elif abs(value) >= 1_000_000:
        return f"${value/1_000_000:,.2f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:,.2f}K"
    else:
        return f"${value:,.2f}"


def display_results(
    filing: MappedFilingEntry,
    resolution,
    ratios: list[RatioResult],
    concepts_count: int
) -> None:
    """Display the analysis results."""
    print_separator(f"Ratio Analysis: {filing.company}")

    print(f"\n  Filing: {filing.market.upper()} / {filing.form} / {filing.date}")
    print(f"  Concepts Analyzed: {concepts_count}")
    print(f"  Components Resolved: {len(resolution.resolved)}/{len(resolution.matches)}")
    print(f"  High Confidence Rate: {resolution.high_confidence_rate:.1f}%")

    # Component resolution details
    print_separator("Component Resolution", "-")

    for component_id, match_result in resolution.matches.items():
        status = "[OK]" if match_result.is_matched else "[--]"
        concept = match_result.matched_concept or "Not matched"
        conf = match_result.confidence.value.upper() if match_result.is_matched else "-"
        score = match_result.total_score if match_result.is_matched else 0

        print(f"  {status} {component_id:20s} -> {concept}")
        if match_result.is_matched:
            print(f"      Score: {score:3d} | Confidence: {conf}")

            # Show score breakdown
            if match_result.rule_breakdown:
                breakdown = []
                for rule_type, rule_score in match_result.rule_breakdown.items():
                    if rule_score.score > 0:
                        breakdown.append(f"{rule_type}:{rule_score.score}")
                if breakdown:
                    print(f"      Breakdown: {', '.join(breakdown)}")

    # Ratio calculations
    print_separator("Financial Ratios", "-")

    for ratio in ratios:
        print(f"\n  {ratio.display_name}")
        print(f"  {'='*40}")

        if ratio.value is not None:
            print(f"  Value: {format_number(ratio.value, is_ratio=True)}")
        else:
            print(f"  Value: Cannot calculate")

        print(f"  Confidence: {ratio.confidence}")
        print()
        print(f"  Formula: Current Assets / Current Liabilities")
        print(f"  Numerator:   {ratio.numerator_concept or 'Not resolved'}")
        print(f"               {format_number(ratio.numerator_value)}")
        print(f"  Denominator: {ratio.denominator_concept or 'Not resolved'}")
        print(f"               {format_number(ratio.denominator_value)}")
        print()
        print(f"  Interpretation: {ratio.interpretation}")

    print_separator("Analysis Complete")


def analyze_filing(filing: MappedFilingEntry) -> None:
    """Run full analysis on a selected filing."""
    print(f"\n  Loading {filing.company} / {filing.form} / {filing.date}...")

    # Step 1: Read mapped statements
    reader = MappedReader()
    statements = reader.read_statements(filing)

    if not statements or not statements.statements:
        print("  [ERROR] Could not read mapped statements")
        return

    total_facts = sum(len(stmt.facts) for stmt in statements.statements)
    print(f"  Loaded {len(statements.statements)} statements with {total_facts} facts")

    # Step 2: Convert facts to concept metadata
    print("  Converting facts to concept metadata...")
    concepts = convert_facts_to_concepts(statements, filing)
    print(f"  Created {len(concepts)} unique concepts")

    if not concepts:
        print("  [ERROR] No concepts extracted from statements")
        return

    # Step 3: Initialize matching engine
    print("  Initializing matching engine...")
    try:
        coordinator = MatchingCoordinator()
        components = coordinator.get_all_components()
        print(f"  Loaded {len(components)} component definitions")
    except Exception as e:
        print(f"  [ERROR] Failed to initialize matcher: {e}")
        return

    # Step 4: Build concept index
    print("  Building concept index...")
    concept_index = coordinator.build_index(concepts)
    print(f"  Indexed {len(concept_index)} concepts")

    # Step 5: Resolve components
    print("  Resolving components...")
    resolution = coordinator.resolve_all(
        concept_index=concept_index,
        filing_id=f"{filing.market}_{filing.company}_{filing.form}_{filing.date}"
    )
    print(f"  Resolved {len(resolution.resolved)}/{len(components)} components")

    # Step 6: Calculate ratios
    print("  Calculating ratios...")
    ratios = calculate_ratios(resolution, statements)

    # Step 7: Display results
    display_results(filing, resolution, ratios, len(concepts))


def create_demo_concepts() -> list[ConceptMetadata]:
    """
    Create demo concepts simulating a real SEC filing (Apple-like data).

    This allows testing the matching engine without actual mapped files.
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
            },
            definition="Assets expected to be converted to cash within one year.",
            balance_type="debit",
            period_type="instant",
            is_abstract=False,
            presentation_parent="us-gaap:AssetsAbstract",
            presentation_level=2,
            calculation_children=[
                {"qname": "us-gaap:CashAndCashEquivalentsAtCarryingValue", "weight": 1.0, "order": 1},
                {"qname": "us-gaap:AccountsReceivableNetCurrent", "weight": 1.0, "order": 2},
                {"qname": "us-gaap:InventoryNet", "weight": 1.0, "order": 3},
            ]
        ),
        # Cash
        ConceptMetadata(
            qname="us-gaap:CashAndCashEquivalentsAtCarryingValue",
            local_name="CashAndCashEquivalentsAtCarryingValue",
            prefix="us-gaap",
            labels={'standard': "Cash and Cash Equivalents"},
            balance_type="debit",
            period_type="instant",
            presentation_parent="us-gaap:AssetsCurrent",
            presentation_level=3,
        ),
        # Receivables
        ConceptMetadata(
            qname="us-gaap:AccountsReceivableNetCurrent",
            local_name="AccountsReceivableNetCurrent",
            prefix="us-gaap",
            labels={'standard': "Accounts Receivable, Net"},
            balance_type="debit",
            period_type="instant",
            presentation_parent="us-gaap:AssetsCurrent",
            presentation_level=3,
        ),
        # Inventory
        ConceptMetadata(
            qname="us-gaap:InventoryNet",
            local_name="InventoryNet",
            prefix="us-gaap",
            labels={'standard': "Inventory, Net"},
            balance_type="debit",
            period_type="instant",
            presentation_parent="us-gaap:AssetsCurrent",
            presentation_level=3,
        ),
        # Total Assets
        ConceptMetadata(
            qname="us-gaap:Assets",
            local_name="Assets",
            prefix="us-gaap",
            labels={'standard': "Assets", 'terse': "Total Assets"},
            definition="Sum of all assets.",
            balance_type="debit",
            period_type="instant",
            presentation_level=1,
            calculation_children=[
                {"qname": "us-gaap:AssetsCurrent", "weight": 1.0, "order": 1},
                {"qname": "us-gaap:AssetsNoncurrent", "weight": 1.0, "order": 2},
            ]
        ),
        # Assets Abstract
        ConceptMetadata(
            qname="us-gaap:AssetsAbstract",
            local_name="AssetsAbstract",
            prefix="us-gaap",
            labels={'standard': "Assets [Abstract]"},
            is_abstract=True,
            presentation_level=1,
        ),
        # Current Liabilities
        ConceptMetadata(
            qname="us-gaap:LiabilitiesCurrent",
            local_name="LiabilitiesCurrent",
            prefix="us-gaap",
            labels={
                'standard': "Liabilities, Current",
                'terse': "Current Liabilities",
            },
            definition="Obligations due within one year.",
            balance_type="credit",
            period_type="instant",
            presentation_parent="us-gaap:LiabilitiesAbstract",
            presentation_level=2,
            calculation_children=[
                {"qname": "us-gaap:AccountsPayableCurrent", "weight": 1.0, "order": 1},
                {"qname": "us-gaap:AccruedLiabilitiesCurrent", "weight": 1.0, "order": 2},
            ]
        ),
        # Accounts Payable
        ConceptMetadata(
            qname="us-gaap:AccountsPayableCurrent",
            local_name="AccountsPayableCurrent",
            prefix="us-gaap",
            labels={'standard': "Accounts Payable"},
            balance_type="credit",
            period_type="instant",
            presentation_parent="us-gaap:LiabilitiesCurrent",
            presentation_level=3,
        ),
        # Total Equity
        ConceptMetadata(
            qname="us-gaap:StockholdersEquity",
            local_name="StockholdersEquity",
            prefix="us-gaap",
            labels={'standard': "Stockholders' Equity", 'terse': "Total Equity"},
            balance_type="credit",
            period_type="instant",
            presentation_level=2,
        ),
        # Revenue
        ConceptMetadata(
            qname="us-gaap:Revenues",
            local_name="Revenues",
            prefix="us-gaap",
            labels={'standard': "Revenues", 'terse': "Total Revenue"},
            definition="Revenue from operations.",
            balance_type="credit",
            period_type="duration",
            presentation_level=1,
        ),
        # Net Income
        ConceptMetadata(
            qname="us-gaap:NetIncomeLoss",
            local_name="NetIncomeLoss",
            prefix="us-gaap",
            labels={'standard': "Net Income (Loss)", 'terse': "Net Income"},
            definition="Net profit or loss.",
            balance_type="credit",
            period_type="duration",
            presentation_level=1,
        ),
    ]
    return concepts


# Demo fact values (Apple-like numbers in thousands)
DEMO_FACT_VALUES = {
    "us-gaap:AssetsCurrent": 143_566_000,
    "us-gaap:CashAndCashEquivalentsAtCarryingValue": 29_965_000,
    "us-gaap:AccountsReceivableNetCurrent": 60_932_000,
    "us-gaap:InventoryNet": 6_331_000,
    "us-gaap:Assets": 352_755_000,
    "us-gaap:LiabilitiesCurrent": 145_308_000,
    "us-gaap:AccountsPayableCurrent": 64_115_000,
    "us-gaap:StockholdersEquity": 62_146_000,
    "us-gaap:Revenues": 383_285_000,
    "us-gaap:NetIncomeLoss": 96_995_000,
}


def run_demo_mode() -> int:
    """Run in demo mode with sample data."""
    print_separator("DEMO MODE - Using Sample Data")

    print("\n  This demo simulates analyzing a company filing (Apple-like data)")
    print("  to demonstrate the Dynamic Concept Matching Engine.\n")

    # Step 1: Create demo concepts
    print("  [1] Creating demo concepts...")
    concepts = create_demo_concepts()
    print(f"      Created {len(concepts)} sample concepts")

    # Step 2: Initialize matching engine
    print("\n  [2] Initializing matching engine...")
    try:
        coordinator = MatchingCoordinator()
        components = coordinator.get_all_components()
        print(f"      Loaded {len(components)} component definitions:")
        for cid in components:
            print(f"        - {cid}")
    except Exception as e:
        print(f"      [ERROR] Failed to initialize matcher: {e}")
        return 1

    # Step 3: Build concept index
    print("\n  [3] Building concept index...")
    concept_index = coordinator.build_index(concepts)
    print(f"      Indexed {len(concept_index)} concepts")

    # Step 4: Resolve components
    print("\n  [4] Resolving components...")
    resolution = coordinator.resolve_all(
        concept_index=concept_index,
        filing_id="demo_apple_10k_2024"
    )
    print(f"      Resolved {len(resolution.resolved)}/{len(components)} components")
    print(f"      High confidence rate: {resolution.high_confidence_rate:.1f}%")

    # Step 5: Display component resolution
    print_separator("Component Resolution Details", "-")

    for component_id, match_result in resolution.matches.items():
        status = "[OK]" if match_result.is_matched else "[--]"
        concept = match_result.matched_concept or "Not matched"
        conf = match_result.confidence.value.upper() if match_result.is_matched else "-"
        score = match_result.total_score if match_result.is_matched else 0

        print(f"\n  {status} {component_id}")
        print(f"      Matched: {concept}")
        if match_result.is_matched:
            print(f"      Score: {score} | Confidence: {conf}")
            # Score breakdown
            if match_result.rule_breakdown:
                breakdown = []
                for rule_type, rule_score in match_result.rule_breakdown.items():
                    if rule_score.score > 0:
                        breakdown.append(f"{rule_type}:{rule_score.score}")
                if breakdown:
                    print(f"      Breakdown: {', '.join(breakdown)}")

    # Step 6: Calculate and display ratios
    print_separator("Financial Ratio Calculation", "-")

    # Get matched concepts and their demo values
    current_assets_concept = resolution.get_concept('current_assets')
    current_liab_concept = resolution.get_concept('current_liabilities')

    current_assets_value = DEMO_FACT_VALUES.get(current_assets_concept) if current_assets_concept else None
    current_liab_value = DEMO_FACT_VALUES.get(current_liab_concept) if current_liab_concept else None

    print(f"\n  CURRENT RATIO")
    print(f"  {'='*50}")
    print(f"\n  Formula: Current Assets / Current Liabilities")
    print()
    print(f"  Numerator (Current Assets):")
    print(f"    Matched Concept: {current_assets_concept or 'NOT RESOLVED'}")
    if current_assets_value:
        print(f"    Value: ${current_assets_value:,.0f} thousand")

    print()
    print(f"  Denominator (Current Liabilities):")
    print(f"    Matched Concept: {current_liab_concept or 'NOT RESOLVED'}")
    if current_liab_value:
        print(f"    Value: ${current_liab_value:,.0f} thousand")

    print()
    if current_assets_value and current_liab_value:
        ratio = current_assets_value / current_liab_value
        print(f"  RESULT: {ratio:.2f}")
        print()
        print(f"  Interpretation: {interpret_current_ratio(ratio)}")

        # Confidence assessment
        assets_conf = resolution.get_confidence('current_assets')
        liab_conf = resolution.get_confidence('current_liabilities')
        if assets_conf == Confidence.HIGH and liab_conf == Confidence.HIGH:
            print(f"  Calculation Confidence: HIGH")
        else:
            print(f"  Calculation Confidence: MEDIUM (component confidence varies)")
    else:
        print(f"  RESULT: Cannot calculate - missing data")

    # Summary
    print_separator("Demo Complete")
    print("\n  The matching engine successfully:")
    print("    [OK] Loaded component definitions from dictionary/")
    print("    [OK] Matched concepts using label, hierarchy, and calculation rules")
    print("    [OK] Calculated financial ratio from matched components")
    print()
    print("  To analyze real filings:")
    print("    1. Run the mapper module on parsed XBRL filings")
    print("    2. Ensure output is at: /mnt/map_pro/mapper/mapped_statements/")
    print("    3. Run this script again")
    print()

    return 0


def analyze_parsed_filing(filing: ParsedFilingEntry, config: ConfigLoader) -> None:
    """Analyze a parsed filing (when mapped data not available)."""
    print(f"\n  Loading parsed filing: {filing.company} / {filing.form} / {filing.date}...")

    reader = ParsedReader()
    parsed = reader.read_parsed_filing(filing)

    if not parsed:
        print("  [ERROR] Could not read parsed filing")
        return

    print(f"  Loaded {len(parsed.facts)} facts")

    # Convert to concepts
    print("  Converting facts to concept metadata...")
    concepts = []
    seen_concepts = set()

    for fact in parsed.facts:
        if not fact.concept:
            continue

        qname = fact.concept
        if qname in seen_concepts:
            continue
        seen_concepts.add(qname)

        if ':' in qname:
            prefix, local_name = qname.split(':', 1)
        else:
            prefix = ''
            local_name = qname

        labels = {}
        if hasattr(fact, 'label') and fact.label:
            labels['standard'] = fact.label

        concept = ConceptMetadata(
            qname=qname,
            local_name=local_name,
            prefix=prefix,
            labels=labels,
            period_type='instant' if getattr(fact, 'is_instant', True) else 'duration',
            is_abstract=False,
        )
        concepts.append(concept)

    print(f"  Created {len(concepts)} unique concepts")

    if not concepts:
        print("  [ERROR] No concepts extracted")
        return

    # Run matching
    print("  Initializing matching engine...")
    try:
        coordinator = MatchingCoordinator()
        components = coordinator.get_all_components()
        print(f"  Loaded {len(components)} component definitions")
    except Exception as e:
        print(f"  [ERROR] Failed to initialize matcher: {e}")
        return

    print("  Building concept index...")
    concept_index = coordinator.build_index(concepts)
    print(f"  Indexed {len(concept_index)} concepts")

    print("  Resolving components...")
    resolution = coordinator.resolve_all(
        concept_index=concept_index,
        filing_id=f"{filing.market}_{filing.company}_{filing.form}_{filing.date}"
    )
    print(f"  Resolved {len(resolution.resolved)}/{len(components)} components")

    # Display results
    print_separator(f"Analysis: {filing.company}")

    print(f"\n  Filing: {filing.market.upper()} / {filing.form} / {filing.date}")
    print(f"  Source: Parsed Filing")
    print(f"  Concepts: {len(concepts)}")
    print(f"  Components Resolved: {len(resolution.resolved)}/{len(resolution.matches)}")
    print(f"  High Confidence Rate: {resolution.high_confidence_rate:.1f}%")

    print_separator("Component Resolution", "-")

    for component_id, match_result in resolution.matches.items():
        status = "[OK]" if match_result.is_matched else "[--]"
        concept = match_result.matched_concept or "Not matched"
        conf = match_result.confidence.value.upper() if match_result.is_matched else "-"

        print(f"\n  {status} {component_id}")
        print(f"      Matched: {concept}")
        if match_result.is_matched:
            print(f"      Score: {match_result.total_score} | Confidence: {conf}")

    print_separator("Analysis Complete")


def main() -> int:
    """Main entry point."""
    print_separator("Ratio Check - Dynamic Concept Matching Engine")

    # Setup
    setup_logging(verbose=False)

    print("\n  Initializing...")

    try:
        config = ConfigLoader()
    except Exception as e:
        print(f"  [ERROR] Failed to load configuration: {e}")
        return 1

    # Discover filings from all sources
    print("  Discovering filings from all data sources...")

    options = discover_all_filings(config)

    if not options:
        print("\n  No filings found in any data source.")
        print()
        print("-" * 60)
        demo_choice = input("  Run in DEMO mode with sample data? (y/n): ").strip().lower()
        if demo_choice == 'y':
            return run_demo_mode()
        else:
            print("\n  Goodbye!")
            return 0

    # Main loop
    while True:
        # Display menu
        display_filing_menu(options)

        # Get user selection
        selection = get_user_selection(options)

        if selection is None:
            print("\n  Goodbye!")
            return 0

        if selection == 'demo':
            run_demo_mode()
            print()
            again = input("  Continue with real filings? (y/n): ").strip().lower()
            if again != 'y':
                return 0
            continue

        if selection == 'refresh':
            options = discover_all_filings(config)
            continue

        # Analyze selected filing based on source
        if selection.source == 'mapped':
            analyze_filing(selection.entry)
        else:
            analyze_parsed_filing(selection.entry, config)

        # Ask to continue
        print()
        again = input("  Analyze another filing? (y/n): ").strip().lower()
        if again != 'y':
            print("\n  Goodbye!")
            return 0


if __name__ == "__main__":
    sys.exit(main())
