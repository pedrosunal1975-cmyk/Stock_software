# Path: verification/tests/fixtures.py
"""
Test Fixtures for Verification Module v2

Sample XBRL data structures for internal pipeline testing.
Creates realistic parsed.json data that exercises all pipeline stages.

Contains:
- Sample facts with various attributes (positive, negative, nil)
- Sample contexts (instant, duration, dimensional)
- Sample units (currency, shares, ratios)
- Sample calculations (parent-child with weights)
"""

import json
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class TestFilingFixture:
    """Container for a test filing with all data."""
    name: str
    parsed_data: dict
    expected_facts: int
    expected_contexts: int
    expected_calculations: int
    temp_dir: Optional[Path] = None

    def create_temp_file(self) -> Path:
        """Create temporary parsed.json file."""
        if self.temp_dir is None:
            self.temp_dir = Path(tempfile.mkdtemp(prefix='verification_test_'))

        parsed_json = self.temp_dir / 'parsed.json'
        with open(parsed_json, 'w', encoding='utf-8') as f:
            json.dump(self.parsed_data, f, indent=2)

        return parsed_json

    def cleanup(self):
        """Remove temporary files."""
        import shutil
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


def create_simple_balance_sheet_fixture() -> TestFilingFixture:
    """
    Create a simple balance sheet fixture.

    Contains:
    - Assets = CurrentAssets + NoncurrentAssets
    - CurrentAssets = Cash + Receivables + Inventory
    - Liabilities = CurrentLiabilities + NoncurrentLiabilities
    - Equity = RetainedEarnings + CommonStock
    - Assets = Liabilities + Equity (fundamental equation)
    """
    parsed_data = {
        'metadata': {
            'entry_point': 'test-filing.htm',
            'taxonomy_references': ['us-gaap-2023'],
        },
        'namespaces': {
            'us-gaap': 'http://fasb.org/us-gaap/2023',
            'dei': 'http://xbrl.sec.gov/dei/2023',
        },
        'facts': [
            # Current Assets breakdown
            {
                'concept': 'us-gaap:CashAndCashEquivalents',
                'value': 50000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:AccountsReceivableNet',
                'value': 30000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:InventoryNet',
                'value': 20000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:AssetsCurrent',
                'value': 100000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Noncurrent Assets
            {
                'concept': 'us-gaap:PropertyPlantAndEquipmentNet',
                'value': 150000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:Goodwill',
                'value': 50000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:AssetsNoncurrent',
                'value': 200000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Total Assets
            {
                'concept': 'us-gaap:Assets',
                'value': 300000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Liabilities
            {
                'concept': 'us-gaap:AccountsPayable',
                'value': 25000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:LiabilitiesCurrent',
                'value': 50000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:LongTermDebt',
                'value': 100000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:LiabilitiesNoncurrent',
                'value': 100000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:Liabilities',
                'value': 150000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Equity
            {
                'concept': 'us-gaap:CommonStockValue',
                'value': 50000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:RetainedEarningsAccumulatedDeficit',
                'value': 100000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:StockholdersEquity',
                'value': 150000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Total Liabilities + Equity
            {
                'concept': 'us-gaap:LiabilitiesAndStockholdersEquity',
                'value': 300000000,
                'context_id': 'c_20231231_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
        ],
        'contexts': {
            'c_20231231_instant': {
                'period_type': 'instant',
                'instant': '2023-12-31',
                'entity': '0001234567',
            },
            'c_20221231_instant': {
                'period_type': 'instant',
                'instant': '2022-12-31',
                'entity': '0001234567',
            },
        },
        'units': {
            'USD': {'measure': 'iso4217:USD'},
            'shares': {'measure': 'xbrli:shares'},
        },
        'calculations': {
            'http://example.com/role/BalanceSheet': {
                'trees': [
                    {
                        'concept': 'us-gaap:Assets',
                        'children': [
                            {'concept': 'us-gaap:AssetsCurrent', 'weight': 1.0, 'order': 1},
                            {'concept': 'us-gaap:AssetsNoncurrent', 'weight': 1.0, 'order': 2},
                        ],
                    },
                    {
                        'concept': 'us-gaap:AssetsCurrent',
                        'children': [
                            {'concept': 'us-gaap:CashAndCashEquivalents', 'weight': 1.0, 'order': 1},
                            {'concept': 'us-gaap:AccountsReceivableNet', 'weight': 1.0, 'order': 2},
                            {'concept': 'us-gaap:InventoryNet', 'weight': 1.0, 'order': 3},
                        ],
                    },
                    {
                        'concept': 'us-gaap:AssetsNoncurrent',
                        'children': [
                            {'concept': 'us-gaap:PropertyPlantAndEquipmentNet', 'weight': 1.0, 'order': 1},
                            {'concept': 'us-gaap:Goodwill', 'weight': 1.0, 'order': 2},
                        ],
                    },
                    {
                        'concept': 'us-gaap:Liabilities',
                        'children': [
                            {'concept': 'us-gaap:LiabilitiesCurrent', 'weight': 1.0, 'order': 1},
                            {'concept': 'us-gaap:LiabilitiesNoncurrent', 'weight': 1.0, 'order': 2},
                        ],
                    },
                    {
                        'concept': 'us-gaap:StockholdersEquity',
                        'children': [
                            {'concept': 'us-gaap:CommonStockValue', 'weight': 1.0, 'order': 1},
                            {'concept': 'us-gaap:RetainedEarningsAccumulatedDeficit', 'weight': 1.0, 'order': 2},
                        ],
                    },
                    {
                        'concept': 'us-gaap:LiabilitiesAndStockholdersEquity',
                        'children': [
                            {'concept': 'us-gaap:Liabilities', 'weight': 1.0, 'order': 1},
                            {'concept': 'us-gaap:StockholdersEquity', 'weight': 1.0, 'order': 2},
                        ],
                    },
                ],
            },
        },
    }

    return TestFilingFixture(
        name='SimpleBalanceSheet',
        parsed_data=parsed_data,
        expected_facts=17,
        expected_contexts=2,
        expected_calculations=13,  # Total children in all trees
    )


def create_income_statement_fixture() -> TestFilingFixture:
    """
    Create an income statement fixture with sign corrections.

    Contains:
    - Revenues (positive)
    - CostOfGoodsSold (negative weight, should be subtracted)
    - GrossProfit = Revenues - CostOfGoodsSold
    - OperatingExpenses (negative weight)
    - OperatingIncome = GrossProfit - OperatingExpenses
    """
    parsed_data = {
        'metadata': {
            'entry_point': 'test-income.htm',
            'taxonomy_references': ['us-gaap-2023'],
        },
        'namespaces': {
            'us-gaap': 'http://fasb.org/us-gaap/2023',
        },
        'facts': [
            # Revenues
            {
                'concept': 'us-gaap:Revenues',
                'value': 500000000,
                'context_id': 'c_2023_duration',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Cost of Goods Sold (reported as positive, weight is -1)
            {
                'concept': 'us-gaap:CostOfGoodsSold',
                'value': 300000000,
                'context_id': 'c_2023_duration',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Gross Profit
            {
                'concept': 'us-gaap:GrossProfit',
                'value': 200000000,
                'context_id': 'c_2023_duration',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Operating Expenses
            {
                'concept': 'us-gaap:OperatingExpenses',
                'value': 100000000,
                'context_id': 'c_2023_duration',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Operating Income
            {
                'concept': 'us-gaap:OperatingIncomeLoss',
                'value': 100000000,
                'context_id': 'c_2023_duration',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Interest Expense (with sign="-" in iXBRL)
            {
                'concept': 'us-gaap:InterestExpense',
                'value': 10000000,
                'context_id': 'c_2023_duration',
                'unit_ref': 'USD',
                'decimals': -3,
                'sign': '-',
            },
            # Net Income
            {
                'concept': 'us-gaap:NetIncomeLoss',
                'value': 90000000,
                'context_id': 'c_2023_duration',
                'unit_ref': 'USD',
                'decimals': -3,
            },
        ],
        'contexts': {
            'c_2023_duration': {
                'period_type': 'duration',
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'entity': '0001234567',
            },
        },
        'units': {
            'USD': {'measure': 'iso4217:USD'},
        },
        'calculations': {
            'http://example.com/role/IncomeStatement': {
                'trees': [
                    {
                        'concept': 'us-gaap:GrossProfit',
                        'children': [
                            {'concept': 'us-gaap:Revenues', 'weight': 1.0, 'order': 1},
                            {'concept': 'us-gaap:CostOfGoodsSold', 'weight': -1.0, 'order': 2},
                        ],
                    },
                    {
                        'concept': 'us-gaap:OperatingIncomeLoss',
                        'children': [
                            {'concept': 'us-gaap:GrossProfit', 'weight': 1.0, 'order': 1},
                            {'concept': 'us-gaap:OperatingExpenses', 'weight': -1.0, 'order': 2},
                        ],
                    },
                    {
                        'concept': 'us-gaap:NetIncomeLoss',
                        'children': [
                            {'concept': 'us-gaap:OperatingIncomeLoss', 'weight': 1.0, 'order': 1},
                            {'concept': 'us-gaap:InterestExpense', 'weight': -1.0, 'order': 2},
                        ],
                    },
                ],
            },
        },
    }

    return TestFilingFixture(
        name='IncomeStatementWithSigns',
        parsed_data=parsed_data,
        expected_facts=7,
        expected_contexts=1,
        expected_calculations=6,
    )


def create_dimensional_fixture() -> TestFilingFixture:
    """
    Create a fixture with dimensional contexts.

    Contains:
    - Base facts without dimensions
    - Segment breakdown by ProductLine dimension
    - Same concept with different dimensional qualifiers
    """
    parsed_data = {
        'metadata': {
            'entry_point': 'test-dimensional.htm',
            'taxonomy_references': ['us-gaap-2023'],
        },
        'namespaces': {
            'us-gaap': 'http://fasb.org/us-gaap/2023',
            'company': 'http://example.com/2023',
        },
        'facts': [
            # Total revenues (no dimension)
            {
                'concept': 'us-gaap:Revenues',
                'value': 1000000000,
                'context_id': 'c_2023_total',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Revenues by segment - Product A
            {
                'concept': 'us-gaap:Revenues',
                'value': 600000000,
                'context_id': 'c_2023_segmentA',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            # Revenues by segment - Product B
            {
                'concept': 'us-gaap:Revenues',
                'value': 400000000,
                'context_id': 'c_2023_segmentB',
                'unit_ref': 'USD',
                'decimals': -3,
            },
        ],
        'contexts': {
            'c_2023_total': {
                'period_type': 'duration',
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'entity': '0001234567',
            },
            'c_2023_segmentA': {
                'period_type': 'duration',
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'entity': '0001234567',
                'dimensions': {
                    'us-gaap:StatementBusinessSegmentsAxis': 'company:ProductAMember',
                },
            },
            'c_2023_segmentB': {
                'period_type': 'duration',
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'entity': '0001234567',
                'dimensions': {
                    'us-gaap:StatementBusinessSegmentsAxis': 'company:ProductBMember',
                },
            },
        },
        'units': {
            'USD': {'measure': 'iso4217:USD'},
        },
        'calculations': {},
    }

    return TestFilingFixture(
        name='DimensionalSegments',
        parsed_data=parsed_data,
        expected_facts=3,
        expected_contexts=3,
        expected_calculations=0,
    )


def create_failing_calculation_fixture() -> TestFilingFixture:
    """
    Create a fixture with intentional calculation errors.

    Tests that the verification system correctly detects:
    - Sum mismatches
    - Missing children
    - Inconsistent totals
    """
    parsed_data = {
        'metadata': {
            'entry_point': 'test-failing.htm',
            'taxonomy_references': ['us-gaap-2023'],
        },
        'namespaces': {
            'us-gaap': 'http://fasb.org/us-gaap/2023',
        },
        'facts': [
            # Current Assets - WRONG total (should be 100M, is 110M)
            {
                'concept': 'us-gaap:CashAndCashEquivalents',
                'value': 50000000,
                'context_id': 'c_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:AccountsReceivableNet',
                'value': 30000000,
                'context_id': 'c_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:InventoryNet',
                'value': 20000000,
                'context_id': 'c_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
            {
                'concept': 'us-gaap:AssetsCurrent',
                'value': 110000000,  # INTENTIONAL ERROR: should be 100M
                'context_id': 'c_instant',
                'unit_ref': 'USD',
                'decimals': -3,
            },
        ],
        'contexts': {
            'c_instant': {
                'period_type': 'instant',
                'instant': '2023-12-31',
                'entity': '0001234567',
            },
        },
        'units': {
            'USD': {'measure': 'iso4217:USD'},
        },
        'calculations': {
            'http://example.com/role/BalanceSheet': {
                'trees': [
                    {
                        'concept': 'us-gaap:AssetsCurrent',
                        'children': [
                            {'concept': 'us-gaap:CashAndCashEquivalents', 'weight': 1.0, 'order': 1},
                            {'concept': 'us-gaap:AccountsReceivableNet', 'weight': 1.0, 'order': 2},
                            {'concept': 'us-gaap:InventoryNet', 'weight': 1.0, 'order': 3},
                        ],
                    },
                ],
            },
        },
    }

    return TestFilingFixture(
        name='FailingCalculation',
        parsed_data=parsed_data,
        expected_facts=4,
        expected_contexts=1,
        expected_calculations=3,
    )


def get_all_fixtures() -> list[TestFilingFixture]:
    """Get all available test fixtures."""
    return [
        create_simple_balance_sheet_fixture(),
        create_income_statement_fixture(),
        create_dimensional_fixture(),
        create_failing_calculation_fixture(),
    ]


__all__ = [
    'TestFilingFixture',
    'create_simple_balance_sheet_fixture',
    'create_income_statement_fixture',
    'create_dimensional_fixture',
    'create_failing_calculation_fixture',
    'get_all_fixtures',
]
