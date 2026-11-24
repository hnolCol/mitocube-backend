"""
Integration tests for the admin account/MFA reset routes.
The FastAPI app must be importable and serve routes without a running
Neo4j database, using FastAPI dependency overrides.
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
from services.users import get_user_from_token, is_user_admin
from lib.database.Database import get_db


UPDATES = []


class FakeUserDB:
    def get_user_by_tag(self, tag):
        return UserModel(
            tag=tag,
            firstname="Test",
            lastname="User",
            email="test.user@age.mpg.de",
            created_at=time.time(),
            role=UserRolesEnum.STANDARD,
            allow_login=True,
            mfa_enabled=True,
        )

    def create_plain_password(self, N=10):
        return "plaintext-password"

    def hash_password(self, password):
        return f"hashed:{password}"

    def update(self, tag, user_props):
        UPDATES.append((tag, user_props))
        return True


class FakeDB:
    users = FakeUserDB()


def make_admin(tag="abcdefgh"):
    return UserModel(
        tag=tag,
        firstname="Admin",
        lastname="User",
        email="admin@age.mpg.de",
        created_at=time.time(),
        role=UserRolesEnum.ADMIN,
        allow_login=True,
    )


def make_standard_user(tag="standard"):
    return UserModel(
        tag=tag,
        firstname="Standard",
        lastname="User",
        email="standard@age.mpg.de",
        created_at=time.time(),
        role=UserRolesEnum.STANDARD,
        allow_login=True,
    )


@pytest.fixture(scope="module")
def app():
    """Mount only the router under test."""
    from fastapi import FastAPI
    from routers.authentication.user import router as user_router

    test_app = FastAPI()
    test_app.include_router(user_router)
    return test_app


@pytest.fixture
def admin_client(app, monkeypatch):
    UPDATES.clear()
    monkeypatch.setattr(app, "dependency_overrides", {})
    app.dependency_overrides[get_db] = lambda: FakeDB()
    app.dependency_overrides[get_user_from_token] = lambda: make_admin()
    app.dependency_overrides[is_user_admin] = lambda: make_admin()

    import routers.authentication.user as user_router_module
    from lib.mfa.mfa import mfa_runtime

    monkeypatch.setattr(user_router_module, "send_email_in_background", lambda **kwargs: None)
    monkeypatch.setattr(mfa_runtime, "reset_attempts", lambda user_tag: None)
    monkeypatch.setattr(mfa_runtime, "clear_challenge", lambda user_tag: None)
    monkeypatch.setattr(mfa_runtime, "reset_login_failures", lambda key: None)

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


class TestResetAccount:
    def test_reset_sends_new_password_and_disables_mfa(self, admin_client):
        resp = admin_client.post("/api/users/ABCDEFGH/reset")
        assert resp.status_code == 200
        assert resp.json() == {"success": True}
        assert len(UPDATES) == 1
        tag, user_props = UPDATES[0]
        assert tag == "ABCDEFGH"
        assert user_props["password"] == "hashed:plaintext-password"
        assert user_props["mfa_enabled"] is False
        assert user_props["mfa_secret"] is None


class TestResetMFA:
    def test_reset_mfa_disables_mfa_without_touching_password(self, admin_client):
        resp = admin_client.post("/api/users/ABCDEFGH/reset_mfa")
        assert resp.status_code == 200
        assert resp.json() == {"success": True}
        assert len(UPDATES) == 1
        tag, user_props = UPDATES[0]
        assert tag == "ABCDEFGH"
        assert user_props == {"mfa_enabled": False, "mfa_secret": None}


class TestAdminOnly:
    def test_non_admin_users_are_rejected(self, app, monkeypatch):
        monkeypatch.setattr(app, "dependency_overrides", {})
        app.dependency_overrides[get_db] = lambda: FakeDB()
        app.dependency_overrides[get_user_from_token] = lambda: make_standard_user()

        import routers.authentication.user as user_router_module
        from lib.mfa.mfa import mfa_runtime

        monkeypatch.setattr(user_router_module, "send_email_in_background", lambda **kwargs: None)
        monkeypatch.setattr(mfa_runtime, "reset_attempts", lambda user_tag: None)
        monkeypatch.setattr(mfa_runtime, "clear_challenge", lambda user_tag: None)
        monkeypatch.setattr(mfa_runtime, "reset_login_failures", lambda key: None)

        with TestClient(app, raise_server_exceptions=False) as c:
            reset_resp = c.post("/api/users/ABCDEFGH/reset")
            mfa_resp = c.post("/api/users/ABCDEFGH/reset_mfa")
        app.dependency_overrides.clear()
        assert reset_resp.status_code in (401, 403)
        assert mfa_resp.status_code in (401, 403)


class TestUnknownUser:
    def test_reset_of_unknown_user_returns_404(self, app, monkeypatch):
        class EmptyUserDB:
            def get_user_by_tag(self, tag):
                return None

        class EmptyDB:
            users = EmptyUserDB()

        monkeypatch.setattr(app, "dependency_overrides", {})
        app.dependency_overrides[get_db] = lambda: EmptyDB()
        app.dependency_overrides[get_user_from_token] = lambda: make_admin()
        app.dependency_overrides[is_user_admin] = lambda: make_admin()

        with TestClient(app, raise_server_exceptions=False) as c:
            reset_resp = c.post("/api/users/UNKNOWN/reset")
            mfa_resp = c.post("/api/users/UNKNOWN/reset_mfa")
        app.dependency_overrides.clear()
        assert reset_resp.status_code == 404
        assert mfa_resp.status_code == 404
