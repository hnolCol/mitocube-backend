"""Integration tests for the attribute hierarchy resolution:
the attributes query with include_parent_paths and the CA update
validation / auto-completion."""
import sys
import time
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.enums.users.roles import UserRolesEnum
from config.models.attributes import AttributeTraitTagResponseModel
from config.models.user import UserModel
from services.users import get_user_from_token
from lib.database.Database import get_db

MS_TYPE = "att_ms_type"
MS_NAME = "att_ms"
MS_TYPE_ORBITRAP = "att_ms_type:orbitrap"
MS_NAME_ECLIPSE = "att_ms:eclipse"


class FakeAttributesDB:
    def __init__(self):
        self.parent_chains = {MS_NAME: [MS_TYPE]}
        self.implied = {MS_NAME_ECLIPSE: [(MS_TYPE, MS_TYPE_ORBITRAP)]}
        self.query_calls = []

    def find_attributes_and_traits(self, search_string=None, min_state=None, limit=None,
                                   attribute_groups=None, attribute_tags=None,
                                   include_parent_paths=False):
        self.query_calls.append(include_parent_paths)
        if not include_parent_paths:
            return [AttributeTraitTagResponseModel(attribute_tag=MS_NAME, trait_tags=[MS_NAME_ECLIPSE])]
        return [AttributeTraitTagResponseModel(
            attribute_tag=MS_NAME,
            trait_tags=[MS_NAME_ECLIPSE],
            parent_tags=self.parent_chains[MS_NAME],
            trait_paths={
                MS_NAME_ECLIPSE: [
                    {"attribute_tag": MS_TYPE, "trait_tag": MS_TYPE_ORBITRAP},
                    {"attribute_tag": MS_NAME, "trait_tag": MS_NAME_ECLIPSE},
                ]
            },
        )]

    def get_parents(self, tag):
        return [MS_TYPE] if tag == MS_NAME else []

    def get_trait_implied_parent_traits(self, trait_tags):
        return {tag: self.implied.get(tag, []) for tag in trait_tags}


class FakeSubmissionDB:
    def __init__(self):
        self.edited_trees = None

    def exists(self, tag=None):
        return True

    def edit_condition_applications(self, tag, attribute_trees):
        self.edited_trees = attribute_trees
        return True


class FakeSubmissionFilterDB:
    def has_user_access(self, user_tag, submission_tag):
        return True


class FakeDB:
    def __init__(self):
        self.attributes = FakeAttributesDB()
        self.submissions = FakeSubmissionDB()
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
def client():
    from routers.attributes.attributes import router as attributes_router
    from routers.submission.ca import router as ca_router

    fake_db = FakeDB()
    app = FastAPI()
    app.include_router(attributes_router)
    app.include_router(ca_router)
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_user_from_token] = lambda: make_user()
    with TestClient(app) as c:
        yield c, fake_db
    app.dependency_overrides.clear()


class TestAttributesQueryParentPaths:
    def test_default_keeps_flat_response(self, client):
        c, db = client
        resp = c.get("/api/attributes/q")
        assert resp.status_code == 200
        body = resp.json()
        assert body[0]["attribute_tag"] == MS_NAME
        assert body[0]["trait_tags"] == [MS_NAME_ECLIPSE]
        assert db.attributes.query_calls[-1] is False

    def test_include_parent_paths_attaches_hierarchy(self, client):
        c, db = client
        resp = c.get("/api/attributes/q", params={"include_parent_paths": True})
        assert resp.status_code == 200
        body = resp.json()
        assert body[0]["parent_tags"] == [MS_TYPE]
        assert body[0]["trait_paths"][MS_NAME_ECLIPSE] == [
            {"attribute_tag": MS_TYPE, "trait_tag": MS_TYPE_ORBITRAP},
            {"attribute_tag": MS_NAME, "trait_tag": MS_NAME_ECLIPSE},
        ]
        assert db.attributes.query_calls[-1] is True


class TestCAUpdateHierarchyValidation:
    def test_child_without_parent_is_auto_completed(self, client):
        c, db = client
        payload = [{"tag": MS_NAME, "type": "attribute", "children": [
            {"tag": MS_NAME_ECLIPSE, "type": "trait", "children": None}
        ]}]
        resp = c.post("/api/submissions/sub-1/ca/update", json=payload)
        assert resp.status_code == 200
        assert resp.json() is True
        trees = db.submissions.edited_trees
        assert len(trees) == 1
        parent = trees[0]
        assert parent.tag == MS_TYPE
        assert parent.children[0].tag == MS_TYPE_ORBITRAP
        assert parent.children[0].children[0].tag == MS_NAME

    def test_child_without_implication_passes_through(self, client):
        c, db = client
        payload = [{"tag": MS_NAME, "type": "attribute", "children": [
            {"tag": "att_ms:unknown", "type": "trait", "children": None}
        ]}]
        resp = c.post("/api/submissions/sub-1/ca/update", json=payload)
        assert resp.status_code == 200
        trees = db.submissions.edited_trees
        assert len(trees) == 1
        assert trees[0].tag == MS_NAME
        assert trees[0].children[0].tag == "att_ms:unknown"

    def test_nested_child_below_wrong_parent_is_rejected(self, client):
        c, _ = client
        payload = [{"tag": "att_other", "type": "attribute", "children": [
            {"tag": "att_other:t", "type": "trait", "children": [
                {"tag": MS_NAME, "type": "attribute", "children": [
                    {"tag": MS_NAME_ECLIPSE, "type": "trait", "children": None}
                ]}
            ]}
        ]}]
        resp = c.post("/api/submissions/sub-1/ca/update", json=payload)
        assert resp.status_code == 409
        assert "below one of its parent" in resp.json()["detail"]

    def test_parentless_attribute_passes_through(self, client):
        c, db = client
        payload = [{"tag": "att_organ", "type": "attribute", "children": [
            {"tag": "att_organ:heart", "type": "trait", "children": None}
        ]}]
        resp = c.post("/api/submissions/sub-1/ca/update", json=payload)
        assert resp.status_code == 200
        assert db.submissions.edited_trees[0].tag == "att_organ"
