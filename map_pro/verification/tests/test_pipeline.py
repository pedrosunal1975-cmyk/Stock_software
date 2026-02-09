# Path: verification/tests/test_pipeline.py
"""
Internal Pipeline Test for Verification Module v2

Tests the 3-stage pipeline (Discovery -> Preparation -> Verification)
using test fixtures. Validates:
1. Stage 1: Data discovery from parsed.json
2. Stage 2: Data preparation and organization
3. Stage 3: Verification checks and results

Usage:
    python -m verification.tests.test_pipeline

Or run individual tests:
    python -m verification.tests.test_pipeline --stage 1
"""

import sys
import logging
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from verification.tests.fixtures import (
    get_all_fixtures,
    create_simple_balance_sheet_fixture,
    create_income_statement_fixture,
    create_dimensional_fixture,
    create_failing_calculation_fixture,
    TestFilingFixture,
)
from verification.engine.processors import (
    PipelineOrchestrator,
    VerificationResult,
)
from verification.engine.processors.stage1_discovery import DiscoveryProcessor
from verification.engine.processors.stage2_preparation import PreparationProcessor
from verification.engine.processors.stage3_verification import VerificationProcessor


class PipelineTestRunner:
    """
    Internal test runner for verification pipeline.

    Runs test fixtures through all pipeline stages and validates results.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.errors = []

        # Configure logging
        level = logging.DEBUG if verbose else logging.WARNING
        logging.basicConfig(
            level=level,
            format='[%(levelname)s] %(name)s: %(message)s',
        )

    def run_all_tests(self) -> bool:
        """Run all pipeline tests."""
        self._print_header('VERIFICATION_V2 PIPELINE TESTS')

        # Test Stage 1: Discovery
        self._print_section('STAGE 1: Discovery')
        self.test_stage1_discovery()

        # Test Stage 2: Preparation
        self._print_section('STAGE 2: Preparation')
        self.test_stage2_preparation()

        # Test Stage 3: Verification
        self._print_section('STAGE 3: Verification')
        self.test_stage3_verification()

        # Test full pipeline
        self._print_section('FULL PIPELINE')
        self.test_full_pipeline()

        # Test failing calculations
        self._print_section('FAILING CALCULATIONS (Expected Failures)')
        self.test_failing_calculations()

        # Print summary
        self._print_summary()

        return self.failed == 0

    def test_stage1_discovery(self):
        """Test Stage 1: Discovery Processor."""
        processor = DiscoveryProcessor()

        for fixture in get_all_fixtures():
            test_name = f"Discovery: {fixture.name}"
            try:
                parsed_json = fixture.create_temp_file()
                result = processor.discover(parsed_json)

                # Validate discovery results
                facts_ok = len(result.facts) == fixture.expected_facts
                contexts_ok = len(result.contexts) == fixture.expected_contexts
                calc_ok = len(result.calculations) == fixture.expected_calculations

                if facts_ok and contexts_ok and calc_ok:
                    self._pass(test_name)
                else:
                    details = []
                    if not facts_ok:
                        details.append(f"facts: {len(result.facts)} != {fixture.expected_facts}")
                    if not contexts_ok:
                        details.append(f"contexts: {len(result.contexts)} != {fixture.expected_contexts}")
                    if not calc_ok:
                        details.append(f"calculations: {len(result.calculations)} != {fixture.expected_calculations}")
                    self._fail(test_name, ', '.join(details))

            except Exception as e:
                self._error(test_name, str(e))
            finally:
                fixture.cleanup()

    def test_stage2_preparation(self):
        """Test Stage 2: Preparation Processor."""
        discovery = DiscoveryProcessor()
        preparation = PreparationProcessor()

        fixture = create_simple_balance_sheet_fixture()
        test_name = "Preparation: SimpleBalanceSheet"

        try:
            parsed_json = fixture.create_temp_file()

            # Run discovery
            discovery_result = discovery.discover(parsed_json)

            # Run preparation
            prep_result = preparation.prepare(discovery_result)

            # Validate preparation results
            checks = [
                (len(prep_result.facts) > 0, "facts should not be empty"),
                (len(prep_result.fact_groups) > 0, "fact_groups should not be empty"),
                (len(prep_result.calculations) > 0, "calculations should not be empty"),
            ]

            failed_checks = [msg for ok, msg in checks if not ok]
            if not failed_checks:
                self._pass(test_name)
            else:
                self._fail(test_name, '; '.join(failed_checks))

        except Exception as e:
            self._error(test_name, str(e))
        finally:
            fixture.cleanup()

    def test_stage3_verification(self):
        """Test Stage 3: Verification Processor."""
        discovery = DiscoveryProcessor()
        preparation = PreparationProcessor()
        verification = VerificationProcessor()

        fixture = create_simple_balance_sheet_fixture()
        test_name = "Verification: SimpleBalanceSheet"

        try:
            parsed_json = fixture.create_temp_file()

            # Run full pipeline manually
            discovery_result = discovery.discover(parsed_json)
            prep_result = preparation.prepare(discovery_result)
            verify_result = verification.verify(prep_result)

            # Validate verification results
            checks = [
                (verify_result.summary is not None, "summary should exist"),
                (verify_result.summary.total_checks > 0, "should have checks"),
                (len(verify_result.checks) > 0, "checks list should not be empty"),
                (0 <= verify_result.summary.score <= 100, "score should be 0-100"),
            ]

            failed_checks = [msg for ok, msg in checks if not ok]
            if not failed_checks:
                self._pass(test_name)
                if self.verbose:
                    print(f"    Score: {verify_result.summary.score:.1f}/100")
                    print(f"    Total checks: {verify_result.summary.total_checks}")
                    print(f"    Passed: {verify_result.summary.passed}")
                    print(f"    Failed: {verify_result.summary.failed}")
            else:
                self._fail(test_name, '; '.join(failed_checks))

        except Exception as e:
            self._error(test_name, str(e))
        finally:
            fixture.cleanup()

    def test_full_pipeline(self):
        """Test full pipeline orchestration."""
        orchestrator = PipelineOrchestrator()

        for fixture in get_all_fixtures():
            if fixture.name == 'FailingCalculation':
                continue  # Skip this one, tested separately

            test_name = f"Pipeline: {fixture.name}"
            try:
                parsed_json = fixture.create_temp_file()

                # Run full pipeline
                result = orchestrator.run(parsed_json)

                # Validate result structure
                checks = [
                    (result is not None, "result should not be None"),
                    (result.summary is not None, "summary should exist"),
                    (isinstance(result.processing_time_ms, (int, float)), "processing_time should be numeric"),
                    (result.verification_timestamp is not None, "timestamp should exist"),
                ]

                failed_checks = [msg for ok, msg in checks if not ok]
                if not failed_checks:
                    self._pass(test_name)
                    if self.verbose:
                        print(f"    Score: {result.summary.score:.1f}/100 ({result.processing_time_ms:.0f}ms)")
                else:
                    self._fail(test_name, '; '.join(failed_checks))

            except Exception as e:
                self._error(test_name, str(e))
            finally:
                fixture.cleanup()

    def test_failing_calculations(self):
        """Test that failing calculations are detected."""
        orchestrator = PipelineOrchestrator()
        fixture = create_failing_calculation_fixture()
        test_name = "Detection: FailingCalculation"

        try:
            parsed_json = fixture.create_temp_file()

            # Run pipeline
            result = orchestrator.run(parsed_json)

            # Should have failed checks
            failed_checks = [c for c in result.checks if not c.passed]

            if len(failed_checks) > 0:
                self._pass(test_name)
                if self.verbose:
                    print(f"    Correctly detected {len(failed_checks)} failures")
                    for check in failed_checks[:3]:
                        print(f"      - {check.check_name}: {check.message}")
            else:
                self._fail(test_name, "Should have detected calculation failures")

        except Exception as e:
            self._error(test_name, str(e))
        finally:
            fixture.cleanup()

    def _print_header(self, title: str):
        """Print section header."""
        sep = '=' * 60
        print()
        print(sep)
        print(f'  {title}')
        print(sep)
        print()

    def _print_section(self, title: str):
        """Print subsection header."""
        print()
        print(f'--- {title} ---')
        print()

    def _pass(self, test_name: str):
        """Record a passing test."""
        self.passed += 1
        print(f'  [PASS] {test_name}')

    def _fail(self, test_name: str, reason: str):
        """Record a failing test."""
        self.failed += 1
        print(f'  [FAIL] {test_name}')
        print(f'         Reason: {reason}')
        self.errors.append((test_name, reason))

    def _error(self, test_name: str, error: str):
        """Record a test error."""
        self.failed += 1
        print(f'  [ERROR] {test_name}')
        print(f'          {error}')
        self.errors.append((test_name, f'ERROR: {error}'))

    def _print_summary(self):
        """Print test summary."""
        sep = '=' * 60
        total = self.passed + self.failed
        print()
        print(sep)
        print('  TEST SUMMARY')
        print(sep)
        print()
        print(f'  Total tests: {total}')
        print(f'  Passed:      {self.passed}')
        print(f'  Failed:      {self.failed}')
        print()

        if self.failed == 0:
            print('  [OK] All tests passed!')
        else:
            print('  [FAIL] Some tests failed:')
            for name, reason in self.errors:
                print(f'    - {name}: {reason}')

        print()
        print(sep)


def run_single_stage_test(stage: int) -> bool:
    """Run tests for a single stage."""
    runner = PipelineTestRunner(verbose=True)

    if stage == 1:
        runner._print_header('STAGE 1 TESTS')
        runner.test_stage1_discovery()
    elif stage == 2:
        runner._print_header('STAGE 2 TESTS')
        runner.test_stage2_preparation()
    elif stage == 3:
        runner._print_header('STAGE 3 TESTS')
        runner.test_stage3_verification()
    else:
        print(f'Invalid stage: {stage}. Use 1, 2, or 3.')
        return False

    runner._print_summary()
    return runner.failed == 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Run verification pipeline tests')
    parser.add_argument(
        '--stage',
        type=int,
        choices=[1, 2, 3],
        help='Test only a specific stage (1, 2, or 3)',
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output',
    )

    args = parser.parse_args()

    if args.stage:
        success = run_single_stage_test(args.stage)
    else:
        runner = PipelineTestRunner(verbose=args.verbose or True)
        success = runner.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
