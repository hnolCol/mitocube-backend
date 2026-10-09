"""Contract tests: every membership-changing write must invalidate the affected
users' cached submission scopes.

These tests pin down the invalidation contract documented in
lib/cache/scope_cache.py and enforced by the hooks in the Neo4j submission,
research group and consortium classes. They use a fake driver so no database is
required - the contract under test is "which cache keys get invalidated", not
"does Cypher work".
"""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from tests.conftest import *  # noqa: F401,F403 - sets the test env vars

import pytest


class RecordingScopeCache:
    """Records invalidate_cached_scope / invalidate_all_cached_scopes calls."""
    invalidated_users: list = []
    invalidated_all: int = 0

    @classmethod
    def reset(cls):
        cls.invalidated_users = []
        cls.invalidated_all = 0


@pytest.fixture(autouse=True)
def recording_scope_cache(monkeypatch):
    """Patches lib.cache.scope_cache so every invalidation is recorded instead of
    hitting the (not started) Mongo cache runtime. The DB classes import the
    module inside their methods (import lib.cache.scope_cache), so patching the
    module functions is sufficient."""
    import lib.cache.scope_cache as scope_cache_module

    def _invalidate_cached(user_tag):
        RecordingScopeCache.invalidated_users.append(user_tag)
        return None

    def _invalidate_all():
        RecordingScopeCache.invalidated_all += 1
        return 0

    RecordingScopeCache.reset()
    monkeypatch.setattr(scope_cache_module, "invalidate_cached_scope", _invalidate_cached)
    monkeypatch.setattr(scope_cache_module, "invalidate_all_cached_scopes", _invalidate_all)
    yield RecordingScopeCache
    RecordingScopeCache.reset()


class FakeDriver:
    """Minimal neo4j driver stub: execute_query returns a truthy list."""
    def execute_query(self, *args, **kwargs):
        return [True]


def make_submissions_db():
    from lib.database.neo4j.Submission import Neo4JSubmissions
    db = Neo4JSubmissions.__new__(Neo4JSubmissions)
    db._driver = FakeDriver()
    return db


def make_research_group_db():
    from lib.database.neo4j.ResearchGroup import Neo4JResearchGroup
    db = Neo4JResearchGroup.__new__(Neo4JResearchGroup)
    db._driver = FakeDriver()
    return db


def make_consortium_db():
    from lib.database.neo4j.Consortium import Neo4JConsortium
    db = Neo4JConsortium.__new__(Neo4JConsortium)
    db._driver = FakeDriver()
    return db


class TestSubmissionWrites:
    def test_insert_invalidates_creator_and_collaborators(self, recording_scope_cache):
        db = make_submissions_db()
        db.exists = lambda tag: False
        db.insert(tag="subm-1", title="t", user_tag="owner-1", collaborators=["collab-1", "collab-2"])
        assert sorted(recording_scope_cache.invalidated_users) == ["collab-1", "collab-2", "owner-1"]

    def test_insert_without_collaborators_invalidates_creator(self, recording_scope_cache):
        db = make_submissions_db()
        db.exists = lambda tag: False
        db.insert(tag="subm-1", title="t", user_tag="owner-1")
        assert recording_scope_cache.invalidated_users == ["owner-1"]

    def test_set_collaborators_invalidates_all_collaborators(self, recording_scope_cache):
        db = make_submissions_db()
        db.set_collaborators(tag="subm-1", collaborator_tags=["c-1", "c-2"], replace=True)
        assert sorted(recording_scope_cache.invalidated_users) == ["c-1", "c-2"]

    def test_update_owner_invalidates_new_owner(self, recording_scope_cache):
        db = make_submissions_db()
        db.get_creator = lambda tag: "prev-owner"
        db.update_owner(tag="subm-1", user_tag="new-owner", add_prev_user_to_collaborators=True)
        assert recording_scope_cache.invalidated_users == ["new-owner"]

    def test_update_owner_without_collab_invalidates_previous_owner(self, recording_scope_cache):
        db = make_submissions_db()
        db.get_creator = lambda tag: "prev-owner"
        db.update_owner(tag="subm-1", user_tag="new-owner", add_prev_user_to_collaborators=False)
        assert sorted(recording_scope_cache.invalidated_users) == ["new-owner", "prev-owner"]


class TestResearchGroupWrites:
    def test_insert_users_invalidates_users(self, recording_scope_cache):
        db = make_research_group_db()
        db.insert_users(tag="rg-1", user_tags=["u-1", "u-2"])
        assert sorted(recording_scope_cache.invalidated_users) == ["u-1", "u-2"]

    def test_remove_users_invalidates_users(self, recording_scope_cache):
        db = make_research_group_db()
        db.exists = lambda tag: True
        db.remove_users(tag="rg-1", user_tags=["u-1"])
        assert recording_scope_cache.invalidated_users == ["u-1"]


class TestConsortiumWrites:
    def test_share_submission_invalidates_namespace(self, recording_scope_cache):
        db = make_consortium_db()
        db.exists = lambda tag: True
        db.share_submission("cons-1", "subm-1", user_tag="owner-1", approved=True)
        assert recording_scope_cache.invalidated_all == 1

    def test_unshare_submission_invalidates_namespace(self, recording_scope_cache):
        db = make_consortium_db()
        db.unshare_submission("cons-1", "subm-1")
        assert recording_scope_cache.invalidated_all == 1

    def test_approve_share_request_invalidates_namespace(self, recording_scope_cache):
        db = make_consortium_db()
        db.approve_share_request("cons-1", "subm-1", user_tag="pi-1")
        assert recording_scope_cache.invalidated_all == 1

    def test_deny_share_request_invalidates_namespace(self, recording_scope_cache):
        db = make_consortium_db()
        db.deny_share_request("cons-1", "subm-1")
        assert recording_scope_cache.invalidated_all == 1

    def test_insert_groups_invalidates_namespace(self, recording_scope_cache):
        db = make_consortium_db()
        db.exists = lambda tag: True
        db.insert_groups(tag="cons-1", group_tags=["rg-1"])
        assert recording_scope_cache.invalidated_all == 1

    def test_remove_groups_invalidates_namespace(self, recording_scope_cache):
        db = make_consortium_db()
        db.exists = lambda tag: True
        db.remove_groups(tag="cons-1", group_tags=["rg-1"])
        assert recording_scope_cache.invalidated_all == 1
