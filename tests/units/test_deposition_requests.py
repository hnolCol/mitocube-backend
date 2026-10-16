import pytest
import time

from config.enums.users.roles import UserRolesEnum
from config.models.requests import (
    DepositionRequestInsertModel,
    DepositionRequestModel,
)
from config.models.user import UserModel
from fastapi import HTTPException
from routers.requests import depositions


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


class FakeDepositionRequestsDB:
    """Minimal in-memory implementation of the deposition request flow."""

    def __init__(self, submissions=None, requests=None):
        self.submissions = submissions or {}   # tag -> title
        self.requests = requests or {}         # tag -> DepositionRequestModel
        self._counter = 0

    def insert(self, request: DepositionRequestInsertModel, user_tag: str) -> str:
        if request.submission_tag not in self.submissions:
            raise ValueError(f"Submission with tag '{request.submission_tag}' does not exist.")
        for r in self.requests.values():
            if (r.submission_tag == request.submission_tag
                    and r.status == "pending"):
                raise ValueError("A pending deposition request for this submission exists already.")
        self._counter += 1
        tag = f"dr-{self._counter}"
        self.requests[tag] = DepositionRequestModel(
            tag=tag,
            submission_tag=request.submission_tag,
            user_tag=user_tag,
            comment=request.comment,
            database=request.database,
        )
        return tag

    def get(self, tags=None, status=None, submission_tag=None, user_tag=None, limit=50):
        result = []
        for r in self.requests.values():
            if status is not None and r.status != status:
                continue
            if submission_tag is not None and r.submission_tag != submission_tag:
                continue
            if user_tag is not None and r.user_tag != user_tag:
                continue
            result.append(r)
        return sorted(result, key=lambda r: (r.created_at or 0), reverse=True)[:limit]

    def get_pending(self, limit=50):
        return self.get(status="pending", limit=limit)

    def get_for_submission(self, submission_tag, limit=10):
        return self.get(submission_tag=submission_tag, limit=limit)

    def complete(self, tag, reviewer_tag, identifier, url=None, token=None, comment=None):
        if tag not in self.requests:
            raise ValueError(f"Deposition request with tag '{tag}' not found.")
        r = self.requests[tag]
        if r.status != "pending":
            raise ValueError(f"Deposition request with tag '{tag}' is not pending.")
        if identifier is None or len(identifier.strip()) == 0:
            raise ValueError("The deposition identifier is required.")
        r.status = "deposited"
        r.identifier = identifier
        r.url = url
        r.token = token
        r.reviewer_tag = reviewer_tag
        r.reviewed_at = time.time()
        r.review_comment = comment
        return r

    def delete(self, tag):
        if tag not in self.requests:
            raise ValueError(f"Deposition request with tag '{tag}' not found.")
        if self.requests[tag].status != "pending":
            raise ValueError(f"Deposition request with tag '{tag}' is not pending.")
        del self.requests[tag]
        return True

    def reject(self, tag, reviewer_tag, comment=None):
        if tag not in self.requests:
            raise ValueError(f"Deposition request with tag '{tag}' not found.")
        r = self.requests[tag]
        if r.status != "pending":
            raise ValueError(f"Deposition request with tag '{tag}' is not pending.")
        r.status = "rejected"
        r.reviewer_tag = reviewer_tag
        r.reviewed_at = time.time()
        r.review_comment = comment
        return r


class FakeDatabase:
    def __init__(self, db_requests, users):
        self.deposition_requests = db_requests
        self.users = users

    def submission_exists(self, tag):
        return tag in self.deposition_requests.submissions

    def submissions(self, tag):
        raise NotImplementedError


def test_insert_rejects_unknown_submission():
    db = FakeDepositionRequestsDB()
    request = DepositionRequestInsertModel(submission_tag="unknown", database="PRIDE")
    with pytest.raises(ValueError, match="does not exist"):
        db.insert(request=request, user_tag="user1")


