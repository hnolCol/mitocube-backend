from typing import List, Optional, Dict
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

def _get_managed_group_tags(user : UserModel, consortium_tag : str, db : DatabaseABC) -> List[str]:
    """Returns the eligible research groups of the consortium whose members the user may manage:
    for curators/admins all of them, otherwise only the consortium groups the user leads
    (as head/PI) or is a member of (as group curator)."""
    consortium_group_tags = db.consortiums.get_groups(tag = consortium_tag)
    if user.role >= UserRolesEnum.CURATOR:
        return consortium_group_tags
    managed_group_tags = set(db.research_groups.get_headed_group_tags(user_tag = user.tag))
    if user.role >= UserRolesEnum.GROUP_CURATOR:
        managed_group_tags.update(db.research_groups.find(user_tags = [user.tag], limit = None))
    return [group_tag for group_tag in consortium_group_tags if group_tag in managed_group_tags]


def _get_managed_user_tags(user : UserModel, consortium_tag : str, db : DatabaseABC) -> set:
    """Returns the users of the research groups the user may manage in the consortium."""
    managed_user_tags = set()
    for group_tag in _get_managed_group_tags(user, consortium_tag, db):
        managed_user_tags.update(db.research_groups.get_users(tag = group_tag))
    return managed_user_tags

