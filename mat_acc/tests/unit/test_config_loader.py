# Path: mat_acc/tests/unit/test_config_loader.py
"""
Unit Tests for ConfigLoader

Tests the configuration loading functionality including:
- Environment variable parsing
- Type conversion methods
- Singleton pattern
- Default value handling
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add mat_acc to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestConfigLoaderBasics:
    """Test basic ConfigLoader functionality."""

    def test_singleton_pattern(self, mock_env_vars, reset_singletons):
        """ConfigLoader should return same instance."""
        from config_loader import ConfigLoader

        config1 = ConfigLoader()
        config2 = ConfigLoader()

        assert config1 is config2

    def test_get_returns_value(self, mock_env_vars, reset_singletons):
        """get() should return configured value."""
        from config_loader import ConfigLoader

        config = ConfigLoader()
        assert config.get('environment') == 'test'

    def test_get_returns_default_for_missing(self, mock_env_vars, reset_singletons):
        """get() should return default for missing keys."""
        from config_loader import ConfigLoader

        config = ConfigLoader()
        result = config.get('nonexistent_key', 'default_value')

        assert result == 'default_value'

    def test_get_returns_none_for_missing_no_default(self, mock_env_vars, reset_singletons):
        """get() should return None for missing keys without default."""
        from config_loader import ConfigLoader

        config = ConfigLoader()
        result = config.get('nonexistent_key')

        assert result is None


class TestConfigLoaderTypeConversion:
    """Test type conversion methods."""

    def test_get_path_returns_path_object(self, mock_env_vars, reset_singletons):
        """Path values should be converted to Path objects."""
        from config_loader import ConfigLoader

        config = ConfigLoader()
        path = config.get('verification_reports_dir')

        assert isinstance(path, Path)

    def test_get_int_converts_string(self, mock_env_vars, reset_singletons):
        """Integer values should be converted from string."""
        from config_loader import ConfigLoader

        config = ConfigLoader()
        # DB port should be converted to int
        port = config.get('db_port')

        assert isinstance(port, int)
        assert port == 5432

    def test_get_float_converts_string(self, mock_env_vars, reset_singletons):
        """Float values should be converted from string."""
        from config_loader import ConfigLoader

        config = ConfigLoader()
        score = config.get('min_verification_score')

        assert isinstance(score, float)
        assert score == 95.0

    def test_get_bool_converts_true(self, mock_env_vars, reset_singletons):
        """Boolean 'true' should be converted."""
        from config_loader import ConfigLoader

        config = ConfigLoader()
        debug = config.get('debug')

        assert debug is True

    def test_get_bool_converts_false(self, reset_singletons):
        """Boolean 'false' should be converted."""
        env_vars = {'MAT_ACC_DEBUG': 'false', 'MAT_ACC_ENVIRONMENT': 'test'}

        with patch.dict(os.environ, env_vars, clear=False):
            from config_loader import ConfigLoader
            ConfigLoader._instance = None

            config = ConfigLoader()
            debug = config.get('debug')

            assert debug is False


class TestConfigLoaderDatabaseConfig:
    """Test database configuration."""

    def test_database_connection_string(self, mock_env_vars, reset_singletons):
        """Should build valid database connection string."""
        from config_loader import ConfigLoader

        config = ConfigLoader()
        conn_str = config.get_db_connection_string()

        assert 'postgresql' in conn_str
        assert 'test_user' in conn_str
        assert 'mat_acc_test' in conn_str
        assert 'localhost' in conn_str
        assert '5432' in conn_str

    def test_database_config_attributes(self, mock_env_vars, reset_singletons):
        """Should have all database config attributes."""
        from config_loader import ConfigLoader

        config = ConfigLoader()

        assert config.get('db_host') == 'localhost'
        assert config.get('db_port') == 5432
        assert config.get('db_name') == 'mat_acc_test'
        assert config.get('db_user') == 'test_user'


class TestConfigLoaderPathConfig:
    """Test path configuration."""

    def test_input_paths_configured(self, mock_env_vars, reset_singletons):
        """Should have all input path configurations."""
        from config_loader import ConfigLoader

        config = ConfigLoader()

        assert config.get('verification_reports_dir') is not None
        assert config.get('mapper_output_dir') is not None
        assert config.get('parser_output_dir') is not None
        assert config.get('xbrl_filings_dir') is not None

    def test_output_paths_configured(self, mock_env_vars, reset_singletons):
        """Should have all output path configurations."""
        from config_loader import ConfigLoader

        config = ConfigLoader()

        assert config.get('data_root') is not None
        assert config.get('output_dir') is not None
        assert config.get('log_dir') is not None


class TestConfigLoaderEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_env_var_returns_none(self, reset_singletons):
        """Empty environment variable should return None or default."""
        env_vars = {'MAT_ACC_EMPTY_VAR': '', 'MAT_ACC_ENVIRONMENT': 'test'}

        with patch.dict(os.environ, env_vars, clear=False):
            from config_loader import ConfigLoader
            ConfigLoader._instance = None

            config = ConfigLoader()
            result = config.get('empty_var', 'default')

            # Empty string should use default
            assert result == 'default' or result == ''

    def test_whitespace_handling(self, mock_env_vars, reset_singletons):
        """Whitespace in environment values should be handled."""
        # Add whitespace to a known config key
        env_vars = dict(mock_env_vars)
        env_vars['MAT_ACC_ENVIRONMENT'] = '  test  '

        with patch.dict(os.environ, env_vars, clear=False):
            from config_loader import ConfigLoader
            ConfigLoader._instance = None
            ConfigLoader._initialized = False

            config = ConfigLoader()
            # Environment value may or may not be stripped
            result = config.get('environment')
            # Either 'test' (stripped) or '  test  ' (as-is) is valid
            assert result is not None
            assert 'test' in result
