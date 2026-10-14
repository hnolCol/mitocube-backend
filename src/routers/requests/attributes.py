from fastapi import APIRouter, Depends, HTTPException
from typing import List, Literal, Optional

from config.models.requests import (
    AttributeRequestInsertModel,
    AttributeRequestModel,
    AttributeRequestReviewModel,
)
from config.models.user import UserModel
from lib.database.abstract.Database import DatabaseABC
from lib.database.Database import get_db
from services.users import get_user_from_token, is_user_at_least_curator

router = APIRouter(dependencies=[Depends(get_user_from_token)],
                   prefix="/api/requests/attributes",
                   tags=["Attribute Requests"])


@router.post("", summary="Propose a new attribute or trait. Any verified user can submit a request.")
def create_attribute_request(request: AttributeRequestInsertModel,
                             user: UserModel = Depends(get_user_from_token),
                             db: DatabaseABC = Depends(get_db)) -> dict:
    """Creates a pending request for a new attribute (optionally with traits)
    or a new trait for an existing attribute. The request is stored and must
    be accepted by a curator before any attribute/trait is created."""
    if request.kind == "trait" and not db.attributes.exists(tag=request.trait.attribute_tag):
        raise HTTPException(status_code=404, detail="Attribute not found.")
    tag = db.attribute_requests.insert(request=request, user_tag=user.tag)
    return {"tag": tag}


@router.get("", summary="Returns attribute requests. Pending requests are visible to curators only.")
def get_attribute_requests(status: Optional[Literal["pending", "accepted", "rejected"]] = None,
                           limit: int = 50,
                           user: UserModel = Depends(is_user_at_least_curator),
                           db: DatabaseABC = Depends(get_db)) -> List[AttributeRequestModel]:
    """Returns the attribute requests, newest first. Requires at least curator rights."""
    return db.attribute_requests.get(status=status, limit=limit)


@router.get("/pending", summary="Returns the pending attribute requests. Curator rights required.")
def get_pending_attribute_requests(limit: int = 50,
                                    user: UserModel = Depends(is_user_at_least_curator),
                                    db: DatabaseABC = Depends(get_db)) -> List[AttributeRequestModel]:
    """Returns the pending attribute requests, newest first."""
    return db.attribute_requests.get_pending(limit=limit)


@router.post("/{request_tag}/accept", summary="Accepts a pending request and creates the proposed attribute/trait. Curator rights required.")
def accept_attribute_request(request_tag: str,
                             review: AttributeRequestReviewModel = AttributeRequestReviewModel(),
                             user: UserModel = Depends(is_user_at_least_curator),
                             db: DatabaseABC = Depends(get_db)) -> AttributeRequestModel:
    """Accepts a pending attribute request. The proposed attribute and/or trait
    is created and the request is marked accepted."""
    try:
        return db.attribute_requests.accept(tag=request_tag, reviewer_tag=user.tag, comment=review.comment)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{request_tag}/reject", summary="Rejects a pending request. The proposal is not created. Curator rights required.")
def reject_attribute_request(request_tag: str,
                             review: AttributeRequestReviewModel = AttributeRequestReviewModel(),
                             user: UserModel = Depends(is_user_at_least_curator),
                             db: DatabaseABC = Depends(get_db)) -> AttributeRequestModel:
    """Rejects a pending attribute request. The proposed attribute/trait is not
    created and the request is marked rejected."""
    try:
        return db.attribute_requests.reject(tag=request_tag, reviewer_tag=user.tag, comment=review.comment)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
