# Path: mat_acc/ratio_check/ratio_definitions.py
"""
Ratio Definitions

Standard financial ratio definitions used for analysis.
Each ratio specifies numerator/denominator component IDs
that match dictionary/components/ definitions.

The ratio_id field enables filtering by the industry registry
(skip_ratios uses these IDs).
"""

# Standard financial ratios organized by category
STANDARD_RATIOS = [
    # =================================================================
    # LIQUIDITY RATIOS - Measure ability to meet short-term obligations
    # =================================================================
    {
        'ratio_id': 'current_ratio',
        'name': 'Current Ratio',
        'category': 'liquidity',
        'formula': 'Current Assets / Current Liabilities',
        'numerator': 'current_assets',
        'denominator': 'current_liabilities',
    },
    {
        'ratio_id': 'quick_ratio',
        'name': 'Quick Ratio',
        'category': 'liquidity',
        'formula': '(Current Assets - Inventory) / Current Liabilities',
        'numerator': ['current_assets', '-inventory'],
        'denominator': 'current_liabilities',
    },
    {
        'ratio_id': 'cash_ratio',
        'name': 'Cash Ratio',
        'category': 'liquidity',
        'formula': 'Cash and Equivalents / Current Liabilities',
        'numerator': 'cash_and_equivalents',
        'denominator': 'current_liabilities',
    },
    # =================================================================
    # LEVERAGE RATIOS - Measure financial leverage and debt capacity
    # =================================================================
    {
        'ratio_id': 'debt_to_equity',
        'name': 'Debt to Equity',
        'category': 'leverage',
        'formula': 'Total Liabilities / Total Equity',
        'numerator': 'total_liabilities',
        'denominator': 'total_equity',
    },
    {
        'ratio_id': 'debt_ratio',
        'name': 'Debt Ratio',
        'category': 'leverage',
        'formula': 'Total Liabilities / Total Assets',
        'numerator': 'total_liabilities',
        'denominator': 'total_assets',
    },
    {
        'ratio_id': 'equity_multiplier',
        'name': 'Equity Multiplier',
        'category': 'leverage',
        'formula': 'Total Assets / Total Equity',
        'numerator': 'total_assets',
        'denominator': 'total_equity',
    },
    {
        'ratio_id': 'interest_coverage',
        'name': 'Interest Coverage',
        'category': 'leverage',
        'formula': 'Operating Income / Interest Expense',
        'numerator': 'operating_income',
        'denominator': 'interest_expense',
    },
    # =================================================================
    # PROFITABILITY RATIOS - Measure ability to generate profits
    # =================================================================
    {
        'ratio_id': 'gross_margin',
        'name': 'Gross Margin',
        'category': 'profitability',
        'formula': 'Gross Profit / Revenue',
        'numerator': 'gross_profit',
        'denominator': 'revenue',
    },
    {
        'ratio_id': 'operating_margin',
        'name': 'Operating Margin',
        'category': 'profitability',
        'formula': 'Operating Income / Revenue',
        'numerator': 'operating_income',
        'denominator': 'revenue',
    },
    {
        'ratio_id': 'net_profit_margin',
        'name': 'Net Profit Margin',
        'category': 'profitability',
        'formula': 'Net Income / Revenue',
        'numerator': 'net_income',
        'denominator': 'revenue',
    },
    {
        'ratio_id': 'return_on_assets',
        'name': 'Return on Assets',
        'category': 'profitability',
        'formula': 'Net Income / Total Assets',
        'numerator': 'net_income',
        'denominator': 'total_assets',
    },
    {
        'ratio_id': 'return_on_equity',
        'name': 'Return on Equity',
        'category': 'profitability',
        'formula': 'Net Income / Total Equity',
        'numerator': 'net_income',
        'denominator': 'total_equity',
    },
    {
        'ratio_id': 'ebitda_margin',
        'name': 'EBITDA Margin',
        'category': 'profitability',
        'formula': 'EBITDA / Revenue',
        'numerator': 'ebitda',
        'denominator': 'revenue',
    },
    # =================================================================
    # EFFICIENCY RATIOS - Measure asset utilization
    # =================================================================
    {
        'ratio_id': 'asset_turnover',
        'name': 'Asset Turnover',
        'category': 'efficiency',
        'formula': 'Revenue / Total Assets',
        'numerator': 'revenue',
        'denominator': 'total_assets',
    },
    {
        'ratio_id': 'inventory_turnover',
        'name': 'Inventory Turnover',
        'category': 'efficiency',
        'formula': 'Cost of Goods Sold / Inventory',
        'numerator': 'cost_of_goods_sold',
        'denominator': 'inventory',
    },
    {
        'ratio_id': 'receivables_turnover',
        'name': 'Receivables Turnover',
        'category': 'efficiency',
        'formula': 'Revenue / Accounts Receivable',
        'numerator': 'revenue',
        'denominator': 'accounts_receivable',
    },
    {
        'ratio_id': 'payables_turnover',
        'name': 'Payables Turnover',
        'category': 'efficiency',
        'formula': 'Cost of Goods Sold / Accounts Payable',
        'numerator': 'cost_of_goods_sold',
        'denominator': 'accounts_payable',
    },
    # =================================================================
    # CASH FLOW QUALITY - Trust the numbers
    # =================================================================
    {
        'ratio_id': 'cash_conversion_ratio',
        'name': 'Cash Conversion Ratio',
        'category': 'cash_flow_quality',
        'formula': 'Operating Cash Flow / Net Income',
        'numerator': 'operating_cash_flow',
        'denominator': 'net_income',
    },
    {
        'ratio_id': 'free_cash_flow',
        'name': 'Free Cash Flow',
        'category': 'cash_flow_quality',
        'formula': 'Operating Cash Flow - Capital Expenditures',
        'numerator': ['operating_cash_flow', '-capital_expenditures'],
        'denominator': None,
        'calculation_type': 'absolute',
    },
    {
        'ratio_id': 'sloan_accrual_ratio',
        'name': 'Sloan Accrual Ratio',
        'category': 'cash_flow_quality',
        'formula': '(Net Income - Operating Cash Flow) / Total Assets',
        'numerator': ['net_income', '-operating_cash_flow'],
        'denominator': 'total_assets',
    },
    # =================================================================
    # CAPITAL ALLOCATION - How money is deployed
    # =================================================================
    {
        'ratio_id': 'roic',
        'name': 'Return on Invested Capital',
        'category': 'capital_allocation',
        'formula': 'NOPAT / Invested Capital',
        'calculation_type': 'roic',
        'components': [
            'operating_income', 'income_tax_expense',
            'income_before_tax', 'total_equity',
            'total_debt', 'cash_and_equivalents',
        ],
    },
    {
        'ratio_id': 'capital_intensity',
        'name': 'Capital Intensity',
        'category': 'capital_allocation',
        'formula': 'Total Assets / Revenue',
        'numerator': 'total_assets',
        'denominator': 'revenue',
    },
    {
        'ratio_id': 'r_and_d_intensity',
        'name': 'R&D Intensity',
        'category': 'capital_allocation',
        'formula': 'R&D Expense / Revenue',
        'numerator': 'r_and_d_expense',
        'denominator': 'revenue',
    },
    # =================================================================
    # DUPONT DECOMPOSITION - Anatomy of returns
    # =================================================================
    {
        'ratio_id': 'tax_burden',
        'name': 'Tax Burden',
        'category': 'dupont',
        'formula': 'Net Income / Income Before Tax',
        'numerator': 'net_income',
        'denominator': 'income_before_tax',
    },
    {
        'ratio_id': 'interest_burden',
        'name': 'Interest Burden',
        'category': 'dupont',
        'formula': 'Income Before Tax / Operating Income',
        'numerator': 'income_before_tax',
        'denominator': 'operating_income',
    },
    {
        'ratio_id': 'dupont_roe',
        'name': 'DuPont ROE',
        'category': 'dupont',
        'formula': ('Tax Burden x Interest Burden x Operating Margin'
                    ' x Asset Turnover x Equity Multiplier'),
        'calculation_type': 'dupont',
        'components': [
            'net_income', 'income_before_tax', 'operating_income',
            'revenue', 'total_assets', 'total_equity',
        ],
    },
    # =================================================================
    # FINANCIAL DISTRESS - Survival probability
    # =================================================================
    {
        'ratio_id': 'altman_z_score',
        'name': 'Altman Z-Score',
        'category': 'distress',
        'formula': '1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E',
        'calculation_type': 'altman_z',
        'components': [
            'current_assets', 'current_liabilities',
            'retained_earnings', 'total_assets',
            'operating_income', 'total_equity',
            'total_liabilities', 'revenue',
        ],
    },
    # =================================================================
    # OPERATING LEVERAGE - Cost structure sensitivity
    # =================================================================
    {
        'ratio_id': 'sga_to_revenue',
        'name': 'SG&A to Revenue',
        'category': 'operating_leverage',
        'formula': 'SG&A / Revenue',
        'numerator': 'selling_general_admin',
        'denominator': 'revenue',
    },
    {
        'ratio_id': 'operating_expense_ratio',
        'name': 'Operating Expense Ratio',
        'category': 'operating_leverage',
        'formula': '(Revenue - Operating Income) / Revenue',
        'numerator': ['revenue', '-operating_income'],
        'denominator': 'revenue',
    },
]


# Lookup by ratio_id for filtering
RATIO_BY_ID = {r['ratio_id']: r for r in STANDARD_RATIOS}


__all__ = ['STANDARD_RATIOS', 'RATIO_BY_ID']
