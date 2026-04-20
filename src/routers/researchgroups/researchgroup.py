
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException
from config.models.user import UserModel, PublicUser
from config.models.timeline import SubmissionTimelineResponseModel, TimelineModel, TimelineInputModel
from services.users import get_user_from_token, is_user_at_least_curator
from lib.database.Database import Database
from config.models.researchgroup import ResearchGroupInput, ResearchGroupResponseModel, ResearchGroupResponseModel, ResearchGroupModel
from config.models.parameter import APIParamString

DB = Database.DB()

router = APIRouter(
    prefix="/api/researchgroups",
    tags=["Research Groups","Permissions"],
    )

research_group_not_found_exception = HTTPException(status_code=404, detail="Research group not found")


@router.get("/details")
def get_research_groups_details(user: UserModel = Depends(get_user_from_token)) -> List[ResearchGroupModel]:
    return DB.research_groups.get_details()

@router.get("/")
def get_research_groups() -> List[str]:
    ""
    print(DB.research_groups.get_tags())
    return DB.research_groups.get_tags()
    
    
@router.get("/{research_group_tag}/users/count")
def get_research_group_user_count(research_group_tag : str) -> int:
    "" 
    if not DB.research_groups.exists(tag = research_group_tag):
        raise 
    return DB.research_groups.get_users_count(tag = research_group_tag)

@router.get("/{research_group_tag}")
def get_research_group_by_tag(research_group_tag : str) -> ResearchGroupResponseModel:
    "" 
    if not DB.research_groups.exists(tag = research_group_tag):
        raise research_group_not_found_exception
    research_group = DB.research_groups.get(tag = research_group_tag)
    return ResearchGroupResponseModel(**research_group.model_dump())

@router.post("/")
def add_research_group(research_group : ResearchGroupInput) -> bool:
    return DB.research_groups.insert(research_group)
    
    
@router.post("/{research_group_tag}/users")
def add_users_to_research_group(research_group_tag : str, user_tags : List[str]):
    "" 
    DB.research_groups.add_users(tag = research_group_tag, user_tags = user_tags)
    
@router.delete("/{research_group_tag}/users")
def add_users_to_research_group(research_group_tag : str, user_tags : List[str]):
    "" 
    DB.research_groups.remove_users(tag = research_group_tag, user_tags = user_tags)
    
    
@router.get("/{research_group_tag}/users")
def get_users_in_research_group(research_group_tag : str) -> List[str]:
    "" 
    user_tags = DB.research_groups.get_users(research_group_tag)
    return user_tags
    