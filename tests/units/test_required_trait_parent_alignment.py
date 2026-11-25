import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

pytest.importorskip("neo4j")

from lib.database.neo4j.Attributes import Neo4JAttributes


class FakeDriver:
    """Answers the exists-check and the required-trait owner query with canned data."""

    def __init__(self, owner_map=None, attribute_exists=False):
        self.calls = []
        self._owner_map = owner_map or {}
        self._attribute_exists = attribute_exists

    def execute_query(self, query=None, query_=None, **kwargs):
        q = " ".join((query if query is not None else query_).split())
        self.calls.append((q, kwargs))
        if "OPTIONAL MATCH (a:Attribute)-[:HAS_TRAIT]->(t:Trait" in q:
            tags = kwargs.get("required_trait_tags", [])
            return [[t, self._owner_map.get(t, [])] for t in tags]
        if "EXISTS" in q and "Attribute" in q:
            return [self._attribute_exists]
        return [True]


# trait tags follow the "<attribute_tag>:<value>" convention, so the owner is the prefix
OWNERS = {
    "att_compound:dmso": ["att_compound"],
    "att_treatment:heat": ["att_treatment"],
    "att_treatment:cold": ["att_treatment"],
    "att_organism:human": ["att_organism"],
}


class TestValidateRequiredTraitsForParents:
    def test_multiple_parents_each_with_required_trait_is_valid(self):
        driver = FakeDriver(OWNERS)
        attrs = Neo4JAttributes(driver)
        invalid = attrs.validate_required_traits_for_parents(
            parents=["att_compound", "att_treatment"],
            required_trait_tags=["att_compound:dmso", "att_treatment:heat"],
        )
        assert invalid == []

    def test_yes_no_yes_per_parent_is_valid(self):
        # att_treatment deliberately has no required trait (the "no" case)
        driver = FakeDriver(OWNERS)
        attrs = Neo4JAttributes(driver)
        invalid = attrs.validate_required_traits_for_parents(
            parents=["att_compound", "att_treatment", "att_organism"],
            required_trait_tags=["att_compound:dmso", "att_organism:human"],
        )
        assert invalid == []

    def test_required_trait_of_non_parent_attribute_is_invalid(self):
        driver = FakeDriver(OWNERS)
        attrs = Neo4JAttributes(driver)
        invalid = attrs.validate_required_traits_for_parents(
            parents=["att_compound"],
            required_trait_tags=["att_compound:dmso", "att_organism:human"],
        )
        assert invalid == ["att_organism:human"]

    def test_unknown_trait_is_invalid(self):
        driver = FakeDriver(OWNERS)
        attrs = Neo4JAttributes(driver)
        invalid = attrs.validate_required_traits_for_parents(
            parents=["att_compound"],
            required_trait_tags=["att_compound:does_not_exist"],
        )
        assert invalid == ["att_compound:does_not_exist"]

    def test_required_traits_without_any_parent_are_invalid(self):
        driver = FakeDriver(OWNERS)
        attrs = Neo4JAttributes(driver)
        invalid = attrs.validate_required_traits_for_parents(parents=[], required_trait_tags=["att_compound:dmso"])
        assert invalid == ["att_compound:dmso"]

    def test_empty_required_traits_are_valid(self):
        driver = FakeDriver(OWNERS)
        attrs = Neo4JAttributes(driver)
        assert attrs.validate_required_traits_for_parents(parents=["att_compound"], required_trait_tags=[]) == []
        assert driver.calls == []  # no query needed


class TestInsertUpdateValidation:
    def test_insert_rejects_required_trait_of_non_parent(self):
        driver = FakeDriver(OWNERS, attribute_exists=False)
        attrs = Neo4JAttributes(driver)
        with pytest.raises(ValueError, match="not traits of any of the parent"):
            attrs.insert(tag="att_concentration", text="Concentration",
                         parents=["att_compound"], required_trait_tags=["att_organism:human"])
        # no write query must have been issued
        assert not any("MERGE" in q for q, _ in driver.calls)

    def test_insert_accepts_yes_no_yes(self):
        driver = FakeDriver(OWNERS, attribute_exists=False)
        attrs = Neo4JAttributes(driver)
        ok = attrs.insert(tag="att_concentration", text="Concentration",
                          parents=["att_compound", "att_treatment"],
                          required_trait_tags=["att_compound:dmso"])
        assert ok is True
        write_calls = [q for q, _ in driver.calls if "MERGE" in q or "UNWIND" in q]
        assert len(write_calls) > 0

    def test_update_rejects_required_trait_of_non_parent_before_deleting_relations(self):
        driver = FakeDriver(OWNERS, attribute_exists=True)
        attrs = Neo4JAttributes(driver)
        with pytest.raises(ValueError, match="not traits of any of the parent"):
            attrs.update(tag="att_concentration", text="Concentration",
                         parents=["att_treatment"], required_trait_tags=["att_compound:dmso"])
        # validation must run before the relationship delete, so a rejected update keeps the old state
        assert not any("DELETE" in q for q, _ in driver.calls)

    def test_update_accepts_multiple_parents_with_mixed_required_traits(self):
        driver = FakeDriver(OWNERS, attribute_exists=True)
        attrs = Neo4JAttributes(driver)
        ok = attrs.update(tag="att_concentration", text="Concentration",
                          parents=["att_compound", "att_treatment", "att_organism"],
                          required_trait_tags=["att_compound:dmso", "att_organism:human"])
        assert ok is True


class TestGetRequiredTraitOwnerTags:
    def test_owner_query_maps_traits_to_attributes(self):
        driver = FakeDriver(OWNERS)
        attrs = Neo4JAttributes(driver)
        owners = attrs.get_required_trait_owner_tags(["att_compound:dmso", "att_organism:human", "unknown"])
        assert owners == {"att_compound:dmso": ["att_compound"], "att_organism:human": ["att_organism"], "unknown": []}
        query, params = driver.calls[0]
        assert "HAS_TRAIT" in query
        assert params["required_trait_tags"] == ["att_compound:dmso", "att_organism:human", "unknown"]
