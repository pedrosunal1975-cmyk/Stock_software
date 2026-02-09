# Path: components/period_normalizer.py
"""
Period Normalizer

Normalizes and compares XBRL periods.

Handles:
- Instant vs duration periods
- Fiscal vs calendar periods
- Period overlap detection
- Period normalization
"""

import logging
from typing import Optional
from dataclasses import dataclass

from ..mapping.models.context import Context
from ..components.constants import (
    PERIOD_TYPE_INSTANT,
    PERIOD_TYPE_DURATION,
)


@dataclass
class NormalizedPeriod:
    """
    Normalized period representation.
    
    Attributes:
        period_type: instant or duration
        start_date: Start date (None for instant)
        end_date: End date (or instant date)
        fiscal_year: Fiscal year
        fiscal_period: Fiscal period (Q1, Q2, etc.)
    """
    period_type: str
    start_date: Optional[date]
    end_date: date
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None


class PeriodNormalizer:
    """
    Period normalization and comparison.
    
    Example:
        normalizer = PeriodNormalizer()
        
        # Normalize period
        period = normalizer.normalize(context)
        
        # Check if periods match
        match = normalizer.periods_match(context1, context2)
        
        # Check if instant is within duration
        within = normalizer.instant_in_duration(instant_ctx, duration_ctx)
    """
    
    def __init__(self):
        """Initialize period normalizer."""
        self.logger = logging.getLogger('components.period_normalizer')
    
    def normalize(self, context: Context) -> NormalizedPeriod:
        """
        Normalize context period.
        
        Args:
            context: XBRL context
            
        Returns:
            Normalized period
        """
        if context.is_instant():
            return NormalizedPeriod(
                period_type=PERIOD_TYPE_INSTANT,
                start_date=None,
                end_date=context.instant,
                fiscal_year=self._infer_fiscal_year(context.instant),
                fiscal_period=self._infer_fiscal_period(context.instant)
            )
        else:
            return NormalizedPeriod(
                period_type=PERIOD_TYPE_DURATION,
                start_date=context.start_date,
                end_date=context.end_date,
                fiscal_year=self._infer_fiscal_year(context.end_date),
                fiscal_period=self._infer_fiscal_period_duration(
                    context.start_date,
                    context.end_date
                )
            )
    
    def periods_match(
        self,
        context1: Context,
        context2: Context,
        tolerance_days: int = 0
    ) -> bool:
        """
        Check if periods match.
        
        Args:
            context1: First context
            context2: Second context
            tolerance_days: Allowed difference in days
            
        Returns:
            True if periods match within tolerance
        """
        # Must be same type
        if context1.period_type != context2.period_type:
            return False
        
        if context1.is_instant():
            # Compare instant dates
            diff = abs((context1.instant - context2.instant).days)
            return diff <= tolerance_days
        else:
            # Compare duration dates
            start_diff = abs((context1.start_date - context2.start_date).days)
            end_diff = abs((context1.end_date - context2.end_date).days)
            return start_diff <= tolerance_days and end_diff <= tolerance_days
    
    def instant_in_duration(
        self,
        instant_context: Context,
        duration_context: Context
    ) -> bool:
        """
        Check if instant is within duration period.
        
        Args:
            instant_context: Instant context
            duration_context: Duration context
            
        Returns:
            True if instant falls within duration
        """
        if not instant_context.is_instant() or not duration_context.is_duration():
            return False
        
        instant = instant_context.instant
        start = duration_context.start_date
        end = duration_context.end_date
        
        return start <= instant <= end
    
    def get_period_label(self, context: Context) -> str:
        """
        Get human-readable period label.
        
        Args:
            context: XBRL context
            
        Returns:
            Period label (e.g., "2023-Q4", "2023-12-31")
        """
        period = self.normalize(context)
        
        if period.period_type == PERIOD_TYPE_INSTANT:
            return period.end_date.strftime('%Y-%m-%d')
        else:
            if period.fiscal_period:
                return f"{period.fiscal_year}-{period.fiscal_period}"
            else:
                return f"{period.start_date.strftime('%Y-%m-%d')} to {period.end_date.strftime('%Y-%m-%d')}"
    
    def _infer_fiscal_year(self, end_date: date) -> Optional[int]:
        """
        Placeholder for fiscal year determination.
        
        CRITICAL: Fiscal year CANNOT be reliably inferred from dates because
        companies have different fiscal year-ends:
        - Walmart: fiscal year ending January 31, 2024 → Fiscal Year 2024
        - Microsoft: fiscal year ending June 30, 2024 → Fiscal Year 2024
        - BUT: A company with Jan 31, 2024 end might call it FY2023 or FY2024
        
        PROPER "READ AS-IS" APPROACH:
        Fiscal year information should be DISCOVERED from XBRL filing metadata.
        Common locations (but should be discovered, not assumed):
        - Document and Entity Information (DEI) concepts in instance
        - Fiscal year focus declarations
        - Company-specific fiscal year end date declarations
        
        The specific concept names vary by taxonomy and should be discovered
        by examining the filing's declared concepts, NOT hardcoded.
        
        Args:
            end_date: Period end date
            
        Returns:
            None - fiscal year should be discovered from filing metadata
        """
        # Do NOT infer fiscal year from date - this violates "read as-is" principle
        # Fiscal year should be discovered from filing metadata concepts
        return None
    
    def _infer_fiscal_period(self, end_date: date) -> Optional[str]:
        """
        Placeholder for fiscal period determination.
        
        CRITICAL: Fiscal periods CANNOT be reliably inferred from dates because
        companies have different fiscal year-ends:
        - Walmart: fiscal year ends January 31 (Jan = their Q4, not calendar Q1)
        - Microsoft: fiscal year ends June 30 (Jun = their Q4, not calendar Q2)
        - Apple: fiscal year ends September (Sep = their Q4, not calendar Q3)
        
        PROPER "READ AS-IS" APPROACH:
        Fiscal period information should be extracted from XBRL filing metadata:
        - dei:DocumentFiscalPeriodFocus (e.g., "Q1", "Q2", "FY")
        - dei:DocumentFiscalYearFocus
        - dei:CurrentFiscalYearEndDate
        
        These concepts are explicitly declared in the filing and should be
        used instead of making calendar-based assumptions.
        
        Args:
            end_date: Period end date
            
        Returns:
            None - fiscal period should come from filing metadata, not inferred
        """
        # Do NOT infer fiscal periods from dates - this violates "read as-is" principle
        # Fiscal period should be extracted from dei:DocumentFiscalPeriodFocus
        return None
    
    def _infer_fiscal_period_duration(
        self,
        start_date: date,
        end_date: date
    ) -> Optional[str]:
        """
        Placeholder for duration-based fiscal period determination.
        
        CRITICAL: This method previously attempted to classify periods as FY, Q1-Q4,
        or monthly based on duration length. However, this violates "read as-is":
        - A 90-day period could be Q1 for one company, Q4 for another
        - Duration alone doesn't determine fiscal period designation
        
        PROPER "READ AS-IS" APPROACH:
        Fiscal period should be extracted from XBRL filing DEI metadata:
        - dei:DocumentFiscalPeriodFocus
        - dei:DocumentType (e.g., "10-Q", "10-K")
        
        Args:
            start_date: Period start date
            end_date: Period end date
            
        Returns:
            None - fiscal period should come from filing metadata, not duration
        """
        # Do NOT infer fiscal periods from duration - this violates "read as-is"
        # Fiscal period should be extracted from dei:DocumentFiscalPeriodFocus
        return None


__all__ = ['PeriodNormalizer', 'NormalizedPeriod']