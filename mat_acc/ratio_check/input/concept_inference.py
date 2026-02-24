# Path: mat_acc/ratio_check/input/concept_inference.py
"""
Concept Inference Utilities

Pure functions for inferring XBRL concept metadata from naming
patterns. Used by concept_builder and concept_enricher.

All heuristics are taxonomy-agnostic (work with US-GAAP, IFRS,
UK-GAAP, company extensions) because they operate on local
concept names which follow universal accounting conventions.
"""
import re
from typing import Optional


def local_name_to_label(local_name: str) -> str:
    """
    Convert CamelCase local name to human-readable label.

    E.g., "AssetsCurrent" -> "Assets Current"
         "TotalLiabilities" -> "Total Liabilities"
    """
    spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', local_name)
    spaced = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', spaced)
    return spaced


def infer_balance_type(local_name: str) -> Optional[str]:
    """
    Infer balance type from concept name.

    Priority order prevents misclassification of compound names:
    - "IncomeTaxExpenseBenefit" -> debit (expense overrides income)
    - "NetIncomeLoss" -> credit (income is primary concept)
    - "CostOfGoodsSold" -> debit (cost is primary concept)
    """
    local_lower = local_name.lower()

    # Strong debit indicators - checked FIRST because they override
    # generic credit keywords in compound names
    strong_debit = [
        'expense', 'cost', 'purchase', 'payment',
        'depreciation', 'amortization', 'prepaid',
    ]
    for pattern in strong_debit:
        if pattern in local_lower:
            return 'debit'

    # Credit indicators
    credit_patterns = [
        'liabilities', 'liability', 'revenue', 'income', 'gain',
        'payable', 'equity', 'capital', 'retained', 'earnings',
        'accumulated', 'provision', 'reserve', 'profit',
    ]
    for pattern in credit_patterns:
        if pattern in local_lower:
            return 'credit'

    # Remaining debit indicators
    debit_patterns = [
        'assets', 'loss', 'receivable',
        'inventory', 'equipment', 'property',
        'dividend',
    ]
    for pattern in debit_patterns:
        if pattern in local_lower:
            return 'debit'

    return None


def infer_period_type(local_name: str) -> Optional[str]:
    """
    Infer period type from concept name.

    Priority order prevents misclassification:
    - "PaymentsToAcquirePropertyPlantAndEquipment" -> duration
      (cash flow action word overrides balance sheet noun)
    """
    local_lower = local_name.lower()

    # Strong duration indicators - checked FIRST because cash flow
    # action words override balance sheet nouns in compound names.
    # "cashflow" catches CashFlowsFrom... before "cash" triggers instant.
    strong_duration = [
        'cashflow', 'payment', 'proceeds', 'purchase',
        'repayment', 'issuance', 'acquisition',
    ]
    for pattern in strong_duration:
        if pattern in local_lower:
            return 'duration'

    # Instant indicators (balance sheet items)
    instant_patterns = [
        'assets', 'liabilities', 'equity', 'balance',
        'receivable', 'payable', 'inventory', 'cash',
        'property', 'equipment', 'accumulated',
    ]
    for pattern in instant_patterns:
        if pattern in local_lower:
            return 'instant'

    # Duration indicators (income statement items)
    duration_patterns = [
        'revenue', 'expense', 'income', 'cost', 'sales',
        'gain', 'loss', 'earnings', 'profit', 'margin',
    ]
    for pattern in duration_patterns:
        if pattern in local_lower:
            return 'duration'

    return None


__all__ = [
    'local_name_to_label',
    'infer_balance_type',
    'infer_period_type',
]
