# Path: mat_acc/ratio_check/industry_detector.py
"""
Industry Detector

Auto-detects industry group from XBRL concepts in a filing.
Uses concept fingerprinting: each industry has signature concepts
that only appear in that sector's filings.

Also uses negative signals: presence of general-industry concepts
(like COGS or Inventory) reduces the likelihood of specialized
industry classification.

Detection runs AFTER concept building, BEFORE matching.
Returns industry type used to select the ratio model.
"""

from core.logger.ipo_logging import get_process_logger


logger = get_process_logger('industry_detector')


# Signature concepts for each industry group.
# 'strong' = highly specific (2 pts), 'moderate' = common (1 pt).
INDUSTRY_SIGNALS = {
    'banking': {
        'strong': [
            'InterestIncomeExpenseNet',
            'ProvisionForLoanLossesExpensed',
            'LoansAndLeasesReceivableNetReportedAmount',
            'DepositsFromCustomers',
            'NetInterestIncome',
        ],
        'moderate': [
            'InterestIncomeExpenseAfterProvision',
            'AllowanceForLoanAndLeaseLosses',
            'FederalFundsSoldAndSecuritiesPurchased',
        ],
        'threshold': 3,
    },
    'insurance': {
        'strong': [
            'PremiumsEarnedNet',
            'PolicyholderBenefitsAndClaimsIncurred',
            'DeferredPolicyAcquisitionCosts',
            'UnearnedPremiums',
            'LossAndLossAdjustmentExpenseReserve',
        ],
        'moderate': [
            'NetInvestmentIncome',
            'PolicyholderDividends',
            'ReinsuranceRecoverables',
        ],
        'threshold': 3,
    },
    'reit': {
        'strong': [
            'FundsFromOperations',
            'RealEstateInvestmentPropertyNet',
            'RealEstateInvestmentPropertyAtCost',
        ],
        'moderate': [
            'NumberOfRealEstateProperties',
            'AreaOfRealEstateProperty',
            'OccupancyRate',
            'OperatingLeaseRevenue',
        ],
        'threshold': 3,
    },
}

# Concepts that indicate a general/industrial company.
# Their presence reduces specialized industry scores.
# Each negative signal reduces score by 1 point.
NEGATIVE_SIGNALS = [
    'CostOfRevenue',
    'CostOfGoodsAndServicesSold',
    'CostOfGoodsSold',
    'InventoryNet',
    'GrossProfit',
]


class IndustryDetector:
    """
    Detects industry group from XBRL concept names in a filing.

    Uses contains-matching against concept local_names to count
    signal hits. The industry with the highest score above its
    threshold wins. If multiple industries exceed threshold, the
    one with the most strong signals wins (then highest score).
    Defaults to 'general' if no signals match.
    """

    def __init__(self):
        """Initialize detector."""
        self.logger = get_process_logger('industry_detector')
        self._signals_found: dict[str, list[str]] = {}

    def detect(self, concept_index) -> str:
        """
        Detect industry from concepts in the filing.

        Args:
            concept_index: ConceptIndex with all filing concepts

        Returns:
            Industry type: 'general', 'banking', 'insurance', 'reit'
        """
        all_local_names = self._collect_local_names(concept_index)
        self._signals_found.clear()

        neg_count = self._count_negative_signals(all_local_names)
        candidates = []

        for industry, config in INDUSTRY_SIGNALS.items():
            score, strong_count, matched = self._score_industry(
                config, all_local_names,
            )
            self._signals_found[industry] = matched
            adjusted = max(0, score - neg_count)
            if adjusted >= config['threshold']:
                candidates.append(
                    (adjusted, strong_count, industry, matched)
                )

        if not candidates:
            self._log_result('general', 0)
            return 'general'

        # Best = highest adjusted score, then most strong signals
        candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
        best = candidates[0]
        self._log_result(best[2], best[0])
        return best[2]

    def get_signals_found(self) -> dict[str, list[str]]:
        """Return matched signals per industry for diagnostics."""
        return dict(self._signals_found)

    def _collect_local_names(self, concept_index) -> set[str]:
        """Extract all local names from concept index."""
        names = set()
        for concept in concept_index.get_all_concepts():
            if concept.local_name:
                names.add(concept.local_name.lower())
        return names

    def _count_negative_signals(self, local_names: set[str]) -> int:
        """Count general-industry indicators that argue against
        specialized classification."""
        count = 0
        for signal in NEGATIVE_SIGNALS:
            if signal.lower() in local_names:
                count += 1
        return count

    def _score_industry(
        self, config: dict, local_names: set[str],
    ) -> tuple[int, int, list[str]]:
        """
        Score an industry against available concepts.

        Returns (total_score, strong_count, matched_signal_names).
        """
        matched = []
        score = 0
        strong_count = 0

        for signal in config['strong']:
            if signal.lower() in local_names:
                score += 2
                strong_count += 1
                matched.append(signal)

        for signal in config['moderate']:
            if signal.lower() in local_names:
                score += 1
                matched.append(signal)

        return score, strong_count, matched

    def _log_result(self, industry: str, score: int) -> None:
        """Log the detection result."""
        if industry == 'general':
            self.logger.info("Industry detected: general (no signals)")
        else:
            signals = self._signals_found.get(industry, [])
            names = ', '.join(signals[:5])
            self.logger.info(
                f"Industry detected: {industry} "
                f"(score={score}, signals: {names})"
            )


__all__ = ['IndustryDetector', 'INDUSTRY_SIGNALS']
