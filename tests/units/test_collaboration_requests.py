import pytest

from config.enums.users.roles import UserRolesEnum
from config.exceptions.HTTPExceptions import submission_tag_not_found, submission_access_forbidden
from config.models.collaborations import CollaborationRequestInput, CollaborationRequestModel, SubmissionExploreModel
from config.models.messages import ConversationInput, MessageInput
from config.models.user import UserModel
from services.encryption import create_password_hash
import time


def make_user(**overrides):
    base = dict(
        tag="abcdefgh",
        firstname="Test",
        lastname="User",
        email="test.user@age.mpg.de",
        created_at=time.time(),
        password="pw-secret-123",
        role=UserRolesEnum.STANDARD,
        mfa_enabled=False,
        allow_login=True,
    )
    base.update(overrides)
    return UserModel(**base)


class FakeCollaborationsDB:
    """Minimal in-memory implementation of the collaboration request flow."""
    def __init__(self, submissions=None, requests=None, groups=None):
        self.submissions = submissions or {}  # tag -> creator_tag
        self.requests = requests or {}        # request_tag -> CollaborationRequestModel
        self.groups = groups or {}            # group_tag -> [user_tags]
        self.collaborators = {}               # submission_tag -> [user_tags]
        self.approved_tags = []

    def create_collaboration_request(self, submission_tag, requested_by, input):
        if submission_tag not in self.submissions:
            raise ValueError("Submission does not exist.")
        for r in self.requests.values():
            if r.submission_tag == submission_tag and r.requested_by == requested_by and r.status == "pending":
                return None
        tag = f"cr-{len(self.requests) + 1}"
        self.requests[tag] = CollaborationRequestModel(
            tag=tag,
            submission_tag=submission_tag,
            requested_by=requested_by,
            requested_for_user_tag=input.requested_for_user_tag,
            requested_for_group_tag=input.requested_for_group_tag,
            message=input.message,
        )
        return tag

    def get_collaboration_request(self, request_tag):
        return self.requests.get(request_tag)

    def has_pending_collaboration_request(self, submission_tag, requested_by):
        return any(r.submission_tag == submission_tag and r.requested_by == requested_by and r.status == "pending"
                   for r in self.requests.values())

    def approve_collaboration_request(self, request_tag, approved_by):
        request = self.requests.get(request_tag)
        if request is None or request.status != "pending":
            return False
        request.status = "approved"
        self.approved_tags.append(request_tag)
        if request.requested_for_group_tag:
            new_collaborators = self.groups.get(request.requested_for_group_tag, [])
        else:
            new_collaborators = [request.requested_for_user_tag or request.requested_by]
        self.collaborators.setdefault(request.submission_tag, []).extend(new_collaborators)
        return True

    def deny_collaboration_request(self, request_tag):
        request = self.requests.get(request_tag)
        if request is None or request.status != "pending":
            return False
        request.status = "denied"
        return True


class FakeDB:
    def __init__(self, collaborations=None, submissions=None, research_groups=None, consortiums=None):
        self.collaborations = collaborations
        self.submissions = submissions
        self.research_groups = research_groups
        self.consortiums = consortiums


class FakeSubmissionsDB:
    def __init__(self, submissions=None, has_access_users=None):
        self.submissions = submissions or {}
        self.has_access_users = has_access_users or set()

    def exists(self, tag):
        return tag in self.submissions

    def has_user_access(self, user_tag, submission_tag):
        return (user_tag, submission_tag) in self.has_access_users

    def get_creator(self, tag):
        return self.submissions.get(tag)


class FakeResearchGroupsDB:
    def __init__(self, groups=None):
        self.groups = groups or {}

    def exists(self, tag):
        return tag in self.groups

    def get_users(self, tag):
        return self.groups.get(tag, [])


class TestCollaborationRequestFlow:

    def test_create_request_returns_tag(self):
        db = FakeCollaborationsDB(submissions={"subm-1": "owner-1"})
        tag = db.create_collaboration_request(
            submission_tag="subm-1", requested_by="user-1",
            input=CollaborationRequestInput(submission_tag="subm-1"))
        assert tag is not None
        assert db.requests[tag].status == "pending"

    def test_duplicate_pending_request_returns_none(self):
        db = FakeCollaborationsDB(submissions={"subm-1": "owner-1"})
        db.create_collaboration_request(submission_tag="subm-1", requested_by="user-1",
                                        input=CollaborationRequestInput(submission_tag="subm-1"))
        tag2 = db.create_collaboration_request(submission_tag="subm-1", requested_by="user-1",
                                               input=CollaborationRequestInput(submission_tag="subm-1"))
        assert tag2 is None

    def test_unknown_submission_raises(self):
        db = FakeCollaborationsDB()
        with pytest.raises(ValueError):
            db.create_collaboration_request(submission_tag="nope", requested_by="user-1",
                                            input=CollaborationRequestInput(submission_tag="nope"))

    def test_approve_adds_requesting_user_as_collaborator(self):
        db = FakeCollaborationsDB(submissions={"subm-1": "owner-1"})
        tag = db.create_collaboration_request(submission_tag="subm-1", requested_by="user-1",
                                              input=CollaborationRequestInput(submission_tag="subm-1"))
        assert db.approve_collaboration_request(tag, approved_by="owner-1") is True
        assert "user-1" in db.collaborators["subm-1"]
        assert db.requests[tag].status == "approved"

    def test_approve_for_group_adds_all_group_members(self):
        db = FakeCollaborationsDB(submissions={"subm-1": "owner-1"}, groups={"rg-1": ["user-1", "user-2"]})
        tag = db.create_collaboration_request(
            submission_tag="subm-1", requested_by="user-1",
            input=CollaborationRequestInput(submission_tag="subm-1", requested_for_group_tag="rg-1"))
        assert db.approve_collaboration_request(tag, approved_by="owner-1") is True
        assert set(db.collaborators["subm-1"]) == {"user-1", "user-2"}

    def test_deny_keeps_collaborators_empty(self):
        db = FakeCollaborationsDB(submissions={"subm-1": "owner-1"})
        tag = db.create_collaboration_request(submission_tag="subm-1", requested_by="user-1",
                                              input=CollaborationRequestInput(submission_tag="subm-1"))
        assert db.deny_collaboration_request(tag) is True
        assert db.collaborators.get("subm-1", []) == []
        assert db.requests[tag].status == "denied"

    def test_approve_twice_fails(self):
        db = FakeCollaborationsDB(submissions={"subm-1": "owner-1"})
        tag = db.create_collaboration_request(submission_tag="subm-1", requested_by="user-1",
                                              input=CollaborationRequestInput(submission_tag="subm-1"))
        assert db.approve_collaboration_request(tag, approved_by="owner-1") is True
        assert db.approve_collaboration_request(tag, approved_by="owner-1") is False


class TestExploreModel:

    def test_explore_model_contains_only_minimal_fields(self):
        model = SubmissionExploreModel(tag="subm-1", title="My dataset",
                                       owner_tag="owner-1", research_group_tag="rg-1")
        dumped = model.model_dump()
        assert set(dumped.keys()) == {
            "tag", "title", "state", "created_at", "owner_tag", "owner_firstname",
            "owner_lastname", "owner_institute", "research_group_tag",
            "research_group_text", "research_group_institute", "has_open_collaboration_request"}
        # no sensitive submission fields (samples, quantifications, metatexts)
        assert "samples" not in dumped and "metatext" not in dumped
