# Path: mat_acc/ratio_check/workflow.py
"""
Ratio Check Workflow

CLI entry points and interactive helpers for ratio analysis.
Provides setup_logging(), main(), and display/save helpers
used by the orchestrator's interactive mode.

Usage:
    python -m ratio_check
"""

import sys
import logging
from typing import Optional

from config_loader import ConfigLoader
from core.logger.ipo_logging import (
    setup_ipo_logging,
    get_process_logger,
)

from .calculation.ratio_definitions import STANDARD_RATIOS


logger = get_process_logger('ratio_check')


def print_header() -> None:
    """Print application header."""
    print()
    print("=" * 70)
    print("  RATIO CHECK - Financial Statement Analysis")
    print("=" * 70)
    print()


def print_selection(selection) -> None:
    """Print selected filing info."""
    print()
    print("-" * 70)
    print(f"  Selected: {selection.company}")
    print(
        f"  Market: {selection.market.upper()} | "
        f"Form: {selection.form} | Date: {selection.date}"
    )
    print("-" * 70)


def offer_save(result, report_generator) -> None:
    """Offer to save results to file."""
    print("\n  Save results to file? (y/n): ", end='')
    try:
        choice = input().strip().lower()
        if choice == 'y':
            _save_results(result, report_generator)
    except (KeyboardInterrupt, EOFError):
        pass


def _save_results(result, report_generator) -> None:
    """Save results using ReportGenerator."""
    report = report_generator.generate(
        result, ratio_definitions=STANDARD_RATIOS,
    )
    written = report_generator.write(report)
    if written:
        print("\n  Reports saved:")
        for fmt, path in written.items():
            print(f"    [{fmt}] {path}")
    else:
        print("\n  [ERROR] No reports written (check config)")


def setup_logging(
    config: Optional[ConfigLoader] = None,
) -> None:
    """
    Configure IPO logging for the application.

    Sets up file-based logging with IPO separation:
    - input_activity.log: Loading operations
    - process_activity.log: Calculation/matching work
    - output_activity.log: Report generation
    - full_activity.log: All activities
    """
    config = config or ConfigLoader()
    log_dir = config.get('log_dir')
    log_level = config.get('log_level', 'INFO')
    log_console = config.get('log_console', True)

    setup_ipo_logging(
        log_dir=log_dir,
        log_level=log_level,
        console_output=log_console,
    )

    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logger.info(
        f"Logging initialized: level={log_level}, dir={log_dir}"
    )


def main() -> None:
    """Main entry point for ratio analysis CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Financial Ratio Analysis',
    )
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug reporting',
    )
    parser.add_argument(
        '--debug-report',
        action='store_true',
        help='Show debug report only',
    )
    args = parser.parse_args()

    config = ConfigLoader()
    setup_logging(config)

    if args.debug_report:
        from .support.debug_reporter import DebugReporter
        reporter = DebugReporter(config)
        print("\n  Checking logging configuration...")
        reporter.print_report()
        return

    try:
        from .ratio_check import RatioCheckOrchestrator
        orchestrator = RatioCheckOrchestrator(
            config, debug=args.debug,
        )
        orchestrator.run()
        if args.debug:
            orchestrator.debug_reporter.save_report(
                company=orchestrator._last_company,
            )
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user.")
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n  [ERROR] {e}")
        logger.exception("Unhandled exception in ratio_check")
        sys.exit(1)


__all__ = [
    'print_header',
    'print_selection',
    'offer_save',
    'setup_logging',
    'main',
]
