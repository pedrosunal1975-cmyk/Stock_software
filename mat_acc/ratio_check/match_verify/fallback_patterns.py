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
    # --- Balance sheet ---
    'total_assets': [
        '*Assets',
    ],
    'current_assets': [
        '*AssetsCurrent*',
        '*CurrentAssets*',
    ],
    'total_liabilities': [
        '*Liabilities',
        '*LiabilitiesAndStockholdersEquity*',
    ],
    'current_liabilities': [
        '*LiabilitiesCurrent*',
        '*CurrentLiabilities*',
    ],
    'total_equity': [
        '*StockholdersEquity*',
        '*Equity',
        '*ShareholdersEquity*',
    ],
    'cash_and_equivalents': [
        '*CashAndCashEquivalent*',
        '*CashAndDueFromBanks*',
        '*CashCashEquivalent*',
    ],
    'inventory': [
        '*InventoryNet*',
        '*InventoryFinishedGoods*',
        '*Inventories*',
    ],
    'accounts_receivable': [
        '*AccountsReceivableNet*',
        '*TradeAndOtherReceivable*',
        '*TradeReceivable*',
    ],
    'accounts_payable': [
        '*AccountsPayable*',
        '*TradeAndOtherPayable*',
        '*TradePayable*',
    ],
    'long_term_debt': [
        '*LongTermDebt*',
        '*LongTermBorrowing*',
        '*NoncurrentBorrowing*',
        '*ConvertibleLongTermNotesPayable*',
    ],
    'short_term_debt': [
        '*ShortTermBorrowing*',
        '*ShortTermDebt*',
        '*CurrentPortionOfLongTermDebt*',
    ],
    'total_debt': [
        '*DebtCurrent*',
        '*LongTermDebt*',
        '*TotalDebt*',
    ],
    # --- Income statement ---
    'revenue': [
        '*Revenue*',
        '*Revenues*',
        '*Turnover*',
        '*SalesRevenueNet*',
    ],
    'cost_of_goods_sold': [
        '*CostOfRevenue*',
        '*CostOfGoodsAndServicesSold*',
        '*CostOfGoodsSold*',
        '*CostOfSales*',
    ],
    'gross_profit': [
        '*GrossProfit*',
    ],
    'operating_income': [
        '*OperatingIncomeLoss*',
        '*OperatingProfit*',
    ],
    'income_before_tax': [
        '*IncomeLossFromContinuingOperationsBefore*',
        '*ProfitBeforeTax*',
        '*IncomeBeforeIncomeTax*',
    ],
    'income_tax_expense': [
        '*IncomeTaxExpense*',
        '*IncomeTaxesPaid*',
        '*TaxExpense*',
    ],
    'net_income': [
        '*NetIncomeLoss*',
        '*ProfitLoss*',
        '*NetIncome*',
    ],
    'interest_expense': [
        '*InterestExpense*',
        '*FinanceCost*',
    ],
    'ebitda': [
        '*EarningsBeforeInterestTaxes*',
    ],
    'earnings_per_share': [
        '*EarningsPerShareDiluted*',
        '*EarningsPerShareBasic*',
    ],
    'shares_outstanding': [
        '*CommonSharesOutstanding*',
        '*SharesOutstanding*',
        '*WeightedAverageShares*',
    ],
    # --- Cash flow ---
    'capital_expenditures': [
        '*PaymentsToAcquirePropertyPlantAndEquipment*',
        '*CapitalExpenditure*',
        '*PurchaseOfPropertyPlantAndEquipment*',
    ],
    'depreciation_amortization': [
        '*DepreciationAndAmortization*',
        '*DepreciationDepletionAndAmortization*',
        '*DepreciationAmortization*',
    ],
    'operating_cash_flow': [
        '*NetCashProvidedByOperatingActivities*',
        '*CashFlowsFromOperatingActivities*',
        '*OperatingActivitiesCashFlow*',
    ],
    'dividends_paid': [
        '*PaymentsOfDividends*',
        '*DividendsPaid*',
        '*PaymentsOfOrdinaryDividends*',
    ],
}


__all__ = ['FALLBACK_PATTERNS']
