# Path: mat_acc/process/matcher/models/match_result.py
"""
Match Result Models

Models representing the results of concept matching operations.
"""

from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class MatchStatus(str, Enum):
    """Status of a matching attempt."""
    MATCHED = "matched"
    NO_MATCH = "no_match"
    COMPOSITE_RESOLVED = "composite_resolved"
    COMPOSITE_FAILED = "composite_failed"
    REQUIRES_PRIOR_PERIOD = "requires_prior_period"
    EXTERNAL_DATA_REQUIRED = "external_data_required"


class Confidence(str, Enum):
    """Confidence level of a match."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass
class RuleScore:
    """
    Score contribution from a single rule type.

    Attributes:
        rule_type: Type of rule (label, hierarchy, calculation, etc.)
        score: Points contributed by this rule
        details: Detailed breakdown of what matched
    """
    rule_type: str
    score: int
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'rule_type': self.rule_type,
            'score': self.score,
            'details': self.details,
        }


@dataclass
class ScoredMatch:
    """
    A concept that matched with its score breakdown.

    Attributes:
        concept: The matched concept QName (e.g., "us-gaap:AssetsCurrent")
        total_score: Sum of all rule scores
        rule_scores: Breakdown by rule type
        confidence: Calculated confidence level
        rejection_reason: If rejected, why
    """
    concept: str
    total_score: int
    rule_scores: list[RuleScore] = field(default_factory=list)
    confidence: Confidence = Confidence.NONE
    rejection_reason: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'concept': self.concept,
            'total_score': self.total_score,
            'rule_scores': [rs.to_dict() for rs in self.rule_scores],
            'confidence': self.confidence.value,
            'rejection_reason': self.rejection_reason,
        }

    @property
    def is_rejected(self) -> bool:
        """Check if this match was rejected."""
        return self.rejection_reason is not None


@dataclass
class MatchResult:
    """
    Result of attempting to match a component to a concept.

    This is the primary output of the matching process for a single
    component. It contains the matched concept (if any), the score,
    confidence level, and detailed breakdown for traceability.

    Attributes:
        component_id: The component that was being matched
        status: Result status (matched, no_match, etc.)
        matched_concept: The concept that was matched (if any)
        total_score: Total score achieved
        confidence: Confidence level of the match
        rule_breakdown: Detailed breakdown by rule type
        alternatives: Other concepts that were considered
        tiebreaker_used: Which tiebreaker resolved multiple matches
        warnings: Any warnings generated during matching
        matched_at: Timestamp of the match
    """
    component_id: str
    status: MatchStatus
    matched_concept: Optional[str] = None
    total_score: int = 0
    confidence: Confidence = Confidence.NONE
    rule_breakdown: dict[str, RuleScore] = field(default_factory=dict)
    alternatives: list[ScoredMatch] = field(default_factory=list)
    tiebreaker_used: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    matched_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def no_match(cls, component_id: str, reason: Optional[str] = None) -> 'MatchResult':
        """
        Create a result for when no match was found.

        Args:
            component_id: Component that failed to match
            reason: Optional reason for no match

        Returns:
            MatchResult with NO_MATCH status
        """
        result = cls(
            component_id=component_id,
            status=MatchStatus.NO_MATCH,
        )
        if reason:
            result.warnings.append(reason)
        return result

    @classmethod
    def from_scored_match(
        cls,
        component_id: str,
        match: ScoredMatch,
        alternatives: Optional[list[ScoredMatch]] = None,
        tiebreaker_used: Optional[str] = None
    ) -> 'MatchResult':
        """
        Create a result from a successful match.

        Args:
            component_id: Component that was matched
            match: The winning ScoredMatch
            alternatives: Other matches that were considered
            tiebreaker_used: Which tiebreaker was used (if any)

        Returns:
            MatchResult with MATCHED status
        """
        rule_breakdown = {
            rs.rule_type: rs
            for rs in match.rule_scores
        }

        return cls(
            component_id=component_id,
            status=MatchStatus.MATCHED,
            matched_concept=match.concept,
            total_score=match.total_score,
            confidence=match.confidence,
            rule_breakdown=rule_breakdown,
            alternatives=alternatives or [],
            tiebreaker_used=tiebreaker_used,
        )

    @classmethod
    def external_required(cls, component_id: str, reason: str) -> 'MatchResult':
        """
        Create a result for components requiring external data.

        Args:
            component_id: Component requiring external data
            reason: Why external data is needed

        Returns:
            MatchResult with EXTERNAL_DATA_REQUIRED status
        """
        return cls(
            component_id=component_id,
            status=MatchStatus.EXTERNAL_DATA_REQUIRED,
            warnings=[reason],
        )

    @classmethod
    def requires_prior_period(cls, component_id: str) -> 'MatchResult':
        """
        Create a result for components needing prior period data.

        Args:
            component_id: Component requiring prior period

        Returns:
            MatchResult with REQUIRES_PRIOR_PERIOD status
        """
        return cls(
            component_id=component_id,
            status=MatchStatus.REQUIRES_PRIOR_PERIOD,
            warnings=["Requires beginning balance from prior period"],
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'component_id': self.component_id,
            'status': self.status.value,
            'matched_concept': self.matched_concept,
            'total_score': self.total_score,
            'confidence': self.confidence.value,
            'rule_breakdown': {
                k: v.to_dict() for k, v in self.rule_breakdown.items()
            },
            'alternatives': [a.to_dict() for a in self.alternatives],
            'tiebreaker_used': self.tiebreaker_used,
            'warnings': self.warnings,
            'matched_at': self.matched_at.isoformat(),
        }

    @property
    def is_matched(self) -> bool:
        """Check if matching was successful."""
        return self.status == MatchStatus.MATCHED

    @property
    def is_high_confidence(self) -> bool:
        """Check if match has high confidence."""
        return self.confidence == Confidence.HIGH

    @property
    def needs_verification(self) -> bool:
        """Check if match should be manually verified."""
        return (
            self.confidence in (Confidence.LOW, Confidence.MEDIUM)
            or len(self.alternatives) > 0
            or len(self.warnings) > 0
        )


__all__ = [
    'MatchStatus',
    'Confidence',
    'RuleScore',
    'ScoredMatch',
    'MatchResult',
]
