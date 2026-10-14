"""Integration tests for the attribute request workflow:
a user proposes an attribute/trait, curators see the pending request,
accept creates the attribute/trait, reject does not."""
import sys
import time
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.requests import AttributeRequestModel
from services.users import get_user_from_token, is_user_at_least_curator
from lib.database.Database import get_db


class FakeAttributesDB:
    def __init__(self):
        self.attributes = {}
        self.traits = {}

    def exists(self, tag=None, trait=None):
        if trait is not None:
            return trait in self.traits
        return tag in self.attributes

    def insert(self, tag, text, priority=500, allow_input=False, abbreviation=None,
               min_state=None, group_tags=None, parents=None, children=None,
               required_trait_tags=None):
        self.attributes[tag] = {"text": text}
        return True

    def insert_trait(self, trait):
        self.traits[trait.tag] = trait
        return True


class FakeAttributeRequestsDB:
    def __init__(self, attributes):
        self.attributes = attributes
        self.requests = {}

    def insert(self, request, user_tag):
        model = AttributeRequestModel(
            kind=request.kind,
            user_tag=user_tag,
            comment=request.comment,
            attribute=request.attribute,
            trait=request.trait,
        )
        self.requests[model.tag] = model
        return model.tag

    def get(self, tags=None, status=None, limit=50):
        return [r for r in self.requests.values()
                if status is None or r.status == status][:limit]

    def get_pending(self, limit=50):
        return self.get(status="pending", limit=limit)

    def accept(self, tag, reviewer_tag, comment=None):
        r = self.requests[tag]
        if r.status != "pending":
            raise ValueError(f"Attribute request with tag '{tag}' is not pending.")
        if r.kind == "attribute":
            attribute_tag = "att_" + r.attribute.text.replace(" ", "_").lower()
            if self.attributes.exists(tag=attribute_tag):
                raise ValueError(f"An attribute with the tag '{attribute_tag}' exists already.")
            self.attributes.insert(tag=attribute_tag, text=r.attribute.text)
            for t in r.attribute.traits:
                self.attributes.insert_trait(type("T", (), {
                    "tag": f"{attribute_tag}:{t.text.replace(' ', '_').lower()}",
                    "text": t.text})())
        else:
            if not self.attributes.exists(tag=r.trait.attribute_tag):
                raise ValueError(f"Attribute '{r.trait.attribute_tag}' not found.")
            trait_tag = f"{r.trait.attribute_tag}:{r.trait.text.replace(' ', '_').lower()}"
            if self.attributes.exists(tag=r.trait.attribute_tag, trait=trait_tag):
                raise ValueError(f"A trait with the tag '{trait_tag}' exists already for this attribute.")
            self.attributes.insert_trait(type("T", (), {"tag": trait_tag, "text": r.trait.text})())
        r.status = "accepted"
        return r

    def reject(self, tag, reviewer_tag, comment=None):
        r = self.requests[tag]
        if r.status != "pending":
            raise ValueError(f"Attribute request with tag '{tag}' is not pending.")
        r.status = "rejected"
        return r


class FakeDB:
    def __init__(self):
        self.attributes = FakeAttributesDB()
        self.attribute_requests = FakeAttributeRequestsDB(self.attributes)


def make_user(tag="abcdefgh", role=UserRolesEnum.STANDARD):
    return UserModel(
        tag=tag,
        firstname="Test",
        lastname="User",
        email="test.user@age.mpg.de",
        created_at=time.time(),
        role=role,
        allow_login=True,
    )


def _role_too_low():
    from config.exceptions.HTTPExceptions import user_role_too_low
    raise user_role_too_low


@pytest.fixture(scope="module")
def app():
    from fastapi import FastAPI
    from routers.requests.attributes import router as requests_router
    test_app = FastAPI()
    test_app.include_router(requests_router)
    return test_app


@pytest.fixture
def client(app):
    db = FakeDB()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_user_from_token] = lambda: make_user()
    app.dependency_overrides[is_user_at_least_curator] = lambda: make_user(role=UserRolesEnum.CURATOR)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, db
    app.dependency_overrides.clear()


class TestAttributeRequestsRoute:
    def test_standard_user_can_propose_attribute(self, client):
        c, db = client
        resp = c.post("/api/requests/attributes", json={
            "kind": "attribute",
            "attribute": {"text": "New Organ", "traits": [{"text": "Heart", "description": ""}]},
        })
        assert resp.status_code == 200
        tag = resp.json()["tag"]
        assert db.attribute_requests.requests[tag].status == "pending"

    def test_pending_visible_to_curator(self, client):
        c, db = client
        c.post("/api/requests/attributes", json={
            "kind": "attribute", "attribute": {"text": "Other Attribute"}})
        resp = c.get("/api/requests/attributes/pending")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_non_curator_cannot_list_or_review(self, client):
        c, db = client
        c.app.dependency_overrides[is_user_at_least_curator] = _role_too_low
        resp = c.get("/api/requests/attributes")
        assert resp.status_code == 401
        c.app.dependency_overrides[is_user_at_least_curator] = lambda: make_user(role=UserRolesEnum.CURATOR)

    def test_accept_creates_attribute_and_traits(self, client):
        c, db = client
        resp = c.post("/api/requests/attributes", json={
            "kind": "attribute",
            "attribute": {"text": "New Compound",
                          "traits": [{"text": "Drug X", "description": "a drug"}]},
        })
        tag = resp.json()["tag"]
        resp = c.post(f"/api/requests/attributes/{tag}/accept", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"
        assert db.attributes.exists(tag="att_new_compound")
        assert db.attributes.exists(tag="att_new_compound", trait="att_new_compound:drug_x")

    def test_accept_twice_conflicts(self, client):
        c, db = client
        resp = c.post("/api/requests/attributes", json={
            "kind": "attribute", "attribute": {"text": "Once Only"}})
        tag = resp.json()["tag"]
        assert c.post(f"/api/requests/attributes/{tag}/accept", json={}).status_code == 200
        assert c.post(f"/api/requests/attributes/{tag}/accept", json={}).status_code == 409

    def test_reject_does_not_create(self, client):
        c, db = client
        resp = c.post("/api/requests/attributes", json={
            "kind": "attribute", "attribute": {"text": "Rejected Attribute"}})
        tag = resp.json()["tag"]
        resp = c.post(f"/api/requests/attributes/{tag}/reject", json={"comment": "not needed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"
        assert not db.attributes.exists(tag="att_rejected_attribute")

    def test_trait_request_requires_existing_attribute(self, client):
        c, db = client
        resp = c.post("/api/requests/attributes", json={
            "kind": "trait", "trait": {"attribute_tag": "att_missing", "text": "Nope"}})
        assert resp.status_code == 404

    def test_trait_request_accept(self, client):
        c, db = client
        db.attributes.attributes["att_organ"] = {"text": "Organ"}
        resp = c.post("/api/requests/attributes", json={
            "kind": "trait", "trait": {"attribute_tag": "att_organ", "text": "Kidney"}})
        tag = resp.json()["tag"]
        resp = c.post(f"/api/requests/attributes/{tag}/accept", json={})
        assert resp.status_code == 200
        assert db.attributes.exists(tag="att_organ", trait="att_organ:kidney")

    def test_insert_model_validation(self, client):
        c, db = client
        resp = c.post("/api/requests/attributes", json={"kind": "attribute"})
        assert resp.status_code == 422
