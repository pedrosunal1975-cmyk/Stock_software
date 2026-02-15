# Industry-Specific Ratio Models - Implementation Plan

## Overview

Add industry auto-detection and industry-specific ratio calculation models
to mat_acc. The existing matching engine, MIU, evaluators, and value pipeline
remain unchanged. Only the ratio definition layer and component dictionary
are extended.

## Architecture Principle

```
EXISTING (unchanged)          NEW (added)
========================      ========================
Filing Selection              Industry Detector
Value Loading                 Industry Ratio Registry
MIU (3 layers)                Industry-Specific Components
Concept Builder               Industry-Specific Formulas
Matching Engine (5 eval)      Industry Identity Checks
Value Populator (4 pass)
Score Aggregator
```

The industry layer sits BETWEEN filing selection and ratio calculation.
It decides WHICH components to match and WHICH ratios to compute.

---

## Step 1: Industry Detector

**New file:** `mat_acc/ratio_check/industry_detector.py` (~120 lines)

**Purpose:** Auto-detect industry group from XBRL concepts in the filing.

**Method:** Concept fingerprinting. Each industry has signature concepts
that ONLY appear in that sector's filings:

```python
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
        'threshold': 3,  # need 3+ strong OR 5+ moderate
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
```

**Detection logic:**
1. Scan all concept local_names in the ConceptIndex
2. Count matches against each industry's signal patterns (contains match)
3. Pick industry with highest signal count above threshold
4. Default to 'general' if no industry signals detected

**Interface:**
```python
class IndustryDetector:
    def detect(self, concept_index: ConceptIndex) -> str:
        """Returns: 'general', 'banking', 'insurance', or 'reit'"""

    def get_signals_found(self) -> dict[str, list[str]]:
        """Returns matched signals for logging/diagnostics."""
```

**Output logged at INFO level:**
```
[INFO] Industry detected: banking (7 signals: InterestIncomeExpenseNet, ...)
```

---

## Step 2: Industry Ratio Registry

**New file:** `mat_acc/ratio_check/industry_registry.py` (~80 lines)

**Purpose:** Maps industry type to its ratio model configuration.

```python
INDUSTRY_MODELS = {
    'general': {
        'display_name': 'General / Industrial',
        'components': 'all',           # use all 26 existing components
        'ratios': 'standard',          # use all 17 existing ratios
        'extra_components': [],        # no extras needed
        'extra_ratios': [],            # no extras needed
        'skip_ratios': [],             # don't skip any
        'identity_checks': 'standard', # A=L+E, GP=R-COGS, etc.
    },
    'banking': {
        'display_name': 'Banking / Financial Institution',
        'components': 'all',
        'ratios': 'standard',
        'skip_ratios': [               # skip inapplicable standard ratios
            'gross_margin',
            'inventory_turnover',
            'payables_turnover',
            'quick_ratio',
        ],
        'extra_components': [          # new components to match
            'net_interest_income',
            'provision_for_loan_losses',
            'total_loans',
            'total_deposits',
            'noninterest_income',
            'noninterest_expense',
        ],
        'extra_ratios': [              # new ratio formulas
            'net_interest_margin',
            'loan_to_deposit',
            'provision_coverage',
            'efficiency_ratio',
            'noninterest_income_ratio',
        ],
        'identity_checks': 'standard',
    },
    'insurance': {
        'display_name': 'Insurance',
        'components': 'all',
        'ratios': 'standard',
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
            'loss_ratio',
            'expense_ratio',
            'combined_ratio',
            'investment_yield',
            'premium_to_surplus',
        ],
        'identity_checks': 'standard',
    },
    'reit': {
        'display_name': 'Real Estate Investment Trust',
        'components': 'all',
        'ratios': 'standard',
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
            'ffo_per_share',
            'price_to_ffo',
            'ffo_payout_ratio',
        ],
        'identity_checks': 'standard',
    },
}
```

**Interface:**
```python
class IndustryRegistry:
    def get_model(self, industry: str) -> dict:
        """Returns model config for given industry."""

    def get_all_component_ids(self, industry: str) -> list[str]:
        """Returns base + extra component IDs for the industry."""

    def get_applicable_ratios(self, industry: str) -> list[dict]:
        """Returns standard ratios (minus skipped) + extra ratios."""
```

---

## Step 3: Industry-Specific Component Definitions

**New directories under existing structure:**

