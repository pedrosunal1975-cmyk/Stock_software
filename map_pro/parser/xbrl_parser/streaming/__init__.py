# Path: xbrl_parser/streaming/__init__.py
"""
Streaming Module

Provides streaming parsing capabilities for large XBRL filings that
exceed memory limits when loaded entirely into DOM.

Components:
    - stream_parser: SAX-style event-driven parser
    - memory_manager: Memory tracking and management

Example:
    from ..streaming import StreamingParser, should_use_streaming
    
    file_path = Path('large_filing.xml')
    
    if should_use_streaming(file_path):
        parser = StreamingParser(batch_size=1000)
        
        for batch in parser.parse_stream(file_path):
            print(f"Batch {batch.batch_number}: {len(batch.facts)} facts")
            # Process batch incrementally
"""

from ..streaming.stream_parser import (
    StreamBatch,
    StreamingParser,
    should_use_streaming,
)
from ..streaming.memory_manager import (
    MemorySnapshot,
    MemoryThresholds,
    MemoryManager,
)

__all__ = [
    'StreamBatch',
    'StreamingParser',
    'should_use_streaming',
    'MemorySnapshot',
    'MemoryThresholds',
    'MemoryManager',
]
