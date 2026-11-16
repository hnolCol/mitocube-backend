"""Tests for the user-level consortium membership and the membership request pattern.

The tests use a scripted driver stub so no database is required: they pin down
the graph patterns the consortium class must use (direct user membership,
head auto-join on group add, eligibility and blocking checks) and the control
flow of the membership request lifecycle.
"""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from tests.conftest import *  # noqa: F401,F403 - sets the test env vars

import pytest


@pytest.fixture(autouse=True)
def no_scope_cache(monkeypatch):
    """The consortium class invalidates all cached scopes on writes; without a
    running cache runtime this would fail, so the invalidation is stubbed."""
    import lib.database.neo4j.Consortium as consortium_module
    monkeypatch.setattr(consortium_module, "invalidate_all_cached_scopes", lambda: 0)


class ScriptedDriver:
    """Neo4j driver stub that records queries and returns scripted results.

    Results are matched by the first substring found in the query."""
    def __init__(self, responses=None):
        # list of (substring, result) - first match wins; default [True]
        self.responses = responses or []
        self.queries = []

    def execute_query(self, query, *args, **kwargs):
        self.queries.append(query)
        for substring, result in self.responses:
            if substring in query:
                return result
        return [True]


def make_db(driver):
    from lib.database.neo4j.Consortium import Neo4JConsortium
    db = Neo4JConsortium.__new__(Neo4JConsortium)
    db._driver = driver
    db.exists = lambda tag: True
    return db


class TestInsertGroupsJoinsHeads:
    def test_insert_groups_joins_heads_as_members(self):
        driver = ScriptedDriver()
        db = make_db(driver)
        db.insert_groups(tag="cons-1", group_tags=["rg-1"], user_tag="curator-1")
        head_join = [q for q in driver.queries if "MATCH (head:User)-[:HEAD_OF]->(rg)" in q]
        assert len(head_join) == 1
        assert "MERGE (head)-[m:MEMBER_OF]->(c)" in head_join[0]
        assert "m.origin = 'head'" in head_join[0]

    def test_insert_groups_keeps_group_eligibility_relation(self):
        driver = ScriptedDriver()
        db = make_db(driver)
        db.insert_groups(tag="cons-1", group_tags=["rg-1"])
        assert any("MERGE (c)<-[r:MEMBER_OF]-(rg)" in q for q in driver.queries)


class TestUserMembershipEligibility:
    def test_insert_users_rejects_ineligible_user(self):
        driver = ScriptedDriver(responses=[("RETURN EXISTS {", [False])])
        db = make_db(driver)
        with pytest.raises(ValueError, match="not a member of an eligible research group"):
            db.insert_users(tag="cons-1", user_tags=["u-1"], user_tag="curator-1")

    def test_insert_users_accepts_eligible_user(self):
        driver = ScriptedDriver(responses=[("RETURN EXISTS {", [True])])
        db = make_db(driver)
        db.insert_users(tag="cons-1", user_tags=["u-1"], user_tag="curator-1")
        insert = [q for q in driver.queries if "MERGE (u)-[m:MEMBER_OF]->(c)" in q]
        assert len(insert) == 1
        assert "m.origin = 'manual'" in insert[0]

    def test_remove_users_blocked_by_dependent_members(self):
        driver = ScriptedDriver(responses=[("RETURN DISTINCT d.tag", ["u-2", "u-3"])])
        db = make_db(driver)
        with pytest.raises(ValueError, match="u-2, u-3"):
            db.remove_users(tag="cons-1", user_tags=["pi-1"])

    def test_remove_users_deletes_membership_when_unblocked(self):
        driver = ScriptedDriver(responses=[("RETURN DISTINCT d.tag", [])])
        db = make_db(driver)
        db.remove_users(tag="cons-1", user_tags=["u-1"])
        assert any("DELETE m" in q for q in driver.queries)

    def test_remove_groups_blocked_by_dependent_members(self):
        driver = ScriptedDriver(responses=[("RETURN DISTINCT d.tag", ["u-2"])])
        db = make_db(driver)
        with pytest.raises(ValueError, match="u-2"):
            db.remove_groups(tag="cons-1", group_tags=["rg-1"])

    def test_remove_groups_cleans_up_head_membership(self):
        driver = ScriptedDriver(responses=[("RETURN DISTINCT d.tag", [])])
        db = make_db(driver)
        db.remove_groups(tag="cons-1", group_tags=["rg-1"])
        cleanup = [q for q in driver.queries if "m.origin = 'head'" in q and "DELETE m" in q]
        assert len(cleanup) == 1


