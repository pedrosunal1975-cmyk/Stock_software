# Path: mat_acc_files/ratio_check/ratio_check.py
"""
Ratio Check - Main Orchestrator

Complete workflow for financial ratio analysis:
1. Display available filings for selection
2. Build enriched concepts from available sources
3. Run matching engine
4. Calculate and display ratios

Source discovery is handled internally - user just selects a filing.

Usage:
    python -m ratio_check.ratio_check
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from config_loader import ConfigLoader

# Import IPO logging system
from core.logger.ipo_logging import (
    setup_ipo_logging,
    get_process_logger,
    get_input_logger,
    get_output_logger,
)

# Import loaders for source discovery (engine's job)
from loaders import (
    MappedDataLoader,
    ParsedDataLoader,
    XBRLDataLoader,
    MappedFilingEntry,
    ParsedFilingEntry,
)

# Import module components
from .database_checker import DatabaseChecker
from .data_preparer import DataPreparer
from .filing_menu import FilingMenu, FilingSelection
from .concept_builder import ConceptBuilder
from .ratio_calculator import RatioCalculator, AnalysisResult
from .debug_reporter import DebugReporter, ComponentDebugInfo
from .fact_value_lookup import FactValueLookup
from .math_verify import (
    IXBRLExtractor, FactReconciler, IdentityValidator, SignAnalyzer,
)


# Use IPO-aware logger (PROCESS layer for calculation/matching work)
logger = get_process_logger('ratio_check')


class RatioCheckOrchestrator:
    """
    Main orchestrator for ratio analysis workflow.

    Source discovery is handled internally - the engine figures out
    which sources are available and uses them appropriately.

    Example:
        orchestrator = RatioCheckOrchestrator()
        orchestrator.run()
    """

    def __init__(self, config: Optional[ConfigLoader] = None, debug: bool = False):
        """
        Initialize orchestrator.

        Args:
            config: Optional ConfigLoader (creates one if not provided)
            debug: Enable debug reporting
        """
        self.config = config or ConfigLoader()
        self.logger = get_process_logger('ratio_check.orchestrator')
        self.debug = debug

        # Initialize debug reporter
        self.debug_reporter = DebugReporter(self.config)
        self.debug_reporter.start_process()
        self.debug_reporter.mark_stage('config_loaded')

        # Initialize components
        self.database_checker = DatabaseChecker(self.config)
        self.data_preparer = DataPreparer(self.config)
        self.filing_menu = FilingMenu(self.config)
        self.concept_builder = ConceptBuilder(self.config)
        self.ratio_calculator = RatioCalculator(self.config)

        # Loaders for source discovery (engine's responsibility)
        self._parsed_loader = ParsedDataLoader(self.config)
        self._xbrl_loader = self._init_xbrl_loader()

        # Mathematical Integrity Unit components
        self._ixbrl_extractor = IXBRLExtractor()
        self._fact_reconciler = FactReconciler()
        self._sign_analyzer = SignAnalyzer()
        self._identity_validator = IdentityValidator()

    def run(self) -> None:
        """
        Run the complete ratio analysis workflow.

        Interactive CLI workflow:
        1. Show available filings
        2. Get user selection
        3. Build concepts and run analysis
        4. Display results
        """
        self.debug_reporter.mark_stage('logging_initialized')
        self._print_header()

        # Run filing selection menu
        selection = self.filing_menu.run()

        if selection is None:
            print("\n  Exiting ratio check.")
            return

        self.debug_reporter.mark_stage('filing_selected')

        # Show selection
        self._print_selection(selection)

        # Run analysis
        result = self._run_analysis(selection)

        if result:
            # Update debug metrics
            self.debug_reporter.set_metrics(
                components_matched=result.summary.get('matched_components', 0),
                components_total=result.summary.get('total_components', 0),
                ratios_valid=result.summary.get('valid_ratios', 0),
                ratios_total=result.summary.get('total_ratios', 0),
            )
            self.debug_reporter.mark_stage('ratios_calculated')

            # Display results
            self.ratio_calculator.display_results(result)

            # Show debug report if enabled
            if self.debug:
                self.debug_reporter.print_report(verbose=True)

            # Offer to save results
            self._offer_save(result)
        else:
            self.debug_reporter.add_error("Analysis returned no results")

    def run_non_interactive(
        self,
        company: str,
        market: str,
        form: str,
        date: str,
    ) -> Optional[AnalysisResult]:
        """
        Run analysis non-interactively.

        Args:
            company: Company name
            market: Market identifier
            form: Form type
            date: Filing date

        Returns:
            AnalysisResult or None if failed
        """
        # Find the filing using loader
        loader = MappedDataLoader(self.config)
        mapped = loader.find_mapped_filing(market, company, form, date)

        if not mapped:
            self.logger.error(f"Filing not found: {company}/{market}/{form}/{date}")
            return None

        # Create selection
        selection = FilingSelection(
            index=0,
            company=mapped.company,
            market=mapped.market,
            form=mapped.form,
            date=mapped.date,
            mapped_entry=mapped,
        )

        # Run analysis
        return self._run_analysis(selection)

    def _print_header(self) -> None:
        """Print application header."""
        print()
        print("=" * 70)
        print("  RATIO CHECK - Financial Statement Analysis")
        print("=" * 70)
        print()

    def _print_selection(self, selection: FilingSelection) -> None:
        """Print selected filing info."""
        print()
        print("-" * 70)
        print(f"  Selected: {selection.company}")
        print(f"  Market: {selection.market.upper()} | Form: {selection.form} | Date: {selection.date}")
        print("-" * 70)

    def _init_xbrl_loader(self) -> Optional[XBRLDataLoader]:
        """Initialize XBRL loader if configured."""
        try:
            return XBRLDataLoader(self.config)
        except (ValueError, KeyError):
            self.logger.debug("XBRL loader not available (path not configured)")
            return None

    def _find_xbrl_filing(self, selection: FilingSelection) -> Optional[Path]:
        """
        Find XBRL filing directory for a selection.

        Args:
            selection: Selected filing

        Returns:
            Path to filing directory or None
        """
        if not self._xbrl_loader:
            return None

        try:
            return self._xbrl_loader.find_filing_for_company(
                market=selection.market,
                company=selection.company,
                form=selection.form,
                date=selection.date,
            )
        except Exception as e:
            self.logger.debug(f"XBRL filing not found: {e}")
            return None

    def _run_math_verify(
        self, xbrl_dir: Path, value_lookup: FactValueLookup,
    ) -> int:
        """
        Run Mathematical Integrity Unit on loaded values.

        Layer 1: Extract numeric truth from iXBRL source
        Layer 2: Reconcile against parsed/mapped values
        Layer 3: (Identity validation runs after matching)

        Args:
            xbrl_dir: Path to XBRL filing directory
            value_lookup: Loaded value lookup to correct

        Returns:
            Number of corrections applied
        """
        # Layer 1: Extract mathematically correct values from iXBRL
        ixbrl_facts = self._ixbrl_extractor.extract_from_directory(xbrl_dir)
        if not ixbrl_facts:
            self.logger.warning("MIU: No facts extracted from iXBRL")
            return 0

        print(f"  MIU Layer 1: Extracted {len(ixbrl_facts)} primary facts from iXBRL")

        # Sign validation on extracted facts
        sign_checks = self._sign_analyzer.analyze(ixbrl_facts)
        sign_summary = self._sign_analyzer.summarize(sign_checks)
        if sign_summary['anomalies'] > 0:
            print(f"  MIU Sign Check: {sign_summary['anomalies']} anomalies detected")
            for concept, value, note in sign_summary['anomaly_concepts'][:3]:
                local = concept.split(':')[-1] if ':' in concept else concept
                print(f"    - {local}: {value:,.0f} ({note})")
        else:
            print(f"  MIU Sign Check: {sign_summary['consistent']} facts consistent")

        # Build loaded values map for reconciliation against iXBRL truth
        loaded_values = {}
        for fact in ixbrl_facts:
            existing = value_lookup.get_value(fact.concept)
            if existing is not None:
                loaded_values[fact.concept] = existing

        # Layer 2: Reconcile iXBRL against loaded values
        results = self._fact_reconciler.reconcile(
            ixbrl_facts=ixbrl_facts,
            parsed_values=loaded_values,
        )

        # Get sign-only corrections (scale diffs are expected)
        corrections = self._fact_reconciler.get_corrections(results)
        summary = self._fact_reconciler.get_summary(results)

        print(
            f"  MIU Layer 2: {summary['sign_corrections']} sign corrections, "
            f"{summary['scale_diffs']} scale diffs (expected), "
            f"{summary['value_matches']} matched"
        )

        # Apply sign corrections to value lookup
        if corrections:
            corrected = value_lookup.apply_corrections(corrections)
            print(f"  MIU: Applied {corrected} sign corrections to values")
            # Log sample corrections for visibility
            for concept, val in list(corrections.items())[:3]:
                local = concept.split(':')[-1] if ':' in concept else concept
                print(f"    - {local}: corrected to {val:,.0f}")
            return corrected

        return 0

    def _run_identity_checks(self, result) -> None:
        """
        Run Layer 3 identity validation after matching.

        Args:
            result: AnalysisResult with populated component values
        """
        # Build component value map from matched components
        values = {}
        for match in result.component_matches:
            if match.value is not None:
                values[match.component_name] = match.value

        checks = self._identity_validator.validate(values)

        # Display results
        print("\n  MIU Layer 3: Mathematical Identity Checks")
        print("  " + "-" * 50)
        for check in checks:
            if check.skipped:
                continue
            status = '[OK]' if check.passed else '[FAIL]'
            print(f"    {status} {check.identity}")
            if not check.passed and check.lhs_value is not None:
                print(
                    f"          LHS: {check.lhs_value:,.0f}  "
                    f"RHS: {check.rhs_value:,.0f}  "
                    f"diff: {check.difference:,.0f}"
                )

    def _find_parsed_entry(self, selection: FilingSelection) -> Optional[ParsedFilingEntry]:
        """
        Find parsed filing for a selection.

        Engine's responsibility to discover available sources.

        Args:
            selection: Selected filing

        Returns:
            ParsedFilingEntry or None if not found
        """
        try:
            return self._parsed_loader.find_parsed_filing(
                market=selection.market,
                company=selection.company,
                form=selection.form,
                date=selection.date,
            )
        except Exception as e:
            self.logger.debug(f"Parsed filing not found: {e}")
            return None

    def _run_analysis(self, selection: FilingSelection) -> Optional[AnalysisResult]:
        """
        Run the analysis on selected filing.

        Args:
            selection: Selected filing

        Returns:
            AnalysisResult or None
        """
        mapped_entry = selection.mapped_entry

        if not mapped_entry:
            self.logger.error("No mapped entry available")
            self.debug_reporter.add_error("No mapped entry available")
            return None

        print("\n  Loading sources...")

        # Engine discovers what sources are available
        parsed_entry = self._find_parsed_entry(selection)

        sources_used = ["mapped statements"]
        if parsed_entry:
            sources_used.append("parsed.json (concepts only)")

        self.debug_reporter.mark_stage('sources_verified')
        print(f"  Using: {', '.join(sources_used)}")

        # CRITICAL: Create value lookup from mapped statements
        # (Values come from mapped statements only; MIU corrects signs from iXBRL)
        print("\n  Loading fact values from mapped statements...")
        value_lookup = FactValueLookup(self.config)
        value_count = value_lookup.load_from_filing(
            mapped_entry=mapped_entry,
        )
        print(f"  Loaded values for {value_count} concepts")
        value_summary = value_lookup.get_value_summary()
        print(f"  Primary period: {value_summary.get('primary_period', 'N/A')}")
        print(f"  Total values: {value_summary.get('total_values', 0)}")

        # MATHEMATICAL INTEGRITY UNIT: Verify and correct values
        xbrl_dir = self._find_xbrl_filing(selection)
        if xbrl_dir:
            sources_used.append("iXBRL source")
            print("\n  Running Mathematical Integrity Unit...")
            self._run_math_verify(xbrl_dir, value_lookup)
            self.debug_reporter.mark_stage('math_verified')
        else:
            print("\n  [NOTE] iXBRL source not available - skipping MIU")

        print("\n  Building concept index...")

        # Build concept index from available sources
        concept_index = self.concept_builder.build_from_filing(
            mapped_entry=mapped_entry,
            parsed_entry=parsed_entry,
            use_database=True,
        )

        concept_count = len(concept_index)
        self.debug_reporter.set_metrics(concept_count=concept_count)
        self.debug_reporter.mark_stage('concepts_built')

        print(f"  Built index with {concept_count} concepts")

        # Debug: show concepts matching 'assets'
        all_concepts = concept_index.get_all_concepts()
        asset_concepts = [c for c in all_concepts if 'asset' in c.local_name.lower()]
        print(f"\n  Concepts containing 'asset' ({len(asset_concepts)} found):")
        for c in asset_concepts[:5]:
            labels = list(c.labels.values()) if c.labels else ['(no labels)']
            # Also show value if available
            val = value_lookup.get_value(c.qname)
            val_str = f", value={val:,.0f}" if val else ""
            print(f"    - {c.qname}{val_str}")
            print(f"      local_name: {c.local_name}")
            print(f"      labels: {labels[:1]}")  # Just first label
            print(f"      balance: {c.balance_type}, period: {c.period_type}")

        print("\n  Running matching engine...")

        # Run analysis WITH value lookup
        result = self.ratio_calculator.analyze(
            selection=selection,
            concept_index=concept_index,
            value_lookup=value_lookup,  # CRITICAL: Pass value lookup!
        )

        self.debug_reporter.mark_stage('matching_complete')

        # MIU Layer 3: Mathematical identity validation
        if result:
            self._run_identity_checks(result)

        # Capture component debug info for unmatched components
        if result:
            for match in result.component_matches:
                if not match.matched:
                    self.debug_reporter.add_component_debug(ComponentDebugInfo(
                        component_id=match.component_name,
                        matched=False,
                        candidates_found=0,  # Would need enhanced info from matcher
                    ))

        return result

    def _offer_save(self, result: AnalysisResult) -> None:
        """Offer to save results to file."""
        print("\n  Save results to file? (y/n): ", end='')

        try:
            choice = input().strip().lower()
            if choice == 'y':
                self._save_results(result)
        except (KeyboardInterrupt, EOFError):
            pass

    def _save_results(self, result: AnalysisResult) -> None:
        """Save results to JSON file."""
        import json

        # Build output path
        output_dir = Path(self.config.get('ratio_check_output_dir', '/tmp'))
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"ratio_check_{result.company}_{result.date}.json".replace(' ', '_')
        output_path = output_dir / filename

        # Build output data
        output_data = {
            'company': result.company,
            'market': result.market,
            'form': result.form,
            'date': result.date,
            'analysis_date': datetime.now().isoformat(),
            'component_matches': [
                {
                    'component': m.component_name,
                    'matched': m.matched,
                    'concept': m.matched_concept,
                    'confidence': m.confidence,
                    'label': m.label,
                }
                for m in result.component_matches
            ],
            'ratios': [
                {
                    'name': r.ratio_name,
                    'value': r.value,
                    'valid': r.valid,
                    'formula': r.formula,
                    'error': r.error,
                }
                for r in result.ratios
            ],
            'summary': result.summary,
        }

        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n  Results saved to: {output_path}")


def setup_logging(config: Optional[ConfigLoader] = None) -> None:
    """
    Configure IPO logging for the application.

    Sets up file-based logging with IPO separation:
    - input_activity.log: Loading operations
    - process_activity.log: Calculation/matching work
    - output_activity.log: Report generation
    - full_activity.log: All activities

    Args:
        config: ConfigLoader instance (creates one if not provided)
    """
    config = config or ConfigLoader()

    # Get log configuration from config
    log_dir = config.get('log_dir')
    log_level = config.get('log_level', 'INFO')
    log_console = config.get('log_console', True)

    # Setup IPO logging with file handlers
    setup_ipo_logging(
        log_dir=log_dir,
        log_level=log_level,
        console_output=log_console,
    )

    # Reduce noise from third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

    # Log initialization
    logger.info(f"Logging initialized: level={log_level}, dir={log_dir}")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Financial Ratio Analysis')
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug reporting'
    )
    parser.add_argument(
        '--debug-report',
        action='store_true',
        help='Show debug report only (check logging status)'
    )
    args = parser.parse_args()

    # Initialize config first (needed for logging setup)
    config = ConfigLoader()

    # Setup IPO logging with file handlers
    setup_logging(config)

    # If just checking debug status
    if args.debug_report:
        reporter = DebugReporter(config)
        print("\n  Checking logging configuration...")
        reporter.print_report()
        return

    try:
        orchestrator = RatioCheckOrchestrator(config, debug=args.debug)
        orchestrator.run()

        # Always show debug report if debug mode enabled
        if args.debug:
            orchestrator.debug_reporter.save_report()

    except KeyboardInterrupt:
        print("\n\n  Interrupted by user.")
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n  [ERROR] {e}")
        logger.exception("Unhandled exception in ratio_check")
        sys.exit(1)


if __name__ == '__main__':
    main()


__all__ = ['RatioCheckOrchestrator', 'main']
