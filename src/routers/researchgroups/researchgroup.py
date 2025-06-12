
from typing import List, Dict
from fastapi import APIRouter, Depends
from config.models.user import UserModel, PublicUser
from config.models.timeline import SubmissionTimelineResponseModel, TimelineModel, TimelineInputModel
from services.users import get_user_from_token, is_user_at_least_curator
from lib.database.Database import Database
from config.models.researchgroup import ResearchGroupInput, ResearchGroupResponseModel
from config.models.parameter import APIParamString

DB = Database.DB()

router = APIRouter(
    prefix="/api/researchgroups",
    tags=["Research Groups","Permissions"],
    )


@router.get("/")
def get_research_groups() -> List[str]:
    ""
    print(DB.research_groups.get_tags())
    return DB.research_groups.get_tags()
    
@router.get("/{research_group_tag}")
def get_research_group_by_tag(research_group_tag : str) -> ResearchGroupResponseModel:
    "" 
    research_group = DB.research_groups.get(tags = APIParamString(param=research_group_tag).param)[0]
    return ResearchGroupResponseModel(**research_group.model_dump())

@router.post("/")
def add_reserach_group(research_group : ResearchGroupInput):
    DB.research_groups.insert(research_group)
    
    
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
    