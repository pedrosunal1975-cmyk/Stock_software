# Path: mat_acc/process/hierarchy/tree_builder.py
"""
Hierarchy Builder - Main orchestrator for building statement hierarchies.

This module provides a unified interface for building hierarchies from:
- XBRL presentation linkbase files (PRIMARY source)
- Mapped statement JSON files from mapper output

The builder is DYNAMIC and TAXONOMY AGNOSTIC:
- Statement types are DISCOVERED from the data, not hardcoded
- Works with any market (SEC, ESEF, FCA, etc.)

Example:
    builder = HierarchyBuilder()

    # Build from XBRL filing (reads presentation linkbase)
    hierarchies = builder.build_from_xbrl_filing(Path('/path/to/filing/'))

    # Build from mapped statement file
    hierarchy = builder.build_from_statement_file(Path('statement.json'))

    # Build from filing folder
    hierarchies = builder.build_from_filing_folder(Path('/mapped/filing/'))
"""

from pathlib import Path
from typing import Any, Optional

from process.hierarchy.node import HierarchyNode
from process.hierarchy.xbrl_builder import XbrlHierarchyBuilder
from process.hierarchy.mapped_builder import MappedHierarchyBuilder
from process.hierarchy.mat_acc_id import (
    format_mat_acc_id,
    parse_mat_acc_id,
    get_statement_code,
)


