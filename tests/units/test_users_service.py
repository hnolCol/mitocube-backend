import time

import pytest
from pydantic import SecretStr, ValidationError

from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from services.encryption import create_password_hash
from tests.units.conftest import TEST_JWT_KEY

from fastapi import HTTPException
from jose import jwt

import services.users as users_service

check_token_verified = users_service.check_token_verified
check_user_allowed = users_service.check_user_allowed
is_user_admin = users_service.is_user_admin
is_user_at_least_curator = users_service.is_user_at_least_curator


@pytest.fixture(autouse=True)
def _no_user_cache(monkeypatch):
    """Bypass the Mongo-backed user cache in unit tests.

    get_user_from_token consults the cache first; unit tests exercise the
    DB path, so the cache is stubbed to always miss. The login rate
    limiter is stubbed to never limit; dedicated tests cover the limiter.
    """
    monkeypatch.setattr(users_service, "get_cached_user", lambda tag: None)
    monkeypatch.setattr(users_service, "cache_user", lambda user, cache_time=None: None)

    from lib.mfa import mfa as mfa_module

    class _LimiterStub:
        def __init__(self):
            self.failures = {}
            self.limited = False
            self.resets = []

        def is_login_rate_limited(self, key):
            return self.limited

        def register_login_failure(self, key):
            self.failures[key] = self.failures.get(key, 0) + 1
            return self.failures[key]

        def reset_login_failures(self, key):
            self.resets.append(key)

    limiter = _LimiterStub()
    monkeypatch.setattr(mfa_module.mfa_runtime, "is_login_rate_limited", limiter.is_login_rate_limited)
    monkeypatch.setattr(mfa_module.mfa_runtime, "register_login_failure", limiter.register_login_failure)
    monkeypatch.setattr(mfa_module.mfa_runtime, "reset_login_failures", limiter.reset_login_failures)


def get_user_from_login(form_data, db, request=None):
    return users_service.get_user_from_login(form_data, db, request)


def get_user_from_token(claims, db):
    return users_service.get_user_from_token(claims, db)


def is_creator_of_submission_or_curator(submission_tag, user, db):
    return users_service.is_creator_of_submission_or_curator(submission_tag, user, db)


class FakeUserDB:
    def __init__(self, users_by_tag=None, users_by_email=None):
        self.by_tag = users_by_tag or {}
        self.by_email = users_by_email or {}

    def get_user_by_tag(self, tag):
        return self.by_tag.get(tag)

    def get_user_by_email(self, email):
        return self.by_email.get(email)

    def get_users_by_tags(self, tags):
        return [self.by_tag.get(t) for t in tags]


class FakeSubmissionDB:
    def __init__(self, creators=None):
        self.creators = creators or {}

    def exists(self, tag):
        return tag in self.creators

    def get_creator(self, tag):
        return self.creators.get(tag)


class FakeDB:
    def __init__(self, users=None, submissions=None):
        self.users = users or FakeUserDB()
        self.submissions = submissions or FakeSubmissionDB()


def make_user(**overrides):
    base = dict(
        tag="abcdefgh",
        firstname="Test",
        lastname="User",
        email="test.user@age.mpg.de",
        created_at=time.time(),
        password=SecretStr(create_password_hash("pw-secret-123")),
        role=UserRolesEnum.STANDARD,
        mfa_enabled=False,
        allow_login=True,
    )
    base.update(overrides)
    return UserModel(**base)


def make_verified_claims(tag="abcdefgh", **extra):
    claims = {"tag": tag, "verified": True}
    claims.update(extra)
    return claims


def make_token(payload=None):
    base = {"tag": "abcdefgh", "verified": True}
    if payload:
        base.update(payload)
    base.setdefault("exp", time.time() + 3600)
    return jwt.encode(base, TEST_JWT_KEY, algorithm="HS256")


