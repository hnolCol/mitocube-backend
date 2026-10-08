import time
from datetime import timedelta

import pytest

from lib.mfa.mfa import MFARuntime, mfa_settings


class FakeCollection:
    """Minimal pymongo-like collection stored in memory."""

    def __init__(self):
        self.docs = {}

    def find_one(self, query):
        return self.docs.get(query["user_tag"])

    def find_one_and_update(self, query, update, upsert=False, return_document=None):
        tag = query["user_tag"]
        doc = self.docs.get(tag, {"user_tag": tag, "count": 0})
        if "$inc" in update:
            for k, v in update["$inc"].items():
                doc[k] = doc.get(k, 0) + v
        if "$setOnInsert" in update:
            for k, v in update["$setOnInsert"].items():
                doc.setdefault(k, v)
        if "$set" in update:
            for k, v in update["$set"].items():
                doc[k] = v
        self.docs[tag] = doc
        return doc

    def delete_one(self, query):
        self.docs.pop(query["user_tag"], None)


class TestMFALockout:
    def _runtime(self, max_attempts=3):
        rt = MFARuntime()
        rt.attempts = FakeCollection()
        rt.challenges = FakeCollection()
        global mfa_settings
        mfa_settings.MFA_MAX_ATTEMPTS = max_attempts
        return rt

    def test_single_failure_counted(self):
        rt = self._runtime()
        assert rt.register_failure("user-a") == 1
        assert rt.get_failure_count("user-a") == 1

    def test_failures_accumulate(self):
        rt = self._runtime()
        rt.register_failure("user-a")
        rt.register_failure("user-a")
        assert rt.get_failure_count("user-a") == 2

    def test_locked_out_after_max_attempts(self):
        rt = self._runtime(max_attempts=3)
        for _ in range(3):
            rt.register_failure("user-a")
        assert rt.is_locked_out("user-a") is True

    def test_not_locked_out_below_threshold(self):
        rt = self._runtime(max_attempts=3)
        rt.register_failure("user-a")
        rt.register_failure("user-a")
        assert rt.is_locked_out("user-a") is False

    def test_unknown_user_never_locked(self):
        rt = self._runtime()
        assert rt.is_locked_out("unknown") is False
        assert rt.get_failure_count("unknown") == 0

    def test_reset_attempts_clears_lockout(self):
        rt = self._runtime(max_attempts=2)
        rt.register_failure("user-a")
        rt.register_failure("user-a")
        assert rt.is_locked_out("user-a")
        rt.reset_attempts("user-a")
        assert rt.is_locked_out("user-a") is False


class TestMFAChallenges:
    def _runtime(self):
        rt = MFARuntime()
        rt.attempts = FakeCollection()
        rt.challenges = FakeCollection()
        return rt

    def test_store_and_retrieve(self):
        rt = self._runtime()
        rt.store_challenge("user-a", "123456", ttl=timedelta(minutes=15))
        assert rt.get_challenge_code("user-a") == "123456"

    def test_missing_challenge_returns_none(self):
        rt = self._runtime()
        assert rt.get_challenge_code("nobody") is None

    def test_clear_challenge(self):
        rt = self._runtime()
        rt.store_challenge("user-a", "123456", ttl=timedelta(minutes=15))
        rt.clear_challenge("user-a")
        assert rt.get_challenge_code("user-a") is None

    def test_challenge_overwritten_on_new_request(self):
        rt = self._runtime()
        rt.store_challenge("user-a", "111111", ttl=timedelta(minutes=15))
        rt.store_challenge("user-a", "222222", ttl=timedelta(minutes=15))
        assert rt.get_challenge_code("user-a") == "222222"
