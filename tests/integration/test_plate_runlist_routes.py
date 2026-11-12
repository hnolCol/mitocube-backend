"""
Route-level tests for the plate runlist/submission endpoints.
Uses FastAPI dependency_overrides with a fake database, like test_migrated_routers.py.
"""

import sys
import time
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.plates import PlateModel, PlateRunlistModel, PlateSubmissionModel, PlateSubmissionsLayoutModel
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


class FakePlatesDB:
    def __init__(self):
        self.plates = {
            "plate-1": PlateModel(tag="plate-1", name="P-96-001", rows=2, columns=3, created_at=1.0),
            "empty-1": PlateModel(tag="empty-1", name="P-96-002", rows=2, columns=3, created_at=2.0),
        }
        self.runlists = {
            "plate-1": [PlateRunlistModel(
                runlist_tag="rl-1", created_at=100.0, instrument_tag="inst-1", instrument_text="Instrument One",
                n_runs_on_plate=2, used_positions=["A1", "B2"], user_tag="abcdefgh",
                user_firstname="Test", user_lastname="User",
                submission_tag="subm-1", submission_label="subm-1", submission_title="My title")],
        }
        self.submissions = {
            "plate-1": [PlateSubmissionModel(
                submission_tag="subm-1", submission_label="subm-1", submission_title="My title",
                user_tag="abcdefgh", user_firstname="Test", user_lastname="User",
                n_runs_on_plate=2, n_runlists=1)],
        }
        self.layouts = {
            "plate-1": PlateSubmissionsLayoutModel(
                plate_tag="plate-1", rows=2, columns=3,
                wells=[
                    {"row_index": 0, "column_index": 0, "position": "A1", "submission_tag": "subm-1"},
                    {"row_index": 0, "column_index": 1, "position": "A2"},
                    {"row_index": 0, "column_index": 2, "position": "A3"},
                    {"row_index": 1, "column_index": 0, "position": "B1"},
                    {"row_index": 1, "column_index": 1, "position": "B2", "submission_tag": "subm-1"},
                    {"row_index": 1, "column_index": 2, "position": "B3"},
                ],
                submissions=[
                    {"submission_tag": "subm-1", "submission_label": "subm-1", "submission_title": "My title",
                     "user_tag": "abcdefgh", "user_firstname": "Test", "user_lastname": "User", "n_wells": 2},
                ],
            ),
        }

    def exists(self, tag):
        return tag in self.plates

    def get_runlists(self, tag):
        return self.runlists.get(tag, [])

    def get_submissions(self, tag):
        return self.submissions.get(tag, [])

    def get_submission_layout(self, tag):
        return self.layouts.get(tag)


class FakeDB:
    def __init__(self):
        self.plates = FakePlatesDB()


def _make_client(user):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers.plates.plates import router as plates_router

    app = FastAPI()
    app.include_router(plates_router)
    app.dependency_overrides[get_db] = lambda: FakeDB()
    app.dependency_overrides[get_user_from_token] = lambda: user
    return TestClient(app)


@pytest.fixture
def client():
    "Curator client: the plate -> submission information is only visible to curators."
    with _make_client(make_user(role=UserRolesEnum.CURATOR)) as c:
        yield c


class TestPlateRunlistRoutes:
    def test_runlists_of_used_plate(self, client):
        resp = client.get("/api/plates/plate-1/runlists")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["runlist_tag"] == "rl-1"
        assert body[0]["n_runs_on_plate"] == 2
        assert body[0]["used_positions"] == ["A1", "B2"]
        assert body[0]["submission_tag"] == "subm-1"

    def test_runlists_of_unused_plate_is_empty(self, client):
        resp = client.get("/api/plates/empty-1/runlists")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_runlists_of_missing_plate_404(self, client):
        resp = client.get("/api/plates/does-not-exist/runlists")
        assert resp.status_code == 404

    def test_submissions_of_used_plate(self, client):
        resp = client.get("/api/plates/plate-1/submissions")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["submission_tag"] == "subm-1"
        assert body[0]["n_runs_on_plate"] == 2

    def test_submissions_of_missing_plate_404(self, client):
        resp = client.get("/api/plates/does-not-exist/submissions")
        assert resp.status_code == 404

    def test_submissions_layout_full_grid(self, client):
        resp = client.get("/api/plates/plate-1/submissions-layout")
        assert resp.status_code == 200
        body = resp.json()
        assert body["plate_tag"] == "plate-1"
        assert body["rows"] == 2 and body["columns"] == 3
        assert len(body["wells"]) == 6
        assert body["wells"][0]["position"] == "A1"
        assert body["wells"][0]["submission_tag"] == "subm-1"
        assert body["wells"][1]["submission_tag"] is None
        assert body["wells"][5]["position"] == "B3"
        assert body["submissions"][0]["n_wells"] == 2

    def test_submissions_layout_of_missing_plate_404(self, client):
        resp = client.get("/api/plates/does-not-exist/submissions-layout")
        assert resp.status_code == 404

    def test_unauthenticated_rejected(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.plates.plates import router as plates_router

        app = FastAPI()
        app.include_router(plates_router)
        app.dependency_overrides[get_db] = lambda: FakeDB()
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/api/plates/plate-1/runlists")
        assert resp.status_code in (401, 403)

    def test_standard_user_rejected_on_runlists(self):
        with _make_client(make_user()) as c:
            resp = c.get("/api/plates/plate-1/runlists")
        assert resp.status_code == 403

    def test_standard_user_rejected_on_submissions(self):
        with _make_client(make_user()) as c:
            resp = c.get("/api/plates/plate-1/submissions")
        assert resp.status_code == 403

    def test_standard_user_rejected_on_submissions_layout(self):
        with _make_client(make_user()) as c:
            resp = c.get("/api/plates/plate-1/submissions-layout")
        assert resp.status_code == 403

    def test_standard_user_sees_no_runlist_counts(self):
        class FakeCountingDB(FakeDB):
            def __init__(self):
                super().__init__()
                self.plates.list = lambda: [PlateModel(
                    tag="plate-1", name="P-96-001", rows=2, columns=3, created_at=1.0,
                    n_runlists=4, n_submissions=2)]

        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.plates.plates import router as plates_router

        app = FastAPI()
        app.include_router(plates_router)
        app.dependency_overrides[get_db] = lambda: FakeCountingDB()
        app.dependency_overrides[get_user_from_token] = lambda: make_user()
        with TestClient(app) as c:
            body = c.get("/api/plates").json()
        assert body[0]["n_runlists"] == 0
        assert body[0]["n_submissions"] == 0

    def test_curator_sees_runlist_counts(self):
        class FakeCountingDB(FakeDB):
            def __init__(self):
                super().__init__()
                self.plates.list = lambda: [PlateModel(
                    tag="plate-1", name="P-96-001", rows=2, columns=3, created_at=1.0,
                    n_runlists=4, n_submissions=2)]

        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.plates.plates import router as plates_router

        app = FastAPI()
        app.include_router(plates_router)
        app.dependency_overrides[get_db] = lambda: FakeCountingDB()
        app.dependency_overrides[get_user_from_token] = lambda: make_user(role=UserRolesEnum.CURATOR)
        with TestClient(app) as c:
            body = c.get("/api/plates").json()
        assert body[0]["n_runlists"] == 4
        assert body[0]["n_submissions"] == 2
