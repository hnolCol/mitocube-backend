import time
from typing import List, Dict, Optional

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from config.enums.users.roles import UserRolesEnum
from config.exceptions.HTTPExceptions import submission_access_forbidden, submission_tag_not_found
from config.models.user import UserModel
from services.encryption import create_password_hash


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


class FakeHeadsDB:
    def __init__(self, heads=None):
        # group_tag -> list of head user tags
        self.heads = heads or {}

    def get_heads(self, tag):
        return self.heads.get(tag, [])

    def is_head(self, user_tag, group_tag=None):
        if group_tag is not None:
            return user_tag in self.heads.get(group_tag, [])
        return any(user_tag in hs for hs in self.heads.values())


class FakeConsortiumDB:
    def __init__(self):
        self.shares = {}  # (consortium, submission) -> dict(status=..., requested_by=..., approved_by=...)

    def share_submission(self, consortium_tag, submission_tag, user_tag, approved=False):
        if (consortium_tag, submission_tag) in self.shares:
            return True
        self.shares[(consortium_tag, submission_tag)] = dict(
            status="approved" if approved else "pending",
            requested_by=user_tag,
        )
        return True

    def approve_share_request(self, consortium_tag, submission_tag, user_tag):
        share = self.shares.get((consortium_tag, submission_tag))
        if share is None or share["status"] != "pending":
            return False
        share["status"] = "approved"
        share["approved_by"] = user_tag
        return True

    def deny_share_request(self, consortium_tag, submission_tag):
        share = self.shares.pop((consortium_tag, submission_tag), None)
        return share is not None and share["status"] == "pending"


class TestIsHead:
    def test_head_of_group(self):
        db = FakeHeadsDB(heads={"rg-1": ["pi-1"]})
        assert db.is_head("pi-1", "rg-1") is True

    def test_non_head_of_group(self):
        db = FakeHeadsDB(heads={"rg-1": ["pi-1"]})
        assert db.is_head("member-1", "rg-1") is False

    def test_head_of_any_group(self):
        db = FakeHeadsDB(heads={"rg-1": ["pi-1"], "rg-2": ["pi-2"]})
        assert db.is_head("pi-2") is True

    def test_member_of_any_group_is_not_head(self):
        db = FakeHeadsDB(heads={"rg-1": ["pi-1"]})
        assert db.is_head("member-1") is False


class TestShareApprovalFlow:
    def test_pending_share_does_not_exist_as_approved(self):
        db = FakeConsortiumDB()
        db.share_submission("cons-1", "subm-1", user_tag="owner-1", approved=False)
        assert db.shares[("cons-1", "subm-1")]["status"] == "pending"

    def test_immediate_share_is_approved(self):
        db = FakeConsortiumDB()
        db.share_submission("cons-1", "subm-1", user_tag="pi-1", approved=True)
        assert db.shares[("cons-1", "subm-1")]["status"] == "approved"

    def test_approve_pending_request(self):
        db = FakeConsortiumDB()
        db.share_submission("cons-1", "subm-1", user_tag="owner-1", approved=False)
        assert db.approve_share_request("cons-1", "subm-1", user_tag="pi-1") is True
        assert db.shares[("cons-1", "subm-1")]["status"] == "approved"
        assert db.shares[("cons-1", "subm-1")]["approved_by"] == "pi-1"

    def test_approve_non_pending_fails(self):
        db = FakeConsortiumDB()
        db.share_submission("cons-1", "subm-1", user_tag="pi-1", approved=True)
        assert db.approve_share_request("cons-1", "subm-1", user_tag="pi-1") is False

    def test_deny_pending_request_removes_relation(self):
        db = FakeConsortiumDB()
        db.share_submission("cons-1", "subm-1", user_tag="owner-1", approved=False)
        assert db.deny_share_request("cons-1", "subm-1") is True
        assert ("cons-1", "subm-1") not in db.shares

    def test_deny_approved_request_fails(self):
        db = FakeConsortiumDB()
        db.share_submission("cons-1", "subm-1", user_tag="pi-1", approved=True)
        assert db.deny_share_request("cons-1", "subm-1") is False
