# Path: mat_acc/ratio_check/plausibility/auditor.py
"""
Plausibility Auditor

Main orchestrator for plausibility checks.
Runs all check categories and produces a PlausibilityReport.

This is an INTERPRETIVE layer: it reads existing calculation
results and annotates them. It never modifies values or ratios.
"""

from typing import Dict, List, Optional

from core.logger.ipo_logging import get_process_logger

from .models import PlausibilityReport
from .declared_resolver import DeclaredResolver
from .proportion_checks import check_proportions
from .range_checks import check_ranges
from .coherence_checks import check_coherence


logger = get_process_logger('plausibility')


class PlausibilityAuditor:
    """
    Runs plausibility checks on ratio analysis output.

    Usage:
        auditor = PlausibilityAuditor()
        report = auditor.audit(
            component_matches, ratio_results,
            market='sec', ixbrl_facts=facts,
        )
    """

    def __init__(self):
        self._declared = DeclaredResolver()

    def audit(
        self,
        component_matches: list,
        ratio_results: list,
        market: str = 'sec',
        company: str = '',
        ixbrl_facts: Optional[list] = None,
    ) -> PlausibilityReport:
        """
        Run full plausibility audit.

        Args:
            component_matches: List of ComponentMatch
            ratio_results: List of RatioResult
            market: Market identifier (sec, esef)
            company: Company name for context
            ixbrl_facts: Optional iXBRL facts for declared values

        Returns:
            PlausibilityReport with all findings
        """
        report = PlausibilityReport(
            company=company, market=market,
        )

        # Resolve declared values from iXBRL
        if ixbrl_facts:
            self._declared.resolve(ixbrl_facts)

        # Prepare data structures for checks
        comp_data = self._prepare_components(component_matches)
        ratio_data = self._prepare_ratios(ratio_results)

        # Run all check categories
        report.findings.extend(
            check_proportions(comp_data, market),
        )
        report.findings.extend(
            check_ranges(ratio_data, market, self._declared),
        )
        report.findings.extend(
            check_coherence(comp_data, ratio_data),
        )

        # Sort by severity (alerts first)
        severity_order = {
            'alert': 0, 'warning': 1, 'advisory': 2, 'info': 3,
        }
        report.findings.sort(
            key=lambda f: severity_order.get(f.severity.value, 9),
        )

        self._log_summary(report)
        return report

    def _prepare_components(
        self, matches: list,
    ) -> Dict[str, dict]:
        """Convert ComponentMatch list to check-friendly dict."""
        data = {}
        for m in matches:
            if not m.matched:
                continue
            data[m.component_name] = {
                'value': m.value,
                'confidence': m.confidence,
                'matched_concept': m.matched_concept,
                'match_quality': m.match_quality,
                'label': m.label,
            }
        return data

    def _prepare_ratios(
        self, ratios: list,
    ) -> Dict[str, dict]:
        """Convert RatioResult list to check-friendly dict."""
        data = {}
        for r in ratios:
            data[r.ratio_name] = {
                'value': r.value,
                'valid': r.valid,
                'formula': r.formula,
                'numerator': r.numerator,
                'denominator': r.denominator,
                'numerator_value': r.numerator_value,
                'denominator_value': r.denominator_value,
            }
        return data

    def _log_summary(self, report: PlausibilityReport) -> None:
        """Log plausibility summary."""
        counts = report.summary_counts
        total = len(report.findings)
        w = counts.get('warning', 0) + counts.get('alert', 0)
        a = counts.get('advisory', 0)
        i = counts.get('info', 0)
        logger.info(
            f"Plausibility audit: {total} findings "
            f"({w} warnings, {a} advisories, {i} info)"
        )


__all__ = ['PlausibilityAuditor']
