import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.models.attributes import AttributeTree
from services.attribute_hierarchy import complete_or_validate_attribute_trees, resolve_trait_paths


MS_TYPE = "att_ms_type"
MS_NAME = "att_ms"
MS_TYPE_ORBITRAP = "att_ms_type:orbitrap"
MS_NAME_ECLIPSE = "att_ms:eclipse"


class TestResolveTraitPaths:
    def test_resolves_full_path_root_first(self):
        paths = resolve_trait_paths(
            MS_NAME,
            [MS_NAME_ECLIPSE],
            [MS_TYPE],
            {MS_NAME_ECLIPSE: [(MS_TYPE, MS_TYPE_ORBITRAP)]},
        )
        assert paths[MS_NAME_ECLIPSE] == [
            {"attribute_tag": MS_TYPE, "trait_tag": MS_TYPE_ORBITRAP},
            {"attribute_tag": MS_NAME, "trait_tag": MS_NAME_ECLIPSE},
        ]

    def test_omits_traits_without_implication(self):
        paths = resolve_trait_paths(MS_NAME, [MS_NAME_ECLIPSE], [MS_TYPE], {})
        assert paths == {}

    def test_omits_ambiguous_implications(self):
        paths = resolve_trait_paths(
            MS_NAME,
            [MS_NAME_ECLIPSE],
            [MS_TYPE],
            {MS_NAME_ECLIPSE: [(MS_TYPE, "att_ms_type:orbitrap"), (MS_TYPE, "att_ms_type:qtof")]},
        )
        assert paths == {}

    def test_omits_implications_of_other_attributes(self):
        paths = resolve_trait_paths(
            MS_NAME,
            [MS_NAME_ECLIPSE],
            [MS_TYPE],
            {MS_NAME_ECLIPSE: [("att_other", "att_other:trait")]},
        )
        assert paths == {}

    def test_empty_without_parent_chain(self):
        paths = resolve_trait_paths(MS_TYPE, [MS_TYPE_ORBITRAP], [], {MS_TYPE_ORBITRAP: [("att", "att:x")]})
        assert paths == {}

    def test_multi_level_chain_requires_every_level(self):
        implied = {
            "att_c:t": [("att_b", "att_b:t")],
            "att_b:t": [("att_a", "att_a:t")],
        }
        paths = resolve_trait_paths("att_c", ["att_c:t"], ["att_a", "att_b"], implied)
        assert paths["att_c:t"] == [
            {"attribute_tag": "att_a", "trait_tag": "att_a:t"},
            {"attribute_tag": "att_b", "trait_tag": "att_b:t"},
            {"attribute_tag": "att_c", "trait_tag": "att_c:t"},
        ]

    def test_multi_level_chain_omitted_when_level_missing(self):
        implied = {"att_c:t": [("att_b", "att_b:t")]}
        paths = resolve_trait_paths("att_c", ["att_c:t"], ["att_a", "att_b"], implied)
        assert paths == {}


class FakeAttributeHierarchyDB:
    def __init__(self, parents, implied):
        self.parents = parents
        self.implied = implied

    def get_parents(self, tag):
        return self.parents.get(tag, [])

    def get_trait_implied_parent_traits(self, trait_tags):
        return {tag: self.implied.get(tag, []) for tag in trait_tags}


def make_db(parents=None, implied=None):
    return FakeAttributeHierarchyDB(parents or {}, implied or {})


def trait(tag, children=None):
    return AttributeTree(tag=tag, type="trait", children=children or [])


def attribute(tag, children=None):
    return AttributeTree(tag=tag, type="attribute", children=children or [])


