from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from config.enums.users.roles import UserRolesEnum
from config.models.consortium import ConsortiumInput, ConsortiumResponseModel
from services.users import get_user_from_token, is_user_at_least_curator, is_user_admin
from services.encryption import create_hierarchical_hash
from services.submission import check_submission_access
from config.exceptions.HTTPExceptions import tag_not_found
from config.models.parameter import APIParamString

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/consortiums",
    tags=["Consortiums", "Permissions"],
)

consortium_not_found_exception = HTTPException(status_code=404, detail="Consortium not found")


def _check_consortium_exists(consortium_tag : str, db : DatabaseABC):
    if not db.consortiums.exists(tag = consortium_tag):
        raise consortium_not_found_exception


@router.get("/q", response_model=List[str])
def find_consortiums(search_string : Optional[str] = None, group_tags : Optional[str] = None, limit : int = 40, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """Finds consortiums matching the search criteria. Consortiums are visible to all logged-in users."""
    return db.consortiums.find(
        search_string=search_string,
        group_tags=APIParamString(param=group_tags).param,
        limit=limit
    )


@router.get("/")
def get_consortiums(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """"
    Returns the tags of all consortiums.
    """
    return db.consortiums.get_tags()


@router.post("/", summary="Creates a new consortium. Requires at least curator rights.")
def add_consortium(consortium : ConsortiumInput, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> str:
    """"
    Creates a new consortium. The tag is generated from the content of the consortium, so that
    identical consortiums cannot be created twice.
    """
    tag = create_hierarchical_hash(consortium.model_dump())
    db.consortiums.insert(tag, consortium)
    return tag


@router.get("/user", summary="Returns the consortiums the current user is a member of (via their research groups).")
def get_my_consortiums(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """"
    Returns the tags of all consortiums that one of the users research groups is a member of.
    A user can be part of multiple consortiums through different research groups.
    """
    return db.consortiums.find_by_user(user_tag = user.tag, limit = None)



@router.get("/users/{user_tag}", summary="Returns the consortiums of a given user. Requires at least curator rights.")
def get_consortiums_by_user(user_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """"
    Returns the tags of all consortiums that one of the given users research groups is a member of.
    Requires at least curator rights.
    """
    return db.consortiums.find_by_user(user_tag = user_tag, limit = None)



@router.get("/{consortium_tag}")
def get_consortium_by_tag(consortium_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> ConsortiumResponseModel:
    """"
    Returns a consortium by its tag.
    """
    _check_consortium_exists(consortium_tag, db)
    consortium = db.consortiums.get(tag = consortium_tag)
    return ConsortiumResponseModel(**consortium.model_dump())


@router.delete("/{consortium_tag}", summary="Deletes a consortium. Requires admin rights.")
def delete_consortium(consortium_tag : str, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> bool:
    """"
    Deletes a consortium together with its group memberships and shared submissions relations.
    """
    _check_consortium_exists(consortium_tag, db)
    return db.consortiums.delete(tag = consortium_tag)


@router.get("/{consortium_tag}/groups")
def get_consortium_groups(consortium_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """"
    Returns the research groups that are members of the consortium.
    """
    _check_consortium_exists(consortium_tag, db)
    return db.consortiums.get_groups(tag = consortium_tag)


@router.get("/{consortium_tag}/users")
def get_consortium_users(consortium_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """"
    Returns the user tags of all users that are members of the consortiums research groups.
    """
    _check_consortium_exists(consortium_tag, db)
    return db.consortiums.get_user_tags(tag = consortium_tag)


@router.post("/{consortium_tag}/groups", summary="Adds research groups to a consortium. Requires at least curator rights.")
def insert_groups_to_consortium(consortium_tag : str, group_tags : List[str], user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """"
    Adds research groups to a consortium. Requires at least curator rights.
    """
    _check_consortium_exists(consortium_tag, db)
    for group_tag in group_tags:
        if not db.research_groups.exists(tag = group_tag):
            raise HTTPException(status_code=404, detail=f"Research group with tag {group_tag} not found")
    db.consortiums.insert_groups(tag = consortium_tag, group_tags = group_tags)
    return True


@router.delete("/{consortium_tag}/groups", summary="Removes research groups from a consortium. Requires at least curator rights.")
def remove_groups_from_consortium(consortium_tag : str, group_tags : List[str], user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """"
    Removes research groups from a consortium. Requires at least curator rights.
    """
    _check_consortium_exists(consortium_tag, db)
    db.consortiums.remove_groups(tag = consortium_tag, group_tags = group_tags)
    return True


@router.get("/{consortium_tag}/submissions")
def get_consortium_submissions(consortium_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """"
    Returns the submission tags that are shared with the consortium.
    """
    _check_consortium_exists(consortium_tag, db)
    return db.consortiums.get_submission_tags(tag = consortium_tag)


@router.post("/{consortium_tag}/submissions/{submission_tag}",
             summary="Shares a submission with a consortium. Requires the submission owner or a curator.")
def share_submission_with_consortium(consortium_tag : str, submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """"
    Shares a submission with a consortium, so that all members of the consortiums research
    groups can access it. Only the creator of the submission (or a curator) can share it.
    """
    _check_consortium_exists(consortium_tag, db)
    # the check also verifies that the submission exists; only the owner (creator),
    # a collaborator with access or a curator reaches this point - owners decide what to share.
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    creator_tag = db.submissions.get_creator(tag = submission_tag)
    if user.tag != creator_tag and user.role < UserRolesEnum.CURATOR:
        raise HTTPException(status_code=403, detail="Only the owner of the submission can share it with a consortium.")
    return db.consortiums.share_submission(consortium_tag = consortium_tag, submission_tag = submission_tag)


@router.delete("/{consortium_tag}/submissions/{submission_tag}",
               summary="Removes a submission from a consortium. Requires the submission owner or a curator.")
def unshare_submission_with_consortium(consortium_tag : str, submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """"
    Removes a submission from a consortium. Only the creator of the submission (or a curator) can remove it.
    """
    _check_consortium_exists(consortium_tag, db)
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    creator_tag = db.submissions.get_creator(tag = submission_tag)
    if user.tag != creator_tag and user.role < UserRolesEnum.CURATOR:
        raise HTTPException(status_code=403, detail="Only the owner of the submission can remove it from a consortium.")
    return db.consortiums.unshare_submission(consortium_tag = consortium_tag, submission_tag = submission_tag)
