from typing import List, Dict, Optional

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_at_least_curator
from services.encryption import create_hierarchical_hash
from lib.database.Database import Database
from config.models.researchgroup import ResearchGroupInput, ResearchGroupResponseModel, ResearchGroupResponseModel
from config.models.parameter import APIParamString

DB = Database.DB()
router = APIRouter(
    prefix="/api/researchgroups",
    tags=["Research Groups","Permissions"],
    )


research_group_not_found_exception = HTTPException(status_code=404, detail="Research group not found")

@router.get("/q", response_model=List[str])
def find_research_groups(search_string: Optional[str] = None, user_tags: Optional[str] = None, submission_tags: Optional[str] = None, limit: int = 40, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    """Finds research groups matching the search criteria."""
    
    return DB.research_groups.find(
        search_string=search_string,
        user_tags=APIParamString(param=user_tags).param,
        submission_tags=APIParamString(param=submission_tags).param,
        limit=limit
    )
    

@router.get("/")
def get_research_groups(user : UserModel = Depends(get_user_from_token)) -> List[str]:
    ""
    return DB.research_groups.get_tags()
    
@router.get("/{research_group_tag}/users/count")
def get_research_group_user_count(research_group_tag : str, user : UserModel = Depends(get_user_from_token)) -> int:
    "" 
    if not DB.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    return DB.research_groups.get_users_count(tag = research_group_tag)

@router.get("/{research_group_tag}/submissions/count")
def get_research_group_submission_count(research_group_tag : str, user : UserModel = Depends(get_user_from_token)) -> int:
    ""  
    if not DB.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    return DB.research_groups.get_submissions_count(tag = research_group_tag)

@router.get("/{research_group_tag}")
def get_research_group_by_tag(research_group_tag : str, user : UserModel = Depends(get_user_from_token)) -> ResearchGroupResponseModel:
    "" 
    if not DB.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    research_group = DB.research_groups.get(tag = research_group_tag)
    return ResearchGroupResponseModel(**research_group.model_dump())

@router.post("/")
def add_research_group(research_group : ResearchGroupInput, user : UserModel = Depends(get_user_from_token)) -> bool:
    tag = create_hierarchical_hash(research_group.model_dump()) #create a unique tag based on the content of the research group. This way, we can avoid duplicates and also easily check if a research group with the same content already exists.
    return DB.research_groups.insert(tag, research_group)
    
    
@router.post("/{research_group_tag}/users")
def insert_users_to_research_group(research_group_tag : str, user_tags : List[str], user : UserModel = Depends(is_user_at_least_curator)):
    "" 
    DB.research_groups.insert_users(tag = research_group_tag, user_tags = user_tags)
    
@router.delete("/{research_group_tag}/users")
def remove_users_from_research_group(research_group_tag : str, user_tags : List[str], user : UserModel = Depends(is_user_at_least_curator)):
    "" 
    DB.research_groups.remove_users(tag = research_group_tag, user_tags = user_tags)
    
    
@router.get("/{research_group_tag}/users")
def get_users_in_research_group(research_group_tag : str) -> List[str]:
    "" 
    user_tags = DB.research_groups.get_users(research_group_tag)
    return user_tags
    
