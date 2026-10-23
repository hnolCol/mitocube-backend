from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from typing import List, Literal, Optional

from config.models.requests import (
    AttributeProposalModel,
    AttributeRequestApproveModel,
    AttributeRequestCreateModel,
    AttributeRequestInsertModel,
    AttributeRequestModel,
    AttributeRequestReviewModel,
    TraitProposalModel,
    TraitRequestApproveModel,
    TraitRequestBulkCreateModel,
    TraitRequestCreateModel,
)
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.settings.email import get_email_settings
from config.settings.general import get_general_settings
from lib.database.abstract.Database import DatabaseABC
from lib.database.Database import get_db
from services.mail import send_email_in_background
from services.messages import send_message_in_background
from services.users import get_user_from_token, is_user_at_least_curator

EMAIL_SETTINGS = get_email_settings()
GENERAL_SETTINGS = get_general_settings()

router = APIRouter(dependencies=[Depends(get_user_from_token)],
                   prefix="/api",
                   tags=["Attribute & Trait Requests"])

Kind = Literal["attribute", "trait"]


def _get_curator_emails(db: DatabaseABC) -> List[str]:
    return [u.email for u in db.users.get_users()
            if u.role >= UserRolesEnum.CURATOR and u.email is not None]


def _attribute_tag(text: str) -> str:
    return "att_" + text.replace(" ", "_").lower().encode("utf-8", "ignore").decode("utf-8")


def _split_comment(comment: Optional[str]) -> tuple:
    """The attribute request dialog stores the description as the first block
    of the comment; the rest is additional information."""
    if not comment:
        return "", ""
    first, *rest = comment.split("\n\n")
    return first, "\n\n".join(rest)


def _notify_curators(background_task: BackgroundTasks, db: DatabaseABC, user: UserModel,
                     kind: Kind, text: str, description: str = "", comment: Optional[str] = None,
                     attribute_tag: Optional[str] = None, traits: Optional[List[str]] = None) -> None:
    """Emails all curators/admins about a new request. The request is already
    stored at this point, so a mail problem is logged instead of raised."""
    emails = _get_curator_emails(db)
    if len(emails) == 0:
        print(f"[mail] No curator or admin found to notify about the {kind} request '{text}'.")
        return
    review_url = f"{GENERAL_SETTINGS.url}admin/attributes" + (f"/{attribute_tag}" if attribute_tag else "")
    try:
        send_email_in_background(background_tasks=background_task,
                                 subject=f"{kind.capitalize()} Request: {text}",
                                 email_to=emails,
                                 include_setting_cc=False,
                                 body={
                                     "app_name": GENERAL_SETTINGS.app_name,
                                     "kind": kind,
                                     "text": text,
                                     "attribute_tag": attribute_tag,
                                     "description": description,
                                     "traits": ", ".join(traits) if traits else "",
                                     "user": f"{user.firstname} {user.lastname}",
                                     "comment": comment,
                                     "review_url": review_url,
                                 },
                                 template_name=EMAIL_SETTINGS.mail_attribute_requested_template)
    except Exception as e:
        print(f"[mail] Failed to queue the {kind} request email: {e}")


def _notify_requester(background_task: BackgroundTasks, db: DatabaseABC, reviewer: UserModel,
                      request: AttributeRequestModel, approved: bool,
                      review_comment: Optional[str], edited: bool = False) -> None:
    """Notifies the user who created the request about the decision and who made it,
    by email and by a read-only in-app message from MitoCube Support (same body).
    The decision is already stored at this point, so problems are logged instead of raised."""
    requester = db.users.get_user_by_tag(tag=request.user_tag)
    if requester is None:
        print(f"[notify] Requesting user {request.user_tag} not found, request {request.tag}.")
        return
    if request.kind == "trait":
        text, attribute_tag = request.trait.text, request.trait.attribute_tag
        view_url = f"{GENERAL_SETTINGS.url}admin/attributes/{attribute_tag}"
    else:
        text, attribute_tag = request.attribute.text, None
        view_url = f"{GENERAL_SETTINGS.url}admin/attributes/{_attribute_tag(request.attribute.text)}"

    subject = f"{request.kind.capitalize()} Request {'Approved' if approved else 'Denied'}: {text}"
    body = {
        "app_name": GENERAL_SETTINGS.app_name,
        "first_name": requester.firstname,
        "kind": request.kind,
        "text": text,
        "attribute_tag": attribute_tag,
        "approved": approved,
        "edited": edited,
        "reviewer": f"{reviewer.firstname} {reviewer.lastname}".strip(),
        "review_comment": review_comment,
        "view_url": view_url,
    }

    if requester.email is not None:
        try:
            send_email_in_background(background_tasks=background_task,
                                     subject=subject,
                                     email_to=[requester.email],
                                     include_setting_cc=False,
                                     body=body,
                                     template_name=EMAIL_SETTINGS.mail_attribute_request_reviewed_template)
        except Exception as e:
            print(f"[mail] Failed to queue the review email for request {request.tag}: {e}")

    try:
        send_message_in_background(background_tasks=background_task,
                                   db=db,
                                   subject=subject,
                                   user_tags=[requester.tag],
                                   body=body,
                                   template_name=EMAIL_SETTINGS.message_attribute_request_reviewed_template)
    except Exception as e:
        print(f"[messages] Failed to queue the review message for request {request.tag}: {e}")