```
mat_acc/dictionary/components/
├── balance_sheet/          (existing - unchanged)
├── income_statement/       (existing - unchanged)
├── cash_flow/              (existing - unchanged)
├── per_share/              (existing - unchanged)
├── banking/                (NEW)
│   ├── net_interest_income.yaml
│   ├── provision_for_loan_losses.yaml
│   ├── total_loans.yaml
│   ├── total_deposits.yaml
│   ├── noninterest_income.yaml
│   └── noninterest_expense.yaml
├── insurance/              (NEW)
│   ├── premiums_earned.yaml
│   ├── claims_incurred.yaml
│   ├── policy_acquisition_costs.yaml
│   ├── investment_income.yaml
│   └── unearned_premiums.yaml
└── reit/                   (NEW)
    ├── funds_from_operations.yaml
    ├── rental_revenue.yaml
    └── real_estate_assets.yaml
```

Each YAML uses the EXACT same format as existing components.
The matching engine processes them identically - no code changes needed.

**Example: `banking/net_interest_income.yaml`:**
```yaml
component_id: net_interest_income
display_name: "Net Interest Income"
description: "Interest income minus interest expense. Primary revenue for banks."

category: income_statement
subcategory: banking

characteristics:
  balance_type: credit
  period_type: duration
  is_monetary: true
  is_abstract: false
  data_type: monetary

matching_rules:
  label_rules:
    - patterns:
        - "Net Interest Income"
        - "Interest Income, Net"
      match_type: exact
      case_sensitive: false
      weight: 20
    - patterns:
        - "net interest income"
        - "interest income after provision"
      match_type: contains
      case_sensitive: false
      weight: 12

  local_name_rules:
    - patterns:
        - "InterestIncomeExpenseNet"
        - "NetInterestIncome"
        - "InterestIncomeExpenseAfterProvisionForLoanLoss"
      match_type: exact
      weight: 20

scoring:
  min_score: 18
  confidence_levels:
    high: 35
    medium: 27
    low: 18
  tiebreaker: highest_in_hierarchy
  reject_if:
    - condition: "Is abstract concept"
      pattern: "abstract=true"
    - condition: "Is text block"
      pattern: "name~textblock"
    - condition: "Is schedule"
      pattern: "name~schedule"

composition:
  is_composite: false
```

---

## Step 4: Industry-Specific Ratio Formulas

**New directories under existing structure:**

```
mat_acc/dictionary/formulas/
├── liquidity/              (existing - unchanged)
├── leverage/               (existing - unchanged)
├── profitability/          (existing - unchanged)
├── efficiency/             (existing - unchanged)
├── banking/                (NEW)
│   ├── net_interest_margin.yaml
│   ├── loan_to_deposit.yaml
│   ├── provision_coverage.yaml
│   ├── efficiency_ratio.yaml
│   └── noninterest_income_ratio.yaml
├── insurance/              (NEW)
│   ├── loss_ratio.yaml
│   ├── expense_ratio.yaml
│   ├── combined_ratio.yaml
│   ├── investment_yield.yaml
│   └── premium_to_surplus.yaml
└── reit/                   (NEW)
    ├── ffo_per_share.yaml
    ├── price_to_ffo.yaml
    └── ffo_payout_ratio.yaml
```

**Example: `banking/net_interest_margin.yaml`:**
```yaml
ratio_id: net_interest_margin
display_name: "Net Interest Margin"
category: banking

formula:
  expression: "net_interest_income / total_assets"
  components:
    - net_interest_income
    - total_assets

interpretation:
  healthy_range: {min: 0.02, max: 0.04}
  direction: higher_is_better
  context: "Measures how effectively a bank earns from lending vs borrowing"
```

---

## Step 5: Integration into Pipeline

**Modified file:** `mat_acc/ratio_check/ratio_check.py`

Only the orchestration changes. Insert industry detection AFTER concept
building, BEFORE matching:

```
Current flow:
  1. Filing selection
  2. Value loading
  3. MIU verification
  4. Concept building
  5. Match ALL 26 components        <-- CHANGE HERE
  6. Calculate ALL 17 ratios        <-- CHANGE HERE
  7. Identity validation
  8. Display

New flow:
  1. Filing selection
  2. Value loading
  3. MIU verification
  4. Concept building
  5. INDUSTRY DETECTION              <-- NEW
  6. Load base + industry components <-- CHANGED
  7. Match components
  8. Calculate applicable ratios     <-- CHANGED
  9. Identity validation
  10. Display (with industry label)  <-- CHANGED
```

**Changes to ratio_check.py (~30 lines added):**

```python
# After concept building, before matching:
detector = IndustryDetector()
industry = detector.detect(concept_index)
registry = IndustryRegistry()
model = registry.get_model(industry)

print(f"\n  Industry: {model['display_name']}")

# Load components: base + industry-specific
components = self.component_loader.load_all()  # existing 26
if model['extra_components']:
    industry_components = self.component_loader.load_industry(industry)
    components.update(industry_components)

# Match all loaded components (engine unchanged)
resolution = coordinator.resolve_all(concept_index)

# Calculate ratios: standard (minus skipped) + industry extras
applicable_ratios = registry.get_applicable_ratios(industry)
ratio_results = ratio_engine.calculate(applicable_ratios, resolution)
```

