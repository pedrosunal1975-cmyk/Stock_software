# Path: mat_acc/ratio_check/match_verify/fallback_patterns.py
"""
Fallback Concept Patterns

Keyword patterns for concept index scan when matcher alternatives
are exhausted. Uses ConceptIndex.find_by_local_name() wildcards.

These are universal (not company-specific) — they target standard
XBRL taxonomy naming patterns across US-GAAP, IFRS, and extensions.
"""


# component_id -> list of local_name wildcard patterns
FALLBACK_PATTERNS = {
    'capital_expenditures': [
        '*PaymentsToAcquirePropertyPlantAndEquipment*',
        '*CapitalExpenditure*',
        '*PurchaseOfPropertyPlantAndEquipment*',
    ],
    'long_term_debt': [
        '*LongTermDebt*',
        '*LongTermBorrowing*',
        '*NoncurrentBorrowing*',
        '*ConvertibleLongTermNotesPayable*',
    ],
    'total_liabilities': [
        '*Liabilities',
        '*LiabilitiesAndStockholdersEquity*',
    ],
    'depreciation_amortization': [
        '*DepreciationAndAmortization*',
        '*DepreciationDepletionAndAmortization*',
        '*DepreciationAmortization*',
    ],
    'revenue': [
        '*Revenue*',
        '*Revenues*',
        '*Turnover*',
    ],
    'net_income': [
        '*NetIncomeLoss*',
        '*ProfitLoss*',
        '*NetIncome*',
    ],
    'operating_income': [
        '*OperatingIncomeLoss*',
        '*OperatingProfit*',
    ],
    'total_equity': [
        '*StockholdersEquity*',
        '*Equity',
    ],
    'total_assets': [
        '*Assets',
    ],
    'interest_expense': [
        '*InterestExpense*',
        '*FinanceCost*',
    ],
}


__all__ = ['FALLBACK_PATTERNS']
