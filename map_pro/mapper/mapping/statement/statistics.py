# Path: mapping/statement/statistics.py
"""
Statement Building Statistics

Tracks detailed statistics during statement building process.
"""

import logging
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class FilteringStatistics:
    """Statistics about fact filtering."""
    total_candidates: int = 0
    validated_facts: int = 0
    rejected_facts: int = 0
    
    # Rejection reasons
    low_confidence: int = 0
    no_context_match: int = 0
    period_mismatch: int = 0
    dimension_issues: int = 0
    
    # Confidence distribution
    confidence_1_0: int = 0  # Perfect (3/3 sources)
    confidence_0_75: int = 0  # Good (2/3 sources)
    confidence_0_5: int = 0  # Weak (1/3 sources)
    confidence_0_0: int = 0  # No match
    
    def add_validated(self, confidence: float):
        """Record a validated fact."""
        self.validated_facts += 1
        if confidence >= 1.0:
            self.confidence_1_0 += 1
        elif confidence >= 0.75:
            self.confidence_0_75 += 1
        elif confidence >= 0.5:
            self.confidence_0_5 += 1
    
    def add_rejected(self, reason: str):
        """Record a rejected fact."""
        self.rejected_facts += 1
        if 'confidence' in reason.lower():
            self.low_confidence += 1
        elif 'context' in reason.lower():
            self.no_context_match += 1
        elif 'period' in reason.lower():
            self.period_mismatch += 1
        elif 'dimension' in reason.lower():
            self.dimension_issues += 1
    
    @property
    def validation_rate(self) -> float:
        """Percentage of facts that passed validation."""
        if self.total_candidates == 0:
            return 0.0
        return (self.validated_facts / self.total_candidates) * 100


@dataclass
class DimensionalStatistics:
    """Statistics about dimensional facts."""
    total_facts: int = 0
    dimensional_facts: int = 0
    non_dimensional_facts: int = 0
    unique_signatures: int = 0
    signature_counts: dict[str, int] = field(default_factory=dict)
    
    def add_dimensional_fact(self, signature: str):
        """Record a dimensional fact."""
        self.dimensional_facts += 1
        self.signature_counts[signature] = self.signature_counts.get(signature, 0) + 1
        self.unique_signatures = len(self.signature_counts)
    
    def add_non_dimensional_fact(self):
        """Record a non-dimensional fact."""
        self.non_dimensional_facts += 1
    
    @property
    def dimensional_rate(self) -> float:
        """Percentage of facts that are dimensional."""
        if self.total_facts == 0:
            return 0.0
        return (self.dimensional_facts / self.total_facts) * 100


@dataclass
class StatementBuildingStatistics:
    """Complete statistics for statement building."""
    # Overall counts
    total_facts_in_filing: int = 0
    total_statements_built: int = 0
    total_facts_mapped: int = 0
    
    # Per-statement stats
    facts_per_statement: dict[str, int] = field(default_factory=dict)
    statement_types: Counter = field(default_factory=Counter)
    
    # Filtering stats
    filtering: FilteringStatistics = field(default_factory=FilteringStatistics)
    
    # Dimensional stats
    dimensional: DimensionalStatistics = field(default_factory=DimensionalStatistics)
    
    # Value normalization
    values_normalized: int = 0
    normalization_failures: int = 0
    
    # Unit validation
    unit_checks_performed: int = 0
    unit_incompatibilities: int = 0
    
    # Hierarchy validation
    hierarchy_checks_performed: int = 0
    hierarchy_warnings: int = 0
    
    @property
    def coverage_rate(self) -> float:
        """Overall coverage rate."""
        if self.total_facts_in_filing == 0:
            return 0.0
        return (self.total_facts_mapped / self.total_facts_in_filing) * 100
    
    def get_summary(self) -> dict[str, any]:
        """Get summary dictionary."""
        return {
            'overview': {
                'total_facts_in_filing': self.total_facts_in_filing,
                'facts_mapped': self.total_facts_mapped,
                'coverage_rate': f"{self.coverage_rate:.1f}%",
                'statements_built': self.total_statements_built,
            },
            'filtering': {
                'candidates_evaluated': self.filtering.total_candidates,
                'validated': self.filtering.validated_facts,
                'rejected': self.filtering.rejected_facts,
                'validation_rate': f"{self.filtering.validation_rate:.1f}%",
                'confidence_distribution': {
                    'perfect_1_0': self.filtering.confidence_1_0,
                    'good_0_75': self.filtering.confidence_0_75,
                    'weak_0_5': self.filtering.confidence_0_5,
                    'none_0_0': self.filtering.confidence_0_0,
                },
                'rejection_reasons': {
                    'low_confidence': self.filtering.low_confidence,
                    'no_context_match': self.filtering.no_context_match,
                    'period_mismatch': self.filtering.period_mismatch,
                    'dimension_issues': self.filtering.dimension_issues,
                },
            },
            'dimensional': {
                'total_facts': self.dimensional.total_facts,
                'dimensional': self.dimensional.dimensional_facts,
                'non_dimensional': self.dimensional.non_dimensional_facts,
                'dimensional_rate': f"{self.dimensional.dimensional_rate:.1f}%",
                'unique_signatures': self.dimensional.unique_signatures,
            },
            'normalization': {
                'values_normalized': self.values_normalized,
                'failures': self.normalization_failures,
            },
            'validation': {
                'unit_checks': self.unit_checks_performed,
                'unit_incompatibilities': self.unit_incompatibilities,
                'hierarchy_checks': self.hierarchy_checks_performed,
                'hierarchy_warnings': self.hierarchy_warnings,
            },
        }
    
    def print_summary(self):
        """Print formatted summary."""
        summary = self.get_summary()
        
        print("\n" + "="*70)
        print("STATEMENT BUILDING STATISTICS")
        print("="*70)
        
        print("\n OVERVIEW:")
        for key, value in summary['overview'].items():
            print(f"  {key}: {value}")
        
        print("\n FILTERING:")
        print(f"  Candidates evaluated: {summary['filtering']['candidates_evaluated']}")
        print(f"  Validated: {summary['filtering']['validated']} ({summary['filtering']['validation_rate']})")
        print(f"  Rejected: {summary['filtering']['rejected']}")
        
        print("\n  Confidence Distribution:")
        for conf_level, count in summary['filtering']['confidence_distribution'].items():
            print(f"    {conf_level}: {count}")
        
        print("\n  Rejection Reasons:")
        for reason, count in summary['filtering']['rejection_reasons'].items():
            if count > 0:
                print(f"    {reason}: {count}")
        
        print("\n DIMENSIONAL ANALYSIS:")
        for key, value in summary['dimensional'].items():
            print(f"  {key}: {value}")
        
        print("\n NORMALIZATION:")
        for key, value in summary['normalization'].items():
            print(f"  {key}: {value}")
        
        print("\n VALIDATION:")
        for key, value in summary['validation'].items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*70)


__all__ = [
    'StatementBuildingStatistics',
    'FilteringStatistics',
    'DimensionalStatistics',
]