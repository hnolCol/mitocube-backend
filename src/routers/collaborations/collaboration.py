from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from config.settings.email import get_email_settings
from config.settings.general import get_general_settings
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from config.enums.users.roles import UserRolesEnum
from config.models.collaborations import (
    CollaborationRequestInput,
    CollaborationRequestModel,
    SubmissionExploreModel,
)
from services.messages import send_message_in_background
from services.users import get_user_from_token

EMAIL_SETTINGS = get_email_settings()

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


def _group_name(group_tag : Optional[str], db : DatabaseABC) -> Optional[str]:
    """Readable name of a research group, falls back to the tag."""
    if not group_tag:
        return None
    get_text = getattr(db.research_groups, "get_text", None)
    try:
        name = get_text(tag = group_tag) if callable(get_text) else None
    except Exception:
        name = None
    return name or group_tag


def _message_requester(background_task : BackgroundTasks, db : DatabaseABC,
                       reviewer : UserModel, request_tag : str, approved : bool) -> None:
    """Read-only in-app notification from MitoCube Support to the user who created
    the collaboration request. Sent only on the final decision: with PI approval
    enabled, the first approval only marks one side and is not notified. The
    decision is already stored, so problems are logged instead of raised."""
    try:
        request = db.collaborations.get_collaboration_request(request_tag)
        if request is None:
            return
        if approved and request.status != "approved":
            return
        requester = db.users.get_user_by_tag(tag = request.requested_by)
        if requester is None:
            print(f"[messages] Requesting user {request.requested_by} not found, collaboration request {request_tag}.")
            return
        title = db.submissions.get_title(tag = request.submission_tag) or request.submission_tag
        send_message_in_background(background_tasks = background_task,
                                   db = db,
                                   subject = f"Collaboration Request {'Approved' if approved else 'Denied'}: {title}",
                                   user_tags = [requester.tag],
                                   body = {
                                       "app_name": get_general_settings().app_name,
                                       "first_name": requester.firstname,
                                       "title": title,
                                       "submission_tag": request.submission_tag,
                                       "group": _group_name(request.requested_for_group_tag, db),
                                       "approved": approved,
                                       "reviewer": f"{reviewer.firstname} {reviewer.lastname}".strip(),
                                   },
                                   template_name = EMAIL_SETTINGS.message_collaboration_request_reviewed_template,
                                   submission_tag = request.submission_tag if approved else None)
    except Exception as e:
        print(f"[messages] Failed to queue the collaboration message for request {request_tag}: {e}")


@router.get("/submissions/explore", response_model=List[SubmissionExploreModel],
            summary="Discovery endpoint: find submissions by title and tags to request collaboration.")
def explore_submissions(search_string : Optional[str] = None,
                        ca_tags : Optional[List[str]] = Query(None, description="Condition application tags the submission must have (AND semantics)."),
                        user_tags : Optional[List[str]] = Query(None, description="User tags that must be creator or collaborator of the submission (AND semantics)."),
                        limit : int = 40,
                        user : UserModel = Depends(get_user_from_token),
                        db : DatabaseABC = Depends(get_db)) -> List[SubmissionExploreModel]:
    """Finds submissions by title and optionally by condition application and
    user tags (all filters are combined with AND semantics) and returns only the
    minimal metadata required to request collaboration (title, owner, research
    group, state, matched tags). This endpoint is intentionally separate from
    /api/submissions/q: it can return submissions the current user has no access
    to, but never any sensitive data."""
    has_tag_filters = bool(ca_tags or user_tags)
    if has_tag_filters and not get_general_settings().explore_tag_search_enabled:
        raise HTTPException(status_code = 403, detail="Searching submissions by condition applications or users is disabled on this instance.")
    return db.collaborations.explore(search_string = search_string, ca_tags = ca_tags,
                                     user_tags = user_tags, limit = limit)


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
    if db.submission_filter.has_user_access(user_tag = user.tag, submission_tag = request.submission_tag):
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
             summary="Approves a pending collaboration request. Requires the submission owner, a head (PI) of the owners group or a curator. Notifies the requester in-app once fully approved.")
def approve_collaboration_request(request_tag : str,
                                  background_task : BackgroundTasks,
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
    _message_requester(background_task, db, user, request_tag, approved = True)
    return True


@router.post("/requests/{request_tag}/deny",
             summary="Denies a pending collaboration request. Requires the submission owner, a head (PI) of the owners group or a curator. Notifies the requester in-app.")
def deny_collaboration_request(request_tag : str,
                               background_task : BackgroundTasks,
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
    _message_requester(background_task, db, user, request_tag, approved = False)
    return True