**Changes to component_loader.py (~15 lines added):**

```python
def load_industry(self, industry: str) -> dict:
    """Load industry-specific component definitions."""
    industry_path = self.dictionary_path / 'components' / industry
    if not industry_path.exists():
        return {}
    return self._load_from_directory(industry_path)
```

**Changes to ratio_engine.py (~10 lines added):**

Pass the applicable ratio list instead of hardcoded STANDARD_RATIOS.

**Changes to display/output (~5 lines):**

Show industry type in header and adjust "100%" benchmark.

---

## Step 6: Display Changes

**Current output:**
```
  SUMMARY:
    Components: 23/26 matched (88.5%)
    Ratios: 13/17 calculated
```

**New output for Mastercard (banking-adjacent, detected as general/services):**
```
  Industry: General / Services
  SUMMARY:
    Components: 23/23 applicable matched (100.0%)
    Ratios: 13/13 applicable calculated (100.0%)
    Skipped: gross_profit, cost_of_goods_sold, inventory (not applicable)
```

**New output for JPMorgan (banking):**
```
  Industry: Banking / Financial Institution
  SUMMARY:
    Components: 20/20 applicable matched (100.0%)
    Standard Ratios: 10/10 calculated
    Banking Ratios: 5/5 calculated
    Total: 15/15 ratios (100.0%)
```

---

## Implementation Order

### Phase A: Foundation (Steps 1-2)
1. Create `industry_detector.py` with concept fingerprinting
2. Create `industry_registry.py` with model definitions
3. Integrate detection into ratio_check.py (display only, no behavior change)
4. Test: verify detection works for all 8 existing filings

### Phase B: Banking Model (Steps 3-5 for banking only)
5. Create 6 banking component YAMLs
6. Create 5 banking ratio formula YAMLs
7. Modify component_loader to load industry components
8. Modify ratio_engine to accept filtered ratio list
9. Test with a bank filing (need to add one to test data)

### Phase C: Insurance + REIT Models
10. Create insurance component + formula YAMLs
11. Create REIT component + formula YAMLs
12. Test with sample filings

### Phase D: Refinement
13. Add industry-specific identity checks if needed
14. Tune detection signals against more filings
15. Adjust display to show industry-aware percentages

---

## Files Changed (Existing)

| File | Change | Lines |
|------|--------|-------|
| ratio_check.py | Add industry detection call + display | ~30 |
| component_loader.py | Add load_industry() method | ~15 |
| ratio_engine.py | Accept filtered ratio list | ~10 |
| ratio_definitions.py | Export ratios as filterable dict | ~10 |
| Output display | Show industry + adjusted percentages | ~10 |

## Files Created (New)

| File | Purpose | Lines |
|------|---------|-------|
| industry_detector.py | Auto-detect from concepts | ~120 |
| industry_registry.py | Model configurations | ~80 |
| banking/*.yaml (6) | Banking components | ~100 each |
| banking/*.yaml (5) | Banking ratios | ~30 each |
| insurance/*.yaml (5+5) | Insurance components + ratios | ~100+30 |
| reit/*.yaml (3+3) | REIT components + ratios | ~100+30 |

## What Does NOT Change

- Matching engine (coordinator.py, evaluators, scoring, tiebreaker)
- MIU (all 3 layers)
- Value pipeline (fact_value_lookup, value_populator)
- Concept builder
- Component definition format (YAML schema)
- Formula definition format (YAML schema)
- Database layer
- Source loaders (mapped, parsed, XBRL)

---

## Key Design Decision: Services/Tech Sub-Type

Mastercard-type companies (services, tech, payment networks) don't need
a separate model. They use the 'general' model, but the 3 components
that don't exist (gross_profit, cost_of_goods_sold, inventory) are
correctly unmatched. The display should show "23/23 applicable" not
"23/26 total" by detecting which components have no possible match.

**Approach:** After matching, any component with 0 candidates AND
no concept in the index matching ANY of its local_name patterns is
marked as "not applicable" rather than "unmatched". This is a display
change, not a model change.

```python
# In ratio_engine or display:
for component in unmatched:
    if component.best_score == 0 and component.candidates_found == 0:
        status = 'not_applicable'  # No concept exists in filing
    else:
        status = 'unmatched'       # Concept exists but didn't score enough
```

This naturally handles all service/tech companies without a separate model.
