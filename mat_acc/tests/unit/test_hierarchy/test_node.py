# Path: mat_acc/tests/unit/test_hierarchy/test_node.py
"""
Tests for hierarchy node module.
"""

import pytest
import sys
from decimal import Decimal
from pathlib import Path

# Add mat_acc to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from process.hierarchy.constants import NodeType
from process.hierarchy.node import (
    HierarchyNode,
    create_root_node,
    create_abstract_node,
    create_line_item_node,
)


class TestHierarchyNodeCreation:
    """Test HierarchyNode creation."""

    def test_create_basic_node(self):
        """Can create a basic node."""
        node = HierarchyNode(concept="test:Concept", label="Test Label")
        assert node.concept == "test:Concept"
        assert node.label == "Test Label"

    def test_default_node_type(self):
        """Default node type is LINE_ITEM."""
        node = HierarchyNode(concept="test", label="test")
        assert node.node_type == NodeType.LINE_ITEM

    def test_default_values_are_none(self):
        """Default value-related attributes are None."""
        node = HierarchyNode(concept="test", label="test")
        assert node.value is None
        assert node.decimals is None
        assert node.unit is None

    def test_create_with_value(self):
        """Can create node with value."""
        node = HierarchyNode(
            concept="test",
            label="test",
            value=Decimal("1234.56"),
            unit="USD"
        )
        assert node.value == Decimal("1234.56")
        assert node.unit == "USD"


class TestNodeRelationships:
    """Test node parent/child relationships."""

    def test_add_child(self):
        """Can add a child node."""
        parent = HierarchyNode(concept="parent", label="Parent")
        child = HierarchyNode(concept="child", label="Child")

        parent.add_child(child)

        assert child in parent.children
        assert child.parent is parent

    def test_add_child_sets_depth(self):
        """Adding child sets correct depth."""
        parent = HierarchyNode(concept="parent", label="Parent")
        parent.depth = 0
        child = HierarchyNode(concept="child", label="Child")

        parent.add_child(child)

        assert child.depth == 1

    def test_cannot_add_self_as_child(self):
        """Cannot add node as its own child."""
        node = HierarchyNode(concept="test", label="test")

        with pytest.raises(ValueError):
            node.add_child(node)

    def test_remove_child(self):
        """Can remove a child node."""
        parent = HierarchyNode(concept="parent", label="Parent")
        child = HierarchyNode(concept="child", label="Child")

        parent.add_child(child)
        result = parent.remove_child(child)

        assert result is True
        assert child not in parent.children
        assert child.parent is None

    def test_remove_nonexistent_child(self):
        """Removing non-existent child returns False."""
        parent = HierarchyNode(concept="parent", label="Parent")
        other = HierarchyNode(concept="other", label="Other")

        result = parent.remove_child(other)

        assert result is False


class TestNodeProperties:
    """Test node property methods."""

    def test_is_root_true_for_parentless(self):
        """is_root is True for parentless nodes."""
        node = HierarchyNode(concept="root", label="Root")
        assert node.is_root is True

    def test_is_root_false_for_child(self):
        """is_root is False for child nodes."""
        parent = HierarchyNode(concept="parent", label="Parent")
        child = HierarchyNode(concept="child", label="Child")
        parent.add_child(child)

        assert child.is_root is False

    def test_is_leaf_true_for_childless(self):
        """is_leaf is True for childless nodes."""
        node = HierarchyNode(concept="leaf", label="Leaf")
        assert node.is_leaf is True

    def test_is_leaf_false_with_children(self):
        """is_leaf is False for nodes with children."""
        parent = HierarchyNode(concept="parent", label="Parent")
        child = HierarchyNode(concept="child", label="Child")
        parent.add_child(child)

        assert parent.is_leaf is False

    def test_has_value_true_with_value(self):
        """has_value is True when value is set."""
        node = HierarchyNode(concept="test", label="test", value=Decimal("100"))
        assert node.has_value is True

    def test_has_value_false_without_value(self):
        """has_value is False when value is None."""
        node = HierarchyNode(concept="test", label="test")
        assert node.has_value is False

    def test_is_total_for_total_type(self):
        """is_total is True for TOTAL node type."""
        node = HierarchyNode(concept="test", label="test", node_type=NodeType.TOTAL)
        assert node.is_total is True

    def test_is_total_for_total_label(self):
        """is_total is True when label contains 'total'."""
        node = HierarchyNode(concept="test", label="Total Assets")
        assert node.is_total is True


