#!/usr/bin/env python3
# Path: examples/component_reuse.py
"""
Component Reuse Example

Demonstrates using parser components independently for custom workflows.

Note: For iXBRL files (.htm/.html), we first parse with the orchestrator,
then show how to work with the results using individual components.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from xbrl_parser.orchestrator import XBRLParser
from xbrl_parser.foundation.namespace_registry import NamespaceRegistry
from xbrl_parser.foundation.qname import QName


def example_working_with_parsed_data(filing_path):
    """
    Example: Work with parsed data using component methods.
    
    For iXBRL, we parse with orchestrator then manipulate results.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: WORKING WITH PARSED DATA")
    print("=" * 70)
    
    # Parse with orchestrator (handles both XBRL and iXBRL)
    print(f"\nParsing: {filing_path.name}")
    parser = XBRLParser()
    result = parser.parse(filing_path)
    
    print(f"✓ Parsed successfully!")
    print(f"  Facts:    {len(result.instance.facts):,}")
    print(f"  Contexts: {len(result.instance.contexts):,}")
    print(f"  Units:    {len(result.instance.units):,}")
    
    # Now work with the data using component-style access
    print("\nSample contexts (direct access):")
    for i, (ctx_id, context) in enumerate(list(result.instance.contexts.items())[:3], 1):
        print(f"  {i}. {ctx_id}")
        print(f"     Entity: {context.entity.value}")
        print(f"     Period: {context.period.period_type}")
    
    print("\nSample units (direct access):")
    for i, (unit_id, unit) in enumerate(list(result.instance.units.items())[:3], 1):
        print(f"  {i}. {unit_id}: {unit.measures if unit.measures else 'complex'}")
    
    print("\n✓ Use case: Work with parsed data directly")
    
    return result


def example_custom_filtering(result):
    """
    Example: Custom fact filtering and analysis.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: CUSTOM FACT FILTERING")
    print("=" * 70)
    
    # Filter by concept pattern
    revenue_facts = [
        f for f in result.instance.facts 
        if 'revenue' in f.concept.lower()
    ]
    print(f"\nRevenue-related facts: {len(revenue_facts)}")
    
    for i, fact in enumerate(revenue_facts[:5], 1):
        print(f"  {i}. {fact.concept}: {fact.value}")
    
    # Filter by unit
    numeric_facts = [f for f in result.instance.facts if f.unit_ref]
    text_facts = [f for f in result.instance.facts if not f.unit_ref]
    
    print(f"\nFact breakdown:")
    print(f"  Numeric: {len(numeric_facts):,}")
    print(f"  Text:    {len(text_facts):,}")
    
    print("\n✓ Use case: Custom data filtering")


def example_concept_analysis(result):
    """
    Example: Analyze concepts and usage.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: CONCEPT ANALYSIS")
    print("=" * 70)
    
    # Count facts by concept
    concept_counts = {}
    for fact in result.instance.facts:
        concept = fact.concept.split(':')[-1]  # Remove namespace
        concept_counts[concept] = concept_counts.get(concept, 0) + 1
    
    print(f"\nUnique concepts: {len(concept_counts):,}")
    
    # Top concepts
    print("\nTop 10 most used concepts:")
    top = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for i, (concept, count) in enumerate(top, 1):
        print(f"  {i:2d}. {concept:50s} {count:4d} facts")
    
    print("\n✓ Use case: Concept frequency analysis")


def example_namespace_registry():
    """
    Example: Use namespace registry directly.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: NAMESPACE REGISTRY")
    print("=" * 70)
    
    registry = NamespaceRegistry()
    
    print("\nRegistering namespaces...")
    registry.register("us-gaap", "http://fasb.org/us-gaap/2023", "schema.xsd")
    registry.register("dei", "http://xbrl.sec.gov/dei/2023", "dei.xsd")
    
    # Get URIs
    uri1 = registry.get_uri("us-gaap")
    uri2 = registry.get_uri("dei")
    
    print(f"  us-gaap → {uri1}")
    print(f"  dei → {uri2}")
    
    # Create QNames
    qname = QName(uri1, "Assets", "us-gaap")
    print(f"\nQName example: {qname.to_clark_notation()}")
    
    print("\n✓ Use case: Namespace handling in custom XML processing")


def example_custom_export(result):
    """
    Example: Export to custom format.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: CUSTOM EXPORT")
    print("=" * 70)
    
    # Extract balance sheet items
    keywords = ['assets', 'liabilities', 'equity']
    bs_facts = [
        f for f in result.instance.facts
        if any(kw in f.concept.lower() for kw in keywords)
    ]
    
    print(f"\nExtracted {len(bs_facts)} balance sheet facts")
    
    # Custom format
    export_data = []
    for fact in bs_facts[:10]:
        export_data.append({
            'concept': fact.concept.split(':')[-1],
            'value': str(fact.value)[:50],
            'context': fact.context_ref,
            'unit': fact.unit_ref or 'N/A'
        })
    
    print("\nSample export (first 5):")
    for i, item in enumerate(export_data[:5], 1):
        print(f"  {i}. {item['concept']}: {item['value']}")
    
    print("\n✓ Use case: Custom data export formats")


def main():
    if len(sys.argv) < 2:
        print("Usage: python component_reuse.py <path_to_filing>")
        sys.exit(1)
    
    filing_path = Path(sys.argv[1])
    
    if not filing_path.exists():
        print(f"Error: File not found: {filing_path}")
        sys.exit(1)
    
    print("=" * 70)
    print("COMPONENT REUSE EXAMPLES")
    print("=" * 70)
    print(f"\nFiling: {filing_path}")
    
    # Parse once, then demonstrate various component-style operations
    result = example_working_with_parsed_data(filing_path)
    example_custom_filtering(result)
    example_concept_analysis(result)
    example_namespace_registry()
    example_custom_export(result)
    
    # Summary
    print("\n" + "=" * 70)
    print("COMPONENT REUSE SUMMARY")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  ✓ Parse once with orchestrator (handles XBRL & iXBRL)")
    print("  ✓ Work with results using direct component access")
    print("  ✓ Build custom filters and analysis")
    print("  ✓ Use foundation components (NamespaceRegistry, QName)")
    print("  ✓ Export to custom formats")
    print()


if __name__ == "__main__":
    main()
