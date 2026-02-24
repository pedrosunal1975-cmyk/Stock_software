# Path: mat_acc/ratio_check/plausibility/declared_resolver.py
"""
Declared Value Resolver

Extracts company-declared rates and percentages from iXBRL facts.
These are DECLARED expectations - what the company itself reports,
as opposed to NORMATIVE expectations (hardcoded accounting rules).

When a declared value exists, it takes precedence over normative
ranges in plausibility checks.
"""

from typing import Dict, List, Optional


# iXBRL concepts that represent declared rates/percentages.
# Format: declared_key -> list of concept local names to search for.
DECLARED_RATE_CONCEPTS: Dict[str, List[str]] = {
    'effective_tax_rate': [
        'EffectiveIncomeTaxRateContinuingOperations',
    ],
    'depreciation_rate': [
        'PropertyPlantAndEquipmentUsefulLife',
    ],
}

# Maps declared_key to the ratio/component it informs
DECLARED_TO_TARGET: Dict[str, str] = {
    'effective_tax_rate': 'Effective Tax Rate',
}


class DeclaredResolver:
    """
    Resolves declared values from iXBRL facts.

    Searches raw iXBRL fact list for known rate/percentage concepts
    and provides them for plausibility comparison.
    """

    def __init__(self):
        self._declared: Dict[str, float] = {}

    def resolve(self, ixbrl_facts: list) -> Dict[str, float]:
        """
        Extract declared rates from iXBRL facts.

        Args:
            ixbrl_facts: List of VerifiedFact from iXBRL extraction

        Returns:
            Dict mapping declared_key to declared value
        """
        self._declared = {}
        if not ixbrl_facts:
            return self._declared

        # Build local_name -> value index from facts
        fact_index = self._build_fact_index(ixbrl_facts)

        for key, concept_names in DECLARED_RATE_CONCEPTS.items():
            value = self._find_declared(concept_names, fact_index)
            if value is not None:
                self._declared[key] = value

        return self._declared

    def get(self, key: str) -> Optional[float]:
        """Get a resolved declared value by key."""
        return self._declared.get(key)

    def get_for_target(self, target: str) -> Optional[float]:
        """Get declared value for a ratio/component target name."""
        for key, tgt in DECLARED_TO_TARGET.items():
            if tgt == target and key in self._declared:
                return self._declared[key]
        return None

    @property
    def all_declared(self) -> Dict[str, float]:
        """All resolved declared values."""
        return dict(self._declared)

    def _build_fact_index(
        self, facts: list,
    ) -> Dict[str, float]:
        """Index facts by local name for quick lookup."""
        index: Dict[str, float] = {}
        for fact in facts:
            local = self._extract_local(fact.concept)
            if local and fact.value is not None:
                # For rates, prefer values between 0 and 1
                # (some are percentages 0-100, some are decimals)
                index[local] = fact.value
        return index

    def _extract_local(self, concept: str) -> Optional[str]:
        """Extract local name from a QName."""
        if ':' in concept:
            return concept.split(':')[-1]
        if '_' in concept:
            parts = concept.split('_', 1)
            if len(parts) == 2:
                return parts[1]
        return concept

    def _find_declared(
        self,
        concept_names: List[str],
        fact_index: Dict[str, float],
    ) -> Optional[float]:
        """Find the first matching declared value."""
        for name in concept_names:
            if name in fact_index:
                val = fact_index[name]
                # Sanity: rates above 1000% (abs > 10) are likely
                # monetary amounts misidentified as rates
                if abs(val) > 10:
                    continue
                return val
        return None


__all__ = ['DeclaredResolver', 'DECLARED_RATE_CONCEPTS']
