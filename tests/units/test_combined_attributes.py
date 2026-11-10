import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

neo4j = pytest.importorskip("neo4j")

from lib.database.neo4j.Attributes import Neo4JAttributes


class FakeDriver:
    """Returns a pre-scripted result per execute_query call."""

    def __init__(self, results):
        self.results = list(results)
        self.queries = []

    def execute_query(self, query=None, *args, **kwargs):
        self.queries.append(query if query is not None else kwargs.get("query_"))
        return self.results.pop(0)


class TestAttributeCombinedNodes:
    def test_combined_attribute_gets_required_model_defaults(self):
        driver = FakeDriver([
            [True],  # exists
            [{"tag": "att_biomolecule__att_irradiance_type", "combined": True, "name": "att_biomolecule__att_irradiance_type"}],
        ])
        attributes = Neo4JAttributes(driver)
        attribute = attributes.attribute(tag="att_biomolecule__att_irradiance_type")
        assert attribute.tag == "att_biomolecule__att_irradiance_type"
        assert attribute.text == "att_biomolecule__att_irradiance_type"
        assert attribute.allow_input is False
        assert attribute.priority == 500

    def test_regular_attribute_unchanged(self):
        driver = FakeDriver([
            [True],  # exists
            [{"tag": "att_ms_type", "text": "Mass Spectrometer Type", "allow_input": False, "priority": 720}],
        ])
        attributes = Neo4JAttributes(driver)
        attribute = attributes.attribute(tag="att_ms_type")
        assert attribute.text == "Mass Spectrometer Type"
        assert attribute.priority == 720

    def test_find_attribute_excludes_combined_attributes(self):
        driver = FakeDriver([[["att_ms_type"]]])
        attributes = Neo4JAttributes(driver)
        attributes.find_attribute(search_string="ms", attribute_groups=["mandatory"])
        assert "coalesce(a.combined, false) = false" in driver.queries[0]

    def test_get_excludes_combined_attributes(self):
        driver = FakeDriver([[["att_ms_type"]]])
        attributes = Neo4JAttributes(driver)
        attributes.get()
        assert "coalesce(a.combined, false) = false" in driver.queries[0]
