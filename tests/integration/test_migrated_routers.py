"""
Route-level tests for routers migrated to the get_db dependency.
Demonstrates that any migrated router is testable via FastAPI
dependency_overrides with a fake database.
"""

import sys
import time
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from services.users import get_user_from_token
from lib.database.Database import get_db


class FakeDB:
    def __init__(self):
        self.news = FakeNewsDB()
        self.timeline = FakeTimelineDB()
        self.submission = FakeSubmissionDB()


class FakeNewsDB:
    def __init__(self):
        self.items = {"news-1": {"tag": "news-1", "content": "Hello", "user_tag": "abcdefgh"}}
        self.deleted = []

    def find(self, order, limit):
        return ["news-1"]

    def exists(self, tag):
        return tag in self.items

    def get(self, tag):
        return self.items.get(tag)


class FakeTimelineDB:
    def __init__(self):
        self.inserted = []

    def get_timeline_by_submission_tag(self, submission_tag):
        return []


class FakeSubmissionDB:
    def get_state(self, tag):
        return "active"


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
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers.news.news import router as news_router

    app = FastAPI()
    app.include_router(news_router)
    app.dependency_overrides[get_db] = lambda: FakeDB()
    app.dependency_overrides[get_user_from_token] = lambda: make_user()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestNewsRouter:
    def test_find_news(self, client):
        resp = client.get("/api/news", params={"limit": 1})
        assert resp.status_code == 200
        assert resp.json() == ["news-1"]

    def test_get_existing_news(self, client):
        resp = client.get("/api/news/news-1")
        assert resp.status_code == 200
        assert resp.json()["tag"] == "news-1"

    def test_get_missing_news_404(self, client):
        resp = client.get("/api/news/does-not-exist")
        assert resp.status_code == 404

    def test_unauthenticated_rejected(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.news.news import router as news_router

        app = FastAPI()
        app.include_router(news_router)
        app.dependency_overrides[get_db] = lambda: FakeDB()
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/api/news", params={"limit": 1})
        assert resp.status_code in (401, 403)
