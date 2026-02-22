# Path: mat_acc/ratio_check/scale_normalizer.py
"""
Scale Normalizer - Post-processing normalization engine

Read-Learn-Apply approach:
  READ:  Extract scale and unit_ref from iXBRL VerifiedFacts
  LEARN: Detect cross-type scale mismatches between ratio components
  APPLY: Compute normalization factor from XBRL-declared scales

This module runs AFTER ratio calculation is complete. It does NOT
modify original ratio values. It produces annotations that sit
alongside raw results, showing both original and normalized values.

The normalization factor is derived entirely from what the company
declared in their XBRL filing - never hardcoded.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from core.logger.ipo_logging import get_process_logger

from .ratio_models import ComponentMatch, RatioResult


logger = get_process_logger('scale_normalizer')

_SCALE_LABELS = {
    0: 'units', 3: 'thousands', 6: 'millions', 9: 'billions',
}


@dataclass
class ScaleAnnotation:
    """
    Normalization annotation for a single ratio.

    Preserves the raw (original) value alongside the normalized one.
    The factor is derived from XBRL-declared scale attributes.
    """
    ratio_name: str
    raw_value: float
    normalized_value: float
    factor: float
    num_scale: int
    den_scale: int
    num_unit: str
    den_unit: str
    explanation: str


class ScaleNormalizer:
    """
    Post-processing scale normalization engine.

    Reads iXBRL-declared scale and unit metadata to detect when
    ratio components use different reporting scales (e.g. monetary
    in millions vs shares in thousands). Produces annotations
    with normalized values without modifying original calculations.
    """

    def normalize(
        self,
        ratios: List[RatioResult],
        component_matches: List[ComponentMatch],
        ixbrl_facts: list,
        ratio_defs: List[Dict[str, Any]],
    ) -> Dict[str, ScaleAnnotation]:
        """
        Normalize ratios where components have mismatched scales.

        Args:
            ratios: Calculated ratio results (not modified)
            component_matches: Matched components with concept QNames
            ixbrl_facts: VerifiedFact list from iXBRL extraction
            ratio_defs: Ratio definitions with numerator/denominator

        Returns:
            Dict of ratio_name -> ScaleAnnotation (only for ratios
            that needed normalization)
        """
        if not ixbrl_facts:
            logger.info("No iXBRL facts available for normalization")
            return {}

        fact_lookup = self._build_fact_lookup(ixbrl_facts)
        logger.info(
            f"Scale lookup: {len(fact_lookup)} unique concepts "
            f"from {len(ixbrl_facts)} facts"
        )
        match_lookup = {
            m.component_name: m
            for m in component_matches if m.matched
        }
        def_by_name = {d['name']: d for d in ratio_defs}

        annotations: Dict[str, ScaleAnnotation] = {}
        for ratio in ratios:
            if not ratio.valid or ratio.value is None:
                continue
            ratio_def = def_by_name.get(ratio.ratio_name)
            if not ratio_def:
                continue
            annotation = self._check_ratio(
                ratio, ratio_def, match_lookup, fact_lookup,
            )
            if annotation:
                annotations[ratio.ratio_name] = annotation

        if annotations:
            logger.info(
                f"Normalized {len(annotations)} ratios with "
                f"cross-scale mismatches"
            )

        return annotations

    def _build_fact_lookup(
        self, facts: list,
    ) -> Dict[str, Any]:
        """Build concept QName -> first VerifiedFact lookup."""
        lookup: Dict[str, Any] = {}
        for fact in facts:
            if fact.concept not in lookup:
                lookup[fact.concept] = fact
        return lookup

    def _check_ratio(
        self,
        ratio: RatioResult,
        ratio_def: Dict[str, Any],
        match_lookup: Dict[str, ComponentMatch],
        fact_lookup: Dict[str, Any],
    ) -> Optional[ScaleAnnotation]:
        """Check a single ratio for scale mismatch."""
        calc_type = ratio_def.get('calculation_type', 'division')
        if calc_type != 'division':
            return None

        num_def = ratio_def.get('numerator')
        den_def = ratio_def.get('denominator')
        if not num_def or not den_def:
            return None

        num_info = self._get_scale_info(
            num_def, match_lookup, fact_lookup,
        )
        den_info = self._get_scale_info(
            den_def, match_lookup, fact_lookup,
        )
        if not num_info or not den_info:
            missing = []
            if not num_info:
                missing.append(f"numerator({num_def})")
            if not den_info:
                missing.append(f"denominator({den_def})")
            logger.debug(
                f"Skip {ratio.ratio_name}: no iXBRL scale for "
                f"{', '.join(missing)}"
            )
            return None

        scale_diff = num_info['scale'] - den_info['scale']
        if scale_diff == 0:
            return None

        factor = 10 ** scale_diff
        normalized = ratio.value * factor

        return ScaleAnnotation(
            ratio_name=ratio.ratio_name,
            raw_value=ratio.value,
            normalized_value=normalized,
            factor=factor,
            num_scale=num_info['scale'],
            den_scale=den_info['scale'],
            num_unit=num_info['unit'],
            den_unit=den_info['unit'],
            explanation=self._build_explanation(
                num_info, den_info, factor,
            ),
        )

    def _get_scale_info(
        self,
        component_def: Any,
        match_lookup: Dict[str, ComponentMatch],
        fact_lookup: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Get scale and unit info for a component definition."""
        if isinstance(component_def, str):
            return self._lookup_component(
                component_def, match_lookup, fact_lookup,
            )
        if isinstance(component_def, list):
            return self._lookup_first_in_list(
                component_def, match_lookup, fact_lookup,
            )
        return None

    def _lookup_first_in_list(
        self,
        component_list: List[str],
        match_lookup: Dict[str, ComponentMatch],
        fact_lookup: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Get scale info from first resolvable component in list."""
        for item in component_list:
            name = item.lstrip('+-')
            info = self._lookup_component(
                name, match_lookup, fact_lookup,
            )
            if info:
                return info
        return None

    def _lookup_component(
        self,
        name: str,
        match_lookup: Dict[str, ComponentMatch],
        fact_lookup: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Look up a single component's scale info from iXBRL."""
        match = match_lookup.get(name)
        if not match or not match.matched_concept:
            return None
        concept = match.matched_concept
        if concept.startswith('COMPOSITE:'):
            return None
        fact = fact_lookup.get(concept)
        if not fact:
            return None
        return {
            'scale': fact.scale,
            'unit': fact.unit_ref,
            'concept': concept,
        }

    def _build_explanation(
        self,
        num_info: Dict[str, Any],
        den_info: Dict[str, Any],
        factor: float,
    ) -> str:
        """Build human-readable explanation of normalization."""
        num_label = _SCALE_LABELS.get(
            num_info['scale'], f"10^{num_info['scale']}",
        )
        den_label = _SCALE_LABELS.get(
            den_info['scale'], f"10^{den_info['scale']}",
        )
        return (
            f"x{factor:,.0f}: {num_info['unit']} "
            f"({num_label}) / {den_info['unit']} ({den_label})"
        )


__all__ = ['ScaleNormalizer', 'ScaleAnnotation']
