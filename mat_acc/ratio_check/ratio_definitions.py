# Path: mat_acc/ratio_check/ratio_definitions.py
"""
Ratio Definitions

Standard financial ratio definitions used for analysis.
Each ratio specifies numerator/denominator component IDs
that match dictionary/components/ definitions.
"""

# Standard financial ratios organized by category
STANDARD_RATIOS = [
    # =================================================================
    # LIQUIDITY RATIOS - Measure ability to meet short-term obligations
    # =================================================================
    {
        'name': 'Current Ratio',
        'category': 'liquidity',
        'formula': 'Current Assets / Current Liabilities',
        'numerator': 'current_assets',
        'denominator': 'current_liabilities',
    },
    {
        'name': 'Quick Ratio',
        'category': 'liquidity',
        'formula': '(Current Assets - Inventory) / Current Liabilities',
        'numerator': ['current_assets', '-inventory'],
        'denominator': 'current_liabilities',
    },
    {
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
        'name': 'Debt to Equity',
        'category': 'leverage',
        'formula': 'Total Liabilities / Total Equity',
        'numerator': 'total_liabilities',
        'denominator': 'total_equity',
    },
    {
        'name': 'Debt Ratio',
        'category': 'leverage',
        'formula': 'Total Liabilities / Total Assets',
        'numerator': 'total_liabilities',
        'denominator': 'total_assets',
    },
    {
        'name': 'Equity Multiplier',
        'category': 'leverage',
        'formula': 'Total Assets / Total Equity',
        'numerator': 'total_assets',
        'denominator': 'total_equity',
    },
    {
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
        'name': 'Gross Margin',
        'category': 'profitability',
        'formula': 'Gross Profit / Revenue',
        'numerator': 'gross_profit',
        'denominator': 'revenue',
    },
    {
        'name': 'Operating Margin',
        'category': 'profitability',
        'formula': 'Operating Income / Revenue',
        'numerator': 'operating_income',
        'denominator': 'revenue',
    },
    {
        'name': 'Net Profit Margin',
        'category': 'profitability',
        'formula': 'Net Income / Revenue',
        'numerator': 'net_income',
        'denominator': 'revenue',
    },
    {
        'name': 'Return on Assets',
        'category': 'profitability',
        'formula': 'Net Income / Total Assets',
        'numerator': 'net_income',
        'denominator': 'total_assets',
    },
    {
        'name': 'Return on Equity',
        'category': 'profitability',
        'formula': 'Net Income / Total Equity',
        'numerator': 'net_income',
        'denominator': 'total_equity',
    },
    {
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
        'name': 'Asset Turnover',
        'category': 'efficiency',
        'formula': 'Revenue / Total Assets',
        'numerator': 'revenue',
        'denominator': 'total_assets',
    },
    {
        'name': 'Inventory Turnover',
        'category': 'efficiency',
        'formula': 'Cost of Goods Sold / Inventory',
        'numerator': 'cost_of_goods_sold',
        'denominator': 'inventory',
    },
    {
        'name': 'Receivables Turnover',
        'category': 'efficiency',
        'formula': 'Revenue / Accounts Receivable',
        'numerator': 'revenue',
        'denominator': 'accounts_receivable',
    },
    {
        'name': 'Payables Turnover',
        'category': 'efficiency',
        'formula': 'Cost of Goods Sold / Accounts Payable',
        'numerator': 'cost_of_goods_sold',
        'denominator': 'accounts_payable',
    },
]


__all__ = ['STANDARD_RATIOS']
