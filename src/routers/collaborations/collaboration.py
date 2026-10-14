from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from config.enums.users.roles import UserRolesEnum
from config.models.collaborations import (
    CollaborationRequestInput,
    CollaborationRequestModel,
    SubmissionExploreModel,
)
from services.users import get_user_from_token

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/collaborations",
    tags=["Collaborations", "Permissions"],
)

collaboration_request_not_found = HTTPException(status_code=404, detail="No pending collaboration request found.")
collaboration_request_exists = HTTPException(status_code=409, detail="A pending collaboration request already exists for this submission.")


def _get_collaboration_request(request_tag : str, db : DatabaseABC) -> CollaborationRequestModel:
    request = db.collaborations.get_collaboration_request(request_tag)
    if request is None:
        raise collaboration_request_not_found
    return request


def _can_approve(user : UserModel, request : CollaborationRequestModel, db : DatabaseABC) -> bool:
    """The owner of the submission, a head (PI) of the owners research group,
    a head (PI) of the requesting users research group (if the PI approval
    setting is enabled) and curators can approve/deny collaboration requests."""
    if user.role >= UserRolesEnum.CURATOR:
        return True
    creator_tag = db.submissions.get_creator(tag = request.submission_tag)
    if user.tag == creator_tag:
        return True
    if db.consortiums.is_head_of_submission_owner(user_tag = user.tag, submission_tag = request.submission_tag):
        return True
    return db.research_groups.is_head(user_tag = user.tag)


@router.get("/submissions/explore", response_model=List[SubmissionExploreModel],
            summary="Discovery endpoint: find submissions by title to request collaboration.")
def explore_submissions(search_string : Optional[str] = None,
                        limit : int = 40,
                        user : UserModel = Depends(get_user_from_token),
                        db : DatabaseABC = Depends(get_db)) -> List[SubmissionExploreModel]:
    """Finds submissions by title and returns only the minimal metadata required
    to request collaboration (title, owner, research group, state). This endpoint
    is intentionally separate from /api/submissions/q: it can return submissions
    the current user has no access to, but never any sensitive data."""
    return db.collaborations.explore(search_string = search_string, limit = limit)


@router.post("/requests", response_model=str,
             summary="Creates a collaboration request for a submission.")
def create_collaboration_request(request : CollaborationRequestInput,
                                 user : UserModel = Depends(get_user_from_token),
                                 db : DatabaseABC = Depends(get_db)) -> str:
    """Creates a pending collaboration request for a submission. The request can
    be created for the requesting user itself or for one of their research groups
    (in which case all group members become collaborators on approval). The
    request must be approved by the owner of the submission and - if the PI
    approval setting is enabled - by the head of the requesting users research
    group before access is granted."""
    if user.role < UserRolesEnum.STANDARD:
        raise HTTPException(status_code=403, detail="Guests cannot request collaboration.")
    if not db.submissions.exists(tag = request.submission_tag):
        raise HTTPException(status_code=404, detail=f"Submission with tag {request.submission_tag} not found.")
    if db.submissions.has_user_access(user_tag = user.tag, submission_tag = request.submission_tag):
        raise HTTPException(status_code=400, detail="You already have access to this submission.")
    if request.requested_for_user_tag is not None and request.requested_for_user_tag != user.tag:
        raise HTTPException(status_code=403, detail="A collaboration request can only be created for the requesting user.")
    if request.requested_for_group_tag is not None:
        if not db.research_groups.exists(tag = request.requested_for_group_tag):
            raise HTTPException(status_code=404, detail=f"Research group with tag {request.requested_for_group_tag} not found.")
        group_user_tags = db.research_groups.get_users(tag = request.requested_for_group_tag)
        if user.tag not in group_user_tags:
            raise HTTPException(status_code=403, detail="You are not a member of this research group.")
    try:
        request_tag = db.collaborations.create_collaboration_request(
            submission_tag = request.submission_tag,
            requested_by = user.tag,
            input = request,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if request_tag is None:
        raise collaboration_request_exists
    return request_tag


@router.get("/requests", response_model=List[CollaborationRequestModel],
            summary="Returns the pending collaboration requests created by the current user.")
def get_my_collaboration_requests(user : UserModel = Depends(get_user_from_token),
                                  db : DatabaseABC = Depends(get_db)) -> List[CollaborationRequestModel]:
    return db.collaborations.get_pending_collaboration_requests_for_user(user_tag = user.tag)


@router.get("/requests/pending", response_model=List[CollaborationRequestModel],
            summary="Returns the pending collaboration requests the current user can approve.")
def get_pending_collaboration_requests(user : UserModel = Depends(get_user_from_token),
                                       db : DatabaseABC = Depends(get_db)) -> List[CollaborationRequestModel]:
    """Returns the pending collaboration requests of the submissions owned by the
    current user and of the members of the research groups they lead (as head/PI).
    The requests are visible next to the consortium share requests."""
    return db.collaborations.get_pending_collaboration_requests_for_head(user_tag = user.tag)


@router.get("/requests/submissions/{submission_tag}", response_model=List[CollaborationRequestModel],
            summary="Returns all collaboration requests for a submission. Requires the submission owner, a head (PI) or a curator.")
def get_collaboration_requests_for_submission(submission_tag : str,
                                              user : UserModel = Depends(get_user_from_token),
                                              db : DatabaseABC = Depends(get_db)) -> List[CollaborationRequestModel]:
    from services.submission import check_submission_access
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    creator_tag = db.submissions.get_creator(tag = submission_tag)
    if (user.tag != creator_tag
            and user.role < UserRolesEnum.CURATOR
            and not db.consortiums.is_head_of_submission_owner(user_tag = user.tag, submission_tag = submission_tag)):
        raise HTTPException(status_code=403, detail="Only the owner of the submission, a research group head (PI) or a curator can view collaboration requests.")
    return db.collaborations.get_collaboration_requests_for_submission(submission_tag = submission_tag)


@router.post("/requests/{request_tag}/approve",
             summary="Approves a pending collaboration request. Requires the submission owner, a head (PI) of the owners group or a curator.")
def approve_collaboration_request(request_tag : str,
                                  user : UserModel = Depends(get_user_from_token),
                                  db : DatabaseABC = Depends(get_db)) -> bool:
    request = _get_collaboration_request(request_tag, db)
    if request.status != "pending":
        raise collaboration_request_not_found
    if not _can_approve(user, request, db):
        raise HTTPException(status_code=403, detail="Only the owner of the submission, a research group head (PI) or a curator can approve collaboration requests.")
    ok = db.collaborations.approve_collaboration_request(request_tag = request_tag, approved_by = user.tag)
    if not ok:
        raise collaboration_request_not_found
    return True


@router.post("/requests/{request_tag}/deny",
             summary="Denies a pending collaboration request. Requires the submission owner, a head (PI) of the owners group or a curator.")
def deny_collaboration_request(request_tag : str,
                               user : UserModel = Depends(get_user_from_token),
                               db : DatabaseABC = Depends(get_db)) -> bool:
    request = _get_collaboration_request(request_tag, db)
    if request.status != "pending":
        raise collaboration_request_not_found
    if not _can_approve(user, request, db):
        raise HTTPException(status_code=403, detail="Only the owner of the submission, a research group head (PI) or a curator can deny collaboration requests.")
    ok = db.collaborations.deny_collaboration_request(request_tag = request_tag)
    if not ok:
        raise collaboration_request_not_found
    return True
