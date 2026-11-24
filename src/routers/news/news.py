from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Literal

# 
from lib.database.abstract.Database import DatabaseABC

from config.models.user import UserModel
from config.enums.users.roles import UserRolesEnum
# from config.models.attributes import AttributeValueModel
# from config.enums.states import SubmissionStatesEnums
from config.models.news.news import  NewsModel, NewsInsertModel
from config.models.parameter import APIParamString
from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator
from lib.database.Database import get_db



router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/news",
    tags=["News"]
    )



@router.get("")
def find_news(limit : int = 10, order : Literal["asc", "desc"] = "desc", user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """_summary_

    Parameters
    ----------
    order : Literal["asc", "desc"], optional
        The order in which to return the news items, by default "desc"
    limit : int, optional
        _description_, by default 10
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)

    Returns
    -------
    List[str]
        List of tags of the latest news item. Curators and admins receive all news
        items. All other users receive news items without a research group (public)
        and news items targeted at one of their research groups.
    """

    if user.role >= UserRolesEnum.CURATOR:
        return db.news.find(order=order, limit=limit)
    # resolve the groups from the db (same as for submissions), not from the cached user
    own_group_tags = db.research_groups.find(user_tags=[user.tag], limit=None) or []
    return db.news.find(order=order, limit=limit, research_group_tags=own_group_tags)


@router.post("" , summary="Create a news item. Requires admin rights.")
def create_news_item(news_item: NewsInsertModel, user: UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)):
    """Creates a new news item.

    Parameters
    ----------
    news_item : NewsModel
        The news item to create.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    NewsModel
        The created news item.
    """
    if news_item.user_tag is None:
        #add user from the token, only if it is not present
        news_item = NewsInsertModel(**news_item.model_dump(exclude={"user_tag"}), user_tag=user.tag)
    # only curators/admins reach this endpoint; they may create general news without a
    # research group (visible to everyone) or target a specific research group
    if news_item.research_group_tag is not None and not db.research_groups.exists(tag=news_item.research_group_tag):
        raise HTTPException(status_code=404, detail="Research group not found.")

    return db.news.insert(news = news_item)

@router.get("/{news_tag}")
def get_news_by_tag(news_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> NewsModel:
    """Retrieves a news item by its tag.

    Parameters
    ----------
    news_tag : str
        The tag of the news item to retrieve.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)

    Returns
    -------
    NewsModel
        The news item data.

    Raises
    ------
    HTTPException
        If the news item with the given tag does not exist.
    """
    if not db.news.exists(tag = news_tag): raise HTTPException(status_code=404, detail="News item not found.")
    news = db.news.get(tag = news_tag)
    # news targeted at a research group is only visible to members of that group, curators and admins
    if user.role < UserRolesEnum.CURATOR:
        own_group_tags = db.research_groups.find(user_tags=[user.tag], limit=None) or []
        if news.research_group_tag is not None and news.research_group_tag not in own_group_tags:
            raise HTTPException(status_code=404, detail="News item not found.")
    return news

@router.put("/{news_tag}", summary="Update a news item. Requires at least curator rights.")
def update_news_item( news_tag: str,  news_update: NewsModel, user: UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> NewsModel:
    """Updates an existing news item.
    Parameters
    ----------
    news_tag : str
        The tag of the news item to update
    news_update : NewsModel
        The updated news data
    user : UserModel
        The authenticated user (must be at least curator)
    Returns
    -------
    NewsModel
        The updated news item
    """
    if not db.news.exists(tag=news_tag):
        raise HTTPException(status_code=404, detail="News item not found.")
    # only curators/admins reach this endpoint; they may make the news general
    # (no research group, visible to everyone) or target a specific research group
    if news_update.research_group_tag is not None and not db.research_groups.exists(tag=news_update.research_group_tag):
        raise HTTPException(status_code=404, detail="Research group not found.")
    
    news_update.tag = news_tag
    success = db.news.update(news=news_update)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update news item.")
    
    return db.news.get(tag=news_tag)

@router.delete("/{news_tag}", summary="Delete a news item. Requires at least curator rights.")
def delete_news_item(news_tag: str, user: UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """Deletes a news item by its tag.

    Parameters
    ----------
    news_tag : str
        The tag of the news item to delete.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    dict
        A message indicating the result of the deletion.
    """
    if not db.news.exists(tag=news_tag):
        raise HTTPException(status_code=404, detail="News item not found.")

    ok = db.news.delete(tag=news_tag)
    return ok 