# Path: xbrl_parser/market/detector.py
"""
Market Detector

Auto-detect which market/region a filing belongs to based on taxonomy,
elements, and other signals.

This module provides:
- Automatic market detection from filing
- Confidence scoring
- Multi-signal analysis

Example:
    from ..market import MarketDetector
    
    detector = MarketDetector()
    market_id, confidence = detector.detect(parsed_filing)
    
    if confidence > 0.8:
        print(f"Detected market: {market_id}")
"""

import logging
import re

from ..models.parsed_filing import ParsedFiling
from ..market.constants import (
    MARKET_US_SEC,
    MARKET_EU_ESEF,
    MARKET_UK_FRC,
    MARKET_UNKNOWN,
    US_SEC,
    EU_ESEF,
    UK_FRC,
    DETECTION_PRIORITY,
    MIN_DETECTION_CONFIDENCE,
    NAMESPACE_MATCH_WEIGHT,
    REQUIRED_ELEMENT_WEIGHT,
    TAXONOMY_URL_WEIGHT,
    IDENTIFIER_FORMAT_WEIGHT
)


class MarketDetector:
    """
    Detect market/region from XBRL filing.
    
    Uses multiple signals:
    - Taxonomy namespaces
    - Required elements
    - Identifier formats (CIK, LEI, CH number)
    - Taxonomy URLs
    
    Example:
        detector = MarketDetector()
        
        market_id, confidence = detector.detect(filing)
        
        if market_id != MARKET_UNKNOWN:
            print(f"Market: {market_id} (confidence: {confidence:.2%})")
    """
    
    def __init__(self):
        """Initialize market detector."""
        self.logger = logging.getLogger(__name__)
        
        # Market configurations
        self.market_configs = {
            MARKET_US_SEC: US_SEC,
            MARKET_EU_ESEF: EU_ESEF,
            MARKET_UK_FRC: UK_FRC
        }
        
        self.logger.debug("MarketDetector initialized")
    
    def detect(self, filing: ParsedFiling) -> tuple[str, float]:
        """
        Detect market from filing.
        
        Args:
            filing: Parsed filing to analyze
            
        Returns:
            tuple of (market_id, confidence_score)
            confidence_score is 0.0-1.0
            
        Example:
            market_id, confidence = detector.detect(filing)
        """
        self.logger.info("Detecting market for filing")
        
        # Calculate scores for each market
        scores: dict[str, float] = {}
        
        for market_id in DETECTION_PRIORITY:
            score = self._calculate_market_score(filing, market_id)
            scores[market_id] = score
            
            self.logger.debug(f"{market_id} score: {score:.3f}")
        
        # Find highest scoring market
        best_market = max(scores.items(), key=lambda x: x[1])
        market_id, confidence = best_market
        
        # Check if confidence meets threshold
        if confidence < MIN_DETECTION_CONFIDENCE:
            self.logger.warning(
                f"Low confidence detection: {market_id} ({confidence:.2%})"
            )
            return MARKET_UNKNOWN, confidence
        
        self.logger.info(f"Detected market: {market_id} (confidence: {confidence:.2%})")
        return market_id, confidence
    
    def detect_all_scores(self, filing: ParsedFiling) -> dict[str, float]:
        """
        Get detection scores for all markets.
        
        Args:
            filing: Parsed filing to analyze
            
        Returns:
            dict mapping market_id to confidence score
        """
        scores = {}
        
        for market_id in DETECTION_PRIORITY:
            scores[market_id] = self._calculate_market_score(filing, market_id)
        
        return scores
    
    def _calculate_market_score(
        self,
        filing: ParsedFiling,
        market_id: str
    ) -> float:
        """
        Calculate detection score for specific market.
        
        Args:
            filing: Parsed filing
            market_id: Market to check
            
        Returns:
            Score between 0.0 and 1.0
        """
        config = self.market_configs[market_id]
        
        # Calculate component scores
        namespace_score = self._check_namespaces(filing, config)
        element_score = self._check_required_elements(filing, config)
        taxonomy_score = self._check_taxonomy_urls(filing, config)
        identifier_score = self._check_identifier_format(filing, config)
        
        # Weighted average
        total_score = (
            namespace_score * NAMESPACE_MATCH_WEIGHT +
            element_score * REQUIRED_ELEMENT_WEIGHT +
            taxonomy_score * TAXONOMY_URL_WEIGHT +
            identifier_score * IDENTIFIER_FORMAT_WEIGHT
        )
        
        return total_score
    
    def _check_namespaces(
        self,
        filing: ParsedFiling,
        config: type
    ) -> float:
        """Check namespace matches."""
        if not filing.taxonomy or not hasattr(filing.taxonomy, 'namespaces'):
            return 0.0
        
        # Get namespaces from taxonomy
        filing_namespaces = getattr(filing.taxonomy, 'namespaces', {})
        
        # Check for market-specific namespaces
        matches = 0
        for ns in config.NAMESPACES:
            for filing_ns in filing_namespaces.values():
                if ns in filing_ns:
                    matches += 1
                    break
        
        if len(config.NAMESPACES) == 0:
            return 0.0
        
        return matches / len(config.NAMESPACES)
    
    def _check_required_elements(
        self,
        filing: ParsedFiling,
        config: type
    ) -> float:
        """Check for required elements."""
        if not filing.instance or not filing.instance.facts:
            return 0.0
        
        # Get all concepts from facts
        concepts = {fact.concept for fact in filing.instance.facts}
        
        # Check for required elements
        matches = 0
        for required in config.REQUIRED_ELEMENTS:
            for concept in concepts:
                if required in concept:
                    matches += 1
                    break
        
        if len(config.REQUIRED_ELEMENTS) == 0:
            return 0.0
        
        return matches / len(config.REQUIRED_ELEMENTS)
    
    def _check_taxonomy_urls(
        self,
        filing: ParsedFiling,
        config: type
    ) -> float:
        """Check taxonomy URLs."""
        if not filing.metadata or not hasattr(filing.metadata, 'source_files'):
            return 0.0
        
        source_files = filing.metadata.source_files
        
        # Check if any source file URLs match market namespaces
        matches = 0
        for source in source_files:
            source_str = str(source)
            for ns in config.NAMESPACES:
                if ns in source_str:
                    matches += 1
                    break
        
        if len(source_files) == 0:
            return 0.0
        
        return min(matches / len(source_files), 1.0)
    
    def _check_identifier_format(
        self,
        filing: ParsedFiling,
        config: type
    ) -> float:
        """Check identifier format (CIK, LEI, CH number)."""
        if not filing.metadata:
            return 0.0
        
        entity_id = filing.metadata.entity_identifier
        
        if not entity_id:
            return 0.0
        
        # Check format based on market
        if config.MARKET_ID == MARKET_US_SEC:
            # Check CIK format
            if hasattr(config, 'CIK_PATTERN'):
                if re.match(config.CIK_PATTERN, entity_id):
                    return 1.0
        
        elif config.MARKET_ID == MARKET_EU_ESEF:
            # Check LEI format
            if hasattr(config, 'LEI_PATTERN'):
                if re.match(config.LEI_PATTERN, entity_id):
                    return 1.0
        
        elif config.MARKET_ID == MARKET_UK_FRC:
            # Check Companies House number format
            if hasattr(config, 'CH_NUMBER_PATTERN'):
                if re.match(config.CH_NUMBER_PATTERN, entity_id):
                    return 1.0
        
        return 0.0


__all__ = ['MarketDetector']
