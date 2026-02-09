# Path: output/parsed_report/report_generator.py
"""
Report Generation

Generate human-readable reports and summaries from parsed XBRL filings.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
from collections import Counter

from xbrl_parser.models.parsed_filing import ParsedFiling
from xbrl_parser.models.error import ErrorSeverity


class ReportGenerator:
    """
    Generate reports from parsed XBRL filings.
    
    Creates human-readable reports in various formats.
    """
    
    def __init__(self):
        """Initialize report generator."""
        self.logger = logging.getLogger(__name__)
    
    def generate_summary(self, filing: ParsedFiling, parse_time: Optional[float] = None) -> str:
        """
        Generate executive summary of filing with analytics.
        
        Args:
            filing: Parsed filing
            parse_time: Optional parsing time in seconds
            
        Returns:
            Enhanced summary text
        """
        lines = []
        metadata = filing.metadata
        
        lines.append("=" * 70)
        lines.append("XBRL FILING SUMMARY")
        lines.append("=" * 70)
        lines.append("")
        
        # Filing identification
        lines.append("FILING IDENTIFICATION")
        lines.append("-" * 70)
        lines.append(f"Filing ID:       {metadata.filing_id}")
        lines.append(f"Company:         {metadata.company_name or 'N/A'}")
        lines.append(f"Entity ID:       {metadata.entity_identifier}")
        lines.append(f"Document Type:   {metadata.document_type or 'N/A'}")
        lines.append(f"Filing Date:     {metadata.filing_date or 'N/A'}")
        lines.append(f"Period End:      {metadata.period_end_date or 'N/A'}")
        lines.append(f"Market:          {metadata.market or 'N/A'}")
        lines.append("")
        
        # Data summary
        lines.append("DATA SUMMARY")
        lines.append("-" * 70)
        lines.append(f"Total Facts:     {len(filing.instance.facts):,}")
        lines.append(f"Contexts:        {len(filing.instance.contexts):,}")
        lines.append(f"Units:           {len(filing.instance.units):,}")
        lines.append(f"Concepts:        {len(filing.taxonomy.concepts):,}")
        lines.append("")
        
        # Fact analysis
        lines.append("FACT ANALYSIS")
        lines.append("-" * 70)
        
        # By type
        type_counts = {}
        monetary_count = 0
        with_footnotes = 0
        nil_count = 0
        
        for fact in filing.instance.facts:
            fact_type = fact.fact_type.value if fact.fact_type else "UNKNOWN"
            type_counts[fact_type] = type_counts.get(fact_type, 0) + 1
            
            # Check if monetary
            if fact.unit_ref and filing.instance.units.get(fact.unit_ref):
                unit = filing.instance.units[fact.unit_ref]
                if unit.is_monetary:
                    monetary_count += 1
            
            # Check footnotes
            if fact.footnote_refs and len(fact.footnote_refs) > 0:
                with_footnotes += 1
            
            # Check nil
            if fact.is_nil:
                nil_count += 1
        
        # Format type breakdown
        type_list = []
        for ftype in ['NUMERIC', 'TEXT', 'BOOLEAN', 'UNKNOWN']:
            if ftype in type_counts:
                type_list.append(f"{ftype}: {type_counts[ftype]:,}")
        
        lines.append(f"By Type:         {' | '.join(type_list)}")
        
        if monetary_count > 0:
            pct = (monetary_count / len(filing.instance.facts) * 100) if len(filing.instance.facts) > 0 else 0
            lines.append(f"Monetary Facts:  {monetary_count:,} ({pct:.0f}%)")
        
        if with_footnotes > 0:
            lines.append(f"With Footnotes:  {with_footnotes:,} facts reference footnotes")
        
        if nil_count > 0:
            pct = (nil_count / len(filing.instance.facts) * 100) if len(filing.instance.facts) > 0 else 0
            lines.append(f"Nil Facts:       {nil_count:,} ({pct:.0f}%)")
        
        lines.append("")
        
        # Top concepts
        lines.append("TOP CONCEPTS (by frequency)")
        lines.append("-" * 70)
        
        concept_counts = Counter(fact.concept for fact in filing.instance.facts)
        top_concepts = concept_counts.most_common(5)
        
        for i, (concept, count) in enumerate(top_concepts, 1):
            # Shorten concept name if too long
            concept_display = concept.split(':')[-1] if ':' in concept else concept
            if len(concept_display) > 40:
                concept_display = concept_display[:37] + "..."
            lines.append(f"{i}. {concept_display:40s} {count:>6,} facts")
        
        lines.append("")
        
        # Context analysis
        lines.append("CONTEXT ANALYSIS")
        lines.append("-" * 70)
        
        instant_count = 0
        duration_count = 0
        all_dates = []
        
        for context in filing.instance.contexts.values():
            if context.period.period_type:
                period_type = context.period.period_type.value.upper()
                if period_type == "INSTANT":
                    instant_count += 1
                    if context.period.instant:
                        all_dates.append(context.period.instant)
                elif period_type == "DURATION":
                    duration_count += 1
                    if context.period.start_date:
                        all_dates.append(context.period.start_date)
                    if context.period.end_date:
                        all_dates.append(context.period.end_date)
        
        lines.append(f"Period Types:    INSTANT: {instant_count:,} | DURATION: {duration_count:,}")
        
        if all_dates:
            min_date = min(all_dates)
            max_date = max(all_dates)
            lines.append(f"Date Range:      {min_date} to {max_date}")
        
        lines.append("")
        
        # Footnotes
        if hasattr(filing.instance, 'footnotes') and filing.instance.footnotes:
            lines.append("FOOTNOTES")
            lines.append("-" * 70)
            lines.append(f"Total:           {len(filing.instance.footnotes):,} footnote(s) extracted")
            lines.append("")
        
        # Validation
        lines.append("VALIDATION")
        lines.append("-" * 70)
        severity_counts = filing.errors.count_by_severity()
        lines.append(f"Errors:          {severity_counts.get(ErrorSeverity.ERROR, 0):,}")
        lines.append(f"Warnings:        {severity_counts.get(ErrorSeverity.WARNING, 0):,}")
        lines.append("")
        
        # Performance (if provided)
        if parse_time is not None:
            lines.append("PERFORMANCE")
            lines.append("-" * 70)
            lines.append(f"Parse Time:      {parse_time:.2f} seconds")
            if parse_time > 0 and len(filing.instance.facts) > 0:
                throughput = len(filing.instance.facts) / parse_time
                lines.append(f"Facts/Second:    {throughput:,.0f}")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def generate_detailed_report(self, filing: ParsedFiling) -> str:
        """
        Generate detailed report with all information.
        
        Args:
            filing: Parsed filing
            
        Returns:
            Detailed report text
        """
        lines = []
        
        # Include summary
        lines.append(self.generate_summary(filing))
        lines.append("")
        lines.append("")
        
        # Fact breakdown
        lines.append("FACT BREAKDOWN BY TYPE")
        lines.append("-" * 70)
        fact_types = {}
        for fact in filing.instance.facts:
            fact_type = fact.fact_type.value if fact.fact_type else "unknown"
            fact_types[fact_type] = fact_types.get(fact_type, 0) + 1
        
        for fact_type, count in sorted(fact_types.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"{fact_type:20s} {count:>10,}")
        lines.append("")
        
        # Error details
        if len(filing.errors.errors) > 0:
            lines.append("ERRORS AND WARNINGS")
            lines.append("-" * 70)
            
            for severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR, ErrorSeverity.WARNING]:
                errors = filing.errors.get_by_severity(severity)
                if errors:
                    lines.append(f"\n{severity.value.upper()}:")
                    for i, error in enumerate(errors[:10], 1):
                        lines.append(f"  {i}. {error.message}")
                        if error.source_file:
                            lines.append(f"     File: {error.source_file}")
                    
                    if len(errors) > 10:
                        lines.append(f"  ... and {len(errors) - 10} more")
            lines.append("")
        
        # Source files
        lines.append("SOURCE FILES")
        lines.append("-" * 70)
        for source_file in filing.metadata.source_files:
            lines.append(f"  - {source_file}")
        lines.append("")
        
        return "\n".join(lines)
    
    def generate_fact_listing(
        self,
        filing: ParsedFiling,
        concept_filter: Optional[str] = None,
        max_facts: int = 100
    ) -> str:
        """
        Generate listing of facts.
        
        Args:
            filing: Parsed filing
            concept_filter: Optional concept name filter
            max_facts: Maximum facts to include
            
        Returns:
            Fact listing text
        """
        lines = []
        
        lines.append("FACT LISTING")
        lines.append("=" * 80)
        lines.append("")
        
        facts = filing.instance.facts
        if concept_filter:
            facts = [f for f in facts if concept_filter.lower() in f.concept.lower()]
            lines.append(f"Filter: {concept_filter}")
            lines.append("")
        
        facts = facts[:max_facts]
        
        for i, fact in enumerate(facts, 1):
            lines.append(f"{i}. {fact.concept}")
            lines.append(f"   Value:       {fact.value}")
            lines.append(f"   Context:     {fact.context_ref}")
            lines.append(f"   Unit:        {fact.unit_ref or 'N/A'}")
            lines.append(f"   Type:        {fact.fact_type.value if fact.fact_type else 'N/A'}")
            lines.append("")
        
        if len(filing.instance.facts) > max_facts:
            lines.append(f"... and {len(filing.instance.facts) - max_facts} more facts")
        
        return "\n".join(lines)
    
    def save_text_report(
        self,
        filing: ParsedFiling,
        output_path: Path,
        detailed: bool = True
    ) -> None:
        """
        Save report to text file.
        
        Args:
            filing: Parsed filing
            output_path: Output file path
            detailed: Generate detailed report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if detailed:
            report = self.generate_detailed_report(filing)
        else:
            report = self.generate_summary(filing)
        
        output_path.write_text(report)
        self.logger.info(f"Report saved: {output_path}")


__all__ = ['ReportGenerator']