class HierarchyBuilder:
    """
    Unified hierarchy builder that delegates to specialized builders.

    Provides a single interface for building hierarchies from:
    - XBRL presentation linkbase (via XbrlHierarchyBuilder)
    - Mapped statement files (via MappedHierarchyBuilder)

    Example:
        builder = HierarchyBuilder()

        # Build from XBRL filing
        hierarchies = builder.build_from_xbrl_filing(Path('/path/to/filing/'))

        # Build from a single statement JSON file
        hierarchy = builder.build_from_statement_file(Path('statement.json'))

        # Build all statements from a filing folder
        hierarchies = builder.build_from_filing_folder(Path('/mapped/filing/'))

        for name, root in hierarchies.items():
            print(f"{name}: {root.descendant_count} nodes")
    """

    def __init__(self):
        """Initialize the hierarchy builder."""
        self._xbrl_builder = XbrlHierarchyBuilder()
        self._mapped_builder = MappedHierarchyBuilder()
        self._linkbase_parser = None

    # =========================================================================
    # XBRL FILING BUILD METHODS (PRIMARY - reads presentation linkbase)
    # =========================================================================

    def build_from_xbrl_filing(
        self,
        filing_dir: Path
    ) -> dict[str, HierarchyNode]:
        """
        Build hierarchies from XBRL filing's presentation linkbase.

        This is the PRIMARY method for building fact hierarchies.
        It reads the presentation linkbase (_pre.xml) which is the
        authoritative source for statement structure.

        Args:
            filing_dir: Path to the XBRL filing directory

        Returns:
            Dictionary mapping statement names to their root nodes
        """
        return self._xbrl_builder.build_from_filing(filing_dir)

    def build_from_presentation_linkbase(
        self,
        linkbase_path: Path
    ) -> dict[str, HierarchyNode]:
        """
        Build hierarchies directly from a presentation linkbase file.

        Args:
            linkbase_path: Path to the presentation linkbase file (*_pre.xml)

        Returns:
            Dictionary mapping statement names to their root nodes
        """
        return self._xbrl_builder.build_from_linkbase(linkbase_path)

    # =========================================================================
    # MAPPED STATEMENT BUILD METHODS (SECONDARY - for mapper output)
    # =========================================================================

    def build_from_statement_file(
        self,
        json_path: Path
    ) -> Optional[HierarchyNode]:
        """
        Build hierarchy from a single statement JSON file.

        Reads the statement_type and hierarchy fields from the JSON.

        Args:
            json_path: Path to the statement JSON file

        Returns:
            Root node of the hierarchy, or None if build failed
        """
        return self._mapped_builder.build_from_file(json_path)

    def build_from_statement_data(
        self,
        data: dict[str, Any],
        statement_name: str = "statement"
    ) -> Optional[HierarchyNode]:
        """
        Build hierarchy from statement data dictionary.

        Args:
            data: Statement data with hierarchy field
            statement_name: Name for the statement

        Returns:
            Root node of the hierarchy, or None if build failed
        """
        return self._mapped_builder.build_from_data(data, statement_name)

    def build_from_filing_folder(
        self,
        filing_folder: Path,
        include_details: bool = True,
        include_other: bool = True
    ) -> dict[str, HierarchyNode]:
        """
        Build hierarchies from all statement files in a mapped filing folder.

        Searches json/core_statements/, json/details/, json/other/ folders.

        Args:
            filing_folder: Path to the mapped filing folder
            include_details: Whether to include statements from details/
            include_other: Whether to include statements from other/

        Returns:
            Dictionary mapping statement names to their root nodes
        """
        return self._mapped_builder.build_from_folder(
            filing_folder,
            include_details=include_details,
            include_other=include_other
        )

    def build_from_mapped_filing(
        self,
        filing_entry: Any,
        include_details: bool = True,
        include_other: bool = True
    ) -> dict[str, HierarchyNode]:
        """
        Build hierarchies from a MappedFilingEntry.

        Uses the loaders' MappedFilingEntry to find and build hierarchies.

        Args:
            filing_entry: MappedFilingEntry from MappedDataLoader
            include_details: Whether to include statements from details/
            include_other: Whether to include statements from other/

        Returns:
            Dictionary mapping statement names to their root nodes
        """
        return self._mapped_builder.build_from_filing_entry(
            filing_entry,
            include_details=include_details,
            include_other=include_other
        )

    # =========================================================================
    # LEGACY BUILD METHODS (for backward compatibility with tests)
    # =========================================================================

    def build_from_mapped_statement(
        self,
        mapped_data: dict[str, Any],
        statement_key: Optional[str] = None
    ) -> Optional[HierarchyNode]:
        """
        Build hierarchy from a mapped statement dictionary.

        LEGACY METHOD - kept for backward compatibility with existing tests.
        For new code, use build_from_statement_file() or build_from_filing_folder().

        Args:
            mapped_data: Mapped statement data
            statement_key: Optional specific statement to build

        Returns:
            Root node of the hierarchy, or None if build failed
        """
        return self._mapped_builder.build_from_mapped_statement(
            mapped_data, statement_key
        )

    def build_all_statements(
        self,
        mapped_data: dict[str, Any]
    ) -> dict[str, HierarchyNode]:
        """
        Build hierarchies for all statements in mapped data.

        LEGACY METHOD - kept for backward compatibility with existing tests.

        Args:
            mapped_data: Mapped statement data

        Returns:
            Dictionary mapping statement keys to their root nodes
        """
        return self._mapped_builder.build_all_statements(mapped_data)

    # Keep internal methods for test compatibility
    def _detect_statement_type(self, statement_key: str):
        """Detect statement type - kept for test compatibility."""
        return self._mapped_builder._detect_statement_type(statement_key)

    def _determine_node_type(
        self,
        item: dict[str, Any],
        concept: str,
        label: str
    ):
        """Determine node type - kept for test compatibility."""
        return self._mapped_builder._determine_node_type(item, concept, label)

    def _extract_value(self, data: dict[str, Any]):
        """Extract value - kept for test compatibility."""
        from process.hierarchy.builder_utils import extract_value
        return extract_value(data)

    # =========================================================================
    # STATIC UTILITY METHODS
    # =========================================================================

    @staticmethod
    def format_mat_acc_id(
        statement_code: str,
        level: int,
        sibling: int,
        context_ref: Optional[str] = None
    ) -> str:
        """
        Generate a mat_acc_id from components.

        Format: {STATEMENT_CODE}-{LEVEL:03d}-{SIBLING:03d}-{CONTEXT_REF}
        Example: BS-002-001-c4

        Args:
            statement_code: Statement type code (BS, IS, CF, EQ, OT)
            level: Hierarchy level (0 = root)
            sibling: Sibling position (1-based)
            context_ref: Optional context reference (e.g., 'c-4', 'c4')

        Returns:
            Formatted mat_acc_id string
        """
        return format_mat_acc_id(statement_code, level, sibling, context_ref)

    @staticmethod
    def parse_mat_acc_id(mat_acc_id: str) -> dict[str, Any]:
        """
        Parse a mat_acc_id into its components.

        Args:
            mat_acc_id: The mat_acc_id to parse (e.g., 'BS-002-001-c4')

        Returns:
            Dictionary with statement_code, level, sibling, context_ref, position
        """
        return parse_mat_acc_id(mat_acc_id)

    @staticmethod
    def get_statement_code(statement_type: str) -> str:
        """
        Get the statement code for a statement type.

        Args:
            statement_type: Statement type (BALANCE_SHEET, etc.)

        Returns:
            Two-letter code (BS, IS, CF, EQ, OT)
        """
        return get_statement_code(statement_type)

    # =========================================================================
    # PROPERTIES - Aggregate from both builders
    # =========================================================================

    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message from either builder."""
        return self._mapped_builder.last_error or self._xbrl_builder.last_error

    @property
    def build_count(self) -> int:
        """Get total number of successful builds from both builders."""
        return self._xbrl_builder.build_count + self._mapped_builder.build_count

    @property
    def discovered_types(self) -> set[str]:
        """Get all dynamically discovered statement types from both builders."""
        return (
            self._xbrl_builder.discovered_types |
            self._mapped_builder.discovered_types
        )

    def reset_stats(self) -> None:
        """Reset build statistics for both builders."""
        self._xbrl_builder.reset_stats()
        self._mapped_builder.reset_stats()


__all__ = ['HierarchyBuilder']
