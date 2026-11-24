import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

pytest.importorskip("neo4j")
pytest.importorskip("fastapi")

from config.models.attributes import AttributeTree
from lib.database.neo4j.ConditionApplications import Neo4JConditionApplications


class FakeAttributes:
    def __init__(self, allow_input_tags=()):
        self.allow_input_tags = set(allow_input_tags)

    def allow_input(self, tag):
        return tag in self.allow_input_tags

    def get_trait_text(self, tag):
        return {"att_mouse_id:default": "Mouse ID", "att_compound:dmso": "DMSO", "mM": "mM"}.get(tag, tag)


class FakeProteins:
    def get_gene_name(self, tag):
        return tag


class FakeDriver:
    """Records queries; returns canned post-transformer values for read queries."""

    _has_values = False

    def __init__(self, records=None):
        self.calls = []
        self._records = records or []

    def execute_query(self, query, **kwargs):
        q = " ".join(query.split())
        self.calls.append((q, kwargs))
        if "COUNT(cv)" in q:
            return [self._has_values]
        return self._records


def make_ca(allow_input_tags=(), records=None, has_values=False):
    driver = FakeDriver(records)
    driver._has_values = has_values
    return Neo4JConditionApplications(driver, FakeAttributes(allow_input_tags), FakeProteins()), driver


def attribute(tag, children=None, value=None):
    return AttributeTree(tag=tag, type="attribute", value=value, children=children or [])


def trait(tag, children=None, value=None):
    return AttributeTree(tag=tag, type="trait", value=value, children=children or [])


class TestInsertParentAttributeValue:
    def test_value_on_parent_attribute_trait_is_stored_on_ca(self):
        ca, driver = make_ca(allow_input_tags={"att_mouse_id"})
        tree = attribute("att_mouse_id", [trait("att_mouse_id:default", value="Mouse-42")])
        tag = ca.insert(condition_application=tree)
        assert tag is not None
        write_calls = [c for c in driver.calls if "MERGE (ca:ConditionApplication" in c[0]]
        assert len(write_calls) == 1
        query, params = write_calls[0]
        assert "ca.value = $value" in query
        assert params["value"] == "Mouse-42"
        assert params["attribute_tag"] == "att_mouse_id"
        assert params["child_tag"] == "att_mouse_id:default"

    def test_different_values_produce_distinct_condition_applications(self):
        ca, _ = make_ca(allow_input_tags={"att_mouse_id"})
        tag_a = ca.insert(condition_application=attribute("att_mouse_id", [trait("t", value="A")]))
        tag_b = ca.insert(condition_application=attribute("att_mouse_id", [trait("t", value="B")]))
        assert tag_a != tag_b

    def test_empty_value_on_parent_allow_input_trait_is_skipped_not_crash(self):
        ca, driver = make_ca(allow_input_tags={"att_mouse_id"})
        tree = attribute("att_mouse_id", [trait("att_mouse_id:default")])  # no value entered
        assert ca.insert(condition_application=tree) is None
        assert not [c for c in driver.calls if "MERGE" in c[0]]

    def test_trait_without_value_on_regular_attribute_is_still_inserted(self):
        ca, driver = make_ca(allow_input_tags=set())
        tree = attribute("att_compound", [trait("att_compound:dmso")])
        tag = ca.insert(condition_application=tree)
        assert tag is not None
        write_calls = [c for c in driver.calls if "MERGE (ca:ConditionApplication" in c[0]]
        assert len(write_calls) == 1
        assert "ca.value" not in write_calls[0][0]

    def test_nested_child_attribute_value_is_stored_on_condition_value(self):
        ca, driver = make_ca(allow_input_tags=set())
        tree = attribute("att_compound", [trait("att_compound:dmso", [
            attribute("att_concentration", [trait("mM", value=2)])
        ])])
        ca.insert(condition_application=tree)
        cv_calls = [c for c in driver.calls if "MERGE (cv:ConditionValue" in c[0]]
        assert len(cv_calls) == 1
        assert cv_calls[0][1]["value"] == 2
        assert cv_calls[0][1]["attribute_tag"] == "att_concentration"


class TestConditionApplicationText:
    def test_get_text_includes_parent_attribute_trait_value(self):
        record = [[{"label": "ConditionApplication", "tag": "ca1",
                    "attribute_tag": "att_mouse_id", "trait_tag": "att_mouse_id:default",
                    "value": "Mouse-42"}]]
        ca, _ = make_ca(allow_input_tags={"att_mouse_id"}, records=[record], has_values=False)
        text = ca.get_text("ca1")
        assert "Mouse-42" in text
        assert "Mouse ID" in text

    def test_get_text_includes_value_and_nested_children(self):
        ca_map = {"label": "ConditionApplication", "tag": "ca2", "trait_tag": "att_compound:dmso",
                  "attribute_tag": "att_compound", "protein_tag": None, "value": "10 mg"}
        cv_map = {"label": "ConditionValue", "tag": "cv1", "trait_tag": "mM",
                  "attribute_tag": "att_concentration", "protein_tag": None, "value": 2}
        records = [[[ca_map, cv_map]]]
        ca, _ = make_ca(records=records, has_values=True)
        text = ca.get_text("ca2")
        assert "10 mg" in text
        assert "DMSO" in text
        assert "2" in text
        assert "mM" in text
