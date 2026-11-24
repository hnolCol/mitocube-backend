import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

import pytest  # noqa: E402

from lib.database.neo4j.Policy import Neo4JPolicy  # noqa: E402


class FakeDriver:
    def __init__(self, tags):
        self.tags = tags
        self.calls = 0

    def execute_query(self, query, **kwargs):
        self.calls += 1
        return self.tags


@pytest.fixture(autouse=True)
def clear_cache():
    Neo4JPolicy._exists_cache["expires"] = 0.0
    yield
    Neo4JPolicy._exists_cache["expires"] = 0.0


def make_policy(tags):
    return Neo4JPolicy(FakeDriver(tags))


class TestExists:
    def test_false_without_policies(self):
        policy = make_policy([])
        assert policy.exists() is False

    def test_true_with_policies(self):
        policy = make_policy(["terms-of-use"])
        assert policy.exists() is True

    def test_result_is_cached_until_ttl(self):
        policy = make_policy([])
        policy.exists()
        policy.exists()
        assert policy._driver.calls == 1

    def test_cache_expires_after_ttl(self, monkeypatch):
        import lib.database.neo4j.Policy as policy_module

        fake_time = [100.0]
        monkeypatch.setattr(policy_module.time, "monotonic", lambda: fake_time[0])
        policy = make_policy([])
        assert policy.exists() is False
        fake_time[0] += Neo4JPolicy._EXISTS_TTL_SECONDS
        policy.exists()
        assert policy._driver.calls == 2

    def test_invalidation_forces_a_new_query(self):
        policy = make_policy([])
        policy.exists()
        policy._invalidate_exists_cache()
        policy.exists()
        assert policy._driver.calls == 2


class TestCachedShortCircuits:
    def test_get_status_skips_the_database_without_policies(self):
        policy = make_policy([])
        assert policy.get_status("user") == []
        assert policy._driver.calls == 1

    def test_list_skips_the_database_without_policies(self):
        policy = make_policy([])
        assert policy.list() == []
        assert policy._driver.calls == 1
