import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.models.attributes import AttributeTree
from services.attribute_hierarchy import validate_attribute_trees


MS_TYPE = "att_ms_type"
MS_NAME = "att_ms"
MS_TYPE_ORBITRAP = "att_ms_type:orbitrap"
MS_NAME_ECLIPSE = "att_ms:eclipse"


class FakeAttributeHierarchyDB:
    def __init__(self, parents):
        self.parents = parents

    def get_parents(self, tag):
        return self.parents.get(tag, [])


def trait(tag, children=None):
    return AttributeTree(tag=tag, type="trait", children=children or [])


def attribute(tag, children=None):
    return AttributeTree(tag=tag, type="attribute", children=children or [])


class TestValidateAttributeTrees:
    def test_passes_parentless_attributes_through(self):
        db = FakeAttributeHierarchyDB({})
        trees = [attribute("att_organ", [trait("att_organ:heart")])]
        assert validate_attribute_trees(db.get_parents, trees) == trees

    def test_passes_root_level_child_attribute_through(self):
        db = FakeAttributeHierarchyDB({MS_NAME: [MS_TYPE]})
        trees = [attribute(MS_NAME, [trait(MS_NAME_ECLIPSE)])]
        assert validate_attribute_trees(db.get_parents, trees) == trees

    def test_passes_correctly_nested_child_through(self):
        db = FakeAttributeHierarchyDB({MS_NAME: [MS_TYPE]})
        nested = attribute(MS_TYPE, [trait(MS_TYPE_ORBITRAP, [attribute(MS_NAME, [trait(MS_NAME_ECLIPSE)])])])
        assert validate_attribute_trees(db.get_parents, [nested]) == [nested]

    def test_rejects_nested_child_below_wrong_parent(self):
        db = FakeAttributeHierarchyDB({MS_NAME: [MS_TYPE]})
        wrong_parent = attribute("att_other", [trait("att_other:t", [attribute(MS_NAME, [trait(MS_NAME_ECLIPSE)])])])
        with pytest.raises(ValueError, match="below one of its parent"):
            validate_attribute_trees(db.get_parents, [wrong_parent])

    def test_rejects_deeply_nested_child_below_wrong_parent(self):
        db = FakeAttributeHierarchyDB({"att_c": ["att_b"]})
        tree = attribute(
            "att_a",
            [trait("att_a:t", [attribute("att_x", [trait("att_x:t", [attribute("att_c", [trait("att_c:t")])])])])],
        )
        with pytest.raises(ValueError, match="'att_c' must be selected below"):
            validate_attribute_trees(db.get_parents, [tree])