@router.get("/q", response_model=List[str])
def find_consortiums(search_string : Optional[str] = None, group_tags : Optional[str] = None, user_tags : Optional[str] = None, limit : int = 40, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """Finds consortiums matching the search criteria. Consortiums are visible to all logged-in users.
    Filter by research groups (group_tags) or by the users whose research groups are consortium members (user_tags)."""
    return db.consortiums.find(
        search_string=search_string,
        group_tags=APIParamString(param=group_tags).param,
        user_tags=APIParamString(param=user_tags).param,
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
    print(user.tag, db.consortiums.find_by_user(user_tag = user.tag, limit = None))
    return db.consortiums.find_by_user(user_tag = user.tag, limit = None)



@router.get("/users/{user_tag}", summary="Returns the consortiums of a given user. Requires at least curator rights.")
def get_consortiums_by_user(user_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """"
    Returns the tags of all consortiums that one of the given users research groups is a member of.
    Requires at least curator rights.
    """
    return db.consortiums.find_by_user(user_tag = user_tag, limit = None)



@router.get("/terms/pending", summary="Returns the consortiums where the current user heads an eligible group without terms agreement.")
def get_my_pending_terms_agreements(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[Dict]:
    """
    Returns the consortiums where the current user leads (as head/PI) an eligible research group
    that has not yet agreed to the consortium terms. Until the head agrees, the users of the
    group can neither share into nor see the submissions of the consortium.
    """
    return db.consortiums.find_pending_terms_for_head(user_tag = user.tag)


@router.get("/user/pending-terms", summary="Returns the consortiums the current user is a member of where the terms are not agreed yet.")
def get_my_consortiums_with_pending_terms(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """
    Returns the tags of the consortiums the current user is a direct member of where the head (PI)
    of none of the users research groups agreed to the terms yet. Frontends use this to warn
    affected members.
    """
    return db.consortiums.find_consortiums_with_pending_terms_for_user(user_tag = user.tag)


@router.post("/{consortium_tag}/terms/{group_tag}",
             summary="Agrees to the consortium terms for a research group. Requires the head (PI) of the group or a curator.")
def agree_consortium_terms(consortium_tag : str, group_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Records that the research group participates in the consortium: the head (PI) agrees to the
    consortium terms. Only after this agreement the users of the group can share submissions
    with the consortium and see its shared submissions.
    """
    _check_consortium_exists(consortium_tag, db)
    if group_tag not in db.consortiums.get_groups(tag = consortium_tag):
        raise HTTPException(status_code=404, detail=f"Research group with tag {group_tag} is not an eligible group of the consortium.")
    if user.role < UserRolesEnum.CURATOR and not db.research_groups.is_head(user_tag = user.tag, group_tag = group_tag):
        raise HTTPException(status_code=403, detail="Only the head (PI) of the research group or a curator can agree to the consortium terms.")
    return db.consortiums.agree_terms(consortium_tag = consortium_tag, group_tag = group_tag, user_tag = user.tag)


@router.delete("/{consortium_tag}/terms/{group_tag}",
               summary="Revokes the research groups agreement to the consortium terms and revokes all shares of the groups submissions with the consortium. Requires the head (PI) of the group or a curator.")
def revoke_consortium_terms(consortium_tag : str, group_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Revokes the research groups agreement to the consortium terms. The users of the group can
    then neither share submissions with the consortium nor see its shared submissions. All
    shares of the groups submissions with the consortium (pending share requests and approved
    shares) are revoked as well, so the consortium loses access to them.
    """
    _check_consortium_exists(consortium_tag, db)
    if user.role < UserRolesEnum.CURATOR and not db.research_groups.is_head(user_tag = user.tag, group_tag = group_tag):
        raise HTTPException(status_code=403, detail="Only the head (PI) of the research group or a curator can revoke the consortium terms.")
    ok = db.consortiums.revoke_terms(consortium_tag = consortium_tag, group_tag = group_tag)
    if not ok:
        raise HTTPException(status_code=404, detail="No terms agreement found for this research group and consortium.")
    return True


@router.get("/{consortium_tag}/terms", summary="Returns the eligible research groups that agreed to the consortium terms.")
def get_consortium_terms_groups(consortium_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """
    Returns the tags of the eligible research groups whose head (PI) agreed to the consortium terms.
    """
    _check_consortium_exists(consortium_tag, db)
    return db.consortiums.get_terms_group_tags(consortium_tag = consortium_tag)


@router.get("/requests/pending", summary="Returns the pending share requests the current user (as research group head) can approve.")
def get_my_pending_share_requests(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[Dict]:
    """"
    Returns the pending consortium share requests of all users that are members of the
    research groups the current user leads (as head/PI).
    """
    return db.consortiums.get_pending_share_requests_for_head(user_tag = user.tag)

@router.get("/submissions/{submission_tag}/pending", summary="Returns the consortiums with a pending share request for the submission.")
def get_pending_consortium_shares(submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """"
    Returns the tags of all consortiums the submission has a pending share request for.
    """
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    return db.consortiums.get_pending_consortium_tags(submission_tag = submission_tag)

@router.post("/requests/{consortium_tag}/{submission_tag}/approve",
             summary="Approves a pending share request. Requires the head (PI) of the owners research group.")
def approve_share_request(consortium_tag : str, submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Approves a pending consortium share request. The submission becomes immediately
    accessible to all members of the consortium. The final approval comes from the head (PI)
    of the research groups the owner (creator) of the submission is a member of - not from
    curators or admins.
    """
    _check_consortium_exists(consortium_tag, db)
    if not db.consortiums.is_head_of_submission_owner(user_tag = user.tag, submission_tag = submission_tag):
        raise HTTPException(status_code=403, detail="Only the head (PI) of the owners research group can approve a consortium share request.")
    ok = db.consortiums.approve_share_request(consortium_tag = consortium_tag, submission_tag = submission_tag, user_tag = user.tag)
    if not ok:
        raise HTTPException(status_code=404, detail="No pending share request found for this submission and consortium.")
    return True


@router.post("/requests/{consortium_tag}/{submission_tag}/deny",
             summary="Denies a pending share request. Requires the head (PI) of the owners research group.")
def deny_share_request(consortium_tag : str, submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Denies a pending consortium share request. The pending relation is removed, the
    submission stays inaccessible to the consortium. Like the approval, the denial comes
    from the head (PI) of the research groups the owner (creator) is a member of.
    """
    _check_consortium_exists(consortium_tag, db)
    if not db.consortiums.is_head_of_submission_owner(user_tag = user.tag, submission_tag = submission_tag):
        raise HTTPException(status_code=403, detail="Only the head (PI) of the owners research group can deny a consortium share request.")
    ok = db.consortiums.deny_share_request(consortium_tag = consortium_tag, submission_tag = submission_tag)
    if not ok:
        raise HTTPException(status_code=404, detail="No pending share request found for this submission and consortium.")
    return True


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
    Returns the user tags of all users that are direct members of the consortium.
    """
    _check_consortium_exists(consortium_tag, db)
    return db.consortiums.get_user_tags(tag = consortium_tag)

@router.get("/{consortium_tag}/eligible-users", summary="Returns the users of the consortiums eligible research groups. Group curators and heads (PIs) only see the members of their own groups.")
def get_consortium_eligible_users(consortium_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """
    Returns the user tags of all users that are members of the consortiums eligible research groups.
    Curators and admins see all of them, group curators and heads (PIs) only the members of the
    consortium groups they lead or are a member of, since those are the only users they can add.
    """
    _check_consortium_exists(consortium_tag, db)
    if user.role >= UserRolesEnum.CURATOR:
        return db.consortiums.get_eligible_user_tags(tag = consortium_tag)
    return sorted(_get_managed_user_tags(user, consortium_tag, db))


@router.post("/{consortium_tag}/users", summary="Adds users as direct members of a consortium. Requires at least curator rights, or a group curator/head (PI) of one of the consortiums research groups.")
def insert_users_to_consortium(consortium_tag : str, user_tags : List[str], user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Adds users as direct members of a consortium. A user can only be added if they are a member
    of an eligible research group whose head (PI) is a member of the consortium. Curators and
    admins can add every eligible user, group curators and heads (PIs) only the members of the
    consortium groups they lead or are a member of.
    """
    _check_consortium_exists(consortium_tag, db)
    manageable_user_tags = _get_managed_user_tags(user, consortium_tag, db)
    for member_tag in user_tags:
        if member_tag not in manageable_user_tags:
            raise HTTPException(status_code=403, detail="You can only add members of your own research groups to the consortium.")
    for member_tag in user_tags:
        if not db.users.exists(member_tag):
            raise HTTPException(status_code=404, detail=f"User with tag {member_tag} not found")
    try:
        db.consortiums.insert_users(tag = consortium_tag, user_tags = user_tags, user_tag = user.tag)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return True


@router.delete("/{consortium_tag}/users", summary="Removes direct user memberships from a consortium. Requires at least curator rights, or a group curator/head (PI) of one of the consortiums research groups.")
def remove_users_from_consortium(consortium_tag : str, user_tags : List[str], user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Removes direct user memberships from a consortium. Curators and admins can remove every
    direct member, group curators and heads (PIs) only the members of the consortium groups
    they lead or are a member of. Removing a head (PI) is blocked while other members depend on them.
    """
    _check_consortium_exists(consortium_tag, db)
    manageable_user_tags = _get_managed_user_tags(user, consortium_tag, db)
    for member_tag in user_tags:
        if member_tag not in manageable_user_tags:
            raise HTTPException(status_code=403, detail="You can only remove members of your own research groups from the consortium.")
    try:
        db.consortiums.remove_users(tag = consortium_tag, user_tags = user_tags)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return True


@router.post("/{consortium_tag}/groups", summary="Adds research groups to a consortium. Requires at least curator rights.")
def insert_groups_to_consortium(consortium_tag : str, group_tags : List[str], user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """"
    Adds research groups to a consortium as eligible groups. The heads (PIs) of the groups
    automatically become direct members of the consortium.
    """
    _check_consortium_exists(consortium_tag, db)
    for group_tag in group_tags:
        if not db.research_groups.exists(tag = group_tag):
            raise HTTPException(status_code=404, detail=f"Research group with tag {group_tag} not found")
    try:
        db.consortiums.insert_groups(tag = consortium_tag, group_tags = group_tags, user_tag = user.tag)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return True


@router.delete("/{consortium_tag}/groups", summary="Removes research groups from a consortium. Requires at least curator rights.")
def remove_groups_from_consortium(consortium_tag : str, group_tags : List[str], user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """"
    Removes research groups from a consortium. Blocked while members of the group have no other
    eligible group in the consortium.
    """
    _check_consortium_exists(consortium_tag, db)
    try:
        db.consortiums.remove_groups(tag = consortium_tag, group_tags = group_tags)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return True

@router.get("/user/joinable", summary="Returns the consortiums the current user can request to join (their research groups agreed to the terms; the user is not a direct member yet).")
def get_joinable_consortiums(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """
    Returns the tags of the consortiums the head (PI) of at least one of the users research
    groups agreed to the terms of while the user is not a direct member of the consortium yet.
    Users can request to join exactly these consortiums; the requests are approved or denied
    by curators/admins.
    """
    return db.consortiums.find_joinable_consortiums_for_user(user_tag = user.tag)


@router.post("/{consortium_tag}/requests/users/{user_tag}",
             summary="Creates a pending membership request for a user. Every user can request for themselves, heads (PIs) and group curators also for members of their research groups.")
def create_membership_request(consortium_tag : str, user_tag : str, kind : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Creates a pending membership request (kind 'add' or 'remove'). Every user can request a
    membership change for themselves, heads (PIs) and group curators of one of the users
    research groups can also request it for other members of their groups. The request is
    decided by a curator, a group curator or a head (PI) of the users research groups.
    """
    _check_consortium_exists(consortium_tag, db)
    if kind not in ("add", "remove"):
        raise HTTPException(status_code=400, detail="kind must be 'add' or 'remove'.")
    if not db.users.exists(user_tag):
        raise HTTPException(status_code=404, detail=f"User with tag {user_tag} not found")
    if user.role < UserRolesEnum.CURATOR:
        manageable_user_tags = _get_managed_user_tags(user, consortium_tag, db)
        if user_tag != user.tag and user_tag not in manageable_user_tags:
            raise HTTPException(status_code=403, detail="Users can only request membership changes for themselves or for members of their research groups.")
    member_tags = db.consortiums.get_user_tags(tag = consortium_tag)
    if kind == "add" and user_tag in member_tags:
        raise HTTPException(status_code=409, detail="User is already a member of the consortium.")
    if kind == "remove" and user_tag not in member_tags:
        raise HTTPException(status_code=409, detail="User is not a member of the consortium.")
    return db.consortiums.insert_membership_request(consortium_tag = consortium_tag, user_tag = user_tag,
                                                    kind = kind, requested_by = user.tag)


@router.get("/requests/membership", summary="Returns the pending membership requests that concern the current user, their research groups or that they filed themselves.")
def get_my_pending_membership_requests(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[Dict]:
    """
    Returns the pending consortium membership requests that concern the research groups of the
    current user it leads (as head/PI) or curates (as group curator), so those requests are
    routed to the group curator and the PI of the group as well. Requests the current user
    filed themselves or that concern themselves are always included. Curators see all requests.
    """
    if user.role >= UserRolesEnum.CURATOR:
        return db.consortiums.get_pending_membership_requests()
    group_tags = db.research_groups.get_headed_group_tags(user_tag = user.tag)
    if user.role >= UserRolesEnum.GROUP_CURATOR:
        group_tags = list({*group_tags, *db.research_groups.find(user_tags = [user.tag], limit = None)})
    return db.consortiums.get_pending_membership_requests_relevant_to(user_tag = user.tag, group_tags = group_tags)


@router.get("/requests/membership", summary="Returns the pending membership requests that concern the current user, their research groups or that they filed themselves.")
def get_my_pending_membership_requests(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[Dict]:
    """
    Returns the pending consortium membership requests that concern the research groups of the
    current user it leads (as head/PI) or curates (as group curator), so those requests are
    routed to the group curator and the PI of the group as well. Requests the current user
    filed themselves or that concern themselves are always included. Curators see all requests.
    """
    if user.role >= UserRolesEnum.CURATOR:
        return db.consortiums.get_pending_membership_requests()
    group_tags = db.research_groups.get_headed_group_tags(user_tag = user.tag)
    if user.role >= UserRolesEnum.GROUP_CURATOR:
        group_tags = list({*group_tags, *db.research_groups.find(user_tags = [user.tag], limit = None)})
    return db.consortiums.get_pending_membership_requests_relevant_to(user_tag = user.tag, group_tags = group_tags)

@router.post("/requests/{consortium_tag}/membership/{user_tag}/approve",
             summary="Approves a pending membership request. Requires at least curator rights, or a group curator/head (PI) of one of the users research groups.")
def approve_membership_request(consortium_tag : str, user_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Approves a pending consortium membership request. An 'add' request adds the user as a direct
    member, a 'remove' request removes their membership. Curators and admins can decide every
    request, group curators and heads (PIs) the requests of the members of their research groups.
    """
    _check_consortium_exists(consortium_tag, db)
    if user.role < UserRolesEnum.CURATOR and user_tag not in _get_managed_user_tags(user, consortium_tag, db):
        raise HTTPException(status_code=403, detail="Only a curator, a group curator or the head (PI) of one of the users research groups can decide this request.")
    try:
        ok = db.consortiums.approve_membership_request(consortium_tag = consortium_tag, user_tag = user_tag,
                                                        decided_by = user.tag)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="No pending membership request found for this user and consortium.")
    return True

@router.post("/requests/{consortium_tag}/membership/{user_tag}/deny",
             summary="Denies a pending membership request. Requires at least curator rights, or a group curator/head (PI) of one of the users research groups.")
def deny_membership_request(consortium_tag : str, user_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Denies a pending consortium membership request. The pending relation is removed. Curators
    and admins can decide every request, group curators and heads (PIs) the requests of the
    members of their research groups.
    """
    _check_consortium_exists(consortium_tag, db)
    if user.role < UserRolesEnum.CURATOR and user_tag not in _get_managed_user_tags(user, consortium_tag, db):
        raise HTTPException(status_code=403, detail="Only a curator, a group curator or the head (PI) of one of the users research groups can decide this request.")
    ok = db.consortiums.deny_membership_request(consortium_tag = consortium_tag, user_tag = user_tag)
    if not ok:
        raise HTTPException(status_code=404, detail="No pending membership request found for this user and consortium.")
    return True


@router.get("/{consortium_tag}/submissions")
def get_consortium_submissions(consortium_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """"
    Returns the submission tags that are shared with the consortium.
    """
    _check_consortium_exists(consortium_tag, db)
    return db.consortiums.get_submission_tags(tag = consortium_tag)


@router.post("/{consortium_tag}/submissions/{submission_tag}",
             summary="Shares a submission with a consortium. Requires the submission owner or a curator. The final approval comes from the head (PI) of the owners research group.")
def share_submission_with_consortium(consortium_tag : str, submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Shares a submission with a consortium, so that all members of the consortiums research
    groups can access it. Only the creator of the submission (or a curator) can share it.

    The share request is created with status pending unless the requesting user is the head
    (PI) of a research group the owner (creator) is a member of. The final approval always
    comes from the head (PI) of the owners research group - even a curators share request
    stays pending until the PI approves it.
    """
    _check_consortium_exists(consortium_tag, db)
    # the check also verifies that the submission exists; only the owner (creator),
    # a collaborator with access or a curator reaches this point - owners decide what to share.
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    creator_tag = db.submissions.get_creator(tag = submission_tag)
    if user.tag != creator_tag and user.role < UserRolesEnum.CURATOR:
        raise HTTPException(status_code=403, detail="Only the owner of the submission can share it with a consortium.")
    if user.role < UserRolesEnum.CURATOR and not db.consortiums.user_has_terms(consortium_tag = consortium_tag, user_tag = user.tag):
        raise HTTPException(status_code=403, detail="The head (PI) of your research group has not yet agreed to the consortium terms. "
                                                    "Until then you cannot share submissions with this consortium.")
    immediate = db.consortiums.is_head_of_submission_owner(user_tag = user.tag, submission_tag = submission_tag)
    return db.consortiums.share_submission(consortium_tag = consortium_tag, submission_tag = submission_tag,
                                           user_tag = user.tag, approved = immediate)


@router.delete("/{consortium_tag}/submissions/{submission_tag}",
               summary="Removes a submission from a consortium. Requires the submission owner, a head (PI) of the owners research group or a curator.")
def unshare_submission_with_consortium(consortium_tag : str, submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """"
    Removes a submission from a consortium. Only the creator of the submission, a head (PI) of
    one of the owners research groups or a curator can remove it.
    """
    _check_consortium_exists(consortium_tag, db)
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    creator_tag = db.submissions.get_creator(tag = submission_tag)
    if (user.tag != creator_tag
            and user.role < UserRolesEnum.CURATOR
            and not db.consortiums.is_head_of_submission_owner(user_tag = user.tag, submission_tag = submission_tag)):
        raise HTTPException(status_code=403, detail="Only the owner of the submission, a research group head (PI) or a curator can remove it from a consortium.")
    return db.consortiums.unshare_submission(consortium_tag = consortium_tag, submission_tag = submission_tag)
