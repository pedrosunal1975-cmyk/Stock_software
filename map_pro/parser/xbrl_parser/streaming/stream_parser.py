# Path: xbrl_parser/streaming/stream_parser.py
"""
Streaming XBRL Parser

SAX-style event-driven parser for processing large XBRL filings with
minimal memory footprint.

This module provides streaming parsing capabilities for files that would
exceed memory limits if loaded entirely into a DOM. Facts are extracted
and yielded incrementally as they are discovered.
"""

import logging
from pathlib import Path
from typing import Optional
from lxml import etree
from dataclasses import dataclass

from ..models.fact import Fact, FactType
from ..models.context import Context, EntityIdentifier, Period, PeriodType
from ..models.unit import Unit, UnitType
from ..models.error import ParsingError, ErrorSeverity, ErrorCategory
from ..streaming.memory_manager import MemoryManager, MemoryThresholds
from ..foundation.namespace_registry import NamespaceRegistry


@dataclass
class StreamBatch:
    """
    Batch of facts from streaming parser.
    
    Attributes:
        facts: list of facts in this batch
        contexts: Contexts referenced by facts
        units: Units referenced by facts
        batch_number: Sequential batch number
        total_facts_so_far: Total facts processed
    """
    facts: list[Fact]
    contexts: dict[str, Context]
    units: dict[str, Unit]
    batch_number: int
    total_facts_so_far: int


