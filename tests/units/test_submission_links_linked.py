import json
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

pytest.importorskip("neo4j")
pytest.importorskip("fastapi")

from lib.database.neo4j.Submission import Neo4JSubmissions
from config.models.submissions.submissions import NewSubmissionModel


class FakeDriver:
    """Records queries; returns canned post-transformer values for read queries."""

    def __init__(self, records=None):
        self.calls = []
        self._records = records or []

    def execute_query(self, query, **kwargs):
        q = " ".join(query.split())
        self.calls.append((q, kwargs))
        return self._records


def make_submissions(records=None):
    driver = FakeDriver(records)
    return Neo4JSubmissions(driver, meta=None, proteomes=None, condition_applications=None), driver


def test_set_links_stores_json_property():
    subs, driver = make_submissions(records=["subA"])
    links = [{"id": "abc12", "url": "https://example.org/protocol", "comment": "ELN entry"}]
    assert subs.set_links("subA", links) is True
    q, kwargs = driver.calls[-1]
    assert "SET submission.links = $links_json" in q
    assert kwargs["routing_"] == "w"
    assert kwargs["tag"] == "subA"
    assert json.loads(kwargs["links_json"]) == links


def test_set_links_returns_false_when_submission_missing():
    subs, driver = make_submissions(records=[])
    assert subs.set_links("missing", []) is False


def test_get_links_parses_json():
    links = [{"id": "abc12", "url": "https://example.org", "comment": None}]
    subs, driver = make_submissions(records=[json.dumps(links)])
    assert subs.get_links("subA") == links
    q, kwargs = driver.calls[-1]
    assert kwargs["routing_"] == "r"


def test_get_links_empty_cases():
    subs, _ = make_submissions(records=[None])
    assert subs.get_links("subA") == []
    subs, _ = make_submissions(records=[])
    assert subs.get_links("subA") == []


def test_set_linked_submission_creates_relationship_and_property():
    subs, driver = make_submissions(records=["subA"])
    assert subs.set_linked_submission("subA", "subB", user_tag="user1") is True
    q, kwargs = driver.calls[-1]
    assert "MERGE (submission)-[r:LINKED_TO]->(linked)" in q
    assert "SET submission.linked_submission_tag = $linked_submission_tag" in q
    assert kwargs["routing_"] == "w"
    assert kwargs["tag"] == "subA"
    assert kwargs["linked_submission_tag"] == "subB"


def test_set_linked_submission_false_when_missing():
    subs, _ = make_submissions(records=[])
    assert subs.set_linked_submission("subA", "subB") is False


def test_get_linked_submission_tag():
    subs, _ = make_submissions(records=["subB"])
    assert subs.get_linked_submission_tag("subA") == "subB"
    subs, _ = make_submissions(records=[None])
    assert subs.get_linked_submission_tag("subA") is None
    subs, _ = make_submissions(records=[])
    assert subs.get_linked_submission_tag("subA") is None


def test_new_submission_model_has_optional_linked_submission_tag():
    field = NewSubmissionModel.model_fields["linked_submission_tag"]
    assert field.default is None
    assert field.is_required() is False
