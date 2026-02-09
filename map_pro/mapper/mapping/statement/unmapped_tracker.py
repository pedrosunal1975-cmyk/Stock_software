# Path: mapping/statement/unmapped_tracker.py
"""
Unmapped Facts Tracker

Tracks facts that didn't appear in any presentation network.
Investigates WHY they weren't mapped.

WATER PARADIGM:
- Reports facts AS-IS without judgment
- Investigates reasons (not in presentation, no matching context, etc.)
- Provides actionable insights for investigation

RESPONSIBILITY:
- Identify facts not appearing in any statement
- Categorize reasons for being unmapped
- Generate investigation reports
"""

import logging
from typing import Optional
from dataclasses import dataclass, field
from collections import Counter

from ...loaders.parser_output import ParsedFiling
from ...mapping.statement.models import StatementSet


@dataclass
class UnmappedFact:
    """A fact that wasn't mapped to any statement."""
    concept: str
    value: any
    context_ref: str
    unit_ref: Optional[str]
    decimals: Optional[str]
    reason: str  # Why it wasn't mapped
    investigation_notes: list[str] = field(default_factory=list)


@dataclass
class UnmappedFactsReport:
    """Report of unmapped facts."""
    total_facts_in_filing: int
    total_facts_mapped: int
    total_facts_unmapped: int
    coverage_rate: float  # Percentage mapped
    
    unmapped_facts: list[UnmappedFact] = field(default_factory=list)
    reasons_summary: dict[str, int] = field(default_factory=dict)
    concepts_never_mapped: set[str] = field(default_factory=set)
    
    @property
    def unmapped_rate(self) -> float:
        """Percentage unmapped."""
        if self.total_facts_in_filing == 0:
            return 0.0
        return (self.total_facts_unmapped / self.total_facts_in_filing) * 100


