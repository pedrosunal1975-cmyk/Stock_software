# Path: mat_acc/ratio_check/ratio_check.py
"""
Ratio Check - Main Orchestrator

Coordinates the ratio analysis pipeline:
1. Load fact values from mapped statements
2. Run Mathematical Integrity Unit (sign verification)
3. Build enriched concept index
4. Run matching engine and calculate ratios

Source discovery is handled internally - user just selects a filing.
"""

from typing import Optional

from config_loader import ConfigLoader
from core.logger.ipo_logging import get_process_logger

from loaders import (
    MappedDataLoader, ParsedDataLoader, XBRLDataLoader,
)

from .support.database_checker import DatabaseChecker
from .support.data_preparer import DataPreparer
from .support.debug_reporter import DebugReporter, ComponentDebugInfo
from .input.filing_menu import FilingMenu, FilingSelection
from .concept_builder import ConceptBuilder
from .ratio_calculator import RatioCalculator, AnalysisResult
from .fact_value_lookup import FactValueLookup
from .math_verify import (
    IXBRLExtractor, FactReconciler, IdentityValidator, SignAnalyzer,
)
from .math_verify.miu_runner import (
    run_math_verify, run_identity_checks, run_scale_normalization,
)
from .calculation.ratio_definitions import STANDARD_RATIOS
from output.report_generator import ReportGenerator


logger = get_process_logger('ratio_check')


