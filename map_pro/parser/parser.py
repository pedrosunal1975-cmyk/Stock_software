#!/usr/bin/env python3
# Path: parser.py
"""
XBRL Parser - Main CLI Entry Point

Command-line interface that orchestrates the complete XBRL parsing workflow.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Core components
from ..core.ui.cli import FilingCLI
from ..core.config_loader import ConfigLoader
from ..core.data_paths import DataPathsManager
from ..core.logger import setup_ipo_logging

# Parser orchestrator
from xbrl_parser.orchestrator import XBRLParser

# Output classes
from xbrl_parser.serialization.json_serializer import JSONSerializer
from output.extracted_data.data_extractor import DataExtractor
from output.parsed_report.report_generator import ReportGenerator


def main():
    """Main CLI workflow."""
    # Load configuration FIRST
    config = ConfigLoader()
    
    # Configure IPO-aware logging using config
    setup_ipo_logging(
        log_dir=config.get('log_dir'),  # Uses PARSER_LOG_DIR from .env
        log_level=config.get('log_level', 'INFO'),
        console_output=True
    )
    
    logger = logging.getLogger(__name__)
    
    print("=" * 80)
    print("XBRL PARSER - PRODUCTION INTERFACE")
    print("=" * 80)
    
    try:
        # Step 1: Initialize output directories
        print("\nInitializing output directories...")
        manager = DataPathsManager()
        result = manager.ensure_all_directories()
        print(f"Output ready ({len(result['existing'])} directories verified)")
        
        # Step 2: Select filing using CLI
        print("\n" + "=" * 80)
        print("SELECT FILING")
        print("=" * 80)
        
        cli = FilingCLI()
        filing_entry = cli.run()
        
        # Step 3: Parse filing using orchestrator
        print("\n" + "=" * 80)
        print("PARSING FILING")
        print("=" * 80)
        print(f"Filing: {filing_entry.market} | {filing_entry.company} | {filing_entry.form}")
        print(f"Path: {filing_entry.path}\n")
        
        parser = XBRLParser()
        start_time = datetime.now()
        filing = parser.parse(filing_entry.path)
        parse_time = (datetime.now() - start_time).total_seconds()
        
        print(f"\nParsing completed in {parse_time:.2f} seconds")
        print(f"Extracted {len(filing.instance.facts):,} facts")
        
        # Step 3.5: Populate metadata from filing_entry
        filing.metadata.market = filing_entry.market
        filing.metadata.company_name = filing_entry.company.replace("_", " ")
        filing.metadata.document_type = filing_entry.form
        
        # Parse date string to datetime
        try:
            from datetime import datetime as dt
            filing.metadata.filing_date = dt.strptime(filing_entry.date, '%Y-%m-%d')
        except (ValueError, AttributeError):
            filing.metadata.filing_date = None
        
        # Step 3.6: Extract entity_identifier and period_end_date from contexts
        if filing.instance.contexts:
            # Get entity identifier from first context
            first_context = next(iter(filing.instance.contexts.values()))
            filing.metadata.entity_identifier = first_context.entity.value
            
            # Find latest period end date
            end_dates = []
            for context in filing.instance.contexts.values():
                if context.period.end_date:
                    end_dates.append(context.period.end_date)
                elif context.period.instant:
                    end_dates.append(context.period.instant)
            
            if end_dates:
                filing.metadata.period_end_date = max(end_dates)
        
        # Step 4: Generate nested output folder structure: company/form/date/
        company = (filing.metadata.company_name or "Unknown_Company").replace(" ", "_").replace(",", "").replace(".", "")
        doc_type = filing.metadata.document_type or "Filing"
        date_str = filing.metadata.filing_date.strftime('%Y-%m-%d') if filing.metadata.filing_date else "unknown"
        
        # Create nested structure matching mapper's expected input
        market = filing.metadata.market or "unknown"
        filing_folder = Path(config.get("output_parsed_dir")) / market / company / doc_type / date_str
        filing_folder.mkdir(parents=True, exist_ok=True)
        
        # Step 5: Save outputs to filing folder
        print("\n" + "=" * 80)
        print("SAVING OUTPUTS")
        print("=" * 80)
        
        # 5a. JSON report
        json_file = filing_folder / "parsed.json"
        print(f"\n1. JSON Report:")
        print(f"   {json_file}")
        
        serializer = JSONSerializer()
        json_output = serializer.serialize(filing)
        json_file.write_text(json_output)
        
        print(f"   Size: {json_file.stat().st_size / 1024:.1f} KB")
        print(f"   Facts: {len(filing.instance.facts):,}")
        print(f"   ✓ Saved")
        
        # 5b. CSV export
        csv_file = filing_folder / "facts.csv"
        print(f"\n2. CSV Export:")
        print(f"   {csv_file}")
        
        extractor = DataExtractor()
        extractor.save_facts_csv(filing, csv_file, include_context_details=True)
        
        print(f"   Size: {csv_file.stat().st_size / 1024:.1f} KB")
        print(f"   ✓ Saved")
        
        # 5c. Summary report
        summary_file = filing_folder / "summary.txt"
        print(f"\n3. Summary Report:")
        print(f"   {summary_file}")
        
        generator = ReportGenerator()
        summary = generator.generate_summary(filing, parse_time=parse_time)  
        summary_file.write_text(summary)
        
        print(f"   ✓ Saved")
        
        # 5d. Excel export
        excel_file = filing_folder / "workbook.xlsx"
        print(f"\n4. Excel Workbook:")
        print(f"   {excel_file}")
        
        try:
            from output.excel_exporter import ExcelExporter
            excel_exporter = ExcelExporter()
            
            if excel_exporter.has_openpyxl:
                excel_exporter.export(filing, excel_file, include_errors=True)
                print(f"   Size: {excel_file.stat().st_size / 1024:.1f} KB")
                print(f"   ✓ Saved")
            else:
                print(f"   ⚠ Skipped (install: pip install openpyxl)")
        except Exception as e:
            print(f"   ⚠ Excel export failed: {e}")
        
        # Step 6: Display summary
        print("\n" + "=" * 80)
        print(summary)
        
        # Step 7: Display statistics
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)
        
        facts_with_ids = sum(1 for f in filing.instance.facts if f.id)
        facts_with_footnotes = sum(1 for f in filing.instance.facts if f.footnote_refs and len(f.footnote_refs) > 0)
        facts_with_source = sum(1 for f in filing.instance.facts if f.source_line)
        total_footnotes = len(filing.instance.footnotes) if hasattr(filing.instance, 'footnotes') and filing.instance.footnotes else 0
        
        print(f"\nPerformance:")
        print(f"  Parse time: {parse_time:.2f} seconds")
        print(f"  Facts/second: {len(filing.instance.facts) / parse_time:,.0f}" if parse_time > 0 else "  Facts/second: N/A")
        
        print(f"\nFact Attributes:")
        print(f"  With IDs: {facts_with_ids:,}")
        print(f"  With footnote refs: {facts_with_footnotes:,}")
        print(f"  With source tracking: {facts_with_source:,}")
        print(f"\nFootnotes:")
        print(f"  Total extracted: {total_footnotes:,}")
        
        print(f"\nOutput Structure:")
        print(f"  Location: {filing_folder}")
        print(f"  Company: {company}")
        print(f"  Form: {doc_type}")
        print(f"  Date: {date_str}")
        print(f"\nOutput Files:")
        print(f"  JSON: {json_file.name}")
        print(f"  CSV: {csv_file.name}")
        print(f"  Summary: {summary_file.name}")
        print(f"  Excel: {excel_file.name}")
        
        print("\n" + "=" * 80)
        print("PARSING COMPLETE")
        print("=" * 80)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return 1
        
    except Exception as e:
        logger.error(f"Parsing failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())