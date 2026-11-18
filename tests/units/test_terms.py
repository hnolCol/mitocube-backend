import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

import services.terms as terms_service  # noqa: E402


class FakeUser:
    def __init__(self, agreed_to_terms):
        self.agreed_to_terms = agreed_to_terms
        self.tag = "abcdefgh"


class FakePolicy:
    def __init__(self, statuses):
        self.statuses = statuses
        self.user_tag = None

    def get_status(self, user_tag):
        self.user_tag = user_tag
        return self.statuses


class FakeDB:
    def __init__(self, statuses):
        self.policy = FakePolicy(statuses)


class FakeStatus:
    def __init__(self, must_agree):
        self.must_agree = must_agree


class TestRaiseIfTermsNotAccepted:
    def test_agreed_user_passes(self):
        terms_service.raise_if_terms_not_accepted(FakeUser(agreed_to_terms=True), FakeDB([FakeStatus(must_agree=False)]))

    def test_unaccepted_user_gets_403(self):
        user = FakeUser(agreed_to_terms=False)
        with pytest.raises(HTTPException) as e:
            terms_service.raise_if_terms_not_accepted(user, FakeDB([FakeStatus(must_agree=True)]))
        assert e.value.status_code == 403

    def test_pending_agreement_is_checked_for_the_calling_user(self):
        db = FakeDB([FakeStatus(must_agree=True)])
        user = FakeUser(agreed_to_terms=False)
        with pytest.raises(HTTPException):
            terms_service.raise_if_terms_not_accepted(user, db)
        assert db.policy.user_tag == user.tag

    def test_without_required_policy_everyone_passes(self):
        terms_service.raise_if_terms_not_accepted(FakeUser(agreed_to_terms=False), FakeDB([FakeStatus(must_agree=False)]))

    def test_without_db_everyone_passes(self):
        terms_service.raise_if_terms_not_accepted(FakeUser(agreed_to_terms=False))


class TestExemptPaths:
    @pytest.mark.parametrize("path", [
        "/api/auth/token/valid",
        "/api/policy",
        "/api/policy/status",
        "/api/policy/abcdefgh",
        "/api/policy/abcdefgh/agree",
    ])
    def test_exempt_paths(self, path):
        assert terms_service.is_terms_exempt_path(path) is True

    @pytest.mark.parametrize("path", [
        "/api/auth/user/abcdefgh",
        "/api/proteins/abc",
        "/api/performance/runs/insert",
        "/api/info/terms",
        "/api/policyother",
        "/api/auth/user/abcdefgh/useterms",
    ])
    def test_non_exempt_paths(self, path):
        assert terms_service.is_terms_exempt_path(path) is False
