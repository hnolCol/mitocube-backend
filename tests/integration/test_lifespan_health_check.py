"""
Tests for the startup database health check in lib/lifespan.py.
"""

import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from lib.lifespan import lifespan
from lib.database import Database as database_module


class RecordingProxy:
    """Stands in for the lazy DB proxy; records health_check calls."""

    def __init__(self, fail=False):
        self.called = False
        self.fail = fail

    def health_check(self):
        self.called = True
        if self.fail:
            raise ConnectionError("db unreachable")
        return True


@pytest.fixture
def stub_runtime(monkeypatch):
    """Neutralize the Mongo-backed runtimes so no network is touched."""
    class _Null:
        async def startup(self):
            pass

        async def shutdown(self):
            pass

    import lib.lifespan as lifespan_module
    monkeypatch.setattr(lifespan_module, "ai_agent_runtime", _Null())
    monkeypatch.setattr(lifespan_module, "mfa_runtime", _Null())
    monkeypatch.setattr(lifespan_module, "db_cache_runtime", _Null())


class TestStartupHealthCheck:
    def test_health_check_runs_at_startup(self, stub_runtime, monkeypatch):
        proxy = RecordingProxy()
        monkeypatch.setattr(database_module.Database, "DB", staticmethod(lambda: proxy))

        from fastapi import FastAPI
        app = FastAPI(lifespan=lifespan)

        from fastapi.testclient import TestClient
        with TestClient(app):
            assert proxy.called is True

    def test_failed_health_check_does_not_crash_startup(self, stub_runtime, monkeypatch):
        """A broken DB is logged loudly but must not kill the app process."""
        proxy = RecordingProxy(fail=True)
        monkeypatch.setattr(database_module.Database, "DB", staticmethod(lambda: proxy))

        from fastapi import FastAPI
        app = FastAPI(lifespan=lifespan)

        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            resp = client.get("/")
        assert proxy.called is True
