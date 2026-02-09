#!/usr/bin/env python3
# Path: examples/custom_validator.py
"""
Custom Validator Example

This example demonstrates how to create custom validation rules
that check data quality and business logic.

What this example shows:
- Creating custom validation functions
- Implementing business-specific rules
- Generating validation reports
- Data quality checks

Use cases:
- Industry-specific validation rules
- Company-specific compliance checks
- Custom data quality rules
- Regulatory requirements

Usage:
    python examples/custom_validator.py path/to/filing.xml
"""

import sys
from pathlib import Path
from decimal import Decimal, InvalidOperation

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from xbrl_parser.orchestrator import XBRLParser
from xbrl_parser.models.parsed_filing import ParsedFiling


# ============================================================================
# CUSTOM VALIDATION FUNCTIONS
# ============================================================================

def validate_revenue_reasonableness(
    filing: ParsedFiling,
    min_revenue: float = 0,
    max_revenue: float = 1e12
) -> list[dict[str, any]]:
    """
    Validate that revenue figures are within reasonable ranges.
    
    This is an example of a business rule validator.
    
    Args:
        filing: Parsed filing
        min_revenue: Minimum reasonable revenue
        max_revenue: Maximum reasonable revenue
        
    Returns:
        list of validation issues
    """
    issues = []
    revenue_keywords = ['revenue', 'sales']
    
    for fact in filing.instance.facts:
        # Check if this is a revenue fact
        is_revenue = any(kw in fact.concept.lower() for kw in revenue_keywords)
        
        if is_revenue and fact.unit_ref:
            try:
                # Try to convert to decimal
                value_str = str(fact.value).replace(',', '').strip()
                
                # Skip non-numeric values
                if not value_str or not value_str[0].isdigit():
                    continue
                
                value = float(value_str)
                
                # Check reasonableness
                if value < min_revenue:
                    issues.append({
                        'type': 'revenue_below_minimum',
                        'severity': 'WARNING',
                        'concept': fact.concept,
                        'value': value,
                        'message': f"Revenue below minimum: {value:,.0f}"
                    })
                
                elif value > max_revenue:
                    issues.append({
                        'type': 'revenue_exceeds_maximum',
                        'severity': 'WARNING',
                        'concept': fact.concept,
                        'value': value,
                        'message': f"Revenue exceeds maximum: {value:,.0f}"
                    })
            
            except (ValueError, InvalidOperation):
                # Skip non-numeric values
                pass
    
    return issues


def validate_required_concepts(
    filing: ParsedFiling,
    required_concepts: list[str]
) -> list[dict[str, any]]:
    """
    Validate that required concepts are present in the filing.
    
    This is an example of a completeness validator.
    
    Args:
        filing: Parsed filing
        required_concepts: list of required concept keywords
        
    Returns:
        list of validation issues
    """
    issues = []
    
    # Get all concepts in filing (case-insensitive)
    filing_concepts = {fact.concept.lower() for fact in filing.instance.facts}
    
    # Check each required concept
    for required in required_concepts:
        # Check for partial match
        found = any(required.lower() in concept for concept in filing_concepts)
        
        if not found:
            issues.append({
                'type': 'missing_required_concept',
                'severity': 'ERROR',
                'concept': required,
                'message': f"Required concept missing: {required}"
            })
    
    return issues


def validate_date_consistency(filing: ParsedFiling) -> list[dict[str, any]]:
    """
    Validate date consistency across contexts.
    
    This is an example of a structural validator.
    
    Args:
        filing: Parsed filing
        
    Returns:
        list of validation issues
    """
    issues = []
    
    for ctx_id, context in filing.instance.contexts.items():
        period = context.period
        
        # Check duration periods
        if period.start_date and period.end_date:
            if period.start_date >= period.end_date:
                issues.append({
                    'type': 'invalid_period',
                    'severity': 'ERROR',
                    'context': ctx_id,
                    'start_date': str(period.start_date),
                    'end_date': str(period.end_date),
                    'message': f"Invalid period in {ctx_id}: start >= end"
                })
    
    return issues


