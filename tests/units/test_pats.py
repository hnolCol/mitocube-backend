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
        self.admin_revocations = []
        self.creation_blocked = {}

    def get_by_hash(self, token_hash):
        return self.record

    def touch(self, pat_tag):
        self.touched.append(pat_tag)

    def revoke_by_admin(self, pat_tag, revoked_by):
        self.admin_revocations.append((pat_tag, revoked_by))
        return True

    def set_creation_blocked(self, user_tag, blocked):
        self.creation_blocked[user_tag] = blocked
        return True


class FakeUsers:
    def __init__(self, user):
        self.user = user

    def get_user_by_tag(self, tag):
        return self.user


class FakePolicyDB:
    def get_status(self, user_tag):
        return []


class FakeDB:
    def __init__(self, record, user):
        self.pats = FakePATs(record)
        self.users = FakeUsers(user)
        self.policy = FakePolicyDB()


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


class TestAuthenticatePATAuthz:
    def test_standard_role_owner_rejected_at_auth(self, no_rate_limit):
        record = make_record([PATScopeEnum.QC_UPLOAD.value])
        db = FakeDB(record, FakeUser(role=UserRolesEnum.STANDARD))
        with pytest.raises(HTTPException) as e:
            pats_service.authenticate_pat(generate_pat_token(), db)
        assert e.value.status_code == 403

    def test_router_endpoints_require_curator(self):
        import routers.authentication.pats as pats_router
        import services.users as users_service
        for dependency in pats_router.router.dependencies:
            assert dependency.dependency is users_service.is_user_at_least_curator
        assert pats_router.create_pat.__defaults__[0].dependency is users_service.is_user_at_least_curator
        assert pats_router.list_pats.__defaults__[0].dependency is users_service.is_user_at_least_curator
        assert pats_router.revoke_pat.__defaults__[0].dependency is users_service.is_user_at_least_curator


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


class TestAdminEndpoints:
    def test_admin_revoke_records_admin(self):
        db = FakeDB(None, FakeUser())
        import routers.authentication.pats as pats_router
        result = pats_router.revoke_pat_as_admin("pat_abc12345", user=FakeUser(tag="admin1"), db=db)
        assert result["revoked_by"] == "admin1"
        assert db.pats.admin_revocations == [("pat_abc12345", "admin1")]

    def test_set_creation_blocked(self):
        db = FakeDB(None, FakeUser())
        import routers.authentication.pats as pats_router
        result = pats_router.set_pat_creation_blocked("abcdefgh", props=pats_router.PATCreationBlockModel(blocked=True),
                                                      user=FakeUser(tag="admin1"), db=db)
        assert result["creation_blocked"] is True
        assert db.pats.creation_blocked["abcdefgh"] is True

    def test_create_maps_blocked_to_403(self):
        db = FakeDB(None, FakeUser())
        import routers.authentication.pats as pats_router

        class BlockedStore:
            def create(self, **kwargs):
                raise ValueError("Personal access token creation is blocked for user 'abcdefgh'.")

        db.pats = BlockedStore()
        with pytest.raises(HTTPException) as e:
            pats_router.create_pat(props=pats_router.PATInsertModel(name="x", scopes=[PATScopeEnum.QC_UPLOAD]),
                                   user=FakeUser(), db=db)
        assert e.value.status_code == 403