class UnmappedFactsTracker:
    """
    Tracks and investigates facts that weren't mapped to statements.
    
    Water paradigm: Reports what happened without making assumptions
    about what "should" have happened.
    
    Example:
        tracker = UnmappedFactsTracker()
        report = tracker.analyze(parsed_filing, statement_set)
        
        print(f"Unmapped: {report.unmapped_rate:.1f}%")
        for fact in report.unmapped_facts[:10]:
            print(f"{fact.concept}: {fact.reason}")
    """
    
    def __init__(self):
        """Initialize unmapped facts tracker."""
        self.logger = logging.getLogger('mapping.statement.unmapped_tracker')
        self.logger.info("UnmappedFactsTracker initialized")
    
    def analyze(
        self,
        parsed_filing: ParsedFiling,
        statement_set: StatementSet
    ) -> UnmappedFactsReport:
        """
        Analyze which facts were not mapped and why.
        
        Args:
            parsed_filing: Original parsed filing with all facts
            statement_set: Statement set with mapped facts
            
        Returns:
            UnmappedFactsReport with analysis
        """
        total_facts = len(parsed_filing.facts)
        
        # Collect all mapped fact identifiers
        mapped_fact_ids = set()
        for statement in statement_set.statements:
            for fact in statement.facts:
                # Create unique identifier: concept + context + value
                fact_id = self._create_fact_id(
                    fact.concept,
                    fact.context_ref,
                    fact.value
                )
                mapped_fact_ids.add(fact_id)
        
        # Find unmapped facts
        unmapped_facts = []
        for fact in parsed_filing.facts:
            fact_name = self._get_fact_attr(fact, 'name')
            fact_context = self._get_fact_attr(fact, 'context_ref')
            fact_value = self._get_fact_attr(fact, 'value')
            
            fact_id = self._create_fact_id(fact_name, fact_context, fact_value)
            
            if fact_id not in mapped_fact_ids:
                # Investigate why
                reason, notes = self._investigate_unmapped(
                    fact,
                    parsed_filing,
                    statement_set
                )
                
                unmapped_fact = UnmappedFact(
                    concept=fact_name,
                    value=fact_value,
                    context_ref=fact_context,
                    unit_ref=self._get_fact_attr(fact, 'unit_ref'),
                    decimals=self._get_fact_attr(fact, 'decimals'),
                    reason=reason,
                    investigation_notes=notes
                )
                unmapped_facts.append(unmapped_fact)
        
        # Calculate statistics
        total_mapped = len(mapped_fact_ids)
        total_unmapped = len(unmapped_facts)
        coverage = (total_mapped / total_facts * 100) if total_facts > 0 else 0
        
        # Summarize reasons
        reasons_summary = Counter(f.reason for f in unmapped_facts)
        
        # Identify concepts that never got mapped
        all_concepts = set(self._get_fact_attr(f, 'name') for f in parsed_filing.facts)
        mapped_concepts = set(f.concept for s in statement_set.statements for f in s.facts)
        never_mapped = all_concepts - mapped_concepts
        
        report = UnmappedFactsReport(
            total_facts_in_filing=total_facts,
            total_facts_mapped=total_mapped,
            total_facts_unmapped=total_unmapped,
            coverage_rate=coverage,
            unmapped_facts=unmapped_facts,
            reasons_summary=dict(reasons_summary),
            concepts_never_mapped=never_mapped
        )
        
        # Log summary
        self.logger.info(
            f"Unmapped facts analysis: {total_unmapped}/{total_facts} facts unmapped "
            f"({report.unmapped_rate:.1f}%)"
        )
        self.logger.info(f"Reasons breakdown: {dict(reasons_summary)}")
        self.logger.info(f"Concepts never mapped: {len(never_mapped)}")
        
        return report
    
    def _investigate_unmapped(
        self,
        fact,
        parsed_filing: ParsedFiling,
        statement_set: StatementSet
    ) -> tuple[str, list[str]]:
        """
        Investigate why a fact wasn't mapped.
        
        Args:
            fact: The unmapped fact
            parsed_filing: Parsed filing
            statement_set: Statement set
            
        Returns:
            Tuple of (reason, investigation_notes)
        """
        notes = []
        fact_name = self._get_fact_attr(fact, 'name')
        
        # Check if concept appears in ANY presentation hierarchy
        concept_in_presentation = False
        for statement in statement_set.statements:
            if self._concept_in_hierarchy(fact_name, statement.hierarchy):
                concept_in_presentation = True
                notes.append(f"Concept exists in network: {statement.role_uri}")
                break
        
        if not concept_in_presentation:
            reason = "not_in_presentation"
            notes.append("Concept not declared in any presentation network")
            notes.append("Likely a supporting fact not intended for display")
            return reason, notes
        
        # If concept is in presentation but fact wasn't mapped,
        # it's likely a context/period mismatch
        reason = "context_mismatch"
        notes.append("Concept exists in presentation hierarchy")
        notes.append("But this specific fact instance didn't match")
        notes.append("Possible causes: different period, different dimensions, abstract concept")
        
        return reason, notes
    
    def _concept_in_hierarchy(self, concept: str, hierarchy: dict[str, any]) -> bool:
        """
        Check if concept appears anywhere in hierarchy.
        
        Args:
            concept: Concept name
            hierarchy: Hierarchy dictionary
            
        Returns:
            True if concept found in hierarchy
        """
        # Check roots
        if concept in hierarchy.get('roots', []):
            return True
        
        # Check all concepts in children dict
        if concept in hierarchy.get('children', {}):
            return True
        
        # Check all concepts in parents dict
        if concept in hierarchy.get('parents', {}):
            return True
        
        return False
    
    @staticmethod
    def _create_fact_id(concept: str, context: str, value: any) -> str:
        """
        Create unique fact identifier.
        
        Args:
            concept: Concept name
            context: Context reference
            value: Fact value
            
        Returns:
            Unique identifier string
        """
        return f"{concept}|{context}|{str(value)}"
    
    @staticmethod
    def _get_fact_attr(fact, attr, default=None):
        """Get fact attribute from dict or object format."""
        if isinstance(fact, dict):
            return fact.get(attr, default)
        else:
            return getattr(fact, attr, default)
    
    def print_report(self, report: UnmappedFactsReport) -> None:
        """
        Print unmapped facts report.
        
        Args:
            report: UnmappedFactsReport to print
        """
        print("\n" + "="*80)
        print("UNMAPPED FACTS ANALYSIS")
        print("="*80)
        
        print(f"\nOVERVIEW:")
        print(f"  Total facts in filing: {report.total_facts_in_filing}")
        print(f"  Facts mapped: {report.total_facts_mapped} ({report.coverage_rate:.1f}%)")
        print(f"  Facts unmapped: {report.total_facts_unmapped} ({report.unmapped_rate:.1f}%)")
        
        print(f"\nREASONS FOR UNMAPPED FACTS:")
        for reason, count in sorted(report.reasons_summary.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}")
        
        print(f"\nCONCEPTS NEVER MAPPED: {len(report.concepts_never_mapped)}")
        for i, concept in enumerate(sorted(report.concepts_never_mapped)[:20]):
            print(f"  {i+1}. {concept}")
        if len(report.concepts_never_mapped) > 20:
            print(f"  ... and {len(report.concepts_never_mapped) - 20} more")
        
        print(f"\nSAMPLE UNMAPPED FACTS (first 10):")
        for i, fact in enumerate(report.unmapped_facts[:10]):
            print(f"\n  {i+1}. {fact.concept}")
            print(f"     Value: {fact.value}")
            print(f"     Context: {fact.context_ref}")
            print(f"     Reason: {fact.reason}")
            for note in fact.investigation_notes[:2]:
                print(f"     - {note}")
        
        print("\n" + "="*80)


__all__ = [
    'UnmappedFactsTracker',
    'UnmappedFactsReport',
    'UnmappedFact',
]