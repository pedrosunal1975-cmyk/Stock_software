# Path: mat_acc/tests/fixtures/sample_data.py
"""
Sample Data Generators for Testing

Provides functions to generate sample test data for various scenarios.
"""

import json
from pathlib import Path
from typing import Optional


def create_verification_report(
    company: str = 'TestCompany',
    form: str = '10-K',
    date: str = '2024-01-01',
    score: float = 98.5,
    passed: int = 98,
    failed: int = 2,
) -> dict:
    """
    Create a sample verification report.

    Args:
        company: Company name
        form: Form type
        date: Filing date
        score: Verification score
        passed: Number of passed checks
        failed: Number of failed checks

    Returns:
        Dictionary representing verification report
    """
    total = passed + failed

    return {
        'filing_id': f'{company.lower()}-{form.lower()}-{date}',
        'market': 'sec',
        'company': company,
        'form': form,
        'date': date,
        'verified_at': f'{date}T10:00:00Z',
        'processing_time_ms': 1500,
        'summary': {
            'score': score,
            'total_checks': total,
            'passed': passed,
            'failed': failed,
            'skipped': 0,
            'critical_issues': min(failed, 2),
            'warning_issues': max(0, failed - 2),
            'info_issues': 0,
        },
        'checks': [
            {
                'check_name': f'Check {i+1}',
                'check_type': 'calculation',
                'passed': i < passed,
                'severity': 'critical' if i >= passed else 'info',
                'message': f'Check {i+1} {"passed" if i < passed else "failed"}',
                'concept': f'us-gaap:Concept{i+1}',
            }
            for i in range(total)
        ]
    }


def create_mapped_statement(
    company: str = 'TestCompany',
    statement_name: str = 'ConsolidatedBalanceSheet',
    facts_count: int = 10,
) -> dict:
    """
    Create a sample mapped statement.

    Args:
        company: Company name
        statement_name: Name of the statement
        facts_count: Number of facts to generate

    Returns:
        Dictionary representing mapped statement
    """
    facts = []
    concepts = [
        ('us-gaap:Assets', 'Total Assets', 1000000),
        ('us-gaap:CurrentAssets', 'Current Assets', 400000),
        ('us-gaap:Cash', 'Cash and Cash Equivalents', 100000),
        ('us-gaap:Liabilities', 'Total Liabilities', 500000),
        ('us-gaap:CurrentLiabilities', 'Current Liabilities', 200000),
        ('us-gaap:StockholdersEquity', 'Stockholders Equity', 500000),
        ('us-gaap:Revenues', 'Total Revenues', 5000000),
        ('us-gaap:CostOfRevenue', 'Cost of Revenue', 3000000),
        ('us-gaap:GrossProfit', 'Gross Profit', 2000000),
        ('us-gaap:NetIncome', 'Net Income', 500000),
    ]

    for i in range(min(facts_count, len(concepts))):
        concept, label, value = concepts[i]
        facts.append({
            'concept': concept,
            'value': value,
            'unit': 'USD',
            'decimals': -3,
            'period_end': '2024-01-01',
            'context_id': f'ctx{i:03d}',
            'label': label,
            'depth': i % 3,
            'is_total': 'Total' in label,
            'is_abstract': False,
        })

    return {
        'filing_info': {
            'company': company,
            'form_type': '10-K',
            'fiscal_year_end': '2024-01-01',
        },
        'namespaces': {
            'us-gaap': 'http://fasb.org/us-gaap/2024',
        },
        'statements': [
            {
                'name': statement_name,
                'role': f'http://{company.lower()}.com/role/{statement_name}',
                'facts': facts,
            }
        ]
    }


def create_parsed_filing(
    company: str = 'TestCompany',
    facts_count: int = 20,
) -> dict:
    """
    Create a sample parsed.json structure.

    Args:
        company: Company name
        facts_count: Number of facts to generate

    Returns:
        Dictionary representing parsed filing
    """
    contexts = {
        'ctx_instant': {
            'entity': '0001234567',
            'period': {'instant': '2024-01-01'},
        },
        'ctx_duration': {
            'entity': '0001234567',
            'period': {'startDate': '2023-01-02', 'endDate': '2024-01-01'},
        },
    }

    units = {
        'usd': {'measure': 'iso4217:USD'},
        'shares': {'measure': 'xbrli:shares'},
        'pure': {'measure': 'xbrli:pure'},
    }

    concepts = [
        ('us-gaap:Assets', 1000000, 'usd', 'ctx_instant'),
        ('us-gaap:Liabilities', 500000, 'usd', 'ctx_instant'),
        ('us-gaap:Revenues', 5000000, 'usd', 'ctx_duration'),
        ('us-gaap:NetIncome', 500000, 'usd', 'ctx_duration'),
        ('dei:EntityCommonStockSharesOutstanding', 1000000, 'shares', 'ctx_instant'),
    ]

    facts = []
    for i in range(min(facts_count, len(concepts) * 4)):
        idx = i % len(concepts)
        concept, value, unit, ctx = concepts[idx]
        facts.append({
            'concept': concept,
            'value': value * (1 + i // len(concepts) * 0.1),
            'unit': unit,
            'decimals': -3,
            'context_ref': ctx,
        })

    return {
        'filing_info': {
            'document_type': '10-K',
            'company_name': company,
            'fiscal_year_end': '2024-01-01',
        },
        'namespaces': {
            'us-gaap': 'http://fasb.org/us-gaap/2024',
            'dei': 'http://xbrl.sec.gov/dei/2024',
        },
        'contexts': contexts,
        'units': units,
        'facts': facts,
    }


def write_test_files(base_dir: Path, company: str = 'TestCompany') -> dict[str, Path]:
    """
    Write complete set of test files to a directory.

    Args:
        base_dir: Base directory for test files
        company: Company name to use

    Returns:
        Dictionary mapping file type to path
    """
    paths = {}

    # Create directory structure
    verification_dir = base_dir / 'verification' / 'sec' / company / '10-K' / '2024-01-01'
    mapper_dir = base_dir / 'mapper' / 'sec' / company / '10-K' / '2024-01-01' / 'json' / 'core_statements'
    parser_dir = base_dir / 'parser' / 'sec' / company / '10-K' / '2024-01-01'

    for dir_path in [verification_dir, mapper_dir, parser_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Write verification report
    verification_path = verification_dir / 'verification_report.json'
    with open(verification_path, 'w') as f:
        json.dump(create_verification_report(company=company), f, indent=2)
    paths['verification'] = verification_path

    # Write mapped statement
    mapped_path = mapper_dir / 'ConsolidatedBalanceSheet.json'
    with open(mapped_path, 'w') as f:
        json.dump(create_mapped_statement(company=company), f, indent=2)
    paths['mapped'] = mapped_path

    # Write parsed filing
    parsed_path = parser_dir / 'parsed.json'
    with open(parsed_path, 'w') as f:
        json.dump(create_parsed_filing(company=company), f, indent=2)
    paths['parsed'] = parsed_path

    return paths