class TestNodeNavigation:
    """Test node navigation methods."""

    def test_siblings_returns_other_children(self):
        """siblings returns other children of same parent."""
        parent = HierarchyNode(concept="parent", label="Parent")
        child1 = HierarchyNode(concept="child1", label="Child 1")
        child2 = HierarchyNode(concept="child2", label="Child 2")
        child3 = HierarchyNode(concept="child3", label="Child 3")

        parent.add_child(child1)
        parent.add_child(child2)
        parent.add_child(child3)

        siblings = child2.siblings

        assert child1 in siblings
        assert child3 in siblings
        assert child2 not in siblings

    def test_ancestors_returns_path_to_root(self):
        """ancestors returns all nodes from parent to root."""
        root = HierarchyNode(concept="root", label="Root")
        middle = HierarchyNode(concept="middle", label="Middle")
        leaf = HierarchyNode(concept="leaf", label="Leaf")

        root.add_child(middle)
        middle.add_child(leaf)

        ancestors = leaf.ancestors

        assert middle in ancestors
        assert root in ancestors
        assert len(ancestors) == 2

    def test_descendants_returns_all_children(self):
        """descendants returns all nodes below."""
        root = HierarchyNode(concept="root", label="Root")
        child1 = HierarchyNode(concept="child1", label="Child 1")
        child2 = HierarchyNode(concept="child2", label="Child 2")
        grandchild = HierarchyNode(concept="grandchild", label="Grandchild")

        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild)

        descendants = root.descendants

        assert child1 in descendants
        assert child2 in descendants
        assert grandchild in descendants
        assert len(descendants) == 3

    def test_root_property_returns_root(self):
        """root property returns the root node."""
        root = HierarchyNode(concept="root", label="Root")
        middle = HierarchyNode(concept="middle", label="Middle")
        leaf = HierarchyNode(concept="leaf", label="Leaf")

        root.add_child(middle)
        middle.add_child(leaf)

        assert leaf.root is root

    def test_path_returns_path_from_root(self):
        """path returns nodes from root to self."""
        root = HierarchyNode(concept="root", label="Root")
        middle = HierarchyNode(concept="middle", label="Middle")
        leaf = HierarchyNode(concept="leaf", label="Leaf")

        root.add_child(middle)
        middle.add_child(leaf)

        path = leaf.path

        assert path == [root, middle, leaf]


class TestNodeIteration:
    """Test node iteration methods."""

    def test_iter_preorder(self):
        """iter_preorder visits parent before children."""
        root = HierarchyNode(concept="root", label="Root")
        child1 = HierarchyNode(concept="child1", label="Child 1")
        child2 = HierarchyNode(concept="child2", label="Child 2")

        root.add_child(child1)
        root.add_child(child2)

        nodes = list(root.iter_preorder())

        assert nodes[0] is root
        assert len(nodes) == 3

    def test_iter_leaves(self):
        """iter_leaves returns only leaf nodes."""
        root = HierarchyNode(concept="root", label="Root")
        middle = HierarchyNode(concept="middle", label="Middle")
        leaf1 = HierarchyNode(concept="leaf1", label="Leaf 1")
        leaf2 = HierarchyNode(concept="leaf2", label="Leaf 2")

        root.add_child(middle)
        middle.add_child(leaf1)
        root.add_child(leaf2)

        leaves = list(root.iter_leaves())

        assert leaf1 in leaves
        assert leaf2 in leaves
        assert root not in leaves
        assert middle not in leaves

    def test_iter_with_values(self):
        """iter_with_values returns only nodes with values."""
        root = HierarchyNode(concept="root", label="Root")
        no_value = HierarchyNode(concept="abstract", label="Abstract")
        with_value = HierarchyNode(concept="item", label="Item", value=Decimal("100"))

        root.add_child(no_value)
        root.add_child(with_value)

        valued_nodes = list(root.iter_with_values())

        assert with_value in valued_nodes
        assert no_value not in valued_nodes


