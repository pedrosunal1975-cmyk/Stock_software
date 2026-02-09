# Path: mapping/statement/fact_enricher.py
"""
Fact Enricher

Enriches XBRL facts with calculated values for verification and display.

DESIGN PRINCIPLES:
- Preserve raw XBRL data (never modify original values)
- Calculate scaled values for verification engine
- Generate human-readable formatted values
- Maintain audit trail (raw + decimals = verifiable)

RESPONSIBILITY:
- Calculate display_value: value × 10^(-decimals) per XBRL 2.1 Spec Section 4.6.5
- Calculate scaling_factor: 10^(-decimals)
- Format values with currency symbols and separators
- Handle edge cases (missing decimals, non-numeric values, INF precision)

XBRL SPECIFICATION FORMULAS:
- Formula source: xbrl_mathematics.decimals module
- Specification: XBRL 2.1 Section 4.6.5 "The @decimals attribute"
- Authority: XBRL International / IFRS Foundation
- Scope: Universal (applies to all XBRL 2.1 filings globally)

Example:
    enricher = FactEnricher()
    
    fact.value = "26755.7"
    fact.decimals = "-5"
    
    enriched = enricher.enrich_fact(fact)
    # enriched.display_value = "2675570000"
    # enriched.formatted_value = "$2,675,570,000"
    # enriched.scaling_factor = 100000
    
    # Verification:
    # 26755.7 × 10^5 = 2,675,570,000 ✓
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

from ...mapping.statement.models import StatementFact

# Import XBRL specification formulas
from ...xbrl_mathematics.decimals import (
    scale_value_with_decimals,
    parse_decimals_attribute,
)


class FactEnricher:
    """
    Enriches facts with calculated values for verification.
    
    Adds three new fields to each fact:
    1. display_value: Scaled numeric value (value × 10^(-decimals))
    2. formatted_value: Human-readable with currency/separators
    3. scaling_factor: 10^(-decimals) for reference
    
    The verification engine uses display_value for calculations:
    - Balance Sheet: Assets = Liabilities + Equity
    - Income Statement: Net Income = Revenue - Expenses
    - Cash Flow: Ending Cash = Beginning Cash + Net Change
    
    Example:
        enricher = FactEnricher()
        
        # Raw XBRL fact
        fact.value = "26755.7"
        fact.decimals = "-5"
        fact.unit_ref = "usd"
        
        # Enrich
        enriched = enricher.enrich_fact(fact)
        
        # Results
        enriched.display_value = "2675570000"      # For verification
        enriched.formatted_value = "$2,675,570,000" # For humans
        enriched.scaling_factor = 100000           # For reference
    """
    
    def __init__(self):
        """Initialize fact enricher."""
        self.logger = logging.getLogger('mapping.fact_enricher')
    
    def enrich_fact(self, fact: StatementFact) -> StatementFact:
        """
        Calculate and add display values to fact.
        
        Performs three calculations:
        1. display_value = value × 10^(-decimals)
        2. scaling_factor = 10^(-decimals)
        3. formatted_value = human-readable format
        
        Args:
            fact: Statement fact to enrich
            
        Returns:
            Enriched fact with calculated fields
        """
        # If no value, skip enrichment
        if not fact.value:
            fact.display_value = None
            fact.formatted_value = None
            fact.scaling_factor = None
            return fact
        
        # Calculate display value and scaling factor
        if fact.decimals is not None:
            fact.display_value = self._calculate_display_value(
                fact.value, fact.decimals
            )
            fact.scaling_factor = self._calculate_scaling_factor(fact.decimals)
        else:
            # No decimals means value is already scaled
            fact.display_value = fact.value
            fact.scaling_factor = 1
        
        # Format for human display
        fact.formatted_value = self._format_value(
            fact.display_value, fact.unit_ref
        )
        
        return fact
    
    def _calculate_display_value(self, value: str, decimals: str) -> Optional[str]:
        """
        Calculate scaled value using XBRL 2.1 Specification formula.
        
        SOURCE:
        -------
        Formula implementation: xbrl_mathematics.decimals.scale_value_with_decimals()
        Specification: XBRL 2.1 Section 4.6.5 "The @decimals attribute"
        Formula: accurate_value = reported_value × 10^(-decimals)
        
        EXAMPLES:
        ---------
        value="26755.7", decimals="-5" → "2675570000"
        value="100", decimals="-3" → "100000"
        value="1.5", decimals="2" → "0.015"
        value="100", decimals="INF" → "100" (exact value)
        
        Args:
            value: Raw XBRL value (string)
            decimals: XBRL decimals attribute (string, may be "INF")
            
        Returns:
            Scaled value as string, or original value if calculation fails
        """
        try:
            # Parse raw value
            raw_value = Decimal(str(value).replace(',', ''))
            
            # Parse decimals attribute (handles "INF" and integer values)
            decimals_int = parse_decimals_attribute(decimals)
            
            # Special case: INF means exact value (no scaling needed)
            if decimals_int is None:
                return str(raw_value)
            
            # Apply XBRL 2.1 Spec Section 4.6.5 formula
            # Implementation: xbrl_mathematics.decimals.scale_value_with_decimals()
            scaled_value = scale_value_with_decimals(raw_value, decimals_int)
            
            # Return as string (preserve precision)
            return str(scaled_value)
            
        except (InvalidOperation, ValueError, TypeError) as e:
            self.logger.debug(
                f"Cannot calculate display value for {value} with decimals {decimals}: {e}"
            )
            return value  # Return raw value if calculation fails
    
    def _calculate_scaling_factor(self, decimals: str) -> Optional[float]:
        """
        Calculate scaling factor: 10^(-decimals).
        
        SOURCE:
        -------
        Based on XBRL 2.1 Specification Section 4.6.5
        Uses xbrl_mathematics.decimals.parse_decimals_attribute()
        
        EXAMPLES:
        ---------
        decimals="-5" → 100000
        decimals="-3" → 1000
        decimals="2" → 0.01
        decimals="INF" → 1 (no scaling)
        
        Args:
            decimals: XBRL decimals attribute (string, may be "INF")
            
        Returns:
            Scaling factor as float, or None if calculation fails
        """
        try:
            # Parse decimals attribute (handles "INF" and integer values)
            decimals_int = parse_decimals_attribute(decimals)
            
            # Special case: INF means no scaling (factor = 1)
            if decimals_int is None:
                return 1.0
            
            # Calculate: 10^(-decimals)
            return 10 ** (-decimals_int)
            
        except (ValueError, TypeError):
            return None
    
    def _format_value(
        self,
        value: Optional[str],
        unit_ref: Optional[str]
    ) -> Optional[str]:
        """
        Format value for human display with currency symbols and separators.
        
        Examples:
            value="2675570000", unit_ref="usd" → "$2,675,570,000"
            value="-1000000", unit_ref="usd" → "($1,000,000)"
            value="1500", unit_ref="shares" → "1,500"
        
        Args:
            value: Display value (scaled)
            unit_ref: Unit reference (usd, shares, etc.)
            
        Returns:
            Formatted string for human display
        """
        if value is None:
            return None
        
        try:
            # Parse to float for formatting
            num_value = float(value)
            
            # Determine if this is a currency unit
            is_currency = unit_ref and any(
                curr in unit_ref.lower()
                for curr in ['usd', 'eur', 'gbp', 'jpy', 'cny', 'currency']
            )
            
            # Format negative values with parentheses (accounting style)
            if num_value < 0:
                abs_value = abs(num_value)
                if is_currency:
                    return f"(${abs_value:,.0f})"
                else:
                    return f"({abs_value:,.0f})"
            else:
                # Format positive values
                if is_currency:
                    return f"${num_value:,.0f}"
                else:
                    return f"{num_value:,.0f}"
                    
        except (ValueError, TypeError) as e:
            self.logger.debug(f"Cannot format value {value}: {e}")
            return str(value)  # Return as-is if formatting fails
    
    def verify_calculation(
        self,
        value: str,
        decimals: str,
        display_value: str
    ) -> bool:
        """
        Verify that display_value = value × 10^(-decimals).
        
        Used for quality assurance and testing to verify the XBRL specification
        formula is applied correctly.
        
        SOURCE:
        -------
        Formula: XBRL 2.1 Specification Section 4.6.5
        Implementation: xbrl_mathematics.decimals.scale_value_with_decimals()
        
        Args:
            value: Raw XBRL value
            decimals: XBRL decimals attribute
            display_value: Calculated display value
            
        Returns:
            True if calculation is correct per XBRL specification
        """
        try:
            raw = Decimal(str(value).replace(',', ''))
            calc_display = Decimal(display_value)
            
            # Parse decimals (handles "INF")
            decimals_int = parse_decimals_attribute(decimals)
            
            # For INF, values should match exactly
            if decimals_int is None:
                return raw == calc_display
            
            # Apply XBRL 2.1 Spec formula
            expected = scale_value_with_decimals(raw, decimals_int)
            
            # Allow tiny rounding differences
            return abs(expected - calc_display) < Decimal('0.01')
            
        except (InvalidOperation, ValueError, TypeError):
            return False