class TestUserModelValidation:
    def test_valid_email_domain_accepted(self):
        u = make_user(email="someone@age.mpg.de")
        assert u.email == "someone@age.mpg.de"

    def test_disallowed_email_domain_rejected(self):
        with pytest.raises(ValidationError):
            make_user(email="someone@gmail.com")

    def test_cleverly_disguised_domain_rejected(self):
        with pytest.raises(ValidationError):
            make_user(email="someone@age.mpg.de.gmail.net")

    def test_password_never_serialized_as_plaintext(self):
        u = make_user()
        dump = u.model_dump(mode="json")
        assert "pw-secret-123" not in str(dump)

    def test_default_role_is_standard(self):
        assert make_user().role == UserRolesEnum.STANDARD

    def test_role_hierarchy(self):
        assert UserRolesEnum.GUEST < UserRolesEnum.STANDARD
        assert UserRolesEnum.STANDARD < UserRolesEnum.CURATOR
        assert UserRolesEnum.CURATOR < UserRolesEnum.ADMIN


class TestCheckUserAllowed:
    def test_existing_allowed_user_passes(self):
        u = make_user()
        assert check_user_allowed(True, u) is u

    def test_nonexistent_user_raises(self):
        from config.exceptions.HTTPExceptions import user_form_data_incorrect
        with pytest.raises(HTTPException) as e:
            check_user_allowed(False, None)
        assert e.value.status_code == user_form_data_incorrect.status_code

    def test_blocked_user_raises(self):
        from config.exceptions.HTTPExceptions import user_blocked
        with pytest.raises(HTTPException) as e:
            check_user_allowed(True, make_user(allow_login=False))
        assert e.value.status_code == user_blocked.status_code


class TestCheckTokenVerified:
    def test_verified_token_passes(self, token_settings):
        assert check_token_verified(make_verified_claims())["tag"] == "abcdefgh"

    def test_unverified_token_raises(self, token_settings):
        tok = make_token({"verified": False})
        with pytest.raises(HTTPException):
            check_token_verified(tok)

    def test_missing_verified_claim_raises(self, token_settings):
        tok = jwt.encode({"tag": "abcdefgh", "exp": time.time() + 3600}, TEST_JWT_KEY, algorithm="HS256")
        with pytest.raises(HTTPException):
            check_token_verified(tok)


class TestGetUserFromToken:
    def test_valid_token_returns_user(self, token_settings):
        user = make_user()
        db = FakeDB(users=FakeUserDB(users_by_tag={user.tag: user}))
        result = get_user_from_token(make_verified_claims(), db)
        assert result.tag == user.tag

    def test_unknown_tag_raises(self, token_settings):
        db = FakeDB()
        with pytest.raises(HTTPException):
            get_user_from_token(make_verified_claims(), db)

    def test_blocked_user_raises(self, token_settings):
        user = make_user(allow_login=False)
        db = FakeDB(users=FakeUserDB(users_by_tag={user.tag: user}))
        with pytest.raises(HTTPException):
            get_user_from_token(make_verified_claims(), db)


