# Path: mat_acc/process/matcher/evaluators/base_evaluator.py
"""
Base Evaluator

Abstract base class for all rule evaluators.
Defines the interface that all evaluators must implement.
"""

import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.concept_metadata import ConceptMetadata


@dataclass
class EvaluationResult:
    """
    Result of evaluating rules against a concept.

    Attributes:
        score: Total score contribution from this evaluator
        matched_rules: List of rules that matched with details
        evaluator_type: Name of the evaluator that produced this result
    """
    score: int
    matched_rules: list[dict] = field(default_factory=list)
    evaluator_type: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'score': self.score,
            'matched_rules': self.matched_rules,
            'evaluator_type': self.evaluator_type,
        }


class BaseEvaluator(ABC):
    """
    Abstract base class for rule evaluators.

    Each evaluator handles one type of matching rule:
    - LabelEvaluator: Label patterns
    - HierarchyEvaluator: Hierarchy position
    - CalculationEvaluator: Calculation relationships
    - DefinitionEvaluator: Definition keywords
    - ReferenceEvaluator: Standard references
    - LocalNameEvaluator: Concept name patterns

    Subclasses must implement the evaluate() method.

    Example:
        evaluator = LabelEvaluator()
        result = evaluator.evaluate(
            concept=concept_metadata,
            rules=component.matching_rules.label_rules,
            context=additional_context
        )
        print(f"Score: {result.score}")
    """

    def __init__(self):
        """Initialize evaluator."""
        self.logger = logging.getLogger(f'matcher.evaluators.{self.evaluator_type}')

    @property
    @abstractmethod
    def evaluator_type(self) -> str:
        """Return the type name of this evaluator."""
        pass

    @abstractmethod
    def evaluate(
        self,
        concept: ConceptMetadata,
        rules: list[Any],
        context: Optional[dict] = None
    ) -> EvaluationResult:
        """
        Evaluate rules against a concept.

        Args:
            concept: Concept metadata to evaluate
            rules: List of rules for this evaluator type
            context: Additional context (filing metadata, taxonomy data, etc.)

        Returns:
            EvaluationResult with score and matched rules
        """
        pass

    def _pattern_matches(
        self,
        text: str,
        pattern: str,
        case_sensitive: bool = False
    ) -> bool:
        """
        Check if text matches a pattern with wildcards.

        Supports wildcards:
        - * matches any characters
        - Pattern at start: *suffix
        - Pattern at end: prefix*
        - Pattern in middle: *contains*

        Args:
            text: Text to match against
            pattern: Pattern with optional wildcards
            case_sensitive: Whether matching is case-sensitive

        Returns:
            True if pattern matches
        """
        if not case_sensitive:
            text = text.lower()
            pattern = pattern.lower()

        # Handle wildcards
        if '*' in pattern:
            # Convert to regex
            regex_pattern = pattern.replace('*', '.*')
            regex_pattern = f'^{regex_pattern}$'
            try:
                return bool(re.match(regex_pattern, text))
            except re.error:
                return False
        else:
            return pattern == text

    def _normalize_for_matching(self, text: str) -> str:
        """
        Normalize text for matching by removing punctuation.

        Handles variations like:
        - "Stockholders' Equity" vs "Stockholders Equity"
        - "Assets, Current" vs "Assets Current"
        - "Net Income (Loss)" vs "Net Income Loss"

        Args:
            text: Text to normalize

        Returns:
            Normalized text with punctuation removed
        """
        # Remove common punctuation that varies between sources
        # Keep letters, numbers, and spaces
        normalized = re.sub(r"['\",\(\)\-]", '', text)
        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

    def _text_contains(
        self,
        text: str,
        pattern: str,
        case_sensitive: bool = False
    ) -> bool:
        """
        Check if text contains pattern.

        Normalizes both text and pattern to handle punctuation variations.

        Args:
            text: Text to search in
            pattern: Pattern to find
            case_sensitive: Whether matching is case-sensitive

        Returns:
            True if pattern found in text
        """
        # Normalize both for comparison
        text = self._normalize_for_matching(text)
        pattern = self._normalize_for_matching(pattern)

        if not case_sensitive:
            text = text.lower()
            pattern = pattern.lower()

        return pattern in text

    def _text_starts_with(
        self,
        text: str,
        pattern: str,
        case_sensitive: bool = False
    ) -> bool:
        """Check if text starts with pattern (normalized)."""
        text = self._normalize_for_matching(text)
        pattern = self._normalize_for_matching(pattern)
        if not case_sensitive:
            text = text.lower()
            pattern = pattern.lower()
        return text.startswith(pattern)

    def _text_ends_with(
        self,
        text: str,
        pattern: str,
        case_sensitive: bool = False
    ) -> bool:
        """Check if text ends with pattern (normalized)."""
        text = self._normalize_for_matching(text)
        pattern = self._normalize_for_matching(pattern)
        if not case_sensitive:
            text = text.lower()
            pattern = pattern.lower()
        return text.endswith(pattern)

    def _regex_matches(
        self,
        text: str,
        pattern: str,
        case_sensitive: bool = False
    ) -> bool:
        """
        Check if text matches regex pattern.

        Args:
            text: Text to match
            pattern: Regular expression pattern
            case_sensitive: Whether matching is case-sensitive

        Returns:
            True if regex matches
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            return bool(re.search(pattern, text, flags))
        except re.error:
            self.logger.warning(f"Invalid regex pattern: {pattern}")
            return False


__all__ = ['BaseEvaluator', 'EvaluationResult']
