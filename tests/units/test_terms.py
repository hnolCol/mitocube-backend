import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

import services.terms as terms_service  # noqa: E402


class FakeSettings:
    def __init__(self, use_terms_file):
        self.use_terms_file = use_terms_file


class FakeUser:
    def __init__(self, agreed_to_terms):
        self.agreed_to_terms = agreed_to_terms
        self.tag = "abcdefgh"


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch, tmp_path):
    terms_service.terms_of_use_exist.cache_clear()
    yield
    terms_service.terms_of_use_exist.cache_clear()


class TestTermsExist:
    def test_document_with_terms_exists(self, tmp_path, monkeypatch):
        p = tmp_path / "terms.json"
        p.write_text('{"title": "Data Policy", "data_policy_sections": [{"header": "h", "text": "t"}]}')
        monkeypatch.setattr(terms_service, "get_general_settings", lambda: FakeSettings(p))
        assert terms_service.terms_of_use_exist() is True

    def test_empty_document_is_no_terms(self, tmp_path, monkeypatch):
        p = tmp_path / "terms.json"
        p.write_text("{}")
        monkeypatch.setattr(terms_service, "get_general_settings", lambda: FakeSettings(p))
        assert terms_service.terms_of_use_exist() is False

    def test_placeholder_document_is_no_terms(self, tmp_path, monkeypatch):
        p = tmp_path / "terms.json"
        p.write_text('{"title": null, "data_policy_sections": []}')
        monkeypatch.setattr(terms_service, "get_general_settings", lambda: FakeSettings(p))
        assert terms_service.terms_of_use_exist() is False

    def test_unconfigured_is_no_terms(self, monkeypatch):
        monkeypatch.setattr(terms_service, "get_general_settings", lambda: FakeSettings(None))
        assert terms_service.terms_of_use_exist() is False

    def test_unparseable_file_is_no_terms(self, tmp_path, monkeypatch):
        p = tmp_path / "terms.txt"
        p.write_text("not json at all")
        monkeypatch.setattr(terms_service, "get_general_settings", lambda: FakeSettings(p))
        assert terms_service.terms_of_use_exist() is False


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

    def test_without_terms_document_everyone_passes(self, monkeypatch):
        monkeypatch.setattr(terms_service, "get_general_settings", lambda: FakeSettings(None))
        terms_service.raise_if_terms_not_accepted(FakeUser(agreed_to_terms=False), FakeDB([FakeStatus(must_agree=False)]))


class TestExemptPaths:
    @pytest.mark.parametrize("path", [
        "/api/info/terms",
        "/api/auth/token/valid",
        "/api/auth/user/abcdefgh/useterms",
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
        "/api/info/terms/other",
    ])
    def test_non_exempt_paths(self, path):
        assert terms_service.is_terms_exempt_path(path) is False


class TestAcceptUseTermsEndpoint:
    def test_accept_records_flag(self, monkeypatch):
        import routers.authentication.user as user_router
        updated = {}

        class FakeUsers:
            def update(self, tag, user_props):
                updated.update(user_props)
                return True

        class FakeDB:
            users = FakeUsers()

        result = user_router.accept_use_terms("abcdefgh", accept=True, user=FakeUser(agreed_to_terms=False), db=FakeDB())
        assert result["success"] is True
        assert updated == {"agreed_to_terms": True}

    def test_other_user_rejected(self):
        import routers.authentication.user as user_router
        with pytest.raises(HTTPException) as e:
            user_router.accept_use_terms("otheruser", accept=True, user=FakeUser(agreed_to_terms=False), db=None)
        assert e.value.status_code == 403