class RatioCheckOrchestrator:
    """
    Main orchestrator for ratio analysis pipeline.

    Source discovery is handled internally - the engine figures out
    which sources are available and uses them appropriately.
    """

    def __init__(
        self, config: Optional[ConfigLoader] = None,
        debug: bool = False,
    ):
        """Initialize orchestrator."""
        self.config = config or ConfigLoader()
        self.logger = get_process_logger(
            'ratio_check.orchestrator',
        )
        self.debug = debug

        self.debug_reporter = DebugReporter(self.config)
        self.debug_reporter.start_process()
        self.debug_reporter.mark_stage('config_loaded')

        self.database_checker = DatabaseChecker(self.config)
        self.data_preparer = DataPreparer(self.config)
        self.filing_menu = FilingMenu(self.config)
        self.concept_builder = ConceptBuilder(self.config)
        self.ratio_calculator = RatioCalculator(self.config)

        self._parsed_loader = ParsedDataLoader(self.config)
        self._xbrl_loader = self._init_xbrl_loader()
        self._last_company: str = ''
        self._report_generator = ReportGenerator(self.config)

        # MIU components
        self._ixbrl_extractor = IXBRLExtractor()
        self._fact_reconciler = FactReconciler()
        self._sign_analyzer = SignAnalyzer()
        self._identity_validator = IdentityValidator()

    def run(self) -> None:
        """Run the interactive ratio analysis workflow."""
        from .workflow import (
            print_header, print_selection, offer_save,
        )
        self.debug_reporter.mark_stage('logging_initialized')
        print_header()

        selection = self.filing_menu.run()
        if selection is None:
            print("\n  Exiting ratio check.")
            return

        self.debug_reporter.mark_stage('filing_selected')
        self._last_company = selection.company
        print_selection(selection)

        result = self._run_analysis(selection)
        if result:
            self.debug_reporter.set_metrics(
                components_matched=result.summary.get(
                    'matched_components', 0,
                ),
                components_total=result.summary.get(
                    'total_components', 0,
                ),
                ratios_valid=result.summary.get(
                    'valid_ratios', 0,
                ),
                ratios_total=result.summary.get(
                    'total_ratios', 0,
                ),
            )
            self.debug_reporter.mark_stage('ratios_calculated')
            self.ratio_calculator.display_results(result)
            if self.debug:
                self.debug_reporter.print_report(verbose=True)
            offer_save(result, self._report_generator)
        else:
            self.debug_reporter.add_error(
                "Analysis returned no results",
            )

    def run_non_interactive(
        self, company: str, market: str,
        form: str, date: str,
    ) -> Optional[AnalysisResult]:
        """Run analysis non-interactively."""
        loader = MappedDataLoader(self.config)
        mapped = loader.find_mapped_filing(
            market, company, form, date,
        )
        if not mapped:
            self.logger.error(
                f"Filing not found: "
                f"{company}/{market}/{form}/{date}"
            )
            return None

        selection = FilingSelection(
            index=0, company=mapped.company,
            market=mapped.market, form=mapped.form,
            date=mapped.date, mapped_entry=mapped,
        )
        return self._run_analysis(selection)

    def _init_xbrl_loader(self) -> Optional[XBRLDataLoader]:
        """Initialize XBRL loader if configured."""
        try:
            return XBRLDataLoader(self.config)
        except (ValueError, KeyError):
            self.logger.debug("XBRL loader not available")
            return None

    def _find_xbrl_filing(self, selection):
        """Find XBRL filing directory for a selection."""
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

    def _find_parsed_entry(self, selection):
        """Find parsed filing for a selection."""
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

    def _run_analysis(
        self, selection: FilingSelection,
    ) -> Optional[AnalysisResult]:
        """Run the analysis pipeline on selected filing."""
        mapped_entry = selection.mapped_entry
        if not mapped_entry:
            self.logger.error("No mapped entry available")
            return None

        print("\n  Loading sources...")
        parsed_entry = self._find_parsed_entry(selection)
        sources = ["mapped statements"]
        if parsed_entry:
            sources.append("parsed.json (concepts only)")
        self.debug_reporter.mark_stage('sources_verified')
        print(f"  Using: {', '.join(sources)}")

        # Load values from mapped statements
        print("\n  Loading fact values...")
        value_lookup = FactValueLookup(self.config)
        value_count = value_lookup.load_from_filing(
            mapped_entry=mapped_entry,
        )
        vs = value_lookup.get_value_summary()
        print(f"  Loaded {value_count} concepts")
        print(
            f"  Primary period: "
            f"{vs.get('primary_period', 'N/A')}"
        )

        # MIU: Verify and correct values
        xbrl_dir = self._find_xbrl_filing(selection)
        ixbrl_facts = []
        if xbrl_dir:
            sources.append("iXBRL source")
            print("\n  Running Mathematical Integrity Unit...")
            _, ixbrl_facts = run_math_verify(
                self._ixbrl_extractor,
                self._fact_reconciler,
                self._sign_analyzer,
                xbrl_dir, value_lookup,
                market=selection.market,
            )
            self.debug_reporter.mark_stage('math_verified')
        else:
            print(
                "\n  [NOTE] iXBRL not available "
                "- skipping MIU"
            )

        # Build concept index
        print("\n  Building concept index...")
        concept_index = self.concept_builder.build_from_filing(
            mapped_entry=mapped_entry,
            parsed_entry=parsed_entry,
            use_database=True,
        )
        if ixbrl_facts:
            added = self.concept_builder.supplement_from_ixbrl(
                ixbrl_facts, concept_index,
            )
            if added:
                print(
                    f"  Supplemented {added} concepts "
                    f"from iXBRL"
                )

        self.debug_reporter.set_metrics(
            concept_count=len(concept_index),
        )
        self.debug_reporter.mark_stage('concepts_built')
        print(f"  Built index with {len(concept_index)} concepts")

        # Run matching and ratio calculation
        print("\n  Running matching engine...")
        result = self.ratio_calculator.analyze(
            selection=selection,
            concept_index=concept_index,
            value_lookup=value_lookup,
        )
        self.debug_reporter.mark_stage('matching_complete')

        # MIU Layer 3: Identity validation
        if result:
            run_identity_checks(
                self._identity_validator,
                result.component_matches,
            )

        # Scale normalization
        if result and ixbrl_facts:
            result.normalizations = run_scale_normalization(
                self._ixbrl_extractor,
                result.ratios, result.component_matches,
                ixbrl_facts, STANDARD_RATIOS,
            )

        # Track unmatched for debug
        if result:
            self._track_unmatched(result.component_matches)
        return result

    def _track_unmatched(self, matches) -> None:
        """Record unmatched components for debug reporting."""
        for match in matches:
            if not match.matched:
                self.debug_reporter.add_component_debug(
                    ComponentDebugInfo(
                        component_id=match.component_name,
                        matched=False, candidates_found=0,
                    )
                )


__all__ = ['RatioCheckOrchestrator']
