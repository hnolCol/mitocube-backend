"""
Route-level tests for the modular procedure endpoints.
Uses FastAPI dependency_overrides with a fake database, like test_plate_runlist_routes.py.
"""

import sys
import time
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.procedures import (
    ModularProcedureBaseModel,
    ModularProcedureSubmissionModel,
    PublishModularProcedureModel,
)
from services.users import get_user_from_token
from lib.database.Database import get_db


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


class FakeModularProceduresDB:
    def __init__(self):
        self.procedures = {
            "proc-1": ModularProcedureBaseModel(
                tag="proc-1", title="Protein Concentration Measurement", description="Measure it.",
                status="DRAFT", version=1, user_tag="abcdefgh", created_at=1.0,
                condition_application_tags=["ca-1"], protocol_tags=["protocol-1"]),
            "proc-2": ModularProcedureBaseModel(
                tag="proc-2", title="SP3 Digestion", description="Digest it.",
                status="PUBLISHED", version=1, content_hash="abc123", user_tag="abcdefgh",
                created_at=2.0, published_at=3.0,
                condition_application_tags=[], protocol_tags=["protocol-2"]),
        }
        self.submission_links = {
            "proc-2": [
                ModularProcedureSubmissionModel(
                    procedure_tag="proc-2", submission_tag="subm-1", position=0,
                    created_at=10.0, done=False),
            ],
        }
        self.submission_procedures = {
            "subm-1": [
                ModularProcedureSubmissionModel(
                    procedure_tag="proc-2", submission_tag="subm-1", position=0,
                    created_at=10.0, done=False),
            ],
        }
        self.published = []
        self.linked = []
        self.done = []
        self.reopened = []
        self.unlinked = []

    def exists(self, tag):
        return tag in self.procedures

    def get(self, tag):
        if tag not in self.procedures:
            raise KeyError("Modular procedure not found.")
        return self.procedures[tag]

    def find(self, search_string=None, status=None, limit=None):
        tags = []
        for tag, procedure in self.procedures.items():
            if search_string is not None and search_string not in procedure.title:
                continue
            if status is not None and procedure.status != status:
                continue
            tags.append(tag)
        return tags

    def insert(self, title, description, user_tag, condition_application_tags=None, protocol_tags=None):
        tag = "proc-new"
        if tag in self.procedures:
            raise ValueError("Tag is already in the database.")
        self.procedures[tag] = ModularProcedureBaseModel(
            tag=tag, title=title, description=description, status="DRAFT", version=1,
            user_tag=user_tag, condition_application_tags=condition_application_tags or [],
            protocol_tags=protocol_tags or [])
        return tag

    def update(self, tag, title, description, user_tag, condition_application_tags=None, protocol_tags=None):
        if tag not in self.procedures:
            raise ValueError("Modular procedure not found.")
        if self.procedures[tag].status == "PUBLISHED":
            raise ValueError("Published modular procedures are immutable.")
        self.procedures[tag].title = title
        self.procedures[tag].description = description
        return True

    def publish(self, tag, user_tag):
        if tag not in self.procedures:
            raise KeyError("Modular procedure not found.")
        if self.procedures[tag].status == "PUBLISHED":
            raise ValueError("Modular procedure is already published.")
        self.procedures[tag].status = "PUBLISHED"
        self.procedures[tag].content_hash = "deadbeef"
        self.published.append(tag)
        return PublishModularProcedureModel(tag=tag, version=1, content_hash="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

    def link(self, tag, submission_tag, user_tag):
        if tag not in self.procedures:
            raise ValueError("Modular procedure not found.")
        if submission_tag in [link.submission_tag for link in self.submission_links.get(tag, [])]:
            raise ValueError("Submission is already linked to this modular procedure.")
        self.linked.append((tag, submission_tag))
        return True

    def unlink(self, tag, submission_tag):
        self.unlinked.append((tag, submission_tag))
        return True

    def mark_done(self, tag, submission_tag, user_tag):
        self.done.append((tag, submission_tag, user_tag))
        return True

    def reopen(self, tag, submission_tag):
        self.reopened.append((tag, submission_tag))
        return True

    def get_submissions(self, tag):
        if tag not in self.procedures:
            raise KeyError("Modular procedure not found.")
        return self.submission_links.get(tag, [])

    def get_submission_procedures(self, submission_tag):
        return self.submission_procedures.get(submission_tag, [])


class FakeDB:
    def __init__(self):
        self.modular_procedures = FakeModularProceduresDB()


def _make_client(user):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers.procedures.procedures import router as procedures_router

    app = FastAPI()
    app.include_router(procedures_router)
    app.dependency_overrides[get_db] = lambda: FakeDB()
    app.dependency_overrides[get_user_from_token] = lambda: user
    return TestClient(app)


@pytest.fixture
def client():
    "Curator client: modular procedure management is reserved for curators and admins."
    with _make_client(make_user(role=UserRolesEnum.CURATOR)) as c:
        yield c


class TestModularProcedureRoutes:
    def test_query_procedures(self, client):
        resp = client.get("/api/procedures/q")
        assert resp.status_code == 200
        assert set(resp.json()) == {"proc-1", "proc-2"}

    def test_query_procedures_by_status(self, client):
        resp = client.get("/api/procedures/q", params={"status": "PUBLISHED"})
        assert resp.status_code == 200
        assert resp.json() == ["proc-2"]

    def test_get_procedure(self, client):
        resp = client.get("/api/procedures/proc-1")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Protein Concentration Measurement"
        assert resp.json()["status"] == "DRAFT"

    def test_get_missing_procedure_404(self, client):
        resp = client.get("/api/procedures/does-not-exist")
        assert resp.status_code == 404

    def test_insert_procedure(self, client):
        resp = client.post("/api/procedures/", json={
            "title": "New", "description": "New procedure",
            "condition_application_tags": ["ca-1"], "protocol_tags": ["protocol-1"]})
        assert resp.status_code == 200
        assert resp.json()["status"] == "DRAFT"

    def test_update_draft_procedure(self, client):
        resp = client.patch("/api/procedures/proc-1", json={
            "title": "Updated", "description": "Updated description"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    def test_update_published_procedure_rejected(self, client):
        resp = client.patch("/api/procedures/proc-2", json={
            "title": "Updated", "description": "Nope"})
        assert resp.status_code == 400

    def test_publish_draft_procedure(self, client):
        resp = client.post("/api/procedures/proc-1/publish")
        assert resp.status_code == 200
        body = resp.json()
        assert body["tag"] == "proc-1"
        assert len(body["content_hash"]) == 64

    def test_publish_published_procedure_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/publish")
        assert resp.status_code == 400

    def test_link_submission(self, client):
        resp = client.post("/api/procedures/proc-1/link/subm-1")
        assert resp.status_code == 200
        assert resp.json() is True

    def test_get_procedure_submissions(self, client):
        resp = client.get("/api/procedures/proc-2/submissions")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["submission_tag"] == "subm-1"
        assert body[0]["created_at"] == 10.0
        assert body[0]["done"] is False

    def test_get_submission_procedures_ordered(self, client):
        resp = client.get("/api/procedures/submissions/subm-1")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["procedure_tag"] == "proc-2"
        assert body[0]["position"] == 0

    def test_mark_done(self, client):
        resp = client.post("/api/procedures/proc-2/link/subm-1/done")
        assert resp.status_code == 200
        assert resp.json() is True

    def test_reopen(self, client):
        resp = client.delete("/api/procedures/proc-2/link/subm-1/done")
        assert resp.status_code == 200
        assert resp.json() is True


class TestModularProcedurePermissions:
    def test_standard_user_rejected_on_insert(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/", json={"title": "New", "description": "Nope"})
            assert resp.status_code == 403

    def test_standard_user_rejected_on_publish(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/proc-1/publish")
            assert resp.status_code == 403

    def test_standard_user_rejected_on_link(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/proc-1/link/subm-1")
            assert resp.status_code == 403

    def test_standard_user_rejected_on_mark_done(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/proc-2/link/subm-1/done")
            assert resp.status_code == 403

    def test_admin_allowed_on_insert(self):
        with _make_client(make_user(role=UserRolesEnum.ADMIN)) as c:
            resp = c.post("/api/procedures/", json={"title": "New", "description": "Admin"})
            assert resp.status_code == 200

    def test_admin_allowed_on_mark_done(self):
        with _make_client(make_user(role=UserRolesEnum.ADMIN)) as c:
            resp = c.post("/api/procedures/proc-2/link/subm-1/done")
            assert resp.status_code == 200