class StreamingParser:
    """
    Streaming XBRL parser for large files.
    
    Uses SAX-style event-driven parsing to process XBRL filings incrementally,
    yielding batches of facts without loading the entire document into memory.
    
    Example:
        parser = StreamingParser(
            batch_size=1000,
            memory_threshold_mb=512
        )
        
        for batch in parser.parse_stream('large_filing.xml'):
            print(f"Batch {batch.batch_number}: {len(batch.facts)} facts")
            # Process batch incrementally
    """
    
    def __init__(
        self,
        batch_size: int = 1000,
        memory_threshold_mb: float = 512.0,
        enable_memory_management: bool = True
    ):
        """
        Initialize streaming parser.
        
        Args:
            batch_size: Number of facts per batch
            memory_threshold_mb: Memory threshold for cleanup (MB)
            enable_memory_management: Enable automatic memory management
        """
        self.batch_size = batch_size
        self.enable_memory_management = enable_memory_management
        self.logger = logging.getLogger(__name__)
        
        # Memory management
        if self.enable_memory_management:
            thresholds = MemoryThresholds(
                warning_mb=memory_threshold_mb,
                critical_mb=memory_threshold_mb * 2,
                cleanup_trigger_mb=memory_threshold_mb * 0.75
            )
            self.memory_manager = MemoryManager(thresholds=thresholds)
        else:
            self.memory_manager = None
        
        # Namespace registry
        self.namespace_registry = NamespaceRegistry()
        
        # State
        self.contexts: dict[str, Context] = {}
        self.units: dict[str, Unit] = {}
        self.errors: list[ParsingError] = []
        
        # Statistics
        self.total_facts = 0
        self.total_batches = 0
    
    def parse_stream(
        self,
        file_path: Path
    ) -> Generator[StreamBatch, None, None]:
        """
        Parse XBRL file as stream, yielding batches of facts.
        
        Args:
            file_path: Path to XBRL file
            
        Yields:
            StreamBatch objects with facts and metadata
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ParsingError: If file is malformed
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.logger.info(f"Starting streaming parse: {file_path}")
        
        # Reset state
        self.contexts = {}
        self.units = {}
        self.errors = []
        self.total_facts = 0
        self.total_batches = 0
        
        try:
            # Parse file using iterparse (streaming)
            context_iter = etree.iterparse(
                str(file_path),
                events=('start', 'end'),
                huge_tree=True,
                recover=True
            )
            
            current_batch: list[Fact] = []
            
            for event, elem in context_iter:
                # Extract namespace
                if event == 'start':
                    self._process_namespace(elem)
                
                # Process elements on end event
                if event == 'end':
                    # Extract context
                    if elem.tag.endswith('}context') or elem.tag == 'context':
                        self._extract_context(elem)
                    
                    # Extract unit
                    elif elem.tag.endswith('}unit') or elem.tag == 'unit':
                        self._extract_unit(elem)
                    
                    # Extract fact
                    elif self._is_fact_element(elem):
                        fact = self._extract_fact(elem)
                        if fact:
                            current_batch.append(fact)
                            self.total_facts += 1
                    
                    # Clear element to free memory
                    elem.clear()
                    
                    # Remove from parent to allow garbage collection
                    while elem.getprevious() is not None:
                        del elem.getparent()[0]
                    
                    # Yield batch if size reached
                    if len(current_batch) >= self.batch_size:
                        self.total_batches += 1
                        yield StreamBatch(
                            facts=current_batch,
                            contexts=dict(self.contexts),
                            units=dict(self.units),
                            batch_number=self.total_batches,
                            total_facts_so_far=self.total_facts
                        )
                        current_batch = []
                        
                        # Check memory
                        if self.memory_manager:
                            self.memory_manager.check_memory()
            
            # Yield final batch if any facts remain
            if current_batch:
                self.total_batches += 1
                yield StreamBatch(
                    facts=current_batch,
                    contexts=dict(self.contexts),
                    units=dict(self.units),
                    batch_number=self.total_batches,
                    total_facts_so_far=self.total_facts
                )
            
            self.logger.info(
                f"Streaming parse complete: {self.total_facts} facts "
                f"in {self.total_batches} batches"
            )
            
        except etree.XMLSyntaxError as e:
            error = ParsingError(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.XML_MALFORMED,
                message=f"XML syntax error: {e}",
                source_file=file_path
            )
            self.errors.append(error)
            self.logger.error(f"XML parsing failed: {e}")
            raise
        
        except Exception as e:
            error = ParsingError(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.UNKNOWN,
                message=f"Streaming parse failed: {e}",
                source_file=file_path
            )
            self.errors.append(error)
            self.logger.error(f"Streaming parse error: {e}")
            raise
    
    def _process_namespace(self, elem: etree._Element) -> None:
        """
        Extract and register namespace from element.
        
        Args:
            elem: XML element
        """
        if elem.nsmap:
            for prefix, uri in elem.nsmap.items():
                if prefix and uri:
                    self.namespace_registry.register(prefix, uri, declared_in="streaming")
    
    def _is_fact_element(self, elem: etree._Element) -> bool:
        """
        Check if element is a fact.
        
        Args:
            elem: XML element
            
        Returns:
            True if element represents a fact
        """
        # Facts have contextRef attribute
        return elem.get('contextRef') is not None
    
    def _extract_context(self, elem: etree._Element) -> None:
        """
        Extract context from element.
        
        Args:
            elem: Context element
        """
        try:
            context_id = elem.get('id')
            if not context_id:
                return
            
            # Simplified context extraction for streaming mode
            # Create minimal valid EntityIdentifier
            # Find entity element (namespace-agnostic)
            entity_elem = None
            for child in elem:
                if child.tag.endswith('}entity') or child.tag == 'entity':
                    entity_elem = child
                    break
            
            if entity_elem is not None:
                identifier_elem = None
                for child in entity_elem:
                    if child.tag.endswith('}identifier') or child.tag == 'identifier':
                        identifier_elem = child
                        break
                if identifier_elem is not None:
                    scheme = identifier_elem.get('scheme', 'http://unknown')
                    identifier = identifier_elem.text or 'unknown'
                    entity = EntityIdentifier(scheme=scheme, value=identifier)
                else:
                    entity = EntityIdentifier(scheme='http://unknown', value='unknown')
            else:
                entity = EntityIdentifier(scheme='http://unknown', value='unknown')
            
            # Create minimal valid Period
            # Find period element (namespace-agnostic)
            period_elem = None
            for child in elem:
                if child.tag.endswith('}period') or child.tag == 'period':
                    period_elem = child
                    break
            
            if period_elem is not None:
                instant_elem = None
                for child in period_elem:
                    if child.tag.endswith('}instant') or child.tag == 'instant':
                        instant_elem = child
                        break
                if instant_elem is not None:
                    period = Period(
                        period_type=PeriodType.INSTANT,
                        instant=instant_elem.text
                    )
                else:
                    # Assume duration
                    period = Period(
                        period_type=PeriodType.DURATION,
                        start_date=None,
                        end_date=None
                    )
            else:
                period = Period(period_type=PeriodType.INSTANT, instant=None)
            
            context = Context(
                id=context_id,
                entity=entity,
                period=period
            )
            
            self.contexts[context_id] = context
            
        except Exception as e:
            self.logger.debug(f"Failed to extract context: {e}")
    
    def _extract_unit(self, elem: etree._Element) -> None:
        """
        Extract unit from element.
        
        Args:
            elem: Unit element
        """
        try:
            unit_id = elem.get('id')
            if not unit_id:
                return
            
            # Simplified unit extraction for streaming mode
            measures = []
            # Find measure elements (namespace-agnostic)
            measure_elems = []
            for child in elem.iter():
                if child.tag.endswith('}measure') or child.tag == 'measure':
                    measure_elems.append(child)
            for measure_elem in measure_elems:
                if measure_elem.text:
                    measures.append(measure_elem.text)
            
            # Default to SIMPLE unit type
            unit = Unit(
                id=unit_id,
                unit_type=UnitType.SIMPLE,
                measures=measures if measures else ['unknown']
            )
            
            self.units[unit_id] = unit
            
        except Exception as e:
            self.logger.debug(f"Failed to extract unit: {e}")
    
    def _extract_fact(self, elem: etree._Element) -> Optional[Fact]:
        """
        Extract fact from element.
        
        Args:
            elem: Fact element
            
        Returns:
            Fact object or None if extraction fails
        """
        try:
            # Get concept name
            concept = elem.tag
            if '}' in concept:
                concept = concept.split('}')[1]
            
            # Get value
            value = elem.text or ""
            
            # Get references
            context_ref = elem.get('contextRef')
            unit_ref = elem.get('unitRef')
            
            # Get attributes
            decimals = elem.get('decimals')
            precision = elem.get('precision')
            
            # Determine fact type (simplified)
            fact_type = FactType.NUMERIC if unit_ref else FactType.TEXT
            
            fact = Fact(
                concept=concept,
                value=value,
                context_ref=context_ref,
                unit_ref=unit_ref,
                decimals=decimals,
                precision=precision,
                fact_type=fact_type
            )
            
            return fact
            
        except Exception as e:
            self.logger.debug(f"Failed to extract fact from {elem.tag}: {e}")
            return None
    
    def get_statistics(self) -> dict[str, any]:
        """
        Get streaming parse statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_facts': self.total_facts,
            'total_batches': self.total_batches,
            'batch_size': self.batch_size,
            'contexts_found': len(self.contexts),
            'units_found': len(self.units),
            'errors': len(self.errors)
        }
        
        # Add memory statistics if available
        if self.memory_manager:
            stats.update(self.memory_manager.get_statistics())
        
        return stats


def should_use_streaming(
    file_path: Path,
    size_threshold_mb: float = 50.0
) -> bool:
    """
    Determine if streaming should be used for file.
    
    Args:
        file_path: Path to XBRL file
        size_threshold_mb: Size threshold in MB
        
    Returns:
        True if file should be streamed
    """
    if not file_path.exists():
        return False
    
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    return file_size_mb > size_threshold_mb


__all__ = [
    'StreamBatch',
    'StreamingParser',
    'should_use_streaming',
]
