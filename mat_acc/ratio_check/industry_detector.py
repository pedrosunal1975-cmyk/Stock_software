# Path: mat_acc/ratio_check/industry_detector.py
"""
Industry Detector

Auto-detects industry group from XBRL concepts in a filing.
Uses concept fingerprinting: each industry has signature concepts
that only appear in that sector's filings.

Detection runs AFTER concept building, BEFORE matching.
Returns industry type used to select the ratio model.
"""

from core.logger.ipo_logging import get_process_logger


logger = get_process_logger('industry_detector')


# Signature concepts for each industry group.
# 'strong' = highly specific to this industry.
# 'moderate' = common but not exclusive to this industry.
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
            'OperatingLeaseRevenue',
            'RealEstateInvestmentPropertyAtCost',
        ],
        'moderate': [
            'NumberOfRealEstateProperties',
            'AreaOfRealEstateProperty',
            'OccupancyRate',
        ],
        'threshold': 2,
    },
}


class IndustryDetector:
    """
    Detects industry group from XBRL concept names in a filing.

    Uses contains-matching against concept local_names to count
    signal hits. The industry with the highest score above its
    threshold wins. Defaults to 'general' if no signals match.
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
            Industry type: 'general', 'banking', 'insurance', or 'reit'
        """
        all_local_names = self._collect_local_names(concept_index)
        self._signals_found.clear()

        best_industry = 'general'
        best_score = 0

        for industry, config in INDUSTRY_SIGNALS.items():
            score, matched = self._score_industry(
                industry, config, all_local_names,
            )
            self._signals_found[industry] = matched

            if score > best_score and score >= config['threshold']:
                best_score = score
                best_industry = industry

        self._log_result(best_industry, best_score)
        return best_industry

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

    def _score_industry(
        self, industry: str, config: dict, local_names: set[str],
    ) -> tuple[int, list[str]]:
        """
        Score an industry against available concepts.

        Strong signals count as 2 points, moderate as 1.
        Returns (score, list_of_matched_signal_names).
        """
        matched = []
        score = 0

        for signal in config['strong']:
            if signal.lower() in local_names:
                score += 2
                matched.append(signal)

        for signal in config['moderate']:
            if signal.lower() in local_names:
                score += 1
                matched.append(signal)

        return score, matched

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
