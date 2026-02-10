# Path: mat_acc/process/matcher/evaluators/local_name_evaluator.py
"""
Local Name Evaluator

Evaluates matching rules against a concept's local name (the CamelCase
identifier from the XBRL QName). This is a reliable signal because
local names are always available regardless of market, taxonomy, or
label language.

Works with any taxonomy (US-GAAP, IFRS, company extensions) since it
matches against the structural name, not display labels.
"""

from typing import Optional

from .base_evaluator import BaseEvaluator, EvaluationResult
from ..models.concept_metadata import ConceptMetadata
from ..models.component_definition import LocalNameRule, MatchType


class LocalNameEvaluator(BaseEvaluator):
    """
    Evaluates local name matching rules.

    Matches patterns against a concept's local_name attribute.
    Local names are the CamelCase identifiers from XBRL QNames
    (e.g., "AssetsCurrent", "NetIncomeLoss", "Revenues").

    Match types supported:
    - contains: Local name contains pattern (case-insensitive)
    - exact: Exact match on local name
    - starts_with: Local name starts with pattern
    - ends_with: Local name ends with pattern
    - regex: Regular expression match

    Example:
        evaluator = LocalNameEvaluator()
        result = evaluator.evaluate(
            concept=concept,
            rules=[
                LocalNameRule(
                    patterns=["IncomeTaxExpense", "TaxExpense"],
                    match_type=MatchType.CONTAINS,
                    weight=10
                )
            ]
        )
    """

    @property
    def evaluator_type(self) -> str:
        return "local_name"

    def evaluate(
        self,
        concept: ConceptMetadata,
        rules: list[LocalNameRule],
        context: Optional[dict] = None
    ) -> EvaluationResult:
        """
        Evaluate local name rules against concept local name.

        Args:
            concept: Concept with local_name to match
            rules: List of LocalNameRule objects
            context: Optional additional context

        Returns:
            EvaluationResult with total score and matched rules
        """
        total_score = 0
        matched_rules = []

        local_name = concept.local_name
        if not local_name:
            return EvaluationResult(
                score=0,
                matched_rules=[],
                evaluator_type=self.evaluator_type
            )

        for rule in rules:
            matched = False
            matched_pattern = None

            for pattern in rule.patterns:
                if self._matches_local_name(
                    local_name,
                    pattern,
                    rule.match_type,
                    rule.case_sensitive
                ):
                    matched = True
                    matched_pattern = pattern
                    break

            if matched:
                total_score += rule.weight
                matched_rules.append({
                    'patterns': rule.patterns,
                    'match_type': rule.match_type.value,
                    'matched_pattern': matched_pattern,
                    'local_name': local_name,
                    'weight': rule.weight,
                })

                self.logger.debug(
                    f"Local name match: '{matched_pattern}' matched "
                    f"'{local_name}' for {concept.qname}, "
                    f"weight={rule.weight}"
                )

        return EvaluationResult(
            score=total_score,
            matched_rules=matched_rules,
            evaluator_type=self.evaluator_type
        )

    def _matches_local_name(
        self,
        local_name: str,
        pattern: str,
        match_type: MatchType,
        case_sensitive: bool
    ) -> bool:
        """
        Check if local name matches pattern.

        Args:
            local_name: Concept local name (CamelCase)
            pattern: Pattern to match
            match_type: How to perform the match
            case_sensitive: Whether matching is case-sensitive

        Returns:
            True if pattern matches
        """
        if match_type == MatchType.CONTAINS:
            return self._text_contains(
                local_name, pattern, case_sensitive
            )

        elif match_type == MatchType.EXACT:
            if not case_sensitive:
                return local_name.lower() == pattern.lower()
            return local_name == pattern

        elif match_type == MatchType.STARTS_WITH:
            return self._text_starts_with(
                local_name, pattern, case_sensitive
            )

        elif match_type == MatchType.ENDS_WITH:
            return self._text_ends_with(
                local_name, pattern, case_sensitive
            )

        elif match_type == MatchType.REGEX:
            return self._regex_matches(
                local_name, pattern, case_sensitive
            )

        else:
            self.logger.warning(f"Unknown match type: {match_type}")
            return False


__all__ = ['LocalNameEvaluator']
