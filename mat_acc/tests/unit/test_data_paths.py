# Path: mat_acc/tests/unit/test_data_paths.py
"""
Unit Tests for DataPathsManager

Tests the data paths management functionality including:
- Directory creation
- Path validation
- Health checks
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add mat_acc to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestDataPathsManagerInit:
    """Test DataPathsManager initialization."""

    def test_init_creates_config(self, mock_env_vars, reset_singletons):
        """Should initialize with internal ConfigLoader."""
        from core.data_paths import DataPathsManager

        manager = DataPathsManager()

        assert manager.config is not None

    def test_init_tracking_lists(self, mock_env_vars, reset_singletons):
        """Should initialize tracking lists."""
        from core.data_paths import DataPathsManager

        manager = DataPathsManager()

        assert hasattr(manager, '_created_dirs')
        assert hasattr(manager, '_existing_dirs')
        assert hasattr(manager, '_failed_dirs')


class TestEnsureAllDirectories:
    """Test directory creation functionality."""

    def test_returns_dict(self, mock_env_vars, reset_singletons, temp_dir):
        """Should return dictionary with results."""
        # Patch the config to use temp directories
        with patch.dict('os.environ', {
            'MAT_ACC_DATA_ROOT': str(temp_dir / 'data'),
            'MAT_ACC_OUTPUT_DIR': str(temp_dir / 'output'),
            'MAT_ACC_REPORTS_DIR': str(temp_dir / 'reports'),
            'MAT_ACC_RATIOS_DIR': str(temp_dir / 'ratios'),
            'MAT_ACC_NORMALIZED_DIR': str(temp_dir / 'normalized'),
            'MAT_ACC_GRAPHS_DIR': str(temp_dir / 'graphs'),
            'MAT_ACC_AUDIT_DIR': str(temp_dir / 'audit'),
            'MAT_ACC_LOG_DIR': str(temp_dir / 'logs'),
        }):
            from core.data_paths import DataPathsManager
            from config_loader import ConfigLoader
            ConfigLoader._instance = None
            ConfigLoader._initialized = False

            manager = DataPathsManager()
            result = manager.ensure_all_directories()

            assert isinstance(result, dict)
            assert 'created' in result
            assert 'existing' in result
            assert 'failed' in result

    def test_creates_directories(self, mock_env_vars, reset_singletons, temp_dir):
        """Should create directories on data partition."""
        with patch.dict('os.environ', {
            'MAT_ACC_DATA_ROOT': str(temp_dir / 'data'),
            'MAT_ACC_OUTPUT_DIR': str(temp_dir / 'output'),
            'MAT_ACC_REPORTS_DIR': str(temp_dir / 'reports'),
            'MAT_ACC_RATIOS_DIR': str(temp_dir / 'ratios'),
            'MAT_ACC_NORMALIZED_DIR': str(temp_dir / 'normalized'),
            'MAT_ACC_GRAPHS_DIR': str(temp_dir / 'graphs'),
            'MAT_ACC_AUDIT_DIR': str(temp_dir / 'audit'),
            'MAT_ACC_LOG_DIR': str(temp_dir / 'logs'),
        }):
            from core.data_paths import DataPathsManager
            from config_loader import ConfigLoader
            ConfigLoader._instance = None
            ConfigLoader._initialized = False

            manager = DataPathsManager()
            result = manager.ensure_all_directories()

            # Should have created some directories
            total_created = len(result['created']) + len(result['existing'])
            assert total_created > 0


class TestValidateInputPaths:
    """Test input path validation."""

    def test_returns_dict(self, mock_env_vars, reset_singletons):
        """Should return dictionary with validation results."""
        from core.data_paths import DataPathsManager

        manager = DataPathsManager()
        result = manager.validate_input_paths()

        assert isinstance(result, dict)

    def test_contains_validation_categories(self, mock_env_vars, reset_singletons):
        """Should contain validation categories."""
        from core.data_paths import DataPathsManager

        manager = DataPathsManager()
        result = manager.validate_input_paths()

        assert 'valid' in result or 'missing' in result


class TestHealthCheck:
    """Test health check functionality."""

    def test_returns_dict(self, mock_env_vars, reset_singletons):
        """Health check should return dictionary."""
        from core.data_paths import DataPathsManager

        manager = DataPathsManager()
        result = manager.health_check()

        assert isinstance(result, dict)

    def test_contains_status(self, mock_env_vars, reset_singletons):
        """Health check should contain status."""
        from core.data_paths import DataPathsManager

        manager = DataPathsManager()
        result = manager.health_check()

        assert 'status' in result

    def test_status_values(self, mock_env_vars, reset_singletons):
        """Status should be one of expected values."""
        from core.data_paths import DataPathsManager

        manager = DataPathsManager()
        result = manager.health_check()

        assert result['status'] in ['healthy', 'degraded', 'critical']


class TestGetOutputPath:
    """Test output path building."""

    def test_builds_structured_path(self, mock_env_vars, reset_singletons):
        """Should build structured output path."""
        from core.data_paths import DataPathsManager

        manager = DataPathsManager()
        path = manager.get_output_path(
            market='sec',
            company='TestCompany',
            form='10-K',
            date='2024-01-01',
            output_type='reports'
        )

        assert isinstance(path, Path)
        assert 'sec' in str(path)
        assert 'TestCompany' in str(path)

    def test_different_output_types(self, mock_env_vars, reset_singletons):
        """Should handle different output types."""
        from core.data_paths import DataPathsManager

        manager = DataPathsManager()

        for output_type in ['reports', 'ratios', 'normalized', 'graphs', 'audit']:
            path = manager.get_output_path(
                market='sec',
                company='Test',
                form='10-K',
                date='2024-01-01',
                output_type=output_type
            )
            assert isinstance(path, Path)
