# Path: mapper.py
"""
XBRL Statement Extractor - Main CLI Entry Point

Extracts financial statements EXACTLY as company declares them.

DESIGN PRINCIPLE: WATER
- NO hardcoded schemas
- NO transformation  
- NO mapping
- Read company's presentation linkbase
- Export company's structure as-is
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Core components
from .core.ui.cli import MappingCLI
from .core.config_loader import ConfigLoader
from .core.data_paths import DataPathsManager

# IPO Logging
from .core.logger.ipo_logging import setup_ipo_logging

# Statement extraction orchestrator
from .mapping.orchestrator import MappingOrchestrator


def main():
    """Main CLI workflow."""
    
    # Load configuration
    config = ConfigLoader()
    
    # Configure IPO-based logging (creates 4 log files: input, process, output, full)
    log_dir = config.get('log_dir')
    if not log_dir:
        log_dir = Path('/mnt/map_pro/mapper/logs')
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    setup_ipo_logging(
        log_dir=log_dir,
        log_level='INFO',
        console_output=True
    )
    
    logger = logging.getLogger(__name__)
    
    print("=" * 80)
    print("XBRL STATEMENT EXTRACTOR - COMPANY STRUCTURE AS-IS")
    print("=" * 80)
    print()
    print("PRINCIPLE: Water takes the shape of its container")
    print("  Container = Company's XBRL presentation linkbase")
    print("  Output = Company's declared structure (NO transformation)")
    print("=" * 80)
    
    try:
        # Step 1: Initialize output directories
        print("\nInitializing output directories...")
        manager = DataPathsManager()
        result = manager.ensure_all_directories()
        print(f"Output ready ({len(result['existing'])} directories verified)")
        
        # Step 2: Select filing using CLI
        print("\n" + "=" * 80)
        print("SELECT PARSED FILING")
        print("=" * 80)
        
        cli = MappingCLI()
        filing_entry = cli.run()
        
        if not filing_entry:
            print("\nNo filing selected. Exiting.")
            return 0
        
        # Get parsed.json path from filing entry
        parsed_json_path = filing_entry.available_files.get('json')
        
        if not parsed_json_path:
            print(f"\nERROR: No parsed.json found in {filing_entry.filing_folder}")
            return 1
        
        # Step 3: Extract and export company structure
        print("\n" + "=" * 80)
        print("EXTRACTING COMPANY STRUCTURE")
        print("=" * 80)
        print(f"Filing: {filing_entry.company} | {filing_entry.form} | {filing_entry.date}")
        print(f"JSON: {parsed_json_path}\n")
        
        orchestrator = MappingOrchestrator(config=config)
        
        start_time = datetime.now()
        result = orchestrator.extract_and_export(parsed_json_path=parsed_json_path)
        total_time = (datetime.now() - start_time).total_seconds()
        
        print(f"\nExtraction completed in {total_time:.2f} seconds")
        
        # Step 4: Display statistics
        print("\n" + "=" * 80)
        print("EXTRACTION RESULTS")
        print("=" * 80)
        
        stats = result['statistics']
        
        print(f"\nStatements Extracted:")
        print(f"  Total statements: {stats['total_statements']}")
        print(f"  Total fact placements: {stats['total_fact_placements']}")
        
        print(f"\nFiling Information:")
        filing_info = result['filing_info']
        print(f"  Entity: {filing_info.get('entity_name', 'Unknown')}")
        print(f"  CIK: {filing_info.get('cik', 'N/A')}")
        print(f"  Filing Type: {filing_info.get('filing_type', 'Unknown')}")
        print(f"  Period End: {filing_info.get('period_end', 'Unknown')}")
        
        print(f"\nExport Files:")
        for format_type, path in result['export_paths'].items():
            print(f"  {format_type.upper()}: {path}")
        
        print(f"\nPerformance:")
        print(f"  Processing time: {total_time:.2f} seconds")
        
        print("\n" + "=" * 80)
        print("EXTRACTION COMPLETE")
        print("=" * 80)
        print()
        print("NOTE: Output preserves company's exact structure from presentation linkbase.")
        print("      No transformation or standardization has been applied.")
        print("      Use verification system for standardization if needed.")
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return 1
    
    except Exception as e:
        logger.exception(f"Extraction failed: {e}")
        print(f"\nERROR: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())