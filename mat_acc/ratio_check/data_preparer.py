# Path: mat_acc_files/ratio_check/data_preparer.py
"""
Data Preparer

Runs preparation scripts to ensure data is ready for ratio analysis:
- populate_database.py - Create HierarchyNode data
- enrich_taxonomies.py - Add taxonomy labels to nodes
- generate_raw_trees.py - Generate visual tree representations

Executes scripts as subprocesses with proper environment configuration.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from config_loader import ConfigLoader

# Import IPO logging (PROCESS layer for data preparation)
from core.logger.ipo_logging import get_process_logger


# Use IPO-aware logger (PROCESS layer - data preparation)
logger = get_process_logger('data_preparer')


class DataPreparer:
    """
    Runs preparation scripts for ratio analysis.

    Ensures all required data is populated and enriched before
    running the matching engine.

    Example:
        preparer = DataPreparer(config)

        # Check if enrichment is needed
        if not preparer.is_enriched(company, market):
            # Run full preparation
            preparer.prepare_company(company, market)

        # Or run individual steps
        preparer.run_populate_database(company, market)
        preparer.run_enrich_taxonomies()
        preparer.run_generate_raw_trees(company, market)
    """

    def __init__(self, config: ConfigLoader):
        """
        Initialize data preparer.

        Args:
            config: ConfigLoader instance
        """
        self.config = config
        self.logger = get_process_logger('data_preparer')

        # Script paths
        self.scripts_dir = Path(__file__).parent.parent / 'scripts'
        self.populate_script = self.scripts_dir / 'populate_database.py'
        self.enrich_script = self.scripts_dir / 'enrich_taxonomies.py'
        self.raw_trees_script = self.scripts_dir / 'generate_raw_trees.py'

    def _get_script_env(self) -> dict:
        """
        Get environment for running scripts.

        Returns:
            Environment dictionary
        """
        env = os.environ.copy()

        # Ensure mat_acc .env is loaded
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            from dotenv import load_dotenv
            load_dotenv(env_path, override=True)
            env = os.environ.copy()

        return env

    def _run_script(
        self,
        script_path: Path,
        args: list[str] = None,
        timeout: int = 300
    ) -> dict:
        """
        Run a script as subprocess.

        Args:
            script_path: Path to script
            args: Command line arguments
            timeout: Timeout in seconds

        Returns:
            Dictionary with:
                success: True if successful
                output: stdout output
                error: stderr output
        """
        if not script_path.exists():
            return {
                'success': False,
                'output': '',
                'error': f"Script not found: {script_path}",
            }

        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)

        self.logger.info(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                env=self._get_script_env(),
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else '',
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': f"Script timed out after {timeout} seconds",
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
            }

    def run_populate_database(
        self,
        company: Optional[str] = None,
        market: Optional[str] = None,
        limit: Optional[int] = None,
        skip_taxonomy: bool = True,
    ) -> dict:
        """
        Run populate_database.py script.

        Populates HierarchyNode data for filings.

        Args:
            company: Optional company filter (not implemented in script)
            market: Optional market filter
            limit: Optional limit on filings to process
            skip_taxonomy: Skip taxonomy availability check

        Returns:
            Result dictionary from _run_script
        """
        args = []

        if market:
            args.extend(['--market', market])
        if limit:
            args.extend(['--limit', str(limit)])
        if skip_taxonomy:
            args.append('--skip-taxonomy')

        self.logger.info("Running populate_database.py...")
        result = self._run_script(self.populate_script, args, timeout=600)

        if result['success']:
            self.logger.info("populate_database.py completed successfully")
        else:
            self.logger.error(f"populate_database.py failed: {result['error']}")

        return result

    def run_enrich_taxonomies(self) -> dict:
        """
        Run enrich_taxonomies.py script.

        Adds standard_label from taxonomy libraries to HierarchyNodes.

        Returns:
            Result dictionary from _run_script
        """
        self.logger.info("Running enrich_taxonomies.py...")
        result = self._run_script(self.enrich_script, timeout=300)

        if result['success']:
            self.logger.info("enrich_taxonomies.py completed successfully")
        else:
            self.logger.error(f"enrich_taxonomies.py failed: {result['error']}")

        return result

    def run_generate_raw_trees(
        self,
        company: Optional[str] = None,
        market: Optional[str] = None,
    ) -> dict:
        """
        Run generate_raw_trees.py script.

        Generates visual tree representations and raw_tree.json files.

        Args:
            company: Optional company filter
            market: Optional market filter

        Returns:
            Result dictionary from _run_script
        """
        args = []

        # Note: Current script may not support these filters
        # Add them if script supports

        self.logger.info("Running generate_raw_trees.py...")
        result = self._run_script(self.raw_trees_script, timeout=300)

        if result['success']:
            self.logger.info("generate_raw_trees.py completed successfully")
        else:
            self.logger.error(f"generate_raw_trees.py failed: {result['error']}")

        return result

    def prepare_company(
        self,
        company: str,
        market: str,
        force: bool = False,
    ) -> dict:
        """
        Run full preparation for a company.

        Runs all preparation scripts in order:
        1. populate_database.py (if needed)
        2. enrich_taxonomies.py
        3. generate_raw_trees.py (optional)

        Args:
            company: Company name
            market: Market identifier
            force: Force re-run even if data exists

        Returns:
            Dictionary with results from each step
        """
        results = {
            'populate': None,
            'enrich': None,
            'raw_trees': None,
            'overall_success': False,
        }

        # Step 1: Populate database
        self.logger.info(f"Preparing data for {company}/{market}...")

        populate_result = self.run_populate_database(
            market=market,
            skip_taxonomy=True,  # Assume taxonomies are already available
        )
        results['populate'] = populate_result

        if not populate_result['success']:
            self.logger.error("Database population failed")
            return results

        # Step 2: Enrich with taxonomy labels
        enrich_result = self.run_enrich_taxonomies()
        results['enrich'] = enrich_result

        if not enrich_result['success']:
            self.logger.warning("Taxonomy enrichment failed (continuing anyway)")

        # Step 3: Generate raw trees (optional, for visualization)
        # Uncomment if needed:
        # raw_trees_result = self.run_generate_raw_trees()
        # results['raw_trees'] = raw_trees_result

        results['overall_success'] = populate_result['success']

        if results['overall_success']:
            self.logger.info(f"Data preparation complete for {company}/{market}")
        else:
            self.logger.error(f"Data preparation failed for {company}/{market}")

        return results

    def check_preparation_needed(
        self,
        company: str,
        market: str,
    ) -> dict:
        """
        Check if data preparation is needed for a company/market.

        Checks:
        1. If hierarchy data exists in the database
        2. If nodes have been enriched with taxonomy labels

        Args:
            company: Company name
            market: Market identifier

        Returns:
            Dictionary with:
                needs_database: True if hierarchy data is missing
                needs_enrichment: True if taxonomy labels are missing
                node_count: Total nodes found
                enriched_count: Nodes with standard_label
        """
        result = {
            'needs_database': True,
            'needs_enrichment': True,
            'node_count': 0,
            'enriched_count': 0,
        }

        try:
            # Import database modules
            from database import (
                initialize_engine,
                session_scope,
                ProcessedFiling,
                StatementHierarchy,
                HierarchyNode,
            )

            # Initialize database connection
            db_url = self.config.get_db_connection_string()
            initialize_engine(db_url)

            with session_scope() as session:
                # Find the processed filing
                filing = session.query(ProcessedFiling).filter(
                    ProcessedFiling.company_name.ilike(f"%{company}%"),
                    ProcessedFiling.market == market.lower(),
                ).first()

                if not filing:
                    self.logger.debug(f"No processed filing found for {company}/{market}")
                    return result

                # Get hierarchies
                hierarchies = session.query(StatementHierarchy).filter_by(
                    filing_id=filing.filing_id
                ).all()

                if not hierarchies:
                    self.logger.debug(f"No hierarchies found for {company}")
                    return result

                # Count nodes and enriched nodes
                total_nodes = 0
                enriched_nodes = 0

                for hierarchy in hierarchies:
                    # Count all nodes
                    node_count = session.query(HierarchyNode).filter_by(
                        hierarchy_id=hierarchy.hierarchy_id
                    ).count()
                    total_nodes += node_count

                    # Count nodes with standard_label (enriched)
                    enriched_count = session.query(HierarchyNode).filter(
                        HierarchyNode.hierarchy_id == hierarchy.hierarchy_id,
                        HierarchyNode.standard_label.isnot(None),
                        HierarchyNode.standard_label != '',
                    ).count()
                    enriched_nodes += enriched_count

                result['node_count'] = total_nodes
                result['enriched_count'] = enriched_nodes
                result['needs_database'] = total_nodes == 0
                # Consider enriched if at least 50% of nodes have labels
                result['needs_enrichment'] = (
                    total_nodes > 0 and enriched_nodes < total_nodes * 0.5
                )

                self.logger.debug(
                    f"Preparation check for {company}/{market}: "
                    f"{total_nodes} nodes, {enriched_nodes} enriched"
                )

        except Exception as e:
            self.logger.error(f"Error checking preparation needs: {e}")
            # Return defaults (needs preparation)

        return result

    def is_script_available(self, script_name: str) -> bool:
        """
        Check if a preparation script exists.

        Args:
            script_name: Script filename

        Returns:
            True if script exists
        """
        script_path = self.scripts_dir / script_name
        return script_path.exists()

    def get_available_scripts(self) -> list[str]:
        """
        Get list of available preparation scripts.

        Returns:
            List of script names
        """
        scripts = [
            'populate_database.py',
            'enrich_taxonomies.py',
            'generate_raw_trees.py',
        ]
        return [s for s in scripts if self.is_script_available(s)]


__all__ = ['DataPreparer']
