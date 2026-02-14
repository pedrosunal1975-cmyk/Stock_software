# Path: mat_acc/ratio_check/debug_reporter.py
"""
Debug Reporter

Provides detailed status reporting for ratio_check debugging.
Shows current state, component matching status, and logging info.

Use this module to understand where the process is and what's failing.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

from config_loader import ConfigLoader

# Import IPO logging (OUTPUT layer for reporting)
from core.logger.ipo_logging import get_output_logger


# Use IPO-aware logger (OUTPUT layer - debugging reports)
logger = get_output_logger('debug_reporter')


@dataclass
class ComponentDebugInfo:
    """
    Debug information for a single component match attempt.

    Attributes:
        component_id: Component identifier
        matched: Whether match succeeded
        matched_concept: Matched concept QName if any
        confidence: Match confidence score
        candidates_found: Number of candidates evaluated
        rejection_reasons: Why candidates were rejected
        rule_scores: Score breakdown by rule type
        error: Error message if matching failed
    """
    component_id: str
    matched: bool = False
    matched_concept: Optional[str] = None
    confidence: float = 0.0
    candidates_found: int = 0
    rejection_reasons: List[str] = field(default_factory=list)
    rule_scores: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ProcessState:
    """
    Current state of the ratio_check process.

    Tracks which stages have completed and their results.
    """
    # Stage completion
    config_loaded: bool = False
    logging_initialized: bool = False
    filing_selected: bool = False
    sources_verified: bool = False
    concepts_built: bool = False
    matching_complete: bool = False
    ratios_calculated: bool = False

    # Metrics
    concept_count: int = 0
    components_matched: int = 0
    components_total: int = 0
    ratios_valid: int = 0
    ratios_total: int = 0

    # Timing
    start_time: Optional[datetime] = None
    stage_times: Dict[str, float] = field(default_factory=dict)

    # Errors
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DebugReporter:
    """
    Debug reporter for ratio_check process.

    Collects and displays detailed debugging information
    to help understand where the process is and what's failing.

    Example:
        reporter = DebugReporter(config)

        # Track process stages
        reporter.mark_stage('config_loaded')
        reporter.mark_stage('logging_initialized')

        # Add component debug info
        reporter.add_component_debug(ComponentDebugInfo(...))

        # Print full report
        reporter.print_report()
    """

    def __init__(self, config: ConfigLoader):
        """
        Initialize debug reporter.

        Args:
            config: ConfigLoader instance
        """
        self.config = config
        self.logger = get_output_logger('debug_reporter')
        self.state = ProcessState()
        self.component_debug: Dict[str, ComponentDebugInfo] = {}
        self._stage_start: Optional[datetime] = None

    def start_process(self) -> None:
        """Mark the start of the ratio_check process."""
        self.state.start_time = datetime.now()
        self._stage_start = self.state.start_time
        self.logger.info("Ratio check process started")

    def mark_stage(self, stage: str, success: bool = True, error: Optional[str] = None) -> None:
        """
        Mark a stage as complete.

        Args:
            stage: Stage name (e.g., 'config_loaded', 'concepts_built')
            success: Whether stage completed successfully
            error: Error message if failed
        """
        now = datetime.now()

        # Calculate stage duration
        if self._stage_start:
            duration = (now - self._stage_start).total_seconds()
            self.state.stage_times[stage] = duration

        self._stage_start = now

        # Update state
        if hasattr(self.state, stage):
            setattr(self.state, stage, success)

        if error:
            self.state.errors.append(f"[{stage}] {error}")
            self.logger.error(f"Stage '{stage}' failed: {error}")
        else:
            self.logger.info(f"Stage '{stage}' completed in {duration:.3f}s")

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.state.warnings.append(message)
        self.logger.warning(message)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.state.errors.append(message)
        self.logger.error(message)

    def set_metrics(
        self,
        concept_count: Optional[int] = None,
        components_matched: Optional[int] = None,
        components_total: Optional[int] = None,
        ratios_valid: Optional[int] = None,
        ratios_total: Optional[int] = None,
    ) -> None:
        """Update process metrics."""
        if concept_count is not None:
            self.state.concept_count = concept_count
        if components_matched is not None:
            self.state.components_matched = components_matched
        if components_total is not None:
            self.state.components_total = components_total
        if ratios_valid is not None:
            self.state.ratios_valid = ratios_valid
        if ratios_total is not None:
            self.state.ratios_total = ratios_total

    def add_component_debug(self, info: ComponentDebugInfo) -> None:
        """
        Add debug info for a component match attempt.

        Args:
            info: ComponentDebugInfo with match details
        """
        self.component_debug[info.component_id] = info

        if info.matched:
            self.logger.debug(
                f"Component '{info.component_id}' matched to "
                f"'{info.matched_concept}' (confidence: {info.confidence:.2f})"
            )
        else:
            self.logger.debug(
                f"Component '{info.component_id}' NOT matched. "
                f"Candidates: {info.candidates_found}, "
                f"Rejections: {len(info.rejection_reasons)}"
            )

    def get_unmatched_components(self) -> List[ComponentDebugInfo]:
        """Get list of components that failed to match."""
        return [
            info for info in self.component_debug.values()
            if not info.matched
        ]

    def get_low_confidence_matches(self, threshold: float = 0.7) -> List[ComponentDebugInfo]:
        """Get matches with confidence below threshold."""
        return [
            info for info in self.component_debug.values()
            if info.matched and info.confidence < threshold
        ]

    def check_logging_status(self) -> Dict[str, Any]:
        """
        Check current logging configuration status.

        Returns:
            Dictionary with logging status information
        """
        log_dir = self.config.get('log_dir')
        log_level = self.config.get('log_level', 'INFO')

        status = {
            'log_dir': str(log_dir) if log_dir else 'NOT CONFIGURED',
            'log_level': log_level,
            'log_dir_exists': log_dir.exists() if log_dir else False,
            'log_files': [],
            'handlers_active': len(logging.root.handlers),
        }

        # Check for log files
        if log_dir and log_dir.exists():
            status['log_files'] = [f.name for f in log_dir.glob('*.log')]

        return status

    def print_report(self, verbose: bool = False) -> None:
        """
        Print comprehensive debug report.

        Args:
            verbose: Include detailed component info
        """
        print()
        print("=" * 70)
        print("  RATIO CHECK DEBUG REPORT")
        print("=" * 70)

        # Process State
        print("\n  PROCESS STATE:")
        print("-" * 70)
        stages = [
            ('config_loaded', 'Configuration Loaded'),
            ('logging_initialized', 'Logging Initialized'),
            ('filing_selected', 'Filing Selected'),
            ('sources_verified', 'Sources Verified'),
            ('concepts_built', 'Concepts Built'),
            ('matching_complete', 'Matching Complete'),
            ('ratios_calculated', 'Ratios Calculated'),
        ]

        for attr, label in stages:
            status = getattr(self.state, attr, False)
            time_taken = self.state.stage_times.get(attr, 0)
            icon = "[OK]" if status else "[--]"
            time_str = f"({time_taken:.3f}s)" if time_taken else ""
            print(f"    {icon} {label:30s} {time_str}")

        # Metrics
        print("\n  METRICS:")
        print("-" * 70)
        print(f"    Concepts indexed: {self.state.concept_count}")
        print(f"    Components matched: {self.state.components_matched}/{self.state.components_total}")
        if self.state.components_total > 0:
            rate = self.state.components_matched / self.state.components_total * 100
            print(f"    Match rate: {rate:.1f}%")
        print(f"    Ratios valid: {self.state.ratios_valid}/{self.state.ratios_total}")

        # Logging Status
        print("\n  LOGGING STATUS:")
        print("-" * 70)
        log_status = self.check_logging_status()
        print(f"    Log directory: {log_status['log_dir']}")
        print(f"    Directory exists: {log_status['log_dir_exists']}")
        print(f"    Log level: {log_status['log_level']}")
        print(f"    Active handlers: {log_status['handlers_active']}")
        if log_status['log_files']:
            print(f"    Log files: {', '.join(log_status['log_files'])}")
        else:
            print("    Log files: NONE (logs not being written to files!)")

        # Unmatched Components
        unmatched = self.get_unmatched_components()
        if unmatched:
            print(f"\n  UNMATCHED COMPONENTS ({len(unmatched)}):")
            print("-" * 70)
            for info in unmatched[:10]:
                print(f"    [--] {info.component_id}")
                if info.candidates_found == 0:
                    print(f"         No candidates found")
                elif info.rejection_reasons:
                    print(f"         Candidates: {info.candidates_found}, "
                          f"Rejected: {len(info.rejection_reasons)}")
                if verbose and info.rejection_reasons:
                    for reason in info.rejection_reasons[:3]:
                        print(f"           - {reason}")
            if len(unmatched) > 10:
                print(f"    ... and {len(unmatched) - 10} more")

        # Low Confidence Matches
        low_conf = self.get_low_confidence_matches()
        if low_conf:
            print(f"\n  LOW CONFIDENCE MATCHES ({len(low_conf)}):")
            print("-" * 70)
            for info in low_conf[:5]:
                print(f"    [?] {info.component_id} -> {info.matched_concept}")
                print(f"        Confidence: {info.confidence:.2f}")
                if verbose and info.rule_scores:
                    for rule, score in info.rule_scores.items():
                        print(f"          {rule}: {score:.2f}")

        # Errors
        if self.state.errors:
            print(f"\n  ERRORS ({len(self.state.errors)}):")
            print("-" * 70)
            for error in self.state.errors:
                print(f"    [ERROR] {error}")

        # Warnings
        if self.state.warnings:
            print(f"\n  WARNINGS ({len(self.state.warnings)}):")
            print("-" * 70)
            for warning in self.state.warnings:
                print(f"    [WARN] {warning}")

        # Total time
        if self.state.start_time:
            total_time = (datetime.now() - self.state.start_time).total_seconds()
            print(f"\n  Total time: {total_time:.2f}s")

        print()
        print("=" * 70)

    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """
        Save debug report to JSON file.

        Args:
            output_path: Optional output path. Defaults to config output_dir.

        Returns:
            Path to saved report
        """
        import json

        if output_path is None:
            output_dir = self.config.get('output_dir', Path('/tmp'))
            output_path = output_dir / f"debug_report_{datetime.now():%Y%m%d_%H%M%S}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        report_data = {
            'timestamp': datetime.now().isoformat(),
            'state': {
                'config_loaded': self.state.config_loaded,
                'logging_initialized': self.state.logging_initialized,
                'filing_selected': self.state.filing_selected,
                'sources_verified': self.state.sources_verified,
                'concepts_built': self.state.concepts_built,
                'matching_complete': self.state.matching_complete,
                'ratios_calculated': self.state.ratios_calculated,
            },
            'metrics': {
                'concept_count': self.state.concept_count,
                'components_matched': self.state.components_matched,
                'components_total': self.state.components_total,
                'ratios_valid': self.state.ratios_valid,
                'ratios_total': self.state.ratios_total,
            },
            'stage_times': self.state.stage_times,
            'logging_status': self.check_logging_status(),
            'unmatched_components': [
                {
                    'component_id': info.component_id,
                    'candidates_found': info.candidates_found,
                    'rejection_reasons': info.rejection_reasons,
                }
                for info in self.get_unmatched_components()
            ],
            'low_confidence_matches': [
                {
                    'component_id': info.component_id,
                    'matched_concept': info.matched_concept,
                    'confidence': info.confidence,
                    'rule_scores': info.rule_scores,
                }
                for info in self.get_low_confidence_matches()
            ],
            'errors': self.state.errors,
            'warnings': self.state.warnings,
        }

        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        self.logger.info(f"Debug report saved to: {output_path}")
        return output_path


__all__ = ['DebugReporter', 'ComponentDebugInfo', 'ProcessState']
