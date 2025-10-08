from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Literal

# from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.database.Database import Database

from config.models.user import UserModel
# from config.models.attributes import AttributeValueModel
# from config.enums.states import SubmissionStatesEnums
from config.models.news.news import  NewsModel, NewsInsertModel
from config.models.parameter import APIParamString
from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator

DB = Database.DB()


router = APIRouter(
    prefix="/api/news",
    tags=["News"]
    )



@router.get("")
def find_news(limit : int = 10, order : Literal["asc", "desc"] = "desc", user : UserModel = Depends(get_user_from_token)) -> List[str]:
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
        List of tags of the latest news item
    """

    return DB.news.find(order=order, limit=limit)


@router.post("" , summary="Create a news item. Requires admin rights.")
def create_news_item(news_item: NewsInsertModel, user: UserModel = Depends(is_user_at_least_curator)):
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

    return DB.news.insert(news = news_item)

@router.get("/{news_tag}")
def get_news_by_tag(news_tag : str, user : UserModel = Depends(get_user_from_token)) -> NewsModel:
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
    if not DB.news.exists(tag = news_tag): raise HTTPException(status_code=404, detail="News item not found.")
    return DB.news.get(tag = news_tag)



@router.delete("/{news_tag}", summary="Delete a news item. Requires at least curator rights.")
def delete_news_item(news_tag: str, user: UserModel = Depends(is_user_at_least_curator)) -> bool:
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
    if not DB.news.exists(tag=news_tag):
        raise HTTPException(status_code=404, detail="News item not found.")

    ok = DB.news.delete(tag=news_tag)
    return ok 