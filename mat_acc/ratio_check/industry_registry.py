# Path: mat_acc/ratio_check/industry_registry.py
"""
Industry Registry

Maps industry types to their ratio model configurations.
Each model defines which standard ratios to skip and which
industry-specific ratios to add.

The registry does NOT change the matching engine or value pipeline.
It only controls WHICH ratios get calculated.
"""

from core.logger.ipo_logging import get_process_logger


logger = get_process_logger('industry_registry')


# Model configurations per industry.
# 'skip_ratios' = standard ratio IDs to exclude (inapplicable).
# 'extra_components' = additional component IDs needed.
# 'extra_ratios' = industry-specific ratio definitions to add.
INDUSTRY_MODELS = {
    'general': {
        'display_name': 'General / Industrial',
        'skip_ratios': [],
        'extra_components': [],
        'extra_ratios': [],
    },
    'banking': {
        'display_name': 'Banking / Financial Institution',
        'skip_ratios': [
            'gross_margin',
            'inventory_turnover',
            'payables_turnover',
            'quick_ratio',
        ],
        'extra_components': [
            'net_interest_income',
            'provision_for_loan_losses',
            'total_loans',
            'total_deposits',
            'noninterest_income',
            'noninterest_expense',
        ],
        'extra_ratios': [
            {
                'ratio_id': 'net_interest_margin',
                'name': 'Net Interest Margin',
                'category': 'banking',
                'formula': 'Net Interest Income / Total Assets',
                'numerator': 'net_interest_income',
                'denominator': 'total_assets',
            },
            {
                'ratio_id': 'loan_to_deposit',
                'name': 'Loan to Deposit Ratio',
                'category': 'banking',
                'formula': 'Total Loans / Total Deposits',
                'numerator': 'total_loans',
                'denominator': 'total_deposits',
            },
            {
                'ratio_id': 'efficiency_ratio',
                'name': 'Efficiency Ratio',
                'category': 'banking',
                'formula': 'Noninterest Expense / (Net Interest Income + Noninterest Income)',
                'numerator': 'noninterest_expense',
                'denominator': [
                    'net_interest_income',
                    '+noninterest_income',
                ],
            },
            {
                'ratio_id': 'provision_coverage',
                'name': 'Provision Coverage',
                'category': 'banking',
                'formula': 'Provision for Loan Losses / Total Loans',
                'numerator': 'provision_for_loan_losses',
                'denominator': 'total_loans',
            },
            {
                'ratio_id': 'noninterest_income_ratio',
                'name': 'Noninterest Income Ratio',
                'category': 'banking',
                'formula': 'Noninterest Income / Revenue',
                'numerator': 'noninterest_income',
                'denominator': 'revenue',
            },
        ],
    },
    'insurance': {
        'display_name': 'Insurance',
        'skip_ratios': [
            'gross_margin',
            'inventory_turnover',
            'payables_turnover',
            'quick_ratio',
        ],
        'extra_components': [
            'premiums_earned',
            'claims_incurred',
            'policy_acquisition_costs',
            'investment_income',
            'unearned_premiums',
        ],
        'extra_ratios': [
            {
                'ratio_id': 'loss_ratio',
                'name': 'Loss Ratio',
                'category': 'insurance',
                'formula': 'Claims Incurred / Premiums Earned',
                'numerator': 'claims_incurred',
                'denominator': 'premiums_earned',
            },
            {
                'ratio_id': 'expense_ratio',
                'name': 'Expense Ratio',
                'category': 'insurance',
                'formula': 'Policy Acquisition Costs / Premiums Earned',
                'numerator': 'policy_acquisition_costs',
                'denominator': 'premiums_earned',
            },
            {
                'ratio_id': 'combined_ratio',
                'name': 'Combined Ratio',
                'category': 'insurance',
                'formula': '(Claims + Acquisition Costs) / Premiums Earned',
                'numerator': [
                    'claims_incurred',
                    '+policy_acquisition_costs',
                ],
                'denominator': 'premiums_earned',
            },
            {
                'ratio_id': 'investment_yield',
                'name': 'Investment Yield',
                'category': 'insurance',
                'formula': 'Investment Income / Total Assets',
                'numerator': 'investment_income',
                'denominator': 'total_assets',
            },
            {
                'ratio_id': 'premium_to_surplus',
                'name': 'Premium to Surplus',
                'category': 'insurance',
                'formula': 'Premiums Earned / Total Equity',
                'numerator': 'premiums_earned',
                'denominator': 'total_equity',
            },
        ],
    },
    'reit': {
        'display_name': 'Real Estate Investment Trust',
        'skip_ratios': [
            'inventory_turnover',
            'payables_turnover',
        ],
        'extra_components': [
            'funds_from_operations',
            'rental_revenue',
            'real_estate_assets',
        ],
        'extra_ratios': [
            {
                'ratio_id': 'ffo_per_share',
                'name': 'FFO Per Share',
                'category': 'reit',
                'formula': 'Funds From Operations / Shares Outstanding',
                'numerator': 'funds_from_operations',
                'denominator': 'shares_outstanding',
            },
            {
                'ratio_id': 'price_to_ffo',
                'name': 'Price to FFO',
                'category': 'reit',
                'formula': 'Share Price / FFO Per Share',
                'numerator': 'share_price',
                'denominator': 'funds_from_operations',
            },
            {
                'ratio_id': 'ffo_payout_ratio',
                'name': 'FFO Payout Ratio',
                'category': 'reit',
                'formula': 'Dividends Paid / Funds From Operations',
                'numerator': 'dividends_paid',
                'denominator': 'funds_from_operations',
            },
        ],
    },
}


class IndustryRegistry:
    """
    Provides ratio model configuration for a detected industry.

    Used by the ratio calculator to determine which ratios
    to calculate and which components to load.
    """

    def __init__(self):
        """Initialize registry."""
        self.logger = get_process_logger('industry_registry')

    def get_model(self, industry: str) -> dict:
        """
        Get model config for the given industry.

        Args:
            industry: Industry type from IndustryDetector

        Returns:
            Model configuration dict
        """
        if industry not in INDUSTRY_MODELS:
            self.logger.warning(
                f"Unknown industry '{industry}', using general"
            )
            industry = 'general'
        return INDUSTRY_MODELS[industry]

    def get_skip_ratio_ids(self, industry: str) -> list[str]:
        """Get ratio IDs that should be skipped for this industry."""
        model = self.get_model(industry)
        return model['skip_ratios']

    def get_extra_ratios(self, industry: str) -> list[dict]:
        """Get industry-specific ratio definitions."""
        model = self.get_model(industry)
        return model['extra_ratios']

    def get_extra_component_ids(self, industry: str) -> list[str]:
        """Get IDs of extra components needed for this industry."""
        model = self.get_model(industry)
        return model['extra_components']

    def get_display_name(self, industry: str) -> str:
        """Get human-readable industry name."""
        model = self.get_model(industry)
        return model['display_name']


__all__ = ['IndustryRegistry', 'INDUSTRY_MODELS']