def test_insert_and_duplicate_pending():
    db = FakeDepositionRequestsDB(submissions={"sub1": "My dataset"})
    request = DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE", comment="please deposit")
    tag = db.insert(request=request, user_tag="user1")
    assert db.requests[tag].status == "pending"
    with pytest.raises(ValueError, match="exists already"):
        db.insert(request=request, user_tag="user1")
    with pytest.raises(ValueError, match="exists already"):
        db.insert(request=request, user_tag="user2")
    r = db.reject(tag=tag, reviewer_tag="curator1")
    assert r.status == "rejected"
    other = db.insert(request=request, user_tag="user2")
    assert other != tag


def test_complete_stores_identifier_and_token():
    db = FakeDepositionRequestsDB(submissions={"sub1": "My dataset"})
    tag = db.insert(request=DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE"), user_tag="user1")
    r = db.complete(tag=tag, reviewer_tag="curator1", identifier="PXD123456", url="https://www.ebi.ac.uk/pride/archive/projects/PXD123456", token="secret-token")
    assert r.status == "deposited"
    assert r.identifier == "PXD123456"
    assert r.token == "secret-token"
    assert r.reviewer_tag == "curator1"
    with pytest.raises(ValueError, match="not pending"):
        db.complete(tag=tag, reviewer_tag="curator1", identifier="PXD999")


def test_complete_requires_identifier():
    db = FakeDepositionRequestsDB(submissions={"sub1": "My dataset"})
    tag = db.insert(request=DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE"), user_tag="user1")
    with pytest.raises(ValueError, match="identifier is required"):
        db.complete(tag=tag, reviewer_tag="curator1", identifier="   ")


def test_reject():
    db = FakeDepositionRequestsDB(submissions={"sub1": "My dataset"})
    tag = db.insert(request=DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE"), user_tag="user1")
    r = db.reject(tag=tag, reviewer_tag="curator1", comment="not applicable")
    assert r.status == "rejected"
    assert r.review_comment == "not applicable"


def test_visibility_filters_by_user():
    db = FakeDepositionRequestsDB(submissions={"sub1": "My dataset", "sub2": "Other dataset"})
    tag1 = db.insert(request=DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE"), user_tag="user1")
    tag2 = db.insert(request=DepositionRequestInsertModel(submission_tag="sub2", database="PRIDE"), user_tag="user2")
    assert [r.tag for r in db.get(user_tag="user1")] == [tag1]
    assert {r.tag for r in db.get_for_submission("sub1")} == {tag1}
    assert db.get_pending() == [db.requests[tag1], db.requests[tag2]]


def test_get_curator_emails():
    curator = make_user(tag="curator1", email="curator@age.mpg.de", role=UserRolesEnum.CURATOR)
    admin = make_user(tag="admin001"[:8], email="admin@age.mpg.de", role=UserRolesEnum.ADMIN)
    standard = make_user(tag="user0001", email="user@age.mpg.de", role=UserRolesEnum.STANDARD)

    class UsersDB:
        def get_users(self):
            return [standard, curator, admin]

    db = FakeDatabase(db_requests=FakeDepositionRequestsDB(), users=UsersDB())
    emails = depositions._get_curator_emails(db)
    assert set(emails) == {"curator@age.mpg.de", "admin@age.mpg.de"}


def test_create_deposition_request_requires_creator_or_head():
    db_requests = FakeDepositionRequestsDB(submissions={"sub1": "My dataset"})
    class SubmissionsDB:
        def get_creator(self, tag):
            return "creator1"
    class ConsortiumDB:
        def __init__(self, head_tags):
            self.head_tags = head_tags
        def is_head_of_submission_owner(self, user_tag, submission_tag):
            return user_tag in self.head_tags
    class FakeFullDatabase:
        def __init__(self, db_requests, submissions, consortiums):
            self.deposition_requests = db_requests
            self.submissions = submissions
            self.consortiums = consortiums
        def submission_exists(self, tag):
            return tag in self.deposition_requests.submissions
    creator = make_user(tag="creator1")
    head = make_user(tag="head0001")
    other = make_user(tag="other001")
    db = FakeFullDatabase(db_requests, SubmissionsDB(), ConsortiumDB({"head0001"}))
    request = DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE")
    assert depositions._is_creator_or_head("sub1", creator, db)
    assert depositions._is_creator_or_head("sub1", head, db)
    assert not depositions._is_creator_or_head("sub1", other, db)
    with pytest.raises(HTTPException) as exc_info:
        depositions.create_deposition_request(request=request, background_task=None, user=other, db=db)
    assert exc_info.value.status_code == 403

def test_submission_deposition_request_exists_endpoint():
    db_requests = FakeDepositionRequestsDB(submissions={"sub1": "My dataset"})
    tag = db_requests.insert(request=DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE"), user_tag="user1")
    class SubmissionFilterDB:
        def has_user_access(self, user_tag, submission_tag):
            return True
    class SubmissionsDB:
        def exists(self, tag):
            return True
    class FakeFullDatabase:
        def __init__(self, db_requests):
            self.deposition_requests = db_requests
            self.submissions = SubmissionsDB()
            self.submission_filter = SubmissionFilterDB()
        def submission_exists(self, tag):
            return tag in self.deposition_requests.submissions
    db = FakeFullDatabase(db_requests)
    user = make_user(tag="user0001")
    result = depositions.submission_deposition_request_exists(submission_tag="sub1", user=user, db=db)
    assert result == {"pending": True}
    db_requests.reject(tag=tag, reviewer_tag="curator1")
    result = depositions.submission_deposition_request_exists(submission_tag="sub1", user=user, db=db)
    assert result == {"pending": False}


def test_delete_removes_pending_request():
    db = FakeDepositionRequestsDB(submissions={"sub1": "My dataset"})
    tag = db.insert(request=DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE"), user_tag="user1")
    assert db.delete(tag=tag)
    assert tag not in db.requests
    with pytest.raises(ValueError, match="not found"):
        db.delete(tag=tag)
    tag2 = db.insert(request=DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE"), user_tag="user1")
    db.reject(tag=tag2, reviewer_tag="curator1")
    with pytest.raises(ValueError, match="not pending"):
        db.delete(tag=tag2)


def test_revoke_endpoint_permissions():
    db_requests = FakeDepositionRequestsDB(submissions={"sub1": "My dataset"})
    tag = db_requests.insert(request=DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE"), user_tag="creator1")
    class SubmissionsDB:
        def get_creator(self, tag):
            return "creator1"
    class ConsortiumDB:
        def __init__(self, head_tags):
            self.head_tags = head_tags
        def is_head_of_submission_owner(self, user_tag, submission_tag):
            return user_tag in self.head_tags
    class FakeFullDatabase:
        def __init__(self, db_requests, submissions, consortiums):
            self.deposition_requests = db_requests
            self.submissions = submissions
            self.consortiums = consortiums
        def submission_exists(self, tag):
            return tag in self.deposition_requests.submissions
    db = FakeFullDatabase(db_requests, SubmissionsDB(), ConsortiumDB({"head0001"}))
    requester = make_user(tag="creator1")
    head = make_user(tag="head0001")
    other = make_user(tag="other001")
    curator = make_user(tag="curat001", role=UserRolesEnum.CURATOR)

    result = depositions.revoke_deposition_request(request_tag=tag, user=requester, db=db)
    assert result == {"tag": tag, "deleted": True}
    assert tag not in db_requests.requests

    tag2 = db_requests.insert(request=DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE"), user_tag="creator1")
    with pytest.raises(HTTPException) as exc_info:
        depositions.revoke_deposition_request(request_tag=tag2, user=other, db=db)
    assert exc_info.value.status_code == 403
    assert tag2 in db_requests.requests

    depositions.revoke_deposition_request(request_tag=tag2, user=head, db=db)
    tag3 = db_requests.insert(request=DepositionRequestInsertModel(submission_tag="sub1", database="PRIDE"), user_tag="creator1")
    depositions.revoke_deposition_request(request_tag=tag3, user=curator, db=db)

    with pytest.raises(HTTPException) as exc_info:
        depositions.revoke_deposition_request(request_tag="missing", user=requester, db=db)
    assert exc_info.value.status_code == 404


def test_models_validate_status():
    r = DepositionRequestModel(submission_tag="sub1", user_tag="user1", database="PRIDE")
    assert r.status == "pending"
    assert r.identifier is None
    assert r.token is None
