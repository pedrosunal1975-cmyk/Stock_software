#!/usr/bin/env python3
# Path: examples/basic_parsing.py
"""
Basic XBRL Parsing Example

This example demonstrates the most common use case: parsing an XBRL filing
and extracting key information.

What this example shows:
- How to parse an XBRL filing
- How to access facts, contexts, and units
- How to check for errors
- How to get basic statistics

Requirements:
- XBRL filing (XML or HTML for iXBRL)
- Internet connection (for taxonomy downloads)

Usage:
    python examples/basic_parsing.py path/to/filing.xml
    
    # Or with environment variable
    XBRL_FILE=path/to/filing.xml python examples/basic_parsing.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from xbrl_parser.orchestrator import XBRLParser
from xbrl_parser.models.error import ErrorSeverity
from ..output import ReportGenerator


def main():
    """Parse an XBRL filing and display key information."""
    
    # Get filing path from arguments or environment
    if len(sys.argv) > 1:
        filing_path = Path(sys.argv[1])
    elif os.environ.get('XBRL_FILE'):
        filing_path = Path(os.environ['XBRL_FILE'])
    else:
        print("Usage: python basic_parsing.py <path_to_filing>")
        print("   or: XBRL_FILE=path/to/filing.xml python basic_parsing.py")
        sys.exit(1)
    
    # Verify file exists
    if not filing_path.exists():
        print(f"Error: File not found: {filing_path}")
        sys.exit(1)
    
    print("=" * 70)
    print("XBRL BASIC PARSING EXAMPLE")
    print("=" * 70)
    print(f"\nParsing: {filing_path}")
    print()
    
    # Initialize parser with default settings
    parser = XBRLParser()
    
    # Parse the filing
    try:
        result = parser.parse(filing_path)
    except Exception as e:
        print(f"ERROR: Parsing failed: {e}")
        sys.exit(1)
    
    print("Parsing complete!")
    print()
    
    # ========================================================================
    # DISPLAY FILING METADATA
    # ========================================================================
    print("=" * 70)
    print("FILING METADATA")
    print("=" * 70)
    
    metadata = result.metadata
    print(f"Filing ID:       {metadata.filing_id}")
    print(f"Company:         {metadata.company_name or 'N/A'}")
    print(f"Entity ID:       {metadata.entity_identifier}")
    print(f"Document Type:   {metadata.document_type or 'N/A'}")
    print(f"Filing Date:     {metadata.filing_date or 'N/A'}")
    print(f"Period End:      {metadata.period_end_date or 'N/A'}")
    print(f"Market:          {metadata.market or 'N/A'}")
    print()
    
    # ========================================================================
    # DISPLAY DATA COUNTS
    # ========================================================================
    print("=" * 70)
    print("DATA SUMMARY")
    print("=" * 70)
    
    print(f"Total Facts:     {len(result.instance.facts):,}")
    print(f"Contexts:        {len(result.instance.contexts):,}")
    print(f"Units:           {len(result.instance.units):,}")
    print(f"Concepts:        {len(result.taxonomy.concepts):,}")
    print()
    
    # ========================================================================
    # DISPLAY ERROR SUMMARY
    # ========================================================================
    print("=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    
    severity_counts = result.errors.count_by_severity()
    critical = severity_counts.get(ErrorSeverity.CRITICAL, 0)
    errors = severity_counts.get(ErrorSeverity.ERROR, 0)
    warnings = severity_counts.get(ErrorSeverity.WARNING, 0)
    
    print(f"Critical:        {critical}")
    print(f"Errors:          {errors}")
    print(f"Warnings:        {warnings}")
    
    if critical > 0 or errors > 0:
        print("\nSample Errors (first 5):")
        error_list = result.errors.get_by_severity(ErrorSeverity.ERROR)
        if not error_list:
            error_list = result.errors.get_by_severity(ErrorSeverity.CRITICAL)
        
        for i, error in enumerate(error_list[:5], 1):
            print(f"  {i}. {error.message}")
            if error.source_file:
                print(f"     File: {error.source_file}")
    print()
    
    # ========================================================================
    # DISPLAY SAMPLE FACTS
    # ========================================================================
    print("=" * 70)
    print("SAMPLE FACTS (First 10)")
    print("=" * 70)
    
    for i, fact in enumerate(result.instance.facts[:10], 1):
        # Format value for display
        value = fact.value
        if len(str(value)) > 50:
            value = str(value)[:47] + "..."
        
        print(f"\n{i}. {fact.concept}")
        print(f"   Value:       {value}")
        print(f"   Context:     {fact.context_ref}")
        print(f"   Unit:        {fact.unit_ref or 'N/A'}")
        print(f"   Type:        {fact.fact_type.value if fact.fact_type else 'N/A'}")
    
    print()
    
    # ========================================================================
    # DEMONSTRATE FACT FILTERING
    # ========================================================================
    print("=" * 70)
    print("FACT FILTERING EXAMPLE")
    print("=" * 70)
    
    # Example: Find all revenue-related facts
    revenue_facts = [
        f for f in result.instance.facts 
        if 'revenue' in f.concept.lower()
    ]
    
    print(f"\nFacts with 'revenue' in concept: {len(revenue_facts)}")
    
    if revenue_facts:
        print("\nRevenue Facts:")
        for i, fact in enumerate(revenue_facts[:5], 1):
            print(f"  {i}. {fact.concept}: {fact.value}")
    
    # Example: Find facts for a specific context
    if result.instance.contexts:
        first_context_id = next(iter(result.instance.contexts.keys()))
        context_facts = [
            f for f in result.instance.facts
            if f.context_ref == first_context_id
        ]
        print(f"\nFacts for context '{first_context_id}': {len(context_facts)}")
    
    print()
    
    # ========================================================================
    # GENERATE REPORT (OPTIONAL)
    # ========================================================================
    print("=" * 70)
    print("REPORT GENERATION")
    print("=" * 70)
    
    # Generate text report
    report_generator = ReportGenerator()
    summary = report_generator.generate_summary(result)
    
    # Save to file
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    
    report_path = output_dir / f"{metadata.filing_id}_summary.txt"
    report_path.write_text(summary, encoding='utf-8')
    
    print(f"\nSummary report saved: {report_path}")
    print()
    
    # ========================================================================
    # FINAL STATUS
    # ========================================================================
    print("=" * 70)
    print("PARSING COMPLETE")
    print("=" * 70)
    
    if critical == 0 and errors == 0:
        print("\nStatus: SUCCESS - No errors found")
    elif critical > 0:
        print(f"\nStatus: CRITICAL - {critical} critical errors found")
    elif errors > 0:
        print(f"\nStatus: WARNING - {errors} errors found (but parsing succeeded)")
    
    print()
    print("Next steps:")
    print("  - Access facts: result.instance.facts")
    print("  - Access contexts: result.instance.contexts")
    print("  - Access taxonomy: result.taxonomy.concepts")
    print("  - Export data: Use output.DataExtractor")
    print("  - Generate reports: Use output.ReportGenerator")
    print()


if __name__ == "__main__":
    main()