def _insert(request: AttributeRequestInsertModel, user: UserModel, db: DatabaseABC) -> str:
    try:
        return db.attribute_requests.insert(request=request, user_tag=user.tag)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


def _review(kind: Kind, approve: bool, request_tag: str, comment: Optional[str],
            user: UserModel, db: DatabaseABC, background_task: BackgroundTasks,
            edits: Optional[dict] = None) -> AttributeRequestModel:
    if len(db.attribute_requests.get(tags=[request_tag], kind=kind, limit=1)) == 0:
        raise HTTPException(status_code=404, detail=f"{kind.capitalize()} request not found.")
    try:
        if approve:
            result = db.attribute_requests.accept(tag=request_tag, reviewer_tag=user.tag, comment=comment, edits=edits)
        else:
            result = db.attribute_requests.reject(tag=request_tag, reviewer_tag=user.tag, comment=comment)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    _notify_requester(background_task, db, user, result, approved=approve, review_comment=comment, edited=bool(edits))
    return result


# ---------- attribute requests ----------

@router.get("/attribute_requests/pending", summary="Returns all pending attribute requests. Curator rights required.")
def get_pending_attribute_requests(limit: int = 50,
                                   user: UserModel = Depends(is_user_at_least_curator),
                                   db: DatabaseABC = Depends(get_db)) -> List[AttributeRequestModel]:
    """Returns the pending attribute requests, newest first."""
    return db.attribute_requests.get_pending(kind="attribute", limit=limit)


@router.post("/attribute_requests", summary="Proposes a new attribute (optionally with traits). Notifies all curators/admins by email.")
def create_attribute_request(body: AttributeRequestCreateModel,
                             background_task: BackgroundTasks,
                             user: UserModel = Depends(get_user_from_token),
                             db: DatabaseABC = Depends(get_db)) -> dict:
    """Creates a pending attribute request and emails all curators/admins.
    Priority and minimal state are not requestable; curators set them when approving."""
    request = AttributeRequestInsertModel(
        kind="attribute",
        attribute=AttributeProposalModel(**body.model_dump(exclude={"comment", "priority", "min_state"})),
        comment=body.comment,
    )
    tag = _insert(request, user, db)
    description, rest = _split_comment(body.comment)
    _notify_curators(background_task, db, user, "attribute",
                     text=body.text,
                     description=description,
                     comment=rest or None,
                     traits=[t.text for t in body.traits])
    return {"tag": tag, "status": "pending"}


@router.post("/attribute_requests/{request_tag}/approve", summary="Approves an attribute request, optionally with curator edits. Notifies the requester. Curator rights required.")
def approve_attribute_request(request_tag: str,
                              background_task: BackgroundTasks,
                              body: AttributeRequestApproveModel = AttributeRequestApproveModel(),
                              user: UserModel = Depends(is_user_at_least_curator),
                              db: DatabaseABC = Depends(get_db)) -> AttributeRequestModel:
    """Approves a pending attribute request. Fields sent in `attribute`
    override the proposal before the attribute is created."""
    edits = body.attribute.model_dump(exclude_unset=True) if body.attribute is not None else None
    return _review("attribute", True, request_tag, body.comment, user, db, background_task, edits=edits)


@router.post("/attribute_requests/{request_tag}/deny", summary="Denies an attribute request. Notifies the requester. Curator rights required.")
def deny_attribute_request(request_tag: str,
                           background_task: BackgroundTasks,
                           review: AttributeRequestReviewModel = AttributeRequestReviewModel(),
                           user: UserModel = Depends(is_user_at_least_curator),
                           db: DatabaseABC = Depends(get_db)) -> AttributeRequestModel:
    """Denies a pending attribute request. No attribute is created."""
    return _review("attribute", False, request_tag, review.comment, user, db, background_task)


# ---------- trait requests ----------

