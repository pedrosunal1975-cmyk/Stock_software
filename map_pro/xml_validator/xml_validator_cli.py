#!/usr/bin/env python3
"""
XML Validator CLI
=================

Command-line interface for the standalone XML validation tool.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler

from xml_validator import (
    XMLValidator,
    ValidationResult,
    ValidationStatus,
    validate_batch
)


console = Console()


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging with rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)]
    )
    
    return logging.getLogger("xml_validator_cli")


def display_result(result: ValidationResult) -> None:
    """Display validation result with rich formatting."""
    
    # Status panel
    status_color = "green" if result.is_valid else "red"
    status_symbol = "✓" if result.is_valid else "✗"
    
    status_text = f"[{status_color} bold]{status_symbol} {result.status.value.upper()}[/{status_color} bold]"
    
    panel = Panel(
        f"{status_text}\n"
        f"File: {result.file_path.name}\n"
        f"Errors: {len(result.errors)} | Warnings: {len(result.warnings)}\n"
        f"Completed: {', '.join(l.value for l in result.levels_completed)}",
        title="Validation Result",
        border_style=status_color
    )
    console.print(panel)
    
    # Errors table
    if result.errors:
        error_table = Table(title="Errors", show_header=True, header_style="bold red")
        error_table.add_column("#", style="dim", width=4)
        error_table.add_column("Level", style="red")
        error_table.add_column("Location", style="cyan")
        error_table.add_column("Message", style="white")
        
        for i, error in enumerate(result.errors, 1):
            location = f"L{error.line}:C{error.column}" if error.line else "N/A"
            error_table.add_row(
                str(i),
                error.level.value,
                location,
                error.message[:80] + "..." if len(error.message) > 80 else error.message
            )
        
        console.print(error_table)
    
    # Warnings table
    if result.warnings:
        warning_table = Table(title="Warnings", show_header=True, header_style="bold yellow")
        warning_table.add_column("#", style="dim", width=4)
        warning_table.add_column("Level", style="yellow")
        warning_table.add_column("Location", style="cyan")
        warning_table.add_column("Message", style="white")
        
        for i, warning in enumerate(result.warnings, 1):
            location = f"L{warning.line}:C{warning.column}" if warning.line else "N/A"
            warning_table.add_row(
                str(i),
                warning.level.value,
                location,
                warning.message[:80] + "..." if len(warning.message) > 80 else warning.message
            )
        
        console.print(warning_table)


def display_batch_summary(results: dict[Path, ValidationResult]) -> None:
    """Display summary of batch validation."""
    
    total = len(results)
    passed = sum(1 for r in results.values() if r.is_valid)
    failed = total - passed
    
    summary_table = Table(title="Batch Validation Summary", show_header=True)
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Count", justify="right")
    
    summary_table.add_row("Total Files", str(total))
    summary_table.add_row("Passed", f"[green]{passed}[/green]")
    summary_table.add_row("Failed", f"[red]{failed}[/red]")
    summary_table.add_row(
        "Success Rate",
        f"{(passed/total*100):.1f}%" if total > 0 else "N/A"
    )
    
    console.print(summary_table)
    
    # Failed files detail
    if failed > 0:
        failed_table = Table(title="Failed Files", show_header=True, header_style="bold red")
        failed_table.add_column("File", style="cyan")
        failed_table.add_column("Errors", justify="right", style="red")
        failed_table.add_column("Warnings", justify="right", style="yellow")
        
        for path, result in results.items():
            if not result.is_valid:
                failed_table.add_row(
                    path.name,
                    str(len(result.errors)),
                    str(len(result.warnings))
                )
        
        console.print(failed_table)


def validate_single_file(
    file_path: Path,
    schema_path: Optional[Path],
    fail_fast: bool,
    verbose: bool
) -> int:
    """Validate a single XML file."""
    
    logger = setup_logging(verbose)
    
    if not file_path.exists():
        console.print(f"[red]Error:[/red] File not found: {file_path}")
        return 1
    
    if schema_path and not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {schema_path}")
        return 1
    
    console.print(f"\n[bold]Validating XML Document[/bold]")
    console.print(f"File: {file_path}")
    if schema_path:
        console.print(f"Schema: {schema_path}")
    console.print()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Validating...", total=None)
        
        validator = XMLValidator(
            schema_path=schema_path,
            fail_fast=fail_fast,
            logger=logger
        )
        
        result = validator.validate_file(file_path)
        progress.update(task, completed=True)
    
    display_result(result)
    
    return 0 if result.is_valid else 1


def validate_directory(
    directory: Path,
    pattern: str,
    schema_path: Optional[Path],
    fail_fast: bool,
    verbose: bool,
    output_report: Optional[Path]
) -> int:
    """Validate all XML files in a directory."""
    
    logger = setup_logging(verbose)
    
    if not directory.exists():
        console.print(f"[red]Error:[/red] Directory not found: {directory}")
        return 1
    
    if schema_path and not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {schema_path}")
        return 1
    
    # Find XML files
    xml_files = list(directory.glob(pattern))
    
    if not xml_files:
        console.print(f"[yellow]Warning:[/yellow] No files matching '{pattern}' found in {directory}")
        return 0
    
    console.print(f"\n[bold]Batch XML Validation[/bold]")
    console.print(f"Directory: {directory}")
    console.print(f"Pattern: {pattern}")
    console.print(f"Files found: {len(xml_files)}")
    if schema_path:
        console.print(f"Schema: {schema_path}")
    console.print()
    
    validator = XMLValidator(
        schema_path=schema_path,
        fail_fast=fail_fast,
        logger=logger
    )
    
    results = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processing files...", total=len(xml_files))
        
        for xml_file in xml_files:
            progress.update(task, description=f"Validating {xml_file.name}...")
            result = validator.validate_file(xml_file)
            results[xml_file] = result
            progress.advance(task)
    
    # Display individual results
    for xml_file, result in results.items():
        console.print(f"\n[bold cyan]{'─' * 70}[/bold cyan]")
        display_result(result)
    
    # Display summary
    console.print(f"\n[bold cyan]{'═' * 70}[/bold cyan]")
    display_batch_summary(results)
    
    # Save report if requested
    if output_report:
        with open(output_report, 'w', encoding='utf-8') as f:
            for xml_file, result in results.items():
                f.write(result.summary())
                f.write("\n" + "="*70 + "\n")
        console.print(f"\n[green]Report saved:[/green] {output_report}")
    
    # Return non-zero if any validation failed
    failed_count = sum(1 for r in results.values() if not r.is_valid)
    return min(failed_count, 1)


def main():
    """Main CLI entry point."""
    
    parser = argparse.ArgumentParser(
        description="XML Document Validator - Standalone validation tool for XML/XBRL preprocessing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single file
  xml-validator validate document.xml
  
  # Validate with schema
  xml-validator validate document.xml --schema schema.xsd
  
  # Validate all XML files in directory
  xml-validator batch ./documents --pattern "*.xml"
  
  # Validate with report output
  xml-validator batch ./documents --output report.txt
  
  # Continue validation after errors (don't fail fast)
  xml-validator validate document.xml --no-fail-fast
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='XML Validator 1.0.0'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate a single XML file'
    )
    validate_parser.add_argument(
        'file',
        type=Path,
        help='Path to XML file'
    )
    validate_parser.add_argument(
        '-s', '--schema',
        type=Path,
        help='Path to XSD schema file'
    )
    validate_parser.add_argument(
        '--no-fail-fast',
        action='store_true',
        help='Continue validation after errors'
    )
    validate_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    # Batch command
    batch_parser = subparsers.add_parser(
        'batch',
        help='Validate multiple XML files in a directory'
    )
    batch_parser.add_argument(
        'directory',
        type=Path,
        help='Directory containing XML files'
    )
    batch_parser.add_argument(
        '-p', '--pattern',
        default='*.xml',
        help='File pattern to match (default: *.xml)'
    )
    batch_parser.add_argument(
        '-s', '--schema',
        type=Path,
        help='Path to XSD schema file'
    )
    batch_parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output report file path'
    )
    batch_parser.add_argument(
        '--no-fail-fast',
        action='store_true',
        help='Continue validation after errors'
    )
    batch_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    try:
        if args.command == 'validate':
            return validate_single_file(
                file_path=args.file,
                schema_path=args.schema,
                fail_fast=not args.no_fail_fast,
                verbose=args.verbose
            )
        
        elif args.command == 'batch':
            return validate_directory(
                directory=args.directory,
                pattern=args.pattern,
                schema_path=args.schema,
                fail_fast=not args.no_fail_fast,
                verbose=args.verbose,
                output_report=args.output
            )
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Validation interrupted by user[/yellow]")
        return 130
    
    except Exception as e:
        console.print(f"\n[red bold]Error:[/red bold] {str(e)}")
        if args.verbose:
            console.print_exception()
        return 1


if __name__ == "__main__":
    sys.exit(main())