def validate_unit_consistency(filing: ParsedFiling) -> list[dict[str, any]]:
    """
    Validate that similar concepts use consistent units.
    
    This is an example of a semantic validator.
    
    Args:
        filing: Parsed filing
        
    Returns:
        list of validation issues
    """
    issues = []
    
    # Group facts by concept
    concept_units = {}
    
    for fact in filing.instance.facts:
        if fact.unit_ref:
            # Get base concept name (without prefix)
            base_concept = fact.concept.split(':')[-1]
            
            if base_concept not in concept_units:
                concept_units[base_concept] = set()
            
            concept_units[base_concept].add(fact.unit_ref)
    
    # Check for concepts with multiple units
    for concept, units in concept_units.items():
        if len(units) > 1:
            issues.append({
                'type': 'inconsistent_units',
                'severity': 'WARNING',
                'concept': concept,
                'units': list(units),
                'message': f"Concept {concept} uses multiple units: {', '.join(units)}"
            })
    
    return issues


def validate_numeric_precision(filing: ParsedFiling) -> list[dict[str, any]]:
    """
    Validate numeric fact precision.
    
    Args:
        filing: Parsed filing
        
    Returns:
        list of validation issues
    """
    issues = []
    
    for fact in filing.instance.facts:
        # Check numeric facts with decimals
        if fact.unit_ref and fact.decimals:
            try:
                decimals = int(fact.decimals)
                
                # Flag very high precision (might be data error)
                if decimals > 6:
                    issues.append({
                        'type': 'excessive_precision',
                        'severity': 'INFO',
                        'concept': fact.concept,
                        'decimals': decimals,
                        'message': f"Unusually high precision: {decimals} decimals"
                    })
            except ValueError:
                pass
    
    return issues


# ============================================================================
# VALIDATION REPORT GENERATOR
# ============================================================================

def generate_validation_report(
    filing: ParsedFiling,
    all_issues: list[dict[str, any]]
) -> str:
    """
    Generate validation report.
    
    Args:
        filing: Parsed filing
        all_issues: All validation issues
        
    Returns:
        Report text
    """
    lines = []
    
    lines.append("=" * 70)
    lines.append("CUSTOM VALIDATION REPORT")
    lines.append("=" * 70)
    lines.append("")
    
    lines.append(f"Filing: {filing.metadata.filing_id}")
    lines.append(f"Facts: {len(filing.instance.facts):,}")
    lines.append(f"Contexts: {len(filing.instance.contexts):,}")
    lines.append("")
    
    # Count by severity
    by_severity = {}
    for issue in all_issues:
        severity = issue['severity']
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(issue)
    
    lines.append(f"TOTAL ISSUES: {len(all_issues)}")
    lines.append("")
    
    # Show by severity
    for severity in ['ERROR', 'WARNING', 'INFO']:
        if severity in by_severity:
            issues = by_severity[severity]
            lines.append(f"{severity}: {len(issues)}")
            lines.append("-" * 70)
            
            for i, issue in enumerate(issues, 1):
                lines.append(f"{i}. {issue['message']}")
                lines.append(f"   Type: {issue['type']}")
                
                # Add relevant details
                for key, value in issue.items():
                    if key not in ['type', 'severity', 'message']:
                        lines.append(f"   {key}: {value}")
                lines.append("")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)


# ============================================================================
# MAIN EXAMPLE
# ============================================================================

