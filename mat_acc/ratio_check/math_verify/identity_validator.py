# Path: mat_acc/ratio_check/math_verify/identity_validator.py
"""
Identity Validator - Layer 3 of Mathematical Integrity Unit

Validates mathematical identities that must hold regardless of
company, taxonomy, or accounting standard. These are AXIOMS:
- Balance sheet: Assets = Liabilities + Equity
- Gross profit: Revenue - COGS = Gross Profit
- Subset: Current Assets <= Total Assets
- Subset: Current Liabilities <= Total Liabilities
- Sign: Total Assets > 0
- Sign: sign(Equity) = sign(Assets - Liabilities)
"""

from dataclasses import dataclass
from typing import Optional

from core.logger.ipo_logging import get_process_logger


logger = get_process_logger('math_verify.validator')

_DEFAULT_TOLERANCE = 0.005


@dataclass
class IdentityCheck:
    """Result of a mathematical identity validation."""
    identity: str
    lhs_label: str = ''
    lhs_value: Optional[float] = None
    rhs_label: str = ''
    rhs_value: Optional[float] = None
    difference: float = 0.0
    relative_diff: float = 0.0
    passed: bool = False
    severity: str = 'ok'
    skipped: bool = False
    skip_reason: str = ''


class IdentityValidator:
    """
    Validates mathematical identities on financial values.

    Checks run AFTER values are loaded but BEFORE ratios
    are calculated. If an identity fails, something upstream
    is mathematically wrong.
    """

    def __init__(self, tolerance: float = _DEFAULT_TOLERANCE):
        """Initialize with relative tolerance for equality checks."""
        self.tolerance = tolerance
        self.logger = get_process_logger('math_verify.validator')

    def validate(
        self, values: dict[str, Optional[float]]
    ) -> list[IdentityCheck]:
        """Run all applicable identity checks on component values."""
        checks = [
            self._check_balance_sheet(values),
            self._check_gross_profit(values),
            self._check_subset(values, 'current_assets', 'total_assets'),
            self._check_subset(values, 'current_liabilities', 'total_liabilities'),
            self._check_assets_positive(values),
            self._check_equity_sign(values),
        ]
        self._log_results(checks)
        return checks

    def _check_balance_sheet(self, values: dict) -> IdentityCheck:
        """Check: Assets = Liabilities + Equity."""
        a = values.get('total_assets')
        l = values.get('total_liabilities')
        e = values.get('total_equity')

        check = IdentityCheck(
            identity='Assets = Liabilities + Equity',
            lhs_label='Total Assets',
            rhs_label='Total Liabilities + Total Equity',
        )
        if a is None or l is None or e is None:
            check.skipped = True
            check.skip_reason = self._missing(values, 'total_assets', 'total_liabilities', 'total_equity')
            return check

        check.lhs_value = a
        check.rhs_value = l + e
        return self._evaluate_equality(check)

    def _check_gross_profit(self, values: dict) -> IdentityCheck:
        """Check: Revenue - COGS = Gross Profit."""
        r = values.get('revenue')
        c = values.get('cost_of_goods_sold')
        gp = values.get('gross_profit')

        check = IdentityCheck(
            identity='Revenue - COGS = Gross Profit',
            lhs_label='Revenue - COGS',
            rhs_label='Gross Profit',
        )
        if r is None or c is None or gp is None:
            check.skipped = True
            check.skip_reason = self._missing(values, 'revenue', 'cost_of_goods_sold', 'gross_profit')
            return check

        check.lhs_value = r - c
        check.rhs_value = gp
        return self._evaluate_equality(check)

    def _check_subset(self, values: dict, part_key: str, whole_key: str) -> IdentityCheck:
        """Check: |part| <= |whole| (subset relationship)."""
        part = values.get(part_key)
        whole = values.get(whole_key)

        label = part_key.replace('_', ' ').title()
        whole_label = whole_key.replace('_', ' ').title()
        check = IdentityCheck(
            identity=f'{label} <= {whole_label}',
            lhs_label=label,
            rhs_label=whole_label,
        )
        if part is None or whole is None:
            check.skipped = True
            check.skip_reason = self._missing(values, part_key, whole_key)
            return check

        check.lhs_value = abs(part)
        check.rhs_value = abs(whole)
        return self._evaluate_inequality(check)

    def _check_assets_positive(self, values: dict) -> IdentityCheck:
        """Check: Total Assets > 0."""
        assets = values.get('total_assets')
        check = IdentityCheck(
            identity='Total Assets > 0',
            lhs_label='Total Assets', rhs_label='0',
        )
        if assets is None:
            check.skipped = True
            check.skip_reason = 'total_assets not available'
            return check

        check.lhs_value = assets
        check.rhs_value = 0.0
        check.passed = assets > 0
        check.severity = 'ok' if check.passed else 'error'
        check.difference = assets
        return check

    def _check_equity_sign(self, values: dict) -> IdentityCheck:
        """Check: sign(Equity) = sign(Assets - Liabilities)."""
        a = values.get('total_assets')
        l = values.get('total_liabilities')
        e = values.get('total_equity')

        check = IdentityCheck(
            identity='sign(Equity) = sign(Assets - Liabilities)',
            lhs_label='Equity sign', rhs_label='Assets - Liabilities sign',
        )
        if a is None or l is None or e is None:
            check.skipped = True
            check.skip_reason = self._missing(values, 'total_assets', 'total_liabilities', 'total_equity')
            return check

        implied = a - l
        check.lhs_value = e
        check.rhs_value = implied
        check.difference = abs(e - implied)

        if abs(implied) < 1.0 or abs(e) < 1.0:
            check.passed = True
        else:
            check.passed = (e > 0) == (implied > 0)
        check.severity = 'ok' if check.passed else 'error'
        return check

    def _evaluate_equality(self, check: IdentityCheck) -> IdentityCheck:
        """Evaluate LHS ~= RHS within tolerance."""
        lhs, rhs = check.lhs_value, check.rhs_value
        check.difference = abs(lhs - rhs)
        denom = max(abs(lhs), abs(rhs))
        if denom == 0:
            check.relative_diff = 0.0
            check.passed = True
            check.severity = 'ok'
            return check

        check.relative_diff = check.difference / denom
        if check.relative_diff <= self.tolerance:
            check.passed, check.severity = True, 'ok'
        elif check.relative_diff <= self.tolerance * 5:
            check.passed, check.severity = False, 'warning'
        else:
            check.passed, check.severity = False, 'error'
        return check

    def _evaluate_inequality(self, check: IdentityCheck) -> IdentityCheck:
        """Evaluate LHS <= RHS inequality."""
        lhs, rhs = check.lhs_value, check.rhs_value
        check.difference = lhs - rhs
        if rhs == 0:
            check.passed = lhs == 0
        else:
            check.relative_diff = max(0, (lhs - rhs)) / abs(rhs)
            check.passed = check.relative_diff <= self.tolerance
        check.severity = 'ok' if check.passed else 'warning'
        return check

    def _missing(self, values: dict, *keys: str) -> str:
        """Build skip reason from missing component keys."""
        missing = [k for k in keys if values.get(k) is None]
        return f"Missing: {', '.join(missing)}"

    def _log_results(self, checks: list[IdentityCheck]) -> None:
        """Log validation results."""
        passed = sum(1 for c in checks if c.passed and not c.skipped)
        failed = sum(1 for c in checks if not c.passed and not c.skipped)
        skipped = sum(1 for c in checks if c.skipped)
        self.logger.info(
            f"Identity validation: {passed} passed, "
            f"{failed} failed, {skipped} skipped"
        )
        for check in checks:
            if not check.skipped and not check.passed:
                self.logger.warning(
                    f"IDENTITY FAILED: {check.identity} "
                    f"(LHS={check.lhs_value:,.0f}, "
                    f"RHS={check.rhs_value:,.0f}, "
                    f"diff={check.difference:,.0f})"
                )


__all__ = ['IdentityValidator', 'IdentityCheck']
