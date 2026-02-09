#!/usr/bin/env python3
"""
Recursive XML Validator
========================

Validates XML files in deeply nested directory structures.
Useful for XBRL filing directories organized by company/form/period/filing_id.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional
from collections import defaultdict

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel

from xml_validator import XMLValidator, ValidationResult

console = Console()


def find_xml_files(root_dir: Path, pattern: str = "*.xml", max_depth: Optional[int] = None) -> List[Path]:
    """
    Recursively find all XML files in directory tree.
    
    Args:
        root_dir: Root directory to search
        pattern: File pattern to match (default: *.xml)
        max_depth: Maximum depth to search (None = unlimited)
        
    Returns:
        List of XML file paths
    """
    if max_depth is not None:
        # Use rglob with depth limitation
        xml_files = []
        for depth in range(max_depth + 1):
            search_pattern = "/".join(["*"] * depth + [pattern])
            xml_files.extend(root_dir.glob(search_pattern))
        return sorted(set(xml_files))
    else:
        # Unlimited depth
        return sorted(root_dir.rglob(pattern))


def find_xsd_files(root_dir: Path, max_depth: Optional[int] = None) -> List[Path]:
    """Find all XSD schema files."""
    return find_xml_files(root_dir, pattern="*.xsd", max_depth=max_depth)


def group_files_by_directory(file_paths: List[Path]) -> dict:
    """Group files by their parent directory."""
    grouped = defaultdict(list)
    for file_path in file_paths:
        grouped[file_path.parent].append(file_path)
    return dict(grouped)


def validate_recursive(
    root_dir: Path,
    pattern: str = "*.xml",
    schema_path: Optional[Path] = None,
    output_report: Optional[Path] = None,
    max_depth: Optional[int] = None,
    fail_fast: bool = True,
    verbose: bool = False,
    show_tree: bool = False
) -> dict:
    """
    Recursively validate all XML files in directory tree.
    
    Args:
        root_dir: Root directory to search
        pattern: File pattern (default: *.xml)
        schema_path: Optional XSD schema
        output_report: Optional report output path
        max_depth: Maximum directory depth (None = unlimited)
        fail_fast: Stop validation on first error in each file
        verbose: Show detailed progress
        show_tree: Show directory tree structure
        
    Returns:
        Dictionary of validation results
    """
    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print(f"[bold]Recursive XML Validation[/bold]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")
    
    # Find all files
    console.print(f"[yellow]Searching for files in:[/yellow] {root_dir}")
    console.print(f"[yellow]Pattern:[/yellow] {pattern}")
    if max_depth is not None:
        console.print(f"[yellow]Max depth:[/yellow] {max_depth}")
    console.print()
    
    with console.status("[bold green]Searching for XML files...") as status:
        xml_files = find_xml_files(root_dir, pattern, max_depth)
    
    if not xml_files:
        console.print(f"[red]No files matching '{pattern}' found in {root_dir}[/red]")
        return {}
    
    console.print(f"[green]Found {len(xml_files)} files[/green]\n")
    
    # Show directory tree if requested
    if show_tree:
        grouped = group_files_by_directory(xml_files)
        console.print("[bold]Directory Structure:[/bold]")
        for directory in sorted(grouped.keys()):
            rel_path = directory.relative_to(root_dir) if directory != root_dir else Path(".")
            console.print(f"  📁 {rel_path}/")
            for file_path in grouped[directory]:
                console.print(f"    └─ {file_path.name}")
        console.print()
    
    # Create validator
    if schema_path:
        console.print(f"[yellow]Using schema:[/yellow] {schema_path}\n")
    
    validator = XMLValidator(
        schema_path=schema_path,
        fail_fast=fail_fast
    )
    
    # Validate all files
    results = {}
    stats = {
        'total': len(xml_files),
        'valid': 0,
        'invalid': 0,
        'errors_by_type': defaultdict(int),
        'errors_by_directory': defaultdict(int)
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("Validating files...", total=len(xml_files))
        
        for xml_file in xml_files:
            if verbose:
                progress.update(task, description=f"Validating {xml_file.name}...")
            
            result = validator.validate_file(xml_file)
            results[xml_file] = result
            
            # Update statistics
            if result.is_valid:
                stats['valid'] += 1
            else:
                stats['invalid'] += 1
                stats['errors_by_directory'][xml_file.parent] += len(result.errors)
                
                for error in result.errors:
                    stats['errors_by_type'][error.error_type] += 1
            
            progress.advance(task)
    
    # Display summary
    display_summary(stats, results, root_dir)
    
    # Save detailed report
    if output_report:
        save_report(results, stats, root_dir, output_report)
        console.print(f"\n[green]Detailed report saved to:[/green] {output_report}")
    
    return results


def display_summary(stats: dict, results: dict, root_dir: Path):
    """Display validation summary."""
    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print(f"[bold]Validation Summary[/bold]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")
    
    # Overall statistics
    summary_table = Table(title="Overall Statistics", show_header=True)
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Count", justify="right")
    
    summary_table.add_row("Total Files", str(stats['total']))
    summary_table.add_row("Valid", f"[green]{stats['valid']}[/green]")
    summary_table.add_row("Invalid", f"[red]{stats['invalid']}[/red]")
    
    if stats['total'] > 0:
        success_rate = (stats['valid'] / stats['total']) * 100
        summary_table.add_row("Success Rate", f"{success_rate:.1f}%")
    
    console.print(summary_table)
    
    # Error types
    if stats['errors_by_type']:
        console.print()
        error_table = Table(title="Errors by Type", show_header=True)
        error_table.add_column("Error Type", style="red")
        error_table.add_column("Count", justify="right", style="red")
        
        for error_type, count in sorted(stats['errors_by_type'].items(), key=lambda x: x[1], reverse=True):
            error_table.add_row(error_type, str(count))
        
        console.print(error_table)
    
    # Problematic directories
    if stats['errors_by_directory']:
        console.print()
        dir_table = Table(title="Directories with Most Errors", show_header=True)
        dir_table.add_column("Directory", style="cyan")
        dir_table.add_column("Errors", justify="right", style="red")
        
        sorted_dirs = sorted(stats['errors_by_directory'].items(), key=lambda x: x[1], reverse=True)
        for directory, error_count in sorted_dirs[:10]:  # Top 10
            rel_path = directory.relative_to(root_dir) if directory != root_dir else Path(".")
            dir_table.add_row(str(rel_path), str(error_count))
        
        console.print(dir_table)
    
    # Invalid files detail
    if stats['invalid'] > 0:
        console.print()
        invalid_table = Table(title="Invalid Files", show_header=True)
        invalid_table.add_column("File", style="cyan", max_width=50)
        invalid_table.add_column("Errors", justify="right", style="red")
        invalid_table.add_column("Directory", style="dim", max_width=40)
        
        for file_path, result in results.items():
            if not result.is_valid:
                rel_path = file_path.relative_to(root_dir) if file_path.is_relative_to(root_dir) else file_path
                dir_path = file_path.parent.relative_to(root_dir) if file_path.parent.is_relative_to(root_dir) else file_path.parent
                
                invalid_table.add_row(
                    file_path.name,
                    str(len(result.errors)),
                    str(dir_path)
                )
        
        console.print(invalid_table)


def save_report(results: dict, stats: dict, root_dir: Path, output_path: Path):
    """Save detailed validation report to file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("RECURSIVE XML VALIDATION REPORT\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Root Directory: {root_dir}\n")
        f.write(f"Total Files: {stats['total']}\n")
        f.write(f"Valid: {stats['valid']}\n")
        f.write(f"Invalid: {stats['invalid']}\n")
        f.write(f"Success Rate: {(stats['valid']/stats['total']*100):.1f}%\n" if stats['total'] > 0 else "")
        f.write("\n" + "="*70 + "\n\n")
        
        # Write detailed results
        for file_path, result in sorted(results.items()):
            f.write(f"\nFile: {file_path}\n")
            f.write("-" * 70 + "\n")
            f.write(result.summary())
            f.write("\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Recursively validate XML files in nested directory structures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate all XML files recursively
  python validate_recursive.py /mnt/map_pro/
  
  # With schema
  python validate_recursive.py /mnt/map_pro/ \\
      --schema /path/to/schema.xsd
  
  # Limit search depth
  python validate_recursive.py /mnt/map_pro/ \\
      --max-depth 5
  
  # Show directory tree
  python validate_recursive.py /mnt/map_pro/ \\
      --show-tree
  
  # Generate detailed report
  python validate_recursive.py /mnt/map_pro/ \\
      --output /home/a/Desktop/validation_report.txt
  
  # Verbose output
  python validate_recursive.py /mnt/map_pro/ \\
      --verbose
        """
    )
    
    parser.add_argument(
        'directory',
        type=Path,
        help='Root directory to search recursively'
    )
    
    parser.add_argument(
        '-p', '--pattern',
        default='*.xml',
        help='File pattern to match (default: *.xml)'
    )
    
    parser.add_argument(
        '-s', '--schema',
        type=Path,
        help='Path to XSD schema file'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output report file path'
    )
    
    parser.add_argument(
        '-d', '--max-depth',
        type=int,
        help='Maximum directory depth to search (default: unlimited)'
    )
    
    parser.add_argument(
        '--no-fail-fast',
        action='store_true',
        help='Continue validation after errors in each file'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed progress for each file'
    )
    
    parser.add_argument(
        '--show-tree',
        action='store_true',
        help='Show directory tree structure'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.directory.exists():
        console.print(f"[red]Error:[/red] Directory not found: {args.directory}")
        return 1
    
    if args.schema and not args.schema.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {args.schema}")
        return 1
    
    try:
        results = validate_recursive(
            root_dir=args.directory,
            pattern=args.pattern,
            schema_path=args.schema,
            output_report=args.output,
            max_depth=args.max_depth,
            fail_fast=not args.no_fail_fast,
            verbose=args.verbose,
            show_tree=args.show_tree
        )
        
        # Return non-zero if any validation failed
        invalid_count = sum(1 for r in results.values() if not r.is_valid)
        return min(invalid_count, 1)
    
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