# Path: mat_acc/tests/unit/test_hierarchy/test_xbrl_builder.py
"""
Tests for XbrlHierarchyBuilder - builds hierarchies from XBRL presentation linkbase.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from process.hierarchy.xbrl_builder import XbrlHierarchyBuilder
from process.hierarchy.node import HierarchyNode


class TestXbrlHierarchyBuilderInit:
    """Tests for XbrlHierarchyBuilder initialization."""

    def test_create_builder(self):
        """Create builder instance."""
        builder = XbrlHierarchyBuilder()
        assert builder is not None

    def test_initial_build_count_is_zero(self):
        """Initial build count is zero."""
        builder = XbrlHierarchyBuilder()
        assert builder.build_count == 0

    def test_initial_last_error_is_none(self):
        """Initial last error is None."""
        builder = XbrlHierarchyBuilder()
        assert builder.last_error is None

    def test_initial_discovered_types_is_empty(self):
        """Initial discovered types is empty."""
        builder = XbrlHierarchyBuilder()
        assert len(builder.discovered_types) == 0


class TestXbrlHierarchyBuilderProperties:
    """Tests for XbrlHierarchyBuilder properties."""

    def test_last_error_property(self):
        """last_error property is accessible."""
        builder = XbrlHierarchyBuilder()
        assert builder.last_error is None

    def test_build_count_property(self):
        """build_count property is accessible."""
        builder = XbrlHierarchyBuilder()
        assert isinstance(builder.build_count, int)

    def test_discovered_types_returns_copy(self):
        """discovered_types returns a copy."""
        builder = XbrlHierarchyBuilder()
        types1 = builder.discovered_types
        types2 = builder.discovered_types
        assert types1 is not types2


class TestXbrlHierarchyBuilderResetStats:
    """Tests for XbrlHierarchyBuilder.reset_stats()."""

    def test_reset_clears_build_count(self):
        """reset_stats clears build count."""
        builder = XbrlHierarchyBuilder()
        # Simulate a build by manually incrementing (not ideal but works for testing)
        builder._build_count = 5
        builder.reset_stats()
        assert builder.build_count == 0

    def test_reset_clears_last_error(self):
        """reset_stats clears last error."""
        builder = XbrlHierarchyBuilder()
        builder._last_error = "Some error"
        builder.reset_stats()
        assert builder.last_error is None

    def test_reset_clears_discovered_types(self):
        """reset_stats clears discovered types."""
        builder = XbrlHierarchyBuilder()
        builder._discovered_types.add('TEST_TYPE')
        builder.reset_stats()
        assert len(builder.discovered_types) == 0


class TestXbrlHierarchyBuilderBuildFromFiling:
    """Tests for XbrlHierarchyBuilder.build_from_filing()."""

    def test_nonexistent_filing_returns_empty(self):
        """Building from nonexistent filing returns empty dict."""
        builder = XbrlHierarchyBuilder()
        result = builder.build_from_filing(Path('/nonexistent/path'))
        assert result == {}
        assert builder.last_error is not None


class TestXbrlHierarchyBuilderBuildFromLinkbase:
    """Tests for XbrlHierarchyBuilder.build_from_linkbase()."""

    def test_nonexistent_linkbase_returns_empty(self):
        """Building from nonexistent linkbase returns empty dict."""
        builder = XbrlHierarchyBuilder()
        result = builder.build_from_linkbase(Path('/nonexistent/linkbase.xml'))
        assert result == {}


# Integration test with real XBRL data (if available)
class TestXbrlHierarchyBuilderIntegration:
    """Integration tests with real XBRL data."""

    @pytest.fixture
    def plug_filing_path(self):
        """Path to PLUG XBRL filing (if available)."""
        path = Path('/home/user/map_pro/plug_xbrl_filings/PLUG_POWER_INC/filings/10-K/0001558370-25-002049')
        return path if path.exists() else None

    def test_build_from_real_filing(self, plug_filing_path):
        """Test building from real PLUG filing."""
        if plug_filing_path is None:
            pytest.skip("PLUG filing not available")

        builder = XbrlHierarchyBuilder()
        hierarchies = builder.build_from_filing(plug_filing_path)

        # Should find multiple hierarchies
        assert len(hierarchies) > 0

        # Should discover statement types
        assert len(builder.discovered_types) > 0

        # Build count should increase
        assert builder.build_count > 0

    def test_hierarchies_have_mat_acc_ids(self, plug_filing_path):
        """Test that built hierarchies have mat_acc_id."""
        if plug_filing_path is None:
            pytest.skip("PLUG filing not available")

        builder = XbrlHierarchyBuilder()
        hierarchies = builder.build_from_filing(plug_filing_path)

        # Check first hierarchy
        for key, root in list(hierarchies.items())[:1]:
            # Root should have mat_acc_id
            assert 'mat_acc_id' in root.metadata

            # Check some descendants
            for node in list(root.iter_preorder())[:5]:
                assert 'mat_acc_id' in node.metadata

    def test_discovers_main_statement_types(self, plug_filing_path):
        """Test that main statement types are discovered."""
        if plug_filing_path is None:
            pytest.skip("PLUG filing not available")

        builder = XbrlHierarchyBuilder()
        builder.build_from_filing(plug_filing_path)

        types = builder.discovered_types
        # Should discover at least some of the main types
        expected_types = {'BALANCE_SHEET', 'INCOME_STATEMENT', 'CASH_FLOW', 'EQUITY', 'OTHER'}
        assert len(types & expected_types) > 0
