# Path: xbrl_parser/foundation/taxonomy_detector.py
"""
Taxonomy Detection and Market Extraction

Automatic identification of taxonomies and market context.

Features:
- Standard taxonomy detection 
- Primary taxonomy identification
- Market and region metadata extraction
- Confidence scoring
"""

import logging

from ..foundation.namespace_registry import NamespaceRegistry
from ..foundation.namespace_info import (
    TaxonomyType,
    TaxonomyDetectionResult,
    MarketMetadata
)
from ..foundation.url_addresses import (
    TAXONOMY_DETECTION_PATTERNS,
    MARKET_METADATA_MAP
)


class TaxonomyDetector:
    """
    Detect which taxonomies are in use.
    
    Analyzes namespace registry to identify standard taxonomies
    and determine the primary taxonomy.
    
    Example:
        registry = NamespaceRegistry()
        # ... register namespaces ...
        
        detector = TaxonomyDetector(registry)
        result = detector.detect()
        
        print(result.primary_taxonomy)  # TaxonomyType.US_GAAP
        print(result.confidence)  # 0.95
    """
    
    def __init__(self, registry: NamespaceRegistry):
        """
        Initialize detector.
        
        Args:
            registry: Namespace registry to analyze
        """
        self.registry = registry
        self.logger = logging.getLogger(__name__)
        
        # Build TAXONOMY_PATTERNS from imported data
        # Convert string keys to TaxonomyType enum keys
        self.TAXONOMY_PATTERNS = {
            TaxonomyType.US_GAAP: TAXONOMY_DETECTION_PATTERNS['US_GAAP'],
            TaxonomyType.IFRS: TAXONOMY_DETECTION_PATTERNS['IFRS'],
            TaxonomyType.UK_GAAP: TAXONOMY_DETECTION_PATTERNS['UK_GAAP'],
            TaxonomyType.ESEF: TAXONOMY_DETECTION_PATTERNS['ESEF'],
            TaxonomyType.DEI: TAXONOMY_DETECTION_PATTERNS['DEI']
        }
    
    def detect(self) -> TaxonomyDetectionResult:
        """
        Detect taxonomies from registered namespaces.
        
        Returns:
            Detection result with primary taxonomy and confidence
            
        Example:
            result = detector.detect()
            if result.confidence > 0.8:
                print(f"Primary: {result.primary_taxonomy.value}")
        """
        detected = set()
        namespaces_by_taxonomy = {}
        
        # Check each registered namespace
        for uri, info in self.registry.by_uri.items():
            if not info.is_standard:
                continue
            
            # Check against patterns
            for taxonomy_type, patterns in self.TAXONOMY_PATTERNS.items():
                if any(pattern in uri for pattern in patterns):
                    detected.add(taxonomy_type)
                    
                    if taxonomy_type not in namespaces_by_taxonomy:
                        namespaces_by_taxonomy[taxonomy_type] = []
                    namespaces_by_taxonomy[taxonomy_type].append(uri)
        
        # Determine primary taxonomy
        primary = self._determine_primary(detected, namespaces_by_taxonomy)
        
        # Calculate confidence
        confidence = self._calculate_confidence(detected, namespaces_by_taxonomy)
        
        self.logger.info(
            f"Taxonomy detection: primary={primary.value}, "
            f"detected={[t.value for t in detected]}, confidence={confidence:.2f}"
        )
        
        return TaxonomyDetectionResult(
            primary_taxonomy=primary,
            detected_taxonomies=detected,
            namespaces_by_taxonomy=namespaces_by_taxonomy,
            confidence=confidence
        )
    
    def _determine_primary(
        self,
        detected: set[TaxonomyType],
        namespaces_by_taxonomy: dict
    ) -> TaxonomyType:
        """
        Determine primary taxonomy from detected set.
        
        Uses priority order with more specific taxonomies first.
        """
        # Priority order (most specific first)
        priority = [
            TaxonomyType.ESEF,     # EU filings
            TaxonomyType.UK_GAAP,  # UK filings
            TaxonomyType.US_GAAP,  # US filings
            TaxonomyType.IFRS,     # International
        ]
        
        for taxonomy in priority:
            if taxonomy in detected:
                # Check if this is truly primary (has multiple namespaces)
                if len(namespaces_by_taxonomy.get(taxonomy, [])) > 0:
                    return taxonomy
        
        # No standard taxonomy found
        return TaxonomyType.CUSTOM
    
    def _calculate_confidence(
        self,
        detected: set[TaxonomyType],
        namespaces_by_taxonomy: dict
    ) -> float:
        """
        Calculate confidence in detection.
        
        More standard namespaces = higher confidence.
        """
        if not detected:
            return 0.0
        
        # Count total standard namespaces
        total_standard_namespaces = sum(
            len(ns) for ns in namespaces_by_taxonomy.values()
        )
        
        if total_standard_namespaces >= 5:
            return 1.0
        elif total_standard_namespaces >= 3:
            return 0.8
        elif total_standard_namespaces >= 1:
            return 0.6
        else:
            return 0.0


class MarketExtractor:
    """
    Extract market metadata from namespace registry.
    
    Determines market context, regulatory authority,
    and reporting framework from detected taxonomies.
    
    Example:
        registry = NamespaceRegistry()
        detector = TaxonomyDetector(registry)
        extractor = MarketExtractor(registry, detector)
        
        metadata = extractor.extract()
        print(metadata.primary_market)  
        print(metadata.regulatory_authority)  
    """
    
    def __init__(self, registry: NamespaceRegistry, detector: TaxonomyDetector):
        """
        Initialize extractor.
        
        Args:
            registry: Namespace registry
            detector: Taxonomy detector
        """
        self.registry = registry
        self.detector = detector
        self.logger = logging.getLogger(__name__)
        
        # Build MARKET_MAP from imported data
        # Convert string keys to TaxonomyType enum keys
        self.MARKET_MAP = {
            TaxonomyType.US_GAAP: MARKET_METADATA_MAP['US_GAAP'],
            TaxonomyType.UK_GAAP: MARKET_METADATA_MAP['UK_GAAP'],
            TaxonomyType.ESEF: MARKET_METADATA_MAP['ESEF'],
            TaxonomyType.IFRS: MARKET_METADATA_MAP['IFRS'],
        }
    
    def extract(self) -> MarketMetadata:
        """
        Extract market metadata.
        
        Returns:
            Market metadata with primary market and authority
            
        Example:
            metadata = extractor.extract()
            if metadata.confidence > 0.8:
                print(f"Market: {metadata.primary_market}")
        """
        # Detect taxonomies first
        taxonomy_result = self.detector.detect()
        
        # Map primary taxonomy to market
        primary_market, authority, framework = self.MARKET_MAP.get(
            taxonomy_result.primary_taxonomy,
            ("UNKNOWN", "UNKNOWN", "CUSTOM")
        )
        
        # Collect all detected markets
        detected_markets = set()
        for taxonomy in taxonomy_result.detected_taxonomies:
            if taxonomy in self.MARKET_MAP:
                market, _, _ = self.MARKET_MAP[taxonomy]
                detected_markets.add(market)
        
        self.logger.info(
            f"Market extraction: primary={primary_market}, "
            f"authority={authority}, framework={framework}"
        )
        
        return MarketMetadata(
            primary_market=primary_market,
            regulatory_authority=authority,
            reporting_framework=framework,
            detected_markets=detected_markets,
            confidence=taxonomy_result.confidence
        )


__all__ = ['TaxonomyDetector', 'MarketExtractor']
