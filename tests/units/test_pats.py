import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.enums.users.pats import PATScopeEnum  # noqa: E402
from config.enums.users.roles import UserRolesEnum  # noqa: E402
from lib.database.abstract.PATs import (  # noqa: E402
    PAT_TOKEN_PREFIX, generate_pat_token, hash_pat_token,
)
import services.pats as pats_service  # noqa: E402


class FakeUser:
    def __init__(self, tag="abcdefgh", role=UserRolesEnum.CURATOR, allow_login=True):
        self.tag = tag
        self.role = role
        self.allow_login = allow_login


class FakePATs:
    def __init__(self, record=None):
        self.record = record
        self.touched = []

    def get_by_hash(self, token_hash):
        return self.record

    def touch(self, pat_tag):
        self.touched.append(pat_tag)


class FakeUsers:
    def __init__(self, user):
        self.user = user

    def get_user_by_tag(self, tag):
        return self.user


class FakeDB:
    def __init__(self, record, user):
        self.pats = FakePATs(record)
        self.users = FakeUsers(user)


def make_record(scopes, pat_tag="pat_abc12345", user_tag="abcdefgh"):
    return {
        "user_tag": user_tag,
        "pat": {"tag": pat_tag, "name": "qc script", "scopes": scopes,
                "created_at": 1, "expires_at": 2, "last_used_at": None, "revoked": False},
    }


@pytest.fixture
def no_rate_limit(monkeypatch):
    monkeypatch.setattr(pats_service.mfa_runtime, "is_login_rate_limited", lambda key: False)
    monkeypatch.setattr(pats_service.mfa_runtime, "register_login_failure", lambda key: 1)
    monkeypatch.setattr(pats_service.mfa_runtime, "reset_login_failures", lambda key: None)
    monkeypatch.setattr(pats_service, "check_user_allowed", lambda exists, user: user)


class TestTokenGeneration:
    def test_token_has_prefix(self):
        assert generate_pat_token().startswith(PAT_TOKEN_PREFIX)

    def test_tokens_are_unique(self):
        assert generate_pat_token() != generate_pat_token()

    def test_hash_is_deterministic_and_not_plaintext(self):
        token = generate_pat_token()
        assert hash_pat_token(token) == hash_pat_token(token)
        assert token not in hash_pat_token(token)


class TestAuthenticatePAT:
    def test_valid_token_returns_owner(self, no_rate_limit):
        record = make_record([PATScopeEnum.QC_UPLOAD.value])
        db = FakeDB(record, FakeUser())
        user, pat = pats_service.authenticate_pat(generate_pat_token(), db)
        assert user.tag == "abcdefgh"
        assert PATScopeEnum.QC_UPLOAD in pat.scopes
        assert db.pats.touched == ["pat_abc12345"]

    def test_unknown_token_raises_401(self, no_rate_limit):
        db = FakeDB(None, FakeUser())
        with pytest.raises(HTTPException) as e:
            pats_service.authenticate_pat(generate_pat_token(), db)
        assert e.value.status_code == 401

    def test_rate_limited_token_raises_429(self, monkeypatch):
        record = make_record([])
        db = FakeDB(record, FakeUser())
        monkeypatch.setattr(pats_service.mfa_runtime, "is_login_rate_limited", lambda key: True)
        with pytest.raises(HTTPException) as e:
            pats_service.authenticate_pat(generate_pat_token(), db)
        assert e.value.status_code == 429


class TestGetCuratorOrQCUploadPAT:
    def make_request(self, token=None):
        class R:
            headers = {}
            if token is not None:
                headers["authorization"] = f"Bearer {token}"
        return R()

    def test_pat_with_scope_and_curator_owner_passes(self, no_rate_limit):
        record = make_record([PATScopeEnum.QC_UPLOAD.value])
        db = FakeDB(record, FakeUser(role=UserRolesEnum.CURATOR))
        user = pats_service.get_curator_or_qc_upload_pat(self.make_request(generate_pat_token()), db=db)
        assert user.tag == "abcdefgh"

    def test_pat_without_scope_rejected(self, no_rate_limit):
        record = make_record([])
        db = FakeDB(record, FakeUser())
        with pytest.raises(HTTPException) as e:
            pats_service.get_curator_or_qc_upload_pat(self.make_request(generate_pat_token()), db=db)
        assert e.value.status_code == 403

    def test_pat_with_standard_role_owner_rejected(self, no_rate_limit):
        record = make_record([PATScopeEnum.QC_UPLOAD.value])
        db = FakeDB(record, FakeUser(role=UserRolesEnum.STANDARD))
        with pytest.raises(HTTPException) as e:
            pats_service.get_curator_or_qc_upload_pat(self.make_request(generate_pat_token()), db=db)
        assert e.value.status_code == 403

    def test_jwt_falls_back_to_curator_check(self, monkeypatch, no_rate_limit):
        db = FakeDB(None, FakeUser())
        monkeypatch.setattr(pats_service, "get_user_from_token", lambda token, db: FakeUser())
        monkeypatch.setattr(pats_service, "is_user_at_least_curator", lambda user: user)
        user = pats_service.get_curator_or_qc_upload_pat(self.make_request("some.jwt.token"), db=db)
        assert user.tag == "abcdefgh"
