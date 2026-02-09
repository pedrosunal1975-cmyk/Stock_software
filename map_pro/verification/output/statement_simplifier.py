# Path: verification/output/statement_simplifier.py
"""
Statement Simplifier for Verification Module

Creates simplified versions of financial statements.
Extracts key financial metrics for quick analysis.

This is independent from the main verification output -
provides analysis-ready simplified data.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader
from ..loaders.mapped_reader import MappedStatements, Statement, StatementFact
from ..loaders.mapped_data import MappedFilingEntry
from ..constants import LOG_OUTPUT

# Local patterns for key metric extraction (output layer only, not verification)
# These are used for display/export purposes, not for verification logic
TOTAL_ASSETS_PATTERNS = ['Assets', 'TotalAssets']
TOTAL_LIABILITIES_PATTERNS = ['Liabilities', 'TotalLiabilities']
TOTAL_EQUITY_PATTERNS = ['Equity', 'StockholdersEquity', 'ShareholdersEquity']
NET_INCOME_PATTERNS = ['NetIncome', 'ProfitLoss', 'NetIncomeLoss']
REVENUE_PATTERNS = ['Revenue', 'Revenues', 'SalesRevenue', 'NetSales']
CASH_ENDING_PATTERNS = ['CashAndCashEquivalents', 'Cash']


@dataclass
class SimplifiedStatement:
    """
    Simplified version of a financial statement.

    Contains only key line items and totals.
    """
    statement_type: str
    period_end: str
    items: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass
class KeyMetrics:
    """
    Key financial metrics extracted from statements.

    Attributes:
        total_assets: Total assets value
        total_liabilities: Total liabilities value
        total_equity: Total equity value
        revenue: Revenue/sales value
        net_income: Net income value
        cash: Cash and equivalents
        period_end: Reporting period end date
    """
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    cash: Optional[float] = None
    period_end: Optional[str] = None


class StatementSimplifier:
    """
    Creates simplified statement versions.

    Extracts key financial metrics and creates analysis-ready formats.

    Example:
        simplifier = StatementSimplifier()
        metrics = simplifier.extract_key_metrics(statements)
        simplifier.export_simplified(filing, statements)
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize statement simplifier.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.output_dir = self.config.get('simplified_dir')
        self.logger = logging.getLogger('output.statement_simplifier')

    def extract_key_metrics(self, statements: MappedStatements) -> KeyMetrics:
        """
        Extract key financial metrics from statements.

        Args:
            statements: MappedStatements from mapped_reader

        Returns:
            KeyMetrics with extracted values
        """
        self.logger.info(f"{LOG_OUTPUT} Extracting key metrics")

        metrics = KeyMetrics()

        # Find balance sheet
        balance_sheet = self._find_statement_by_type(statements, 'balance')
        if balance_sheet:
            metrics.total_assets = self._find_value(balance_sheet, TOTAL_ASSETS_PATTERNS)
            metrics.total_liabilities = self._find_value(balance_sheet, TOTAL_LIABILITIES_PATTERNS)
            metrics.total_equity = self._find_value(balance_sheet, TOTAL_EQUITY_PATTERNS)
            metrics.cash = self._find_value(balance_sheet, CASH_ENDING_PATTERNS)

            # Get period from first fact with period_end
            for fact in balance_sheet.facts:
                if fact.period_end:
                    metrics.period_end = fact.period_end
                    break

        # Find income statement
        income_stmt = self._find_statement_by_type(statements, 'income')
        if income_stmt:
            metrics.revenue = self._find_value(income_stmt, REVENUE_PATTERNS)
            metrics.net_income = self._find_value(income_stmt, NET_INCOME_PATTERNS)

        self.logger.info(f"{LOG_OUTPUT} Key metrics extracted")

        return metrics

    def simplify_statement(self, statement: Statement) -> SimplifiedStatement:
        """
        Create simplified version of a single statement.

        Keeps only items marked as totals or key line items.

        Args:
            statement: Statement from mapped_reader

        Returns:
            SimplifiedStatement with key items
        """
        simplified = SimplifiedStatement(
            statement_type=self._detect_statement_type(statement),
            period_end='',
            items={},
            metadata={
                'original_name': statement.name,
                'original_role': statement.role,
            }
        )

        # Extract totals and key items
        for fact in statement.facts:
            if fact.is_abstract:
                continue

            # Include totals
            if fact.is_total:
                simplified.items[fact.concept] = {
                    'value': fact.value,
                    'label': fact.label or fact.concept,
                    'is_total': True,
                }

            # Set period from first fact with period_end
            if fact.period_end and not simplified.period_end:
                simplified.period_end = fact.period_end

        return simplified

    def export_simplified(
        self,
        filing: MappedFilingEntry,
        statements: MappedStatements,
        output_path: Optional[Path] = None
    ) -> dict[str, Path]:
        """
        Export simplified statements and key metrics.

        Args:
            filing: MappedFilingEntry for filing info
            statements: MappedStatements to simplify
            output_path: Optional base output path

        Returns:
            Dictionary mapping output type to file path
        """
        self.logger.info(f"{LOG_OUTPUT} Exporting simplified statements for {filing.company}")

        if output_path is None:
            output_path = self._get_default_output_path(filing)

        output_path.mkdir(parents=True, exist_ok=True)
        paths = {}

        # Export key metrics
        metrics = self.extract_key_metrics(statements)
        metrics_path = output_path / 'key_metrics.json'
        self._write_json(self._metrics_to_dict(metrics), metrics_path)
        paths['key_metrics'] = metrics_path

        # Export simplified statements
        for statement in statements.statements:
            simplified = self.simplify_statement(statement)
            stmt_type = simplified.statement_type

            if stmt_type:
                filename = f'{stmt_type}.json'
                stmt_path = output_path / filename
                self._write_json(self._simplified_to_dict(simplified), stmt_path)
                paths[stmt_type] = stmt_path

        self.logger.info(f"{LOG_OUTPUT} Exported {len(paths)} simplified files")

        return paths

    def _get_default_output_path(self, filing: MappedFilingEntry) -> Path:
        """Get default output path for simplified statements."""
        if not self.output_dir:
            raise ValueError("Simplified output directory not configured")

        return (
            self.output_dir /
            filing.market /
            filing.company /
            filing.form /
            filing.date
        )

    def _find_statement_by_type(
        self,
        statements: MappedStatements,
        statement_type: str
    ) -> Optional[Statement]:
        """Find statement by type keyword."""
        type_lower = statement_type.lower()

        for statement in statements.statements:
            name_lower = statement.name.lower()
            role_lower = (statement.role or '').lower()

            if type_lower in name_lower or type_lower in role_lower:
                return statement

        return None

    def _find_value(
        self,
        statement: Statement,
        patterns: list[str]
    ) -> Optional[float]:
        """Find value matching patterns."""
        for fact in statement.facts:
            if fact.is_abstract or fact.value is None:
                continue

            concept_lower = fact.concept.lower()

            for pattern in patterns:
                if pattern.lower() in concept_lower:
                    try:
                        return float(fact.value)
                    except (ValueError, TypeError):
                        continue

        return None

    def _detect_statement_type(self, statement: Statement) -> str:
        """Detect statement type from name/role."""
        name_lower = statement.name.lower()
        role_lower = (statement.role or '').lower()

        combined = name_lower + ' ' + role_lower

        if 'balance' in combined or 'position' in combined:
            return 'balance_sheet'
        elif 'income' in combined or 'operations' in combined or 'profit' in combined:
            return 'income_statement'
        elif 'cash' in combined:
            return 'cash_flow'
        elif 'equity' in combined or 'stockholder' in combined:
            return 'equity'
        elif 'comprehensive' in combined:
            return 'comprehensive_income'

        return 'other'

    def _metrics_to_dict(self, metrics: KeyMetrics) -> dict:
        """Convert metrics to dictionary."""
        return {
            'total_assets': metrics.total_assets,
            'total_liabilities': metrics.total_liabilities,
            'total_equity': metrics.total_equity,
            'revenue': metrics.revenue,
            'net_income': metrics.net_income,
            'cash': metrics.cash,
            'period_end': metrics.period_end,
        }

    def _simplified_to_dict(self, simplified: SimplifiedStatement) -> dict:
        """Convert simplified statement to dictionary."""
        return {
            'statement_type': simplified.statement_type,
            'period_end': simplified.period_end,
            'items': simplified.items,
            'metadata': simplified.metadata,
        }

    def _write_json(self, data: dict, path: Path) -> None:
        """Write data to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)


__all__ = ['StatementSimplifier', 'SimplifiedStatement', 'KeyMetrics']
