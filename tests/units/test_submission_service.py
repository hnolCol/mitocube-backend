import time

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from config.enums.users.roles import UserRolesEnum
from config.exceptions.HTTPExceptions import submission_tag_not_found, submission_access_forbidden
from config.models.user import UserModel
from services.encryption import create_password_hash
from services.submission import check_submission_access, check_submission_tags_access


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


class FakeSubmissionDB:
    def __init__(self, tags=None):
        self.tags = set(tags or [])

    def exists(self, tag):
        return tag in self.tags


class FakeSubmissionFilter:
    def __init__(self, accessible_tags=None):
        self.accessible_tags = set(accessible_tags or [])

    def has_user_access(self, user_tag, submission_tag):
        return submission_tag in self.accessible_tags


class FakeDB:
    def __init__(self, tags=None, accessible_tags=None):
        self.submissions = FakeSubmissionDB(tags=tags)
        self.submission_filter = FakeSubmissionFilter(accessible_tags=accessible_tags)


class TestCheckSubmissionAccess:
    def test_missing_submission_raises_not_found(self):
        user = make_user()
        db = FakeDB(tags=["subm-1"], accessible_tags=["subm-1"])
        with pytest.raises(HTTPException) as e:
            check_submission_access("missing", user, db)
        assert e.value.status_code == submission_tag_not_found.status_code

    def test_no_access_raises_forbidden(self):
        user = make_user()
        db = FakeDB(tags=["subm-1"], accessible_tags=[])
        with pytest.raises(HTTPException) as e:
            check_submission_access("subm-1", user, db)
        assert e.value.status_code == submission_access_forbidden.status_code

    def test_access_granted_returns_true(self):
        user = make_user()
        db = FakeDB(tags=["subm-1"], accessible_tags=["subm-1"])
        assert check_submission_access("subm-1", user, db) is True


class TestCheckSubmissionTagsAccess:
    def test_none_passes(self):
        user = make_user()
        db = FakeDB()
        assert check_submission_tags_access(None, user, db) is True

    def test_empty_string_passes(self):
        user = make_user()
        db = FakeDB()
        assert check_submission_tags_access("", user, db) is True

    def test_string_without_access_raises(self):
        user = make_user()
        db = FakeDB(tags=["subm-1", "subm-2"], accessible_tags=["subm-1"])
        with pytest.raises(HTTPException) as e:
            check_submission_tags_access("subm-1;subm-2", user, db)
        assert e.value.status_code == submission_access_forbidden.status_code

    def test_list_with_access_passes(self):
        user = make_user()
        db = FakeDB(tags=["subm-1", "subm-2"], accessible_tags=["subm-1", "subm-2"])
        assert check_submission_tags_access(["subm-1", "subm-2"], user, db) is True

    def test_missing_tag_in_list_raises_not_found(self):
        user = make_user()
        db = FakeDB(tags=["subm-1"], accessible_tags=["subm-1"])
        with pytest.raises(HTTPException) as e:
            check_submission_tags_access("subm-1;nope", user, db)
        assert e.value.status_code == submission_tag_not_found.status_code