class TestNodeSearch:
    """Test node search methods."""

    def test_find_by_concept(self):
        """find_by_concept finds node by concept name."""
        root = HierarchyNode(concept="root", label="Root")
        child = HierarchyNode(concept="us-gaap:Assets", label="Assets")
        root.add_child(child)

        found = root.find_by_concept("us-gaap:Assets")

        assert found is child

    def test_find_by_concept_not_found(self):
        """find_by_concept returns None when not found."""
        root = HierarchyNode(concept="root", label="Root")

        found = root.find_by_concept("nonexistent")

        assert found is None

    def test_find_by_label(self):
        """find_by_label finds node by label."""
        root = HierarchyNode(concept="root", label="Root")
        child = HierarchyNode(concept="assets", label="Total Assets")
        root.add_child(child)

        found = root.find_by_label("total assets")

        assert found is child

    def test_find_totals(self):
        """find_totals returns all total nodes."""
        root = HierarchyNode(concept="root", label="Root")
        total1 = HierarchyNode(concept="t1", label="Total Assets")
        total2 = HierarchyNode(concept="t2", label="Net Income")
        not_total = HierarchyNode(concept="item", label="Cash")

        root.add_child(total1)
        root.add_child(total2)
        root.add_child(not_total)

        totals = root.find_totals()

        assert total1 in totals
        assert total2 in totals
        assert not_total not in totals


class TestNodeStatistics:
    """Test node statistics methods."""

    def test_child_count(self):
        """child_count returns number of direct children."""
        parent = HierarchyNode(concept="parent", label="Parent")
        for i in range(5):
            parent.add_child(HierarchyNode(concept=f"child{i}", label=f"Child {i}"))

        assert parent.child_count == 5

    def test_descendant_count(self):
        """descendant_count returns total descendants."""
        root = HierarchyNode(concept="root", label="Root")
        child = HierarchyNode(concept="child", label="Child")
        grandchild = HierarchyNode(concept="grandchild", label="Grandchild")

        root.add_child(child)
        child.add_child(grandchild)

        assert root.descendant_count == 2

    def test_max_depth(self):
        """max_depth returns deepest node depth."""
        root = HierarchyNode(concept="root", label="Root")
        root.depth = 0
        child = HierarchyNode(concept="child", label="Child")
        grandchild = HierarchyNode(concept="grandchild", label="Grandchild")

        root.add_child(child)
        child.add_child(grandchild)

        assert root.max_depth == 2


class TestNodeConversion:
    """Test node conversion methods."""

    def test_to_dict(self):
        """to_dict converts node to dictionary."""
        node = HierarchyNode(
            concept="us-gaap:Assets",
            label="Total Assets",
            value=Decimal("1000000"),
            node_type=NodeType.TOTAL
        )

        d = node.to_dict(include_children=False)

        assert d['concept'] == "us-gaap:Assets"
        assert d['label'] == "Total Assets"
        assert d['value'] == "1000000"
        assert d['node_type'] == "total"

    def test_to_text(self):
        """to_text converts subtree to text."""
        root = HierarchyNode(concept="root", label="Balance Sheet")
        root.depth = 0
        child = HierarchyNode(concept="child", label="Assets", value=Decimal("100"))

        root.add_child(child)

        text = root.to_text()

        assert "Balance Sheet" in text
        assert "Assets" in text
        assert "100" in text


class TestFactoryFunctions:
    """Test node factory functions."""

    def test_create_root_node(self):
        """create_root_node creates a root node."""
        root = create_root_node(label="Balance Sheet")

        assert root.label == "Balance Sheet"
        assert root.node_type == NodeType.ROOT
        assert root.depth == 0

    def test_create_abstract_node(self):
        """create_abstract_node creates an abstract node."""
        node = create_abstract_node(concept="us-gaap:AssetsAbstract", label="Assets")

        assert node.node_type == NodeType.ABSTRACT
        assert node.concept == "us-gaap:AssetsAbstract"

    def test_create_line_item_node(self):
        """create_line_item_node creates a line item node."""
        node = create_line_item_node(
            concept="us-gaap:Cash",
            label="Cash",
            value=Decimal("50000"),
            unit="USD"
        )

        assert node.node_type == NodeType.LINE_ITEM
        assert node.value == Decimal("50000")
        assert node.unit == "USD"