class TestCompleteOrValidateAttributeTrees:
    def test_auto_completes_missing_parent(self):
        db = make_db(parents={MS_NAME: [MS_TYPE]}, implied={MS_NAME_ECLIPSE: [(MS_TYPE, MS_TYPE_ORBITRAP)]})
        trees = [attribute(MS_NAME, [trait(MS_NAME_ECLIPSE)])]
        result = complete_or_validate_attribute_trees(db.get_parents, db.get_trait_implied_parent_traits, trees)
        assert len(result) == 1
        parent = result[0]
        assert parent.tag == MS_TYPE
        assert parent.children[0].tag == MS_TYPE_ORBITRAP
        child = parent.children[0].children[0]
        assert child.tag == MS_NAME
        assert child.children[0].tag == MS_NAME_ECLIPSE

    def test_merges_into_existing_parent_root(self):
        db = make_db(parents={MS_NAME: [MS_TYPE]}, implied={MS_NAME_ECLIPSE: [(MS_TYPE, MS_TYPE_ORBITRAP)]})
        trees = [
            attribute(MS_TYPE, [trait(MS_TYPE_ORBITRAP)]),
            attribute(MS_NAME, [trait(MS_NAME_ECLIPSE)]),
        ]
        result = complete_or_validate_attribute_trees(db.get_parents, db.get_trait_implied_parent_traits, trees)
        assert [t.tag for t in result] == [MS_TYPE]
        orbitrap = result[0].children[0]
        assert orbitrap.tag == MS_TYPE_ORBITRAP
        assert [c.tag for c in orbitrap.children] == [MS_NAME]
        assert orbitrap.children[0].children[0].tag == MS_NAME_ECLIPSE

    def test_adds_missing_parent_trait_to_existing_parent_root(self):
        db = make_db(parents={MS_NAME: [MS_TYPE]}, implied={MS_NAME_ECLIPSE: [(MS_TYPE, MS_TYPE_ORBITRAP)]})
        trees = [
            attribute(MS_TYPE, [trait("att_ms_type:qtof")]),
            attribute(MS_NAME, [trait(MS_NAME_ECLIPSE)]),
        ]
        result = complete_or_validate_attribute_trees(db.get_parents, db.get_trait_implied_parent_traits, trees)
        assert [t.tag for t in result] == [MS_TYPE]
        trait_tags = [c.tag for c in result[0].children]
        assert trait_tags == ["att_ms_type:qtof", MS_TYPE_ORBITRAP]

    def test_rejects_ambiguous_implication(self):
        db = make_db(
            parents={MS_NAME: [MS_TYPE]},
            implied={MS_NAME_ECLIPSE: [(MS_TYPE, "att_ms_type:orbitrap"), (MS_TYPE, "att_ms_type:qtof")]},
        )
        trees = [attribute(MS_NAME, [trait(MS_NAME_ECLIPSE)])]
        with pytest.raises(ValueError, match="unambiguously"):
            complete_or_validate_attribute_trees(db.get_parents, db.get_trait_implied_parent_traits, trees)

    def test_rejects_child_without_implication(self):
        db = make_db(parents={MS_NAME: [MS_TYPE]})
        trees = [attribute(MS_NAME, [trait(MS_NAME_ECLIPSE)])]
        with pytest.raises(ValueError, match="without its parent"):
            complete_or_validate_attribute_trees(db.get_parents, db.get_trait_implied_parent_traits, trees)

    def test_rejects_child_attribute_without_traits(self):
        db = make_db(parents={MS_NAME: [MS_TYPE]})
        trees = [attribute(MS_NAME)]
        with pytest.raises(ValueError, match="parent attribute and trait"):
            complete_or_validate_attribute_trees(db.get_parents, db.get_trait_implied_parent_traits, trees)

    def test_rejects_nested_child_below_wrong_parent(self):
        db = make_db(parents={MS_NAME: [MS_TYPE]})
        wrong_parent = attribute("att_other", [trait("att_other:t", [attribute(MS_NAME, [trait(MS_NAME_ECLIPSE)])])])
        with pytest.raises(ValueError, match="below one of its parent"):
            complete_or_validate_attribute_trees(db.get_parents, db.get_trait_implied_parent_traits, [wrong_parent])

    def test_passes_correctly_nested_child_through(self):
        db = make_db(
            parents={MS_NAME: [MS_TYPE]},
            implied={MS_NAME_ECLIPSE: [(MS_TYPE, MS_TYPE_ORBITRAP)]},
        )
        nested = attribute(MS_TYPE, [trait(MS_TYPE_ORBITRAP, [attribute(MS_NAME, [trait(MS_NAME_ECLIPSE)])])])
        result = complete_or_validate_attribute_trees(db.get_parents, db.get_trait_implied_parent_traits, [nested])
        assert result == [nested]

    def test_passes_parentless_attributes_through(self):
        db = make_db()
        trees = [attribute("att_organ", [trait("att_organ:heart")])]
        result = complete_or_validate_attribute_trees(db.get_parents, db.get_trait_implied_parent_traits, trees)
        assert result == trees
