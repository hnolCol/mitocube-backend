from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from typing import List, Literal, Optional

from config.models.requests import (
    DepositionRequestInsertModel,
    DepositionRequestModel,
    DepositionRequestCompleteModel,
    DepositionRequestReviewModel,
)
from config.models.user import UserModel
from lib.database.abstract.Database import DatabaseABC
from lib.database.Database import get_db
from services.mail import send_email_in_background
from services.users import get_user_from_token, is_user_at_least_curator
from config.enums.users.roles import UserRolesEnum
from config.settings.email import get_email_settings
from config.settings.general import get_general_settings

EMAIL_SETTINGS = get_email_settings()
GENERAL_SETTINGS = get_general_settings()

router = APIRouter(dependencies=[Depends(get_user_from_token)],
                   prefix="/api/requests/depositions",
                   tags=["Deposition Requests"])


def _get_curator_emails(db: DatabaseABC) -> List[str]:
    emails = [user.email for user in db.users.get_users()
              if user.role >= UserRolesEnum.CURATOR and user.email is not None]
    if len(emails) == 0:
        raise HTTPException(status_code=404, detail="No curator or admin user found to notify.")
    return emails


@router.post("", summary="Request the deposition of a submission's data to an external database. Any verified user can submit a request.")
def create_deposition_request(request: DepositionRequestInsertModel,
                              background_task: BackgroundTasks,
                              user: UserModel = Depends(get_user_from_token),
                              db: DatabaseABC = Depends(get_db)) -> dict:
    """Creates a pending deposition request for a submission. The request is
    visible to curators/admins only and triggers an email to all curators/admins."""
    if not db.submission_exists(request.submission_tag):
        raise HTTPException(status_code=404, detail="Submission not found.")
    try:
        tag = db.deposition_requests.insert(request=request, user_tag=user.tag)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    submission_title = db.submissions.get_title(tag=request.submission_tag)
    send_email_in_background(background_tasks=background_task,
                             subject=f"Deposition Request: {submission_title} ({request.submission_tag})",
                             email_to=_get_curator_emails(db),
                             include_setting_cc=False,
                             body={
                                 "app_name": GENERAL_SETTINGS.app_name,
                                 "first_name": "Curator",
                                 "database": request.database,
                                 "title": submission_title,
                                 "submission_tag": request.submission_tag,
                                 "user": f"{user.firstname} {user.lastname}",
                                 "comment": request.comment,
                                 "submission_url": f"{GENERAL_SETTINGS.url}submissions/{request.submission_tag}",
                             },
                             template_name=EMAIL_SETTINGS.mail_deposition_requested_template)
    return {"tag": tag}


@router.get("", summary="Returns deposition requests. Curator rights required.")
def get_deposition_requests(status: Optional[Literal["pending", "deposited", "rejected"]] = None,
                            limit: int = 50,
                            user: UserModel = Depends(is_user_at_least_curator),
                            db: DatabaseABC = Depends(get_db)) -> List[DepositionRequestModel]:
    """Returns the deposition requests, newest first. Requires at least curator rights."""
    return db.deposition_requests.get(status=status, limit=limit)


@router.get("/pending", summary="Returns the pending deposition requests. Curator rights required.")
def get_pending_deposition_requests(limit: int = 50,
                                    user: UserModel = Depends(is_user_at_least_curator),
                                    db: DatabaseABC = Depends(get_db)) -> List[DepositionRequestModel]:
    """Returns the pending deposition requests, newest first."""
    return db.deposition_requests.get_pending(limit=limit)


@router.get("/mine", summary="Returns the deposition requests created by the requesting user.")
def get_my_deposition_requests(limit: int = 50,
                               user: UserModel = Depends(get_user_from_token),
                               db: DatabaseABC = Depends(get_db)) -> List[DepositionRequestModel]:
    """Returns the deposition requests created by the requesting user, newest first.
    Deposited requests include the accession identifier, url and login token."""
    return db.deposition_requests.get(user_tag=user.tag, limit=limit)


@router.get("/submissions/{submission_tag}", summary="Returns the deposition requests of a submission.")
def get_submission_deposition_requests(submission_tag: str,
                                       limit: int = 10,
                                       user: UserModel = Depends(get_user_from_token),
                                       db: DatabaseABC = Depends(get_db)) -> List[DepositionRequestModel]:
    """Returns the deposition requests of a submission, newest first.
    Curators see all requests of the submission, users only their own requests."""
    requests = db.deposition_requests.get_for_submission(submission_tag=submission_tag, limit=limit)
    if user.role >= UserRolesEnum.CURATOR:
        return requests
    return [r for r in requests if r.user_tag == user.tag]


@router.post("/{request_tag}/complete", summary="Marks a deposition request as deposited and stores the accession identifier, url and optional login token. Curator rights required.")
def complete_deposition_request(request_tag: str,
                                payload: DepositionRequestCompleteModel,
                                background_task: BackgroundTasks,
                                user: UserModel = Depends(is_user_at_least_curator),
                                db: DatabaseABC = Depends(get_db)) -> DepositionRequestModel:
    """Completes a pending deposition request. The accession identifier and optional
    url and login token are stored on the request and an email with the deposition
    information is sent to the requesting user."""
    try:
        request = db.deposition_requests.complete(tag=request_tag,
                                                   reviewer_tag=user.tag,
                                                   identifier=payload.identifier,
                                                   url=payload.url,
                                                   token=payload.token,
                                                   comment=payload.comment)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    requester = db.users.get_user_by_tag(tag=request.user_tag)
    if requester is None:
        raise HTTPException(status_code=404, detail="Requesting user not found. The deposition request was updated, but the user could not be notified.")
    submission_title = db.submissions.get_title(tag=request.submission_tag)
    send_email_in_background(background_tasks=background_task,
                             subject=f"Deposition Complete : {submission_title} ({request.submission_tag})",
                             email_to=[requester.email],
                             body={
                                 "app_name": GENERAL_SETTINGS.app_name,
                                 "first_name": requester.firstname,
                                 "database": request.database,
                                 "title": submission_title,
                                 "submission_tag": request.submission_tag,
                                 "identifier": request.identifier,
                                 "url": request.url,
                                 "token": request.token,
                                 "submission_url": f"{GENERAL_SETTINGS.url}submissions/{request.submission_tag}",
                             },
                             template_name=EMAIL_SETTINGS.mail_deposition_complete_template)
    return request


@router.post("/{request_tag}/reject", summary="Rejects a pending deposition request. Curator rights required.")
def reject_deposition_request(request_tag: str,
                              review: DepositionRequestReviewModel = DepositionRequestReviewModel(),
                              user: UserModel = Depends(is_user_at_least_curator),
                              db: DatabaseABC = Depends(get_db)) -> DepositionRequestModel:
    """Rejects a pending deposition request. The request is marked rejected."""
    try:
        return db.deposition_requests.reject(tag=request_tag, reviewer_tag=user.tag, comment=review.comment)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