class TestMembershipRequests:
    def test_insert_membership_request_rejects_unknown_kind(self):
        db = make_db(ScriptedDriver())
        with pytest.raises(ValueError, match="Invalid membership request kind"):
            db.insert_membership_request("cons-1", "u-1", kind="invite", requested_by="pi-1")

    def test_insert_membership_request_creates_pending_relation(self):
        driver = ScriptedDriver()
        db = make_db(driver)
        assert db.insert_membership_request("cons-1", "u-1", kind="add", requested_by="pi-1") is True
        create = [q for q in driver.queries if "MEMBERSHIP_REQUEST" in q]
        assert len(create) == 1
        assert "r.status = 'pending'" in create[0]
        assert "r.kind = $kind" in create[0]

    def test_approve_add_request_creates_membership(self):
        driver = ScriptedDriver(responses=[
            ("RETURN r.kind", ["add"]),
            ("RETURN EXISTS {", [True]),
        ])
        db = make_db(driver)
        assert db.approve_membership_request("cons-1", "u-1", decided_by="curator-1") is True
        assert any("MERGE (u)-[m:MEMBER_OF]->(c)" in q for q in driver.queries)
        assert any("DELETE r" in q for q in driver.queries)

    def test_approve_remove_request_deletes_membership(self):
        driver = ScriptedDriver(responses=[("RETURN r.kind", ["remove"])])
        db = make_db(driver)
        assert db.approve_membership_request("cons-1", "u-1", decided_by="curator-1") is True
        assert any("DELETE m" in q for q in driver.queries)

    def test_approve_add_request_rejects_ineligible_user(self):
        driver = ScriptedDriver(responses=[
            ("RETURN r.kind", ["add"]),
            ("RETURN EXISTS {", [False]),
        ])
        db = make_db(driver)
        with pytest.raises(ValueError, match="not eligible"):
            db.approve_membership_request("cons-1", "u-1", decided_by="curator-1")

    def test_approve_without_pending_request_fails(self):
        driver = ScriptedDriver(responses=[("RETURN r.kind", [])])
        db = make_db(driver)
        assert db.approve_membership_request("cons-1", "u-1", decided_by="curator-1") is False

    def test_deny_membership_request_deletes_relation(self):
        driver = ScriptedDriver()
        db = make_db(driver)
        assert db.deny_membership_request("cons-1", "u-1") is True
        assert any("DELETE r" in q for q in driver.queries)

    def test_get_pending_membership_requests_returns_records(self):
        records = [{"user_tag": "u-1", "consortium_tag": "cons-1", "kind": "add"}]
        driver = ScriptedDriver(responses=[("RETURN u.tag AS user_tag", records)])
        db = make_db(driver)
        assert db.get_pending_membership_requests() == records


class TestDirectMembershipReads:
    def test_get_user_tags_uses_direct_membership(self):
        driver = ScriptedDriver(responses=[("RETURN DISTINCT u.tag", ["pi-1", "u-1"])])
        db = make_db(driver)
        assert db.get_user_tags(tag="cons-1") == ["pi-1", "u-1"]
        assert any(
            "MATCH (c:Consortium {tag : $tag})<-[:MEMBER_OF]-(u:User)" in q
            and "ResearchGroup" not in q
            for q in driver.queries
        )

    def test_find_by_user_uses_direct_membership(self):
        driver = ScriptedDriver(responses=[("RETURN DISTINCT c.tag", [["cons-1", 123]])])
        db = make_db(driver)
        assert db.find_by_user(user_tag="u-1", limit=None) == ["cons-1"]
        assert any(
            "(u:User {tag : $user_tag})-[:MEMBER_OF]->(c:Consortium)" in q
            and "ResearchGroup" not in q
            for q in driver.queries
        )

    def test_get_eligible_user_tags_traverses_groups(self):
        driver = ScriptedDriver(responses=[("RETURN DISTINCT u.tag", ["u-1"])])
        db = make_db(driver)
        assert db.get_eligible_user_tags(tag="cons-1") == ["u-1"]
        assert any("ResearchGroup" in q for q in driver.queries)
