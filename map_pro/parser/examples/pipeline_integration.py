#!/usr/bin/env python3
# Path: examples/pipeline_integration.py
"""
Pipeline Integration Example

This example demonstrates batch processing and pipeline integration.

Usage:
    python examples/pipeline_integration.py path/to/filing.xml
"""

import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from xbrl_parser.orchestrator import XBRLParser
from xbrl_parser.parser_modes import ParsingMode
from xbrl_parser.serialization.json_serializer import JSONSerializer
from ..output import ReportGenerator


class PipelineConfig:
    """Pipeline configuration."""
    
    def __init__(self):
        self.parsing_mode = ParsingMode.FULL
        self.continue_on_error = True
        self.output_dir = Path("outputs/pipeline")
        self.output_dir.mkdir(parents=True, exist_ok=True)


class BatchProcessor:
    """Batch file processor."""
    
    def __init__(self, config):
        self.config = config
        self.parser = XBRLParser(mode=config.parsing_mode)
    
    def process_filing(self, filing_path, index, total):
        """Process single filing."""
        result = {
            'filing_name': filing_path.name,
            'status': 'unknown',
            'start_time': datetime.now(),
            'fact_count': 0
        }
        
        try:
            print(f"  [{index}/{total}] {filing_path.name}...")
            parsed = self.parser.parse(filing_path)
            
            result['fact_count'] = len(parsed.instance.facts)
            result['context_count'] = len(parsed.instance.contexts)
            
            # Export
            filing_id = filing_path.stem
            json_path = self.config.output_dir / f"{filing_id}.json"
            JSONSerializer().serialize(parsed, json_path)
            
            txt_path = self.config.output_dir / f"{filing_id}.txt"
            ReportGenerator().save_text_report(parsed, txt_path, detailed=False)
            
            result['status'] = 'success'
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
        
        result['end_time'] = datetime.now()
        result['duration'] = (result['end_time'] - result['start_time']).total_seconds()
        
        return result
    
    def process_batch(self, filings):
        """Process batch of filings."""
        results = []
        for i, path in enumerate(filings, 1):
            result = self.process_filing(path, i, len(filings))
            results.append(result)
        return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline_integration.py <files_or_directory>")
        sys.exit(1)
    
    # Collect files
    filings = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            filings.extend(p.glob("*.xml"))
            filings.extend(p.glob("*.htm"))
        elif p.is_file():
            filings.append(p)
    
    if not filings:
        print("No files found")
        sys.exit(1)
    
    print("=" * 70)
    print("BATCH PROCESSING PIPELINE")
    print("=" * 70)
    print(f"\nFound {len(filings)} filing(s)\n")
    
    # Process
    config = PipelineConfig()
    processor = BatchProcessor(config)
    results = processor.process_batch(filings)
    
    # Report
    successful = sum(1 for r in results if r['status'] == 'success')
    total_facts = sum(r['fact_count'] for r in results)
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\nSuccessful: {successful}/{len(results)}")
    print(f"Total facts: {total_facts:,}")
    print(f"Output: {config.output_dir}\n")


if __name__ == "__main__":
    main()