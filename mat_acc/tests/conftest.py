# Path: mat_acc/tests/conftest.py
"""
Pytest Configuration and Shared Fixtures for mat_acc

Provides common test fixtures used across all test modules.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add mat_acc to path for imports
MAT_ACC_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(MAT_ACC_ROOT))


# ==============================================================================
# ENVIRONMENT FIXTURES
# ==============================================================================

@pytest.fixture
def mock_env_vars():
    """Provide mock environment variables for testing."""
    env_vars = {
        'MAT_ACC_ENVIRONMENT': 'test',
        'MAT_ACC_DEBUG': 'true',

        # Database
        'MAT_ACC_DB_HOST': 'localhost',
        'MAT_ACC_DB_PORT': '5432',
        'MAT_ACC_DB_NAME': 'mat_acc_test',
        'MAT_ACC_DB_USER': 'test_user',
        'MAT_ACC_DB_PASSWORD': 'test_pass',

        # Base paths (REQUIRED by ConfigLoader)
        'MAT_ACC_PROGRAM_DIR': '/tmp/mat_acc_test/program',
        'MAT_ACC_DATA_ROOT': '/tmp/mat_acc_test/data',

        # Input paths (from map_pro) - REQUIRED
        'MAT_ACC_VERIFICATION_REPORTS_DIR': '/tmp/mat_acc_test/verification',
        'MAT_ACC_MAPPER_OUTPUT_DIR': '/tmp/mat_acc_test/mapper',
        'MAT_ACC_PARSER_OUTPUT_DIR': '/tmp/mat_acc_test/parser',
        'MAT_ACC_XBRL_FILINGS_DIR': '/tmp/mat_acc_test/xbrl',
        'MAT_ACC_TAXONOMY_DIR': '/tmp/mat_acc_test/taxonomy',

        # Output paths - REQUIRED
        'MAT_ACC_OUTPUT_DIR': '/tmp/mat_acc_test/output',
        'MAT_ACC_REPORTS_DIR': '/tmp/mat_acc_test/reports',
        'MAT_ACC_RATIOS_DIR': '/tmp/mat_acc_test/ratios',
        'MAT_ACC_NORMALIZED_DIR': '/tmp/mat_acc_test/normalized',
        'MAT_ACC_GRAPHS_DIR': '/tmp/mat_acc_test/graphs',
        'MAT_ACC_AUDIT_DIR': '/tmp/mat_acc_test/audit',
        'MAT_ACC_LOG_DIR': '/tmp/mat_acc_test/logs',

        # Thresholds
        'MAT_ACC_MIN_VERIFICATION_SCORE': '95.0',
        'MAT_ACC_CALCULATION_TOLERANCE': '0.01',
    }

    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_data_structure(temp_dir):
    """Create a complete test data structure mimicking map_pro output."""
    # Create directory structure
    dirs = {
        'verification': temp_dir / 'verification' / 'sec' / 'TestCompany' / '10-K' / '2024-01-01',
        'mapper': temp_dir / 'mapper' / 'sec' / 'TestCompany' / '10-K' / '2024-01-01' / 'json',
        'parser': temp_dir / 'parser' / 'sec' / 'TestCompany' / '10-K' / '2024-01-01',
        'xbrl': temp_dir / 'xbrl' / 'sec' / 'TestCompany' / 'filings' / '10-K' / '2024-01-01',
    }

    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    return dirs


# ==============================================================================
# SAMPLE DATA FIXTURES
# ==============================================================================

@pytest.fixture
def sample_verification_report():
    """Provide a sample verification report JSON structure."""
    return {
        'filing_id': 'test-filing-001',
        'market': 'sec',
        'company': 'TestCompany',
        'form': '10-K',
        'date': '2024-01-01',
        'verified_at': '2024-01-15T10:30:00Z',
        'processing_time_ms': 1500,
        'summary': {
            'score': 98.5,
            'total_checks': 100,
            'passed': 98,
            'failed': 2,
            'skipped': 0,
            'critical_issues': 1,
            'warning_issues': 1,
            'info_issues': 0,
        },
        'checks': [
            {
                'check_name': 'C-Equal Assets',
                'check_type': 'calculation',
                'passed': True,
                'severity': 'critical',
                'message': 'Assets calculation verified',
                'concept': 'us-gaap:Assets',
                'expected_value': 1000000,
                'actual_value': 1000000,
                'difference': 0,
            },
            {
                'check_name': 'C-Equal Liabilities',
                'check_type': 'calculation',
                'passed': False,
                'severity': 'critical',
                'message': 'Liabilities calculation mismatch',
                'concept': 'us-gaap:Liabilities',
                'expected_value': 500000,
                'actual_value': 499990,
                'difference': 10,
            },
        ]
    }


@pytest.fixture
def sample_mapped_statement():
    """Provide a sample mapped statement JSON structure."""
    return {
        'filing_info': {
            'company': 'TestCompany',
            'form_type': '10-K',
            'fiscal_year_end': '2024-01-01',
        },
        'namespaces': {
            'us-gaap': 'http://fasb.org/us-gaap/2024',
        },
        'statements': [
            {
                'name': 'ConsolidatedBalanceSheet',
                'role': 'http://testcompany.com/role/BalanceSheet',
                'facts': [
                    {
                        'concept': 'us-gaap:Assets',
                        'value': 1000000,
                        'unit': 'USD',
                        'decimals': -3,
                        'period_end': '2024-01-01',
                        'context_id': 'ctx001',
                        'label': 'Total Assets',
                        'depth': 0,
                    },
                    {
                        'concept': 'us-gaap:Liabilities',
                        'value': 500000,
                        'unit': 'USD',
                        'decimals': -3,
                        'period_end': '2024-01-01',
                        'context_id': 'ctx001',
                        'label': 'Total Liabilities',
                        'depth': 0,
                    },
                ]
            }
        ]
    }


@pytest.fixture
def sample_parsed_filing():
    """Provide a sample parsed.json structure."""
    return {
        'filing_info': {
            'document_type': '10-K',
            'company_name': 'TestCompany',
            'fiscal_year_end': '2024-01-01',
        },
        'namespaces': {
            'us-gaap': 'http://fasb.org/us-gaap/2024',
            'dei': 'http://xbrl.sec.gov/dei/2024',
        },
        'contexts': {
            'ctx001': {
                'entity': '0001234567',
                'period': {'instant': '2024-01-01'},
            },
            'ctx002': {
                'entity': '0001234567',
                'period': {'startDate': '2023-01-02', 'endDate': '2024-01-01'},
            },
        },
        'units': {
            'usd': {'measure': 'iso4217:USD'},
            'shares': {'measure': 'xbrli:shares'},
        },
        'facts': [
            {
                'concept': 'us-gaap:Assets',
                'value': 1000000,
                'unit': 'usd',
                'decimals': -3,
                'context_ref': 'ctx001',
            },
            {
                'concept': 'us-gaap:Revenues',
                'value': 5000000,
                'unit': 'usd',
                'decimals': -3,
                'context_ref': 'ctx002',
            },
        ]
    }


# ==============================================================================
# FILE CREATION FIXTURES
# ==============================================================================

@pytest.fixture
def create_verification_report(test_data_structure, sample_verification_report):
    """Create a verification report file in the test directory."""
    report_path = test_data_structure['verification'] / 'verification_report.json'
    with open(report_path, 'w') as f:
        json.dump(sample_verification_report, f, indent=2)
    return report_path


@pytest.fixture
def create_mapped_statement(test_data_structure, sample_mapped_statement):
    """Create a mapped statement file in the test directory."""
    # Create core_statements directory
    core_dir = test_data_structure['mapper'] / 'core_statements'
    core_dir.mkdir(parents=True, exist_ok=True)

    statement_path = core_dir / 'ConsolidatedBalanceSheet.json'
    with open(statement_path, 'w') as f:
        json.dump(sample_mapped_statement, f, indent=2)
    return statement_path


@pytest.fixture
def create_parsed_filing(test_data_structure, sample_parsed_filing):
    """Create a parsed.json file in the test directory."""
    parsed_path = test_data_structure['parser'] / 'parsed.json'
    with open(parsed_path, 'w') as f:
        json.dump(sample_parsed_filing, f, indent=2)
    return parsed_path


# ==============================================================================
# MOCK FIXTURES
# ==============================================================================

@pytest.fixture
def mock_config():
    """Create a mock ConfigLoader for testing."""
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        'environment': 'test',
        'debug': True,
        'verification_reports_dir': Path('/tmp/test/verification'),
        'mapper_output_dir': Path('/tmp/test/mapper'),
        'parser_output_dir': Path('/tmp/test/parser'),
        'xbrl_filings_path': Path('/tmp/test/xbrl'),
        'output_dir': Path('/tmp/test/output'),
        'log_dir': Path('/tmp/test/logs'),
        'min_verification_score': 95.0,
    }.get(key, default)
    return config


@pytest.fixture
def mock_config_with_paths(temp_dir, test_data_structure):
    """Create a mock ConfigLoader with real temp paths."""
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        'environment': 'test',
        'debug': True,
        'verification_reports_dir': test_data_structure['verification'].parent.parent.parent.parent,
        'mapper_output_dir': test_data_structure['mapper'].parent.parent.parent.parent.parent,
        'parser_output_dir': test_data_structure['parser'].parent.parent.parent.parent,
        'xbrl_filings_path': test_data_structure['xbrl'].parent.parent.parent.parent.parent,
        'output_dir': temp_dir / 'output',
        'log_dir': temp_dir / 'logs',
        'min_verification_score': 95.0,
    }.get(key, default)
    return config


# ==============================================================================
# UTILITY FIXTURES
# ==============================================================================

@pytest.fixture
def capture_logs():
    """Capture log output for testing."""
    import logging
    from io import StringIO

    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    yield log_capture

    root_logger.removeHandler(handler)


@pytest.fixture
def reset_singletons():
    """Reset any singleton instances between tests."""
    # Import and reset ConfigLoader singleton if it exists
    try:
        from config_loader import ConfigLoader
        ConfigLoader._instance = None
        ConfigLoader._initialized = False
    except ImportError:
        pass

    yield

    # Clean up after test
    try:
        from config_loader import ConfigLoader
        ConfigLoader._instance = None
        ConfigLoader._initialized = False
    except ImportError:
        pass
