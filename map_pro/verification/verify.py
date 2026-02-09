#!/usr/bin/env python3
# Path: verification/verify.py
"""
Verification Module v2 CLI

Main entry point for the verification module.
Validates mapped financial statements for quality assessment.

Usage:
    python verify.py

The CLI will:
1. Show available companies with mapped statements
2. Allow selection of filing to verify
3. Run verification checks using 3-stage pipeline
4. Display results and save reports
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from verification.core.config_loader import ConfigLoader
from verification.core.data_paths import ensure_data_paths
from verification.core.logger.ipo_logging import setup_ipo_logging
from verification.engine import PipelineOrchestrator, VerificationResult

# Use existing loaders from verification module
from verification.loaders.mapped_data import MappedDataLoader, MappedFilingEntry


# IPO Loggers for CLI
logger_input = logging.getLogger('input.cli')
logger_output = logging.getLogger('output.cli')


class VerificationCLI:
    """
    Command-line interface for verification module v2.

    Provides interactive selection and verification of mapped filings.
    Uses the new 3-stage pipeline architecture.
    """

    def __init__(self):
        """Initialize CLI components."""
        self.config = ConfigLoader()

        # Setup IPO logging
        self._setup_logging()

        # Pass config to orchestrator so DiscoveryProcessor can use existing loaders
        self.orchestrator = PipelineOrchestrator(self.config)
        self.mapped_loader = MappedDataLoader(self.config)

    def _setup_logging(self) -> None:
        """Setup IPO-aware logging to log directory."""
        log_dir = self.config.get('log_dir')
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)

            setup_ipo_logging(
                log_dir=log_dir,
                log_level=self.config.get('log_level', 'INFO'),
                console_output=False  # Don't clutter CLI with log output
            )

    def run(self) -> None:
        """Run the verification CLI."""
        self._print_header()

        # Ensure directories exist
        ensure_data_paths()

        while True:
            # Get available filings
            filings = self.mapped_loader.discover_all_mapped_filings()

            if not filings:
                print("\nNo mapped statements found.")
                print("Please run the mapper module first to create mapped statements.")
                break

            # Show menu
            selection = self._show_filing_menu(filings)

            if selection == 0:
                print("\nExiting verification module.")
                break

            if selection == -1:
                # Verify all
                self._verify_all(filings)
            elif 1 <= selection <= len(filings):
                # Verify selected filing
                filing = filings[selection - 1]
                self._verify_filing(filing)

            # Ask to continue
            if not self._ask_continue():
                print("\nExiting verification module.")
                break

    def _print_header(self) -> None:
        """Print CLI header."""
        sep = '=' * 60
        print(sep)
        print('VERIFICATION MODULE v2')
        print('Financial Statement Quality Assessment')
        print('3-Stage Pipeline: Discovery -> Preparation -> Verification')
        print(sep)

    def _show_filing_menu(self, filings: list[MappedFilingEntry]) -> int:
        """
        Show filing selection menu.

        Args:
            filings: List of available filings

        Returns:
            Selected option number (0 to exit, -1 for all)
        """
        print('\nAvailable Companies with Mapped Statements:')
        print('-' * 50)

        for i, filing in enumerate(filings, 1):
            print(f'  {i:2}. {filing.market} | {filing.company} | {filing.form} | {filing.date}')

        print('-' * 50)
        print('  -1. Verify ALL filings')
        print('   0. Exit')
        print()

        while True:
            try:
                choice = input('Enter selection: ').strip()
                selection = int(choice)

                if selection == 0 or selection == -1:
                    return selection
                if 1 <= selection <= len(filings):
                    return selection

                print(f'Invalid selection. Please enter 0-{len(filings)} or -1.')

            except ValueError:
                print('Please enter a valid number.')

    def _verify_filing(self, filing: MappedFilingEntry) -> None:
        """
        Verify a single filing.

        Args:
            filing: Filing to verify
        """
        filing_id = f"{filing.market}/{filing.company}/{filing.form}/{filing.date}"
        sep = '=' * 60

        print(f'\n{sep}')
        print(f'VERIFYING: {filing.company} | {filing.form} | {filing.date}')
        print(sep)

        print(f'[INPUT] Using mapped statements: {filing.filing_folder}')
        logger_input.info(f"Starting verification for {filing_id}")
        logger_input.info(f"Mapped statements path: {filing.filing_folder}")

        # Configure orchestrator
        self.orchestrator.configure(
            naming_strategy='canonical',
            binding_strategy='fallback',
        )

        # Run verification - pass MappedFilingEntry directly
        # DiscoveryProcessor will use existing loaders (MappedReader, XBRLReader)
        result = self.orchestrator.run(filing)

        # Display results
        self._display_results(result, filing)

        # Save outputs
        self._save_outputs(filing, result)

    def _verify_all(self, filings: list[MappedFilingEntry]) -> None:
        """
        Verify all filings.

        Args:
            filings: List of filings to verify
        """
        print(f'\nVerifying {len(filings)} filings...\n')

        results = []
        for i, filing in enumerate(filings, 1):
            print(f'[{i}/{len(filings)}] {filing.company} | {filing.form}...')

            # Run verification - pass MappedFilingEntry directly
            result = self.orchestrator.run(filing)
            results.append((filing, result))

            # Save outputs
            self._save_outputs(filing, result, quiet=True)

            print(f'        Score: {result.summary.score:.1f}/100 '
                  f'({result.summary.critical_issues} critical, '
                  f'{result.summary.warning_issues} warnings)')

        # Show summary
        self._display_batch_summary(results)

    def _display_results(self, result: VerificationResult, filing: MappedFilingEntry) -> None:
        """Display verification results."""
        sep = '=' * 60
        summary = result.summary

        print(f'\n{sep}')
        print('VERIFICATION RESULTS')
        print(sep)

        # Score
        print(f'Overall Score: {summary.score:6.1f}/100')
        print()

        # Statistics
        print(f'Total Checks:  {summary.total_checks}')
        print(f'  - Passed:    {summary.passed}')
        print(f'  - Failed:    {summary.failed}')
        print(f'  - Skipped:   {summary.skipped}')
        print()

        # Issues
        print('Issues Found:')
        if summary.critical_issues > 0:
            print(f'  - CRITICAL: {summary.critical_issues}')
        if summary.warning_issues > 0:
            print(f'  - Warnings: {summary.warning_issues}')
        if summary.info_issues > 0:
            print(f'  - Info:     {summary.info_issues}')

        if summary.critical_issues == 0 and summary.warning_issues == 0:
            print('  No significant issues found.')

        print()

        # Failed checks
        failed = [c for c in result.checks if not c.passed and c.severity == 'critical']
        if failed:
            print('Critical Issues:')
            for check in failed[:5]:
                print(f'  - {check.message}')
            if len(failed) > 5:
                print(f'  ... and {len(failed) - 5} more')
            print()

        # Quality assessment
        if summary.score >= 90:
            quality = 'EXCELLENT'
            desc = 'High quality data, suitable for analysis'
        elif summary.score >= 75:
            quality = 'GOOD'
            desc = 'Generally reliable, minor issues'
        elif summary.score >= 50:
            quality = 'FAIR'
            desc = 'Some issues, use with caution'
        elif summary.score >= 25:
            quality = 'POOR'
            desc = 'Significant issues, review carefully'
        else:
            quality = 'UNUSABLE'
            desc = 'Major issues, not recommended for analysis'

        print(f'Quality Level: {quality}')
        print(f'               {desc}')
        print(sep)

    def _display_batch_summary(self, results: list[tuple]) -> None:
        """Display summary of batch verification."""
        sep = '=' * 60

        print(f'\n{sep}')
        print('BATCH VERIFICATION SUMMARY')
        print(sep)

        print(f'Total filings verified: {len(results)}')
        print()

        # Count by score range
        excellent = sum(1 for _, r in results if r.summary.score >= 90)
        good = sum(1 for _, r in results if 75 <= r.summary.score < 90)
        fair = sum(1 for _, r in results if 50 <= r.summary.score < 75)
        poor = sum(1 for _, r in results if r.summary.score < 50)

        print('By Quality Level:')
        print(f'  EXCELLENT (90+): {excellent}')
        print(f'  GOOD (75-89):    {good}')
        print(f'  FAIR (50-74):    {fair}')
        print(f'  POOR (<50):      {poor}')
        print()

        # Average score
        if results:
            avg_score = sum(r.summary.score for _, r in results) / len(results)
            print(f'Average Score: {avg_score:.1f}/100')

        print(sep)

    def _save_outputs(
        self,
        filing: MappedFilingEntry,
        result: VerificationResult,
        quiet: bool = False
    ) -> None:
        """
        Save verification outputs.

        Args:
            filing: Filing that was verified
            result: Verification result
            quiet: If True, don't print output paths
        """
        import json

        filing_id = f"{filing.market}/{filing.company}/{filing.form}/{filing.date}"

        # Get output directory
        output_dir = self.config.get('output_dir')
        if not output_dir:
            logger_output.warning(f"No output directory configured for {filing_id}")
            if not quiet:
                print('[WARN] No output directory configured')
            return

        # Create output path
        report_dir = (
            Path(output_dir) /
            filing.market /
            filing.company /
            filing.form /
            filing.date
        )
        report_dir.mkdir(parents=True, exist_ok=True)
        logger_output.info(f"Created report directory: {report_dir}")

        # Save verification report
        report_path = report_dir / 'verification_report.json'
        report_data = {
            'filing_id': filing_id,
            'market': filing.market,
            'company': filing.company,
            'form': filing.form,
            'date': filing.date,
            'verified_at': result.verification_timestamp,
            'processing_time_ms': result.processing_time_ms,
            'summary': {
                'score': result.summary.score,
                'total_checks': result.summary.total_checks,
                'passed': result.summary.passed,
                'failed': result.summary.failed,
                'skipped': result.summary.skipped,
                'critical_issues': result.summary.critical_issues,
                'warning_issues': result.summary.warning_issues,
                'info_issues': result.summary.info_issues,
            },
            'checks': [
                {
                    'check_name': c.check_name,
                    'check_type': c.check_type,
                    'passed': c.passed,
                    'severity': c.severity,
                    'message': c.message,
                    'expected_value': c.expected_value,
                    'actual_value': c.actual_value,
                    'difference': c.difference,
                    'concept': c.concept,
                    'context_id': c.context_id,
                    'details': c.details,
                }
                for c in result.checks
            ]
        }

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)

        # Log output activity
        logger_output.info(f"Verification complete for {filing_id}")
        logger_output.info(f"Score: {result.summary.score:.1f}/100, "
                          f"Checks: {result.summary.total_checks} total, "
                          f"{result.summary.passed} passed, "
                          f"{result.summary.failed} failed")
        logger_output.info(f"Report saved: {report_path}")

        if not quiet:
            print(f'\n[OUTPUT] Report saved: {report_path}')

    def _ask_continue(self) -> bool:
        """Ask if user wants to continue."""
        return self._ask_yes_no('\nVerify another filing?')

    def _ask_yes_no(self, prompt: str) -> bool:
        """Ask a yes/no question."""
        while True:
            response = input(f'{prompt} [y/n]: ').strip().lower()
            if response in ['y', 'yes']:
                return True
            if response in ['n', 'no']:
                return False
            print('Please enter y or n.')


def main():
    """Main entry point."""
    try:
        cli = VerificationCLI()
        cli.run()
    except KeyboardInterrupt:
        print('\n\nVerification cancelled.')
        sys.exit(0)
    except Exception as e:
        print(f'\nError: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
