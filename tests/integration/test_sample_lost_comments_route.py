"""
Route-level tests for the sample lost flag and sample comment endpoints.
Uses FastAPI dependency_overrides with a fake database, following
test_migrated_routers.py conventions.
"""

import sys
import time
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.samples import SampleCommentModel
from services.users import get_user_from_token
from lib.database.Database import get_db


class FakeSamplesDB:
    def __init__(self):
        self.samples = {
            "sub-1|s1": {"tag": "sub-1|s1", "text": "s1", "index": 0, "created_at": 1.0, "excluded": False, "lost": False},
            "sub-1|s2": {"tag": "sub-1|s2", "text": "s2", "index": 1, "created_at": 1.0, "excluded": False, "lost": False},
        }
        self.submission_tags = {"sub-1|s1": "sub-1", "sub-1|s2": "sub-1"}
        self.comments = {"sub-1|s1": []}
        self.set_lost_calls = []
        self.set_excluded_calls = []

    def exists(self, tag):
        return tag in self.samples

    def get_submission_tag(self, tag):
        return self.submission_tags.get(tag)

    def get(self, tag):
        return self.samples.get(tag)

    def set_lost(self, tag, lost):
        self.set_lost_calls.append((tag, lost))
        self.samples[tag]["lost"] = lost
        return lost

    def set_excluded(self, tag, excluded):
        self.set_excluded_calls.append((tag, excluded))
        self.samples[tag]["excluded"] = excluded
        return excluded

    def insert_comment(self, tag, comment):
        self.comments[tag].append(comment)
        return True

    def get_comments(self, tag):
        return self.comments.get(tag, [])


class FakeSubmissionsDB:
    def __init__(self):
        self.sample_tags = ["sub-1|s1", "sub-1|s2"]

    def exists(self, tag):
        return tag == "sub-1"

    def get_creator(self, tag):
        return getattr(self, "creator_tag", "abcdefgh")

    def get_samples(self, tag, ignore_excluded=False, ignore_lost=False):
        return self.sample_tags

    def get_stats_outdated(self, tag):
        return False


class FakeSubmissionFilterDB:
    def has_user_access(self, user_tag, submission_tag):
        return True


class FakeDB:
    def __init__(self):
        self.samples = FakeSamplesDB()
        self.submissions = FakeSubmissionsDB()
        self.submission_filter = FakeSubmissionFilterDB()


def make_user(role=UserRolesEnum.STANDARD):
    return UserModel(
        tag="abcdefgh",
        firstname="Test",
        lastname="User",
        email="test.user@age.mpg.de",
        created_at=time.time(),
        role=role,
        allow_login=True,
    )


@pytest.fixture
def db():
    return FakeDB()


@pytest.fixture
def client(db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers.samples.samples import router as samples_router

    app = FastAPI()
    app.include_router(samples_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_user_from_token] = lambda: make_user()
    with TestClient(app) as c:
        yield c


def test_get_sample_returns_lost_flag(client):
    r = client.get("/api/samples/sub-1|s1")
    assert r.status_code == 200
    assert r.json()["lost"] is False


def test_patch_lost(client, db):
    """The default test user is the creator of sub-1, so the creator may mark a sample lost."""
    r = client.patch("/api/samples/sub-1|s1/lost?lost=true")
    assert r.status_code == 200
    assert r.json() is True
    assert db.samples.set_lost_calls == [("sub-1|s1", True)]
    assert db.samples.samples["sub-1|s1"]["lost"] is True


def test_patch_lost_forbidden_for_non_creator(client, db, monkeypatch):
    """A standard user who is not the creator (and not a curator) must not mark a sample lost."""
    db.submissions.creator_tag = "someone-else"
    r = client.patch("/api/samples/sub-1|s1/lost?lost=true")
    assert r.status_code == 403
    assert db.samples.set_lost_calls == []


def test_patch_lost_allowed_for_group_curator(client, db, monkeypatch):
    """A group curator with access to the submission may mark a sample lost."""
    import tests.integration.test_sample_lost_comments_route as t
    from config.enums.users.roles import UserRolesEnum

    db.submissions.creator_tag = "someone-else"
    client.app.dependency_overrides[get_user_from_token] = lambda: make_user(role=UserRolesEnum.GROUP_CURATOR)
    r = client.patch("/api/samples/sub-1|s1/lost?lost=true")
    assert r.status_code == 200
    assert db.samples.set_lost_calls == [("sub-1|s1", True)]
    client.app.dependency_overrides[get_user_from_token] = lambda: make_user()


def test_patch_lost_unfound_sample_404(client):
    r = client.patch("/api/samples/sub-1|missing/lost?lost=true")
    assert r.status_code == 404


def test_patch_exclude_still_works(client, db):
    r = client.patch("/api/samples/sub-1|s1/exclude?excluded=true")
    assert r.status_code == 200
    assert r.json() is True
    assert db.samples.set_excluded_calls == [("sub-1|s1", True)]


def test_patch_exclude_forbidden_for_non_creator(client, db):
    db.submissions.creator_tag = "someone-else"
    r = client.patch("/api/samples/sub-1|s1/exclude?excluded=true")
    assert r.status_code == 403
    assert db.samples.set_excluded_calls == []


def test_insert_comment_sets_user_tag(client, db):
    payload = {"content": "Sample corrupted during shipping."}
    r = client.post("/api/samples/sub-1|s1/comments", json=payload)
    assert r.status_code == 200
    assert r.json() is True
    comments = db.samples.comments["sub-1|s1"]
    assert len(comments) == 1
    assert comments[0].user_tag == "abcdefgh"
    assert comments[0].content == "Sample corrupted during shipping."


def test_get_comments(client, db):
    db.samples.comments["sub-1|s1"].append(
        SampleCommentModel(content="first", user_tag="abcdefgh")
    )
    r = client.get("/api/samples/sub-1|s1/comments")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["content"] == "first"
    assert body[0]["user_tag"] == "abcdefgh"


def test_comment_on_missing_sample_404(client):
    r = client.post("/api/samples/sub-1|missing/comments", json={"content": "x"})
    assert r.status_code == 404


def test_comment_requires_access_to_parent_submission(client, monkeypatch):
    import routers.samples.samples as samples_router_module

    def deny(submission_tag, user, db=None):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="no access")

    monkeypatch.setattr(samples_router_module, "check_submission_access", deny)
    r = client.post("/api/samples/sub-1|s1/comments", json={"content": "x"})
    assert r.status_code == 403


def test_lost_requires_access_to_parent_submission(client, db, monkeypatch):
    """A non-creator standard user with submission access (e.g. a collaborator) must not mark a sample lost."""
    db.submissions.creator_tag = "someone-else"
    r = client.patch("/api/samples/sub-1|s1/lost?lost=true")
    assert r.status_code == 403