def main():
    """Demonstrate custom validation."""
    
    # Get filing path
    if len(sys.argv) < 2:
        print("Usage: python custom_validator.py <path_to_filing>")
        sys.exit(1)
    
    filing_path = Path(sys.argv[1])
    
    if not filing_path.exists():
        print(f"Error: File not found: {filing_path}")
        sys.exit(1)
    
    print("=" * 70)
    print("CUSTOM VALIDATOR EXAMPLE")
    print("=" * 70)
    print(f"\nFiling: {filing_path}")
    print()
    
    # Parse filing
    print("Parsing filing...")
    parser = XBRLParser()
    result = parser.parse(filing_path)
    
    print(f"✓ Parsed: {len(result.instance.facts):,} facts")
    print()
    
    # ========================================================================
    # DEFINE VALIDATION RULES
    # ========================================================================
    print("=" * 70)
    print("VALIDATION RULES")
    print("=" * 70)
    
    print("\n1. Revenue Reasonableness")
    print("   Checks: Revenue within 0 to 1 trillion")
    
    print("\n2. Required Concepts")
    print("   Checks: Presence of key financial concepts")
    
    print("\n3. Date Consistency")
    print("   Checks: Period start < end dates")
    
    print("\n4. Unit Consistency")
    print("   Checks: Concepts use consistent units")
    
    print("\n5. Numeric Precision")
    print("   Checks: Reasonable decimal precision")
    
    print()
    
    # ========================================================================
    # RUN CUSTOM VALIDATION
    # ========================================================================
    print("=" * 70)
    print("RUNNING CUSTOM VALIDATION")
    print("=" * 70)
    
    all_issues = []
    
    # Run each validator
    print("\n1. Revenue Reasonableness Check...")
    issues = validate_revenue_reasonableness(result)
    print(f"   ✓ Found {len(issues)} issues")
    all_issues.extend(issues)
    
    print("\n2. Required Concepts Check...")
    required = ['Assets', 'Liabilities', 'Equity', 'Revenue']
    issues = validate_required_concepts(result, required)
    print(f"   ✓ Found {len(issues)} issues")
    all_issues.extend(issues)
    
    print("\n3. Date Consistency Check...")
    issues = validate_date_consistency(result)
    print(f"   ✓ Found {len(issues)} issues")
    all_issues.extend(issues)
    
    print("\n4. Unit Consistency Check...")
    issues = validate_unit_consistency(result)
    print(f"   ✓ Found {len(issues)} issues")
    all_issues.extend(issues)
    
    print("\n5. Numeric Precision Check...")
    issues = validate_numeric_precision(result)
    print(f"   ✓ Found {len(issues)} issues")
    all_issues.extend(issues)
    
    print()
    
    # ========================================================================
    # DISPLAY RESULTS
    # ========================================================================
    print("=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    
    print(f"\nTotal issues found: {len(all_issues)}")
    
    # Group by severity
    by_severity = {}
    for issue in all_issues:
        severity = issue['severity']
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(issue)
    
    for severity in ['ERROR', 'WARNING', 'INFO']:
        if severity in by_severity:
            issues = by_severity[severity]
            print(f"\n{severity}: {len(issues)}")
            
            # Show first 3
            for i, issue in enumerate(issues[:3], 1):
                print(f"  {i}. {issue['message']}")
            
            if len(issues) > 3:
                print(f"  ... and {len(issues) - 3} more")
    
    print()
    
    # ========================================================================
    # SAVE VALIDATION REPORT
    # ========================================================================
    print("=" * 70)
    print("GENERATING REPORT")
    print("=" * 70)
    
    # Create report
    report = generate_validation_report(result, all_issues)
    
    # Save to file
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    
    report_path = output_dir / "custom_validation_report.txt"
    report_path.write_text(report, encoding='utf-8')
    
    print(f"\n✓ Validation report saved: {report_path}")
    print()
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("=" * 70)
    print("CUSTOM VALIDATOR SUMMARY")
    print("=" * 70)
    
    print("\nKey takeaways:")
    print("  ✓ Easy to create custom validation rules")
    print("  ✓ Simple function-based approach")
    print("  ✓ Flexible validation logic")
    print("  ✓ Custom report generation")
    
    print("\nValidation types demonstrated:")
    print("  1. Business rule - Revenue reasonableness")
    print("  2. Completeness - Required concepts")
    print("  3. Structural - Date consistency")
    print("  4. Semantic - Unit consistency")
    print("  5. Data quality - Numeric precision")
    
    print("\nNext steps:")
    print("  - Create validators for your specific needs")
    print("  - Add industry-specific rules")
    print("  - Integrate with your QA process")
    print("  - Generate compliance reports")
    print()


if __name__ == "__main__":
    main()