@router.get("/trait_requests/pending", summary="Returns all pending trait requests. Curator rights required.")
def get_pending_trait_requests(limit: int = 50,
                               user: UserModel = Depends(is_user_at_least_curator),
                               db: DatabaseABC = Depends(get_db)) -> List[AttributeRequestModel]:
    """Returns the pending trait requests, newest first."""
    return db.attribute_requests.get_pending(kind="trait", limit=limit)


@router.post("/trait_requests", summary="Proposes a new trait for an existing attribute. Notifies all curators/admins by email.")
def create_trait_request(body: TraitRequestCreateModel,
                         background_task: BackgroundTasks,
                         user: UserModel = Depends(get_user_from_token),
                         db: DatabaseABC = Depends(get_db)) -> dict:
    """Creates a pending trait request and emails all curators/admins.
    Priority is not requestable; curators set it when approving."""
    if not db.attributes.exists(tag=body.attribute_tag):
        raise HTTPException(status_code=404, detail="Attribute not found.")
    request = AttributeRequestInsertModel(
        kind="trait",
        trait=TraitProposalModel(**body.model_dump(exclude={"comment", "priority"})),
        comment=body.comment,
    )
    tag = _insert(request, user, db)
    _notify_curators(background_task, db, user, "trait",
                     text=body.text,
                     description=body.description or "",
                     comment=body.comment,
                     attribute_tag=body.attribute_tag)
    return {"tag": tag, "status": "pending"}


@router.post("/trait_requests/bulk", summary="Proposes several new traits for an existing attribute. Each trait becomes its own request. Notifies all curators/admins with one email.")
def create_trait_requests_bulk(body: TraitRequestBulkCreateModel,
                               background_task: BackgroundTasks,
                               user: UserModel = Depends(get_user_from_token),
                               db: DatabaseABC = Depends(get_db)) -> dict:
    """Creates one pending trait request per trait. Traits that exist already or
    have a pending request are skipped and reported. Curators/admins receive a
    single email listing all created requests."""
    if not db.attributes.exists(tag=body.attribute_tag):
        raise HTTPException(status_code=404, detail="Attribute not found.")
    items = [t for t in body.traits if t.text.strip()]
    if len(items) == 0:
        raise HTTPException(status_code=400, detail="Provide at least one trait.")
    if len(items) > 200:
        raise HTTPException(status_code=400, detail="At most 200 traits can be requested at once.")

    created, skipped = [], []
    for t in items:
        text = t.text.strip()
        request = AttributeRequestInsertModel(
            kind="trait",
            trait=TraitProposalModel(attribute_tag=body.attribute_tag, text=text, description=(t.description or "").strip()),
            comment=body.comment,
        )
        try:
            created.append({"tag": db.attribute_requests.insert(request=request, user_tag=user.tag), "text": text})
        except ValueError as e:
            skipped.append({"text": text, "reason": str(e)})

    if len(created) == 0:
        raise HTTPException(status_code=409, detail="No request was created: " + "; ".join(f"{s['text']}: {s['reason']}" for s in skipped))

    _notify_curators(background_task, db, user, "trait",
                     text=created[0]["text"] if len(created) == 1 else f"{len(created)} new traits",
                     comment=body.comment,
                     attribute_tag=body.attribute_tag,
                     traits=[c["text"] for c in created])
    return {"created": created, "skipped": skipped}


@router.post("/trait_requests/{request_tag}/approve", summary="Approves a trait request, optionally with curator edits. Notifies the requester. Curator rights required.")
def approve_trait_request(request_tag: str,
                          background_task: BackgroundTasks,
                          body: TraitRequestApproveModel = TraitRequestApproveModel(),
                          user: UserModel = Depends(is_user_at_least_curator),
                          db: DatabaseABC = Depends(get_db)) -> AttributeRequestModel:
    """Approves a pending trait request. Fields sent in `trait` override
    the proposal before the trait is created."""
    edits = body.trait.model_dump(exclude_unset=True) if body.trait is not None else None
    return _review("trait", True, request_tag, body.comment, user, db, background_task, edits=edits)


@router.post("/trait_requests/{request_tag}/deny", summary="Denies a trait request. Notifies the requester. Curator rights required.")
def deny_trait_request(request_tag: str,
                       background_task: BackgroundTasks,
                       review: AttributeRequestReviewModel = AttributeRequestReviewModel(),
                       user: UserModel = Depends(is_user_at_least_curator),
                       db: DatabaseABC = Depends(get_db)) -> AttributeRequestModel:
    """Denies a pending trait request. No trait is created."""
    return _review("trait", False, request_tag, review.comment, user, db, background_task)