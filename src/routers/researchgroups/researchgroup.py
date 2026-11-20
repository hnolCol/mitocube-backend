from typing import List, Dict, Optional
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from config.models.user import UserModel
from config.enums.users.roles import UserRolesEnum
from services.users import get_user_from_token, is_user_at_least_curator
from lib.cache.user_cache import invalidate_cached_user
from services.submission import check_submission_tags_access
from services.encryption import create_hierarchical_hash
from config.models.researchgroup import ResearchGroupInput, ResearchGroupResponseModel, ResearchGroupResponseModel
from config.models.parameter import APIParamString

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/researchgroups",
    tags=["Research Groups","Permissions"],
    )


research_group_not_found_exception = HTTPException(status_code=404, detail="Research group not found")

@router.get("/q", response_model=List[str])
def find_research_groups(search_string: Optional[str] = None, user_tags: Optional[str] = None, submission_tags: Optional[str] = None, limit: int = 40, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """Finds research groups matching the search criteria."""
    
    check_submission_tags_access(submission_tags = submission_tags, user = user, db = db)
    return db.research_groups.find(
        search_string=search_string,
        user_tags=APIParamString(param=user_tags).param,
        submission_tags=APIParamString(param=submission_tags).param,
        limit=limit
    )
    

@router.get("/")
def get_research_groups(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    ""
    return db.research_groups.get_tags()
    
@router.get("/{research_group_tag}/users/count")
def get_research_group_user_count(research_group_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> int:
    """ 
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    return db.research_groups.get_users_count(tag = research_group_tag)

@router.get("/{research_group_tag}/submissions/count")
def get_research_group_submission_count(research_group_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> int:
    """  
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    return db.research_groups.get_submissions_count(tag = research_group_tag)

@router.patch("/{research_group_tag}", summary="Updates the properties of a research group. Requires at least curator rights.")
def update_research_group(research_group_tag : str,
                          text : str,
                          abbreviation : str,
                          email : str,
                          address : str,
                          institute : str,
                          profile_text : Optional[str] = None,
                          url : Optional[str] = None,
                          user : UserModel = Depends(is_user_at_least_curator),
                          db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Updates the properties of the research group with the given tag.
    The fields are passed as query parameters to match the frontend API hook.
    """
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    research_group = ResearchGroupInput(
        text = text,
        abbreviation = abbreviation,
        email = email,
        address = address,
        institute = institute,
        profile_text = profile_text,
        url = url
    )
    return db.research_groups.update(tag = research_group_tag, research_group = research_group)


@router.get("/{research_group_tag}")
def get_research_group_by_tag(research_group_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> ResearchGroupResponseModel:
    ""
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    research_group = db.research_groups.get(tag = research_group_tag)
    return ResearchGroupResponseModel(**research_group.model_dump())

@router.post("/")
def add_research_group(research_group : ResearchGroupInput, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> str:
    tag = create_hierarchical_hash(research_group.model_dump()) #create a unique tag based on the content of the research group. This way, we can avoid duplicates and also easily check if a research group with the same content already exists.
    db.research_groups.insert(tag, research_group)
    return tag

@router.post("/{research_group_tag}/users")
def insert_users_to_research_group(research_group_tag : str, user_tags : List[str], user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)):
    ""
    db.research_groups.insert_users(tag = research_group_tag, user_tags = user_tags)
    
@router.delete("/{research_group_tag}/users")
def remove_users_from_research_group(research_group_tag : str, user_tags : List[str], user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)):
    ""
    db.research_groups.remove_users(tag = research_group_tag, user_tags = user_tags)
    
    
@router.get("/{research_group_tag}/users")
def get_users_in_research_group(research_group_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    ""
    user_tags = db.research_groups.get_users(research_group_tag)
    return user_tags
    
@router.get("/users/{user_tag}", response_model=List[str], summary="Returns the research groups a user is a member of.")
def get_research_groups_of_user(user_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """
    Returns the tags of all research groups the given user is a member of.
    Useful to find the research_group_tag when (retrospectively) assigning a
    research group head (PI), e.g. via POST /{research_group_tag}/heads/{user_tag}.
    """
    if not db.users.exists(tag = user_tag):
        raise HTTPException(status_code=404, detail=f"User with tag {user_tag} not found.")
    return db.research_groups.find(user_tags = [user_tag], limit = None)


@router.get("/user/is-head", response_model=bool,
            summary="Returns whether the current user is a head (PI) of at least one research group.")
def get_my_is_head(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Returns True if the current user is a head (PI) of at least one research group.
    Frontends use this to decide whether to show PI-only controls.
    """
    return db.research_groups.is_head(user_tag = user.tag)

@router.get("/user/headed", response_model=List[str],
            summary="Returns the tags of the research groups the current user heads (is PI of).")
def get_my_headed_research_groups(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """
    Returns the tags of all research groups the current user is a head (PI) of. Used by the
    frontend to scope PI-only listings (e.g. consortium share terms) to the users own groups.
    """
    return db.research_groups.get_headed_group_tags(user_tag = user.tag)


@router.get("/user/shared-overview", response_model=List[Dict],
            summary="Returns per submission of the current user and their headed groups: owner, shared consortiums (approved/pending) and collaborating users. PI only.")
def get_my_shared_submissions_overview(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[Dict]:
    """
    Returns one entry per submission created by the current user or by a member of a research
    group they head (PI): the submission and owner tags, the consortiums the submission is
    currently shared with (approved and separately pending share requests) and the tags of the
    users collaborating on it via approved collaboration requests.
    """
    return db.research_groups.get_shared_submissions_overview(user_tag = user.tag)

@router.get("/sharing/overview", response_model=Dict,
            summary="Returns the platform-wide submission sharing overview: consortium shares, explore view collaborations and explore-disabled research groups. Requires at least curator rights.")
def get_sharing_overview(user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> Dict:
    """
    Returns the sharing report for admins and curators: one entry per submission shared in any
    way (consortium share approved or pending, explore view collaboration or pending
    collaboration request) with the owner, the owners research groups, the share targets and
    the tags of all research groups whose explore visibility is disabled.
    """
    return {
        "consortium_groups": db.consortiums.get_group_sharing_overview(),
        "submissions": db.research_groups.get_sharing_overview(),
        "explore_disabled_groups": db.research_groups.get_explore_disabled_group_tags()
    }

@router.get("/user/explore-disabled", response_model=bool,
            summary="Returns whether the head (PI) of any of the current users research groups disabled the explore visibility.")
def get_my_explore_disabled(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Returns True if the head (PI) of at least one of the research groups the current user
    is a member of disabled the explore visibility of the groups submissions. Frontends use
    this to hide the explore view from the members of such groups.
    """
    group_tags = db.research_groups.find(user_tags = [user.tag], limit = None)
    return any(db.research_groups.get_explore_disabled(tag = group_tag) for group_tag in group_tags)


@router.get("/{research_group_tag}/explore-disabled", response_model=bool,
            summary="Returns whether the head (PI) of the research group disabled the explore visibility of the groups submissions.")
def get_research_group_explore_disabled(research_group_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Returns True if the head (PI) of the research group disabled the explore visibility.
    If disabled, the groups submissions are hidden from the explore view and the members
    of the group lose access to the explore tab.
    """
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    return db.research_groups.get_explore_disabled(tag = research_group_tag)


@router.put("/{research_group_tag}/explore-disabled", response_model=bool,
            summary="Sets whether the head (PI) of the research group disabled the explore visibility. Requires the head (PI) of the group or a curator.")
def set_research_group_explore_disabled(research_group_tag : str, disabled : bool, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Lets the head (PI) of a research group (or a curator) disable the explore visibility of
    the groups submissions. If disabled, the groups submissions are hidden from the explore
    view for users outside of the group and the members of the group lose access to the
    explore tab.
    """
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    if user.role < UserRolesEnum.CURATOR and not db.research_groups.is_head(user_tag = user.tag, group_tag = research_group_tag):
        raise HTTPException(status_code=403, detail="Only the head (PI) of the research group or a curator can change the explore visibility.")
    return db.research_groups.set_explore_disabled(tag = research_group_tag, disabled = disabled)


@router.get("/{research_group_tag}/heads")
def get_research_group_heads(research_group_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """
    Returns the heads (PIs) of the research group.
    """
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    return db.research_groups.get_heads(tag = research_group_tag)
    
@router.post("/{research_group_tag}/heads/{user_tag}", summary="Makes a user a head (PI) of the research group and promotes them to at least group curator. Requires at least curator rights.")
def set_research_group_head(research_group_tag : str, user_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Makes a user a head (PI) of the research group. The new head (PI) is
    automatically promoted to at least group curator (role 2); an existing
    higher role is never lowered. Requires at least curator rights.
    """
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    if not db.users.exists(tag = user_tag):
        raise HTTPException(status_code=404, detail=f"User with tag {user_tag} not found.")
    if user_tag not in db.research_groups.get_users(tag = research_group_tag):
        raise HTTPException(status_code=400, detail=f"User with tag {user_tag} is not a member of the research group with tag {research_group_tag} and can therefore not be made a head (PI) of it.")
    db.research_groups.set_head(group_tag = research_group_tag, user_tag = user_tag)
    db.users.ensure_role_at_least(tag = user_tag, role = UserRolesEnum.GROUP_CURATOR)
    invalidate_cached_user(user_tag)
    return True
    
@router.delete("/{research_group_tag}/heads/{user_tag}", summary="Removes a user as head (PI) of the research group. Requires at least curator rights.")
def remove_research_group_head(research_group_tag : str, user_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Removes a user as head (PI) of the research group. Requires at least curator rights.
    """
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    db.research_groups.remove_head(group_tag = research_group_tag, user_tag = user_tag)
    return True
    