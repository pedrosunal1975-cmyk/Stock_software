# Path: mat_acc/ratio_check/ratio_defs_extended.py
"""
Extended Ratio Definitions

Additional financial ratios beyond core set. Organized by category,
using existing matched components. No new component YAMLs required.

References:
  - Penman, Financial Statement Analysis & Security Valuation
  - Palepu/Healy, Business Analysis and Valuation
  - Damodaran, Investment Valuation
  - CFA Institute, Financial Reporting and Analysis
"""

EXTENDED_RATIOS = [
    # --- LIQUIDITY ---
    {
        'ratio_id': 'working_capital',
        'name': 'Working Capital',
        'category': 'liquidity',
        'formula': 'Current Assets - Current Liabilities',
        'numerator': ['current_assets', '-current_liabilities'],
        'denominator': None,
        'calculation_type': 'absolute',
    },
    # --- LEVERAGE ---
    {
        'ratio_id': 'debt_to_ebitda',
        'name': 'Debt to EBITDA',
        'category': 'leverage',
        'formula': 'Total Liabilities / EBITDA',
        'numerator': 'total_liabilities',
        'denominator': 'ebitda',
    },
    {
        'ratio_id': 'long_term_debt_to_equity',
        'name': 'Long-term Debt to Equity',
        'category': 'leverage',
        'formula': 'Long-term Debt / Total Equity',
        'numerator': 'long_term_debt',
        'denominator': 'total_equity',
    },
    # --- PROFITABILITY ---
    {
        'ratio_id': 'effective_tax_rate',
        'name': 'Effective Tax Rate',
        'category': 'profitability',
        'formula': 'Income Tax Expense / Income Before Tax',
        'numerator': 'income_tax_expense',
        'denominator': 'income_before_tax',
    },
    {
        'ratio_id': 'return_on_capital_employed',
        'name': 'Return on Capital Employed',
        'category': 'profitability',
        'formula': 'Operating Income / (Total Assets - Current Liabilities)',
        'numerator': 'operating_income',
        'denominator': ['total_assets', '-current_liabilities'],
    },
    # --- EFFICIENCY ---
    {
        'ratio_id': 'days_inventory_outstanding',
        'name': 'Days Inventory Outstanding',
        'category': 'efficiency',
        'formula': '(Inventory / Cost of Goods Sold) * 365',
        'numerator': 'inventory',
        'denominator': 'cost_of_goods_sold',
        'scale_factor': 365,
    },
    {
        'ratio_id': 'days_sales_outstanding',
        'name': 'Days Sales Outstanding',
        'category': 'efficiency',
        'formula': '(Accounts Receivable / Revenue) * 365',
        'numerator': 'accounts_receivable',
        'denominator': 'revenue',
        'scale_factor': 365,
    },
    {
        'ratio_id': 'days_payable_outstanding',
        'name': 'Days Payable Outstanding',
        'category': 'efficiency',
        'formula': '(Accounts Payable / Cost of Goods Sold) * 365',
        'numerator': 'accounts_payable',
        'denominator': 'cost_of_goods_sold',
        'scale_factor': 365,
    },
    {
        'ratio_id': 'cash_conversion_cycle',
        'name': 'Cash Conversion Cycle',
        'category': 'efficiency',
        'formula': 'DIO + DSO - DPO',
        'calculation_type': 'cash_conversion_cycle',
        'components': [
            'inventory', 'cost_of_goods_sold',
            'accounts_receivable', 'revenue',
            'accounts_payable',
        ],
    },
    # --- CASH FLOW QUALITY ---
    {
        'ratio_id': 'free_cash_flow_margin',
        'name': 'Free Cash Flow Margin',
        'category': 'cash_flow_quality',
        'formula': '(Operating Cash Flow - CapEx) / Revenue',
        'numerator': ['operating_cash_flow', '-capital_expenditures'],
        'denominator': 'revenue',
    },
    {
        'ratio_id': 'cash_flow_to_debt',
        'name': 'Cash Flow to Debt',
        'category': 'cash_flow_quality',
        'formula': 'Operating Cash Flow / Total Liabilities',
        'numerator': 'operating_cash_flow',
        'denominator': 'total_liabilities',
    },
    {
        'ratio_id': 'capex_coverage',
        'name': 'CapEx Coverage',
        'category': 'cash_flow_quality',
        'formula': 'Operating Cash Flow / Capital Expenditures',
        'numerator': 'operating_cash_flow',
        'denominator': 'capital_expenditures',
    },
    # --- CAPITAL ALLOCATION ---
    {
        'ratio_id': 'capex_to_revenue',
        'name': 'CapEx to Revenue',
        'category': 'capital_allocation',
        'formula': 'Capital Expenditures / Revenue',
        'numerator': 'capital_expenditures',
        'denominator': 'revenue',
    },
    {
        'ratio_id': 'fixed_asset_turnover',
        'name': 'Fixed Asset Turnover',
        'category': 'capital_allocation',
        'formula': 'Revenue / Property Plant and Equipment',
        'numerator': 'revenue',
        'denominator': 'property_plant_equipment',
    },
    # --- OPERATING LEVERAGE ---
    {
        'ratio_id': 'r_and_d_to_sga',
        'name': 'R&D to SG&A',
        'category': 'operating_leverage',
        'formula': 'R&D Expense / SG&A',
        'numerator': 'r_and_d_expense',
        'denominator': 'selling_general_admin',
    },
    # --- PER SHARE ---
    {
        'ratio_id': 'book_value_per_share',
        'name': 'Book Value per Share',
        'category': 'per_share',
        'formula': 'Total Equity / Shares Outstanding',
        'numerator': 'total_equity',
        'denominator': 'shares_outstanding',
    },
    {
        'ratio_id': 'operating_cf_per_share',
        'name': 'Operating Cash Flow per Share',
        'category': 'per_share',
        'formula': 'Operating Cash Flow / Shares Outstanding',
        'numerator': 'operating_cash_flow',
        'denominator': 'shares_outstanding',
    },
]


__all__ = ['EXTENDED_RATIOS']
