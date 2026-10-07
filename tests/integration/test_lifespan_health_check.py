"""
Tests for the startup health checks (Neo4j + MongoDB runtimes) in
lib/lifespan.py. All runtimes use log-and-continue semantics: a failing
dependency is logged but never aborts the app process.
"""

import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from lib.lifespan import lifespan
from lib.database import Database as database_module


class NullRuntime:
    """Stands in for a Mongo-backed runtime; records health_check calls."""

    def __init__(self, fail_startup=False, fail_health=False):
        self.started = False
        self.health_checked = False
        self.fail_startup = fail_startup
        self.fail_health = fail_health

    async def startup(self):
        if self.fail_startup:
            raise ConnectionError("mongo unreachable")
        self.started = True

    def health_check(self):
        self.health_checked = True
        if self.fail_health:
            raise ConnectionError("mongo unreachable")
        return True

    async def shutdown(self):
        pass


class RecordingDBProxy:
    def __init__(self, fail=False):
        self.called = False
        self.fail = fail

    def health_check(self):
        self.called = True
        if self.fail:
            raise ConnectionError("db unreachable")
        return True


@pytest.fixture
def stub_runtimes(monkeypatch):
    import lib.lifespan as lifespan_module
    runtimes = {
        "ai": NullRuntime(),
        "mfa": NullRuntime(),
        "cache": NullRuntime(),
    }
    # ai_agent_runtime is imported lazily inside the lifespan; stub the
    # module it would import from so the stub is picked up either way.
    import sys, types
    fake_ai_runtime_module = types.ModuleType("lib.ai.agent.runtime")
    fake_ai_runtime_module.ai_agent_runtime = runtimes["ai"]
    real_ai = sys.modules.get("lib.ai.agent.runtime")
    sys.modules["lib.ai.agent.runtime"] = fake_ai_runtime_module
    monkeypatch.setattr(lifespan_module, "mfa_runtime", runtimes["mfa"])
    monkeypatch.setattr(lifespan_module, "db_cache_runtime", runtimes["cache"])

    class _Run:
        pass
    import pytest as _pytest

    yield runtimes

    if real_ai is not None:
        sys.modules["lib.ai.agent.runtime"] = real_ai
    else:
        sys.modules.pop("lib.ai.agent.runtime", None)


def _make_app():
    from fastapi import FastAPI
    return FastAPI(lifespan=lifespan)


class TestStartupHealthCheck:
    def test_health_check_runs_at_startup(self, stub_runtimes, monkeypatch):
        proxy = RecordingDBProxy()
        monkeypatch.setattr(database_module.Database, "DB", staticmethod(lambda: proxy))

        from fastapi.testclient import TestClient
        with TestClient(_make_app()):
            assert proxy.called is True
            assert all(r.health_checked for r in stub_runtimes.values())

    def test_failed_neo4j_health_check_does_not_crash_startup(self, stub_runtimes, monkeypatch):
        proxy = RecordingDBProxy(fail=True)
        monkeypatch.setattr(database_module.Database, "DB", staticmethod(lambda: proxy))

        from fastapi.testclient import TestClient
        with TestClient(_make_app()):
            assert proxy.called is True
            assert all(r.started for r in stub_runtimes.values())

    def test_failed_mongo_runtime_does_not_crash_startup(self, stub_runtimes, monkeypatch):
        proxy = RecordingDBProxy()
        monkeypatch.setattr(database_module.Database, "DB", staticmethod(lambda: proxy))
        stub_runtimes["mfa"].fail_startup = True

        from fastapi.testclient import TestClient
        with TestClient(_make_app()):
            assert proxy.called is True
            assert stub_runtimes["mfa"].started is False
            assert stub_runtimes["ai"].started is True
