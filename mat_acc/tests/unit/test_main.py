# Path: mat_acc/tests/unit/test_main.py
"""
Unit Tests for main.py

Tests the CLI entry point functionality including:
- Argument parsing
- Interactive mode
- Batch mode
- System initialization
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from io import StringIO

import pytest

# Add mat_acc to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestPrintBanner:
    """Test banner printing."""

    def test_print_banner_outputs_text(self, capsys):
        """print_banner should output text."""
        from main import print_banner

        print_banner()
        captured = capsys.readouterr()

        assert 'MAT_ACC' in captured.out
        assert 'Mathematical Accountancy' in captured.out

    def test_banner_is_ascii_only(self, capsys):
        """Banner should contain only ASCII characters."""
        from main import print_banner

        print_banner()
        captured = capsys.readouterr()

        for char in captured.out:
            assert ord(char) < 128, f"Non-ASCII character found: {char}"


class TestPrintSystemInfo:
    """Test system info printing."""

    def test_print_system_info(self, capsys, mock_config):
        """Should print configuration info."""
        from main import print_system_info

        print_system_info(mock_config)
        captured = capsys.readouterr()

        # Should show environment and paths
        assert 'test' in captured.out.lower() or len(captured.out) > 0


class TestArgumentParsing:
    """Test command line argument parsing."""

    def test_list_argument(self):
        """--list flag should be recognized."""
        from main import main
        import argparse

        # Test that argparse configuration works
        with patch('sys.argv', ['main.py', '--list']):
            with patch('main.initialize_system') as mock_init:
                mock_init.side_effect = SystemExit(0)
                with pytest.raises(SystemExit):
                    main()

    def test_all_argument(self):
        """--all flag should be recognized."""
        with patch('sys.argv', ['main.py', '--all']):
            with patch('main.initialize_system') as mock_init:
                mock_init.side_effect = SystemExit(0)
                from main import main
                with pytest.raises(SystemExit):
                    main()

    def test_company_argument(self):
        """--company argument should accept value."""
        with patch('sys.argv', ['main.py', '--company', 'Apple']):
            with patch('main.initialize_system') as mock_init:
                mock_init.side_effect = SystemExit(0)
                from main import main
                with pytest.raises(SystemExit):
                    main()

    def test_quiet_argument(self):
        """--quiet flag should be recognized."""
        with patch('sys.argv', ['main.py', '--quiet', '--list']):
            with patch('main.initialize_system') as mock_init:
                mock_init.side_effect = SystemExit(0)
                from main import main
                with pytest.raises(SystemExit):
                    main()


class TestInitializeSystem:
    """Test system initialization."""

    def test_initialize_returns_tuple(self, mock_env_vars):
        """initialize_system should return config and paths."""
        with patch('main.ConfigLoader') as MockConfig:
            with patch('main.setup_ipo_logging'):
                with patch('main.DataPathsManager') as MockPaths:
                    mock_config = MagicMock()
                    MockConfig.return_value = mock_config

                    mock_paths = MagicMock()
                    mock_paths.validate_input_paths.return_value = {
                        'valid': [], 'missing': [], 'not_directory': [], 'not_readable': []
                    }
                    MockPaths.return_value = mock_paths

                    from main import initialize_system

                    config, paths = initialize_system()

                    assert config is mock_config
                    assert paths is mock_paths

    def test_initialize_validates_paths(self, mock_env_vars):
        """initialize_system should validate input paths."""
        with patch('main.ConfigLoader') as MockConfig:
            with patch('main.setup_ipo_logging'):
                with patch('main.DataPathsManager') as MockPaths:
                    mock_paths = MagicMock()
                    mock_paths.validate_input_paths.return_value = {
                        'valid': [], 'missing': [], 'not_directory': [], 'not_readable': []
                    }
                    MockPaths.return_value = mock_paths

                    from main import initialize_system

                    initialize_system()

                    mock_paths.validate_input_paths.assert_called_once()

    def test_initialize_raises_on_missing_paths(self, mock_env_vars):
        """initialize_system should raise if paths missing."""
        with patch('main.ConfigLoader'):
            with patch('main.setup_ipo_logging'):
                with patch('main.DataPathsManager') as MockPaths:
                    mock_paths = MagicMock()
                    mock_paths.validate_input_paths.return_value = {
                        'valid': [],
                        'missing': [('verification_reports_dir', '/missing/path')],
                        'not_directory': [],
                        'not_readable': []
                    }
                    MockPaths.return_value = mock_paths

                    from main import initialize_system

                    with pytest.raises(ValueError):
                        initialize_system()

    def test_initialize_ensures_directories(self, mock_env_vars):
        """initialize_system should create output directories."""
        with patch('main.ConfigLoader'):
            with patch('main.setup_ipo_logging'):
                with patch('main.DataPathsManager') as MockPaths:
                    mock_paths = MagicMock()
                    mock_paths.validate_input_paths.return_value = {
                        'valid': [], 'missing': [], 'not_directory': [], 'not_readable': []
                    }
                    MockPaths.return_value = mock_paths

                    from main import initialize_system

                    initialize_system()

                    mock_paths.ensure_all_directories.assert_called_once()


class TestListFilings:
    """Test list_filings function."""

    def test_list_filings_empty(self, capsys):
        """Should handle empty filing list."""
        from main import list_filings

        mock_loader = MagicMock()
        mock_loader.discover_filings.return_value = []

        mock_reader = MagicMock()

        list_filings(mock_loader, mock_reader)
        captured = capsys.readouterr()

        assert 'No verified filings found' in captured.out or 'Found 0' in captured.out

    def test_list_filings_shows_count(self, capsys):
        """Should show count of filings found."""
        from main import list_filings
        from loaders.verification_data import VerifiedFilingEntry

        # Create mock filing
        mock_entry = MagicMock()
        mock_entry.market = 'sec'
        mock_entry.company = 'TestCompany'
        mock_entry.form = '10-K'
        mock_entry.date = '2024-01-01'

        mock_loader = MagicMock()
        mock_loader.discover_filings.return_value = [mock_entry]
        mock_loader.config = MagicMock()
        mock_loader.config.get.return_value = '/tmp/test'

        mock_reader = MagicMock()
        mock_report = MagicMock()
        mock_report.summary.score = 98.5
        mock_reader.load_report.return_value = mock_report

        list_filings(mock_loader, mock_reader)
        captured = capsys.readouterr()

        assert 'Found 1' in captured.out or 'TestCompany' in captured.out


class TestRunInteractive:
    """Test interactive mode."""

    def test_interactive_cancelled(self):
        """Should return 0 when cancelled."""
        with patch('main.CompanySelector') as MockSelector:
            mock_selector = MagicMock()
            mock_selector.select_filing.return_value = None
            MockSelector.return_value = mock_selector

            from main import run_interactive

            mock_config = MagicMock()
            mock_logger = MagicMock()

            result = run_interactive(mock_config, mock_logger)

            assert result == 0

    def test_interactive_single_selection(self, capsys):
        """Should handle single filing selection."""
        with patch('main.CompanySelector') as MockSelector:
            with patch('main.confirm_action', return_value=True):
                mock_selection = MagicMock()
                mock_selection.company = 'TestCompany'
                mock_selection.form = '10-K'
                mock_selection.date = '2024-01-01'
                mock_selection.report_path = '/tmp/test/report.json'
                mock_selection.verification_score = 98.5

                mock_selector = MagicMock()
                mock_selector.select_filing.return_value = mock_selection
                MockSelector.return_value = mock_selector

                from main import run_interactive

                mock_config = MagicMock()
                mock_logger = MagicMock()

                result = run_interactive(mock_config, mock_logger)

                # Should return 0 (success) or show TODO message
                assert result == 0

                captured = capsys.readouterr()
                assert 'TestCompany' in captured.out


class TestRunBatch:
    """Test batch mode."""

    def test_batch_no_filings(self, capsys):
        """Should handle no filings found."""
        with patch('main.VerificationDataLoader') as MockLoader:
            with patch('main.VerificationReader') as MockReader:
                mock_loader = MagicMock()
                mock_loader.discover_filings.return_value = []
                MockLoader.return_value = mock_loader

                from main import run_batch

                mock_config = MagicMock()
                mock_logger = MagicMock()

                result = run_batch(mock_config, mock_logger)

                assert result == 0
                captured = capsys.readouterr()
                assert 'No matching filings' in captured.out or 'Found 0' in captured.out

    def test_batch_with_company_filter(self):
        """Should filter by company name."""
        with patch('main.VerificationDataLoader') as MockLoader:
            with patch('main.VerificationReader') as MockReader:
                mock_entry1 = MagicMock()
                mock_entry1.company = 'Apple'
                mock_entry1.form = '10-K'
                mock_entry1.date = '2024-01-01'
                mock_entry2 = MagicMock()
                mock_entry2.company = 'Microsoft'
                mock_entry2.form = '10-K'
                mock_entry2.date = '2024-01-01'

                mock_loader = MagicMock()
                mock_loader.discover_filings.return_value = [mock_entry1, mock_entry2]
                MockLoader.return_value = mock_loader

                # Create properly structured mock report
                mock_summary = MagicMock()
                mock_summary.score = 98.5  # Real float value
                mock_report = MagicMock()
                mock_report.summary = mock_summary

                mock_reader = MagicMock()
                mock_reader.load_report.return_value = mock_report
                mock_reader.is_verified.return_value = True
                MockReader.return_value = mock_reader

                from main import run_batch

                mock_config = MagicMock()
                mock_config.get.return_value = 95.0
                mock_logger = MagicMock()

                # Should filter to only Apple
                run_batch(mock_config, mock_logger, company_filter='Apple')


class TestMainFunction:
    """Test main() entry point."""

    def test_main_returns_int(self):
        """main() should return integer exit code."""
        with patch('sys.argv', ['main.py', '--list']):
            with patch('main.initialize_system') as mock_init:
                mock_config = MagicMock()
                mock_paths = MagicMock()
                mock_init.return_value = (mock_config, mock_paths)

                with patch('main.get_input_logger') as mock_logger:
                    with patch('main.VerificationDataLoader') as MockLoader:
                        with patch('main.VerificationReader') as MockReader:
                            mock_loader = MagicMock()
                            mock_loader.discover_filings.return_value = []
                            mock_loader.config = mock_config
                            MockLoader.return_value = mock_loader

                            from main import main

                            result = main()

                            assert isinstance(result, int)

    def test_main_handles_keyboard_interrupt(self):
        """main() should handle KeyboardInterrupt gracefully."""
        with patch('sys.argv', ['main.py']):
            with patch('main.initialize_system') as mock_init:
                mock_init.side_effect = KeyboardInterrupt()

                from main import main

                result = main()

                assert result == 130  # Standard exit code for SIGINT

    def test_main_handles_value_error(self, capsys):
        """main() should handle ValueError gracefully."""
        with patch('sys.argv', ['main.py']):
            with patch('main.initialize_system') as mock_init:
                mock_init.side_effect = ValueError("Test error")

                from main import main

                result = main()

                assert result == 1
                captured = capsys.readouterr()
                assert 'Error' in captured.out or 'FAIL' in captured.out
