"""
Integration tests: the FastAPI app must be importable and serve routes
without a running Neo4j database, using FastAPI dependency overrides.
"""

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
from services.users import get_db, get_user_from_token


class FakeUserDB:
    def get_user_submission_views(self, tag, limit):
        return ["subm-1", "subm-2"]


class FakeDB:
    users = FakeUserDB()


def make_user(tag="abcdefgh"):
    return UserModel(
        tag=tag,
        firstname="Test",
        lastname="User",
        email="test.user@age.mpg.de",
        created_at=time.time(),
        role=UserRolesEnum.STANDARD,
        allow_login=True,
    )


@pytest.fixture(scope="module")
def app():
    """Mount only the router under test.

    Importing the full ``app`` module pulls in the optional AI/langchain stack,
    which is not relevant to this route and is not always installed.
    """
    from fastapi import FastAPI
    from routers.users.views import router as user_views_router

    test_app = FastAPI()
    test_app.include_router(user_views_router)
    return test_app


@pytest.fixture
def client(app, monkeypatch):
    monkeypatch.setattr(app, "dependency_overrides", {})
    app.dependency_overrides[get_db] = lambda: FakeDB()
    app.dependency_overrides[get_user_from_token] = lambda: make_user()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


class TestUsersViewsRoute:
    def test_views_return_own_history(self, client):
        resp = client.get("/api/users/views", params={"type": "submissions"})
        assert resp.status_code == 200
        assert resp.json() == ["subm-1", "subm-2"]

    def test_no_user_tag_parameter_accepted(self):
        """The IDOR-prone user_tag query parameter must be gone."""
        from routers.users.views import get_last_views
        import inspect

        assert "user_tag" not in inspect.signature(get_last_views).parameters

    def test_unauthenticated_request_rejected(self, app):
        """With no auth override, the route must not leak data.

        Without a valid token the dependency chain raises before the handler
        runs; with the lazy DB proxy in place the failure surfaces as an HTTP
        error response rather than an import-time connection crash.
        """
        app.dependency_overrides.clear()
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/api/users/views", params={"type": "submissions"})
        assert resp.status_code in (401, 403)
        assert resp.json() != ["subm-1", "subm-2"]
