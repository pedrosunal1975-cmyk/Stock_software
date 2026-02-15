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
]


# Lookup by ratio_id for filtering
RATIO_BY_ID = {r['ratio_id']: r for r in STANDARD_RATIOS}


__all__ = ['STANDARD_RATIOS', 'RATIO_BY_ID']