class TestGetUserFromLogin:
    def _form(self, username, password):
        from fastapi.security import OAuth2PasswordRequestForm
        return OAuth2PasswordRequestForm(username=username, password=password, scope="")

    def test_correct_credentials(self, token_settings):
        user = make_user()
        db = FakeDB(users=FakeUserDB(users_by_email={user.email: user}))
        result = get_user_from_login(self._form(user.email, "pw-secret-123"), db)
        assert result.tag == user.tag

    def test_wrong_password_raises(self, token_settings):
        user = make_user()
        db = FakeDB(users=FakeUserDB(users_by_email={user.email: user}))
        with pytest.raises(HTTPException):
            get_user_from_login(self._form(user.email, "wrong"), db)

    def test_unknown_email_raises(self, token_settings):
        db = FakeDB()
        with pytest.raises(HTTPException):
            get_user_from_login(self._form("nobody@age.mpg.de", "pw-secret-123"), db)

    def test_rate_limited_email_rejected_before_password_check(self, token_settings, monkeypatch):
        """A limited email gets 429 without touching the DB or password."""
        from lib.mfa import mfa as mfa_module
        from config.exceptions.HTTPExceptions import login_rate_limited
        import services.users as users_service

        class _Limited:
            def is_login_rate_limited(self, key):
                return key.startswith("email:")

            def register_login_failure(self, key):
                pass

            def reset_login_failures(self, key):
                pass

        monkeypatch.setattr(mfa_module.mfa_runtime, "is_login_rate_limited", _Limited().is_login_rate_limited)

        db = FakeDB()
        try:
            get_user_from_login(self._form("victim@age.mpg.de", "pw-secret-123"), db)
            assert False, "expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 429
            assert e is login_rate_limited

    def test_rate_limited_ip_rejected(self, token_settings, monkeypatch):
        from lib.mfa import mfa as mfa_module
        from fastapi import HTTPException as _HTTP

        class _LimitedIP:
            def is_login_rate_limited(self, key):
                return key.startswith("ip:")

            def register_login_failure(self, key):
                pass

            def reset_login_failures(self, key):
                pass

        monkeypatch.setattr(mfa_module.mfa_runtime, "is_login_rate_limited", _LimitedIP().is_login_rate_limited)

        class _FakeRequest:
            class client:
                host = "10.0.0.1"

        db = FakeDB()
        try:
            get_user_from_login(self._form("victim@age.mpg.de", "pw-secret-123"), db, request=_FakeRequest())
            assert False, "expected HTTPException"
        except _HTTP as e:
            assert e.status_code == 429

    def test_failed_password_registers_failure(self, token_settings, monkeypatch):
        from lib.mfa import mfa as mfa_module

        registered = []

        class _Recording:
            def __init__(self):
                self.counts = {}

            def is_login_rate_limited(self, key):
                return False

            def register_login_failure(self, key):
                registered.append(key)
                return len(registered)

            def reset_login_failures(self, key):
                registered.append(("reset", key))

        monkeypatch.setattr(mfa_module.mfa_runtime, "is_login_rate_limited", _Recording().is_login_rate_limited)
        monkeypatch.setattr(mfa_module.mfa_runtime, "register_login_failure", lambda key: registered.append(key))

        user = make_user()
        db = FakeDB(users=FakeUserDB(users_by_email={user.email: user}))
        with pytest.raises(HTTPException):
            get_user_from_login(self._form(user.email, "wrong-password"), db)
        assert any(k == f"email:{user.email}" for k in registered)


class TestRoleGates:
    def test_standard_user_rejected_from_curator_gate(self):
        with pytest.raises(HTTPException):
            is_user_at_least_curator(make_user(role=UserRolesEnum.STANDARD))

    def test_curator_passes_curator_gate(self):
        u = make_user(role=UserRolesEnum.CURATOR)
        assert is_user_at_least_curator(u) is u

    def test_admin_passes_curator_gate(self):
        u = make_user(role=UserRolesEnum.ADMIN)
        assert is_user_at_least_curator(u) is u

    def test_standard_user_rejected_from_admin_gate(self):
        with pytest.raises(HTTPException):
            is_user_admin(make_user(role=UserRolesEnum.CURATOR))

    def test_admin_passes_admin_gate(self):
        u = make_user(role=UserRolesEnum.ADMIN)
        assert is_user_admin(u) is u


class TestIsCreatorOfSubmissionOrCurator:
    def test_creator_passes(self, token_settings):
        user = make_user()
        db = FakeDB(submissions=FakeSubmissionDB(creators={"subm-1": user.tag}))
        assert is_creator_of_submission_or_curator("subm-1", user, db) is user

    def test_non_creator_standard_user_rejected(self, token_settings):
        user = make_user()
        db = FakeDB(submissions=FakeSubmissionDB(creators={"subm-1": "otherusr"}))
        with pytest.raises(HTTPException):
            is_creator_of_submission_or_curator("subm-1", user, db)

    def test_curator_always_passes(self, token_settings):
        user = make_user(role=UserRolesEnum.CURATOR)
        db = FakeDB(submissions=FakeSubmissionDB(creators={"subm-1": "otherusr"}))
        assert is_creator_of_submission_or_curator("subm-1", user, db) is user

    def test_unknown_submission_raises(self, token_settings):
        user = make_user()
        db = FakeDB(submissions=FakeSubmissionDB(creators={}))
        from config.exceptions.HTTPExceptions import submission_tag_not_found
        with pytest.raises(HTTPException) as e:
            is_creator_of_submission_or_curator("nope", user, db)
        assert e.value.status_code == submission_tag_not_found.status_code
