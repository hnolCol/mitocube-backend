from typing import List, Dict, Optional
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_at_least_curator
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
    "" 
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    return db.research_groups.get_users_count(tag = research_group_tag)

@router.get("/{research_group_tag}/submissions/count")
def get_research_group_submission_count(research_group_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> int:
    ""  
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    return db.research_groups.get_submissions_count(tag = research_group_tag)

@router.get("/{research_group_tag}")
def get_research_group_by_tag(research_group_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> ResearchGroupResponseModel:
    "" 
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    research_group = db.research_groups.get(tag = research_group_tag)
    return ResearchGroupResponseModel(**research_group.model_dump())

@router.post("/")
def add_research_group(research_group : ResearchGroupInput, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    tag = create_hierarchical_hash(research_group.model_dump()) #create a unique tag based on the content of the research group. This way, we can avoid duplicates and also easily check if a research group with the same content already exists.
    return db.research_groups.insert(tag, research_group)
    
    
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


@router.get("/{research_group_tag}/heads")
def get_research_group_heads(research_group_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """
    Returns the heads (PIs) of the research group.
    """
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    return db.research_groups.get_heads(tag = research_group_tag)
    
@router.post("/{research_group_tag}/heads/{user_tag}", summary="Makes a user a head (PI) of the research group. Requires at least curator rights.")
def set_research_group_head(research_group_tag : str, user_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Makes a user a head (PI) of the research group. Requires at least curator rights.
    """
    if not db.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    if not db.users.exists(tag = user_tag):
        raise HTTPException(status_code=404, detail=f"User with tag {user_tag} not found.")
    if user_tag not in db.research_groups.get_users(tag = research_group_tag):
        raise HTTPException(status_code=400, detail=f"User with tag {user_tag} is not a member of the research group with tag {research_group_tag} and can therefore not be made a head (PI) of it.")
    db.research_groups.set_head(group_tag = research_group_tag, user_tag = user_tag)
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
    
