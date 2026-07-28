from __future__ import annotations

from abc import abstractmethod, ABC
from typing import List, Literal  
from config.models.news.news import NewsModel

class NewsABC(ABC):
    """Abstract class to handle news.
    News are displayed to all users and generally public. 
    News are posted if a new dataset is available. 
    """
    
    @abstractmethod
    def exists(self, tag : str) -> bool:
        """Checks if a given tag is associates with a news 

        Parameters
        ----------
        tag : str
            The news tag 

        Returns
        -------
        bool
            If the tag is associated with a news 
        """
    
    @abstractmethod
    def get(self, tags : List[str] = None, limit : int = 10) -> List[NewsModel]:
        """Returns the news either by tag or just the latest news. 

        Parameters
        ----------
        tags : List[str], optional
            if given, it will return the specific news by its tag, by default None
        limit : int, optional
            the maximum number of news to be returned, by default 10

        Returns
        -------
        List[News]
            The news to be returned. The length might be < limit, if not n > limit 
            news exist. IF tag is given, the length is always 1, since if the tag is not found
            an exception is thrown. 
            
        Exceptions
        ----------
        
        """
        
    @abstractmethod
    def find(self, limit : int = None, order : Literal["desc","asc"] = "desc") -> List[str]:
        """
        Finds the latest news items, returns their tags. Limit can be set to restrict the number of items returned.
        Parameters
        ----------
        limit : int, optional
            The maximum number of news items to return, by default None
        order : Literal["desc","asc"], optional
            The order in which to return the news items, by default "desc"  
            
        Returns
        -------
        List[str]
            A list of news item tags.
        """

    @abstractmethod
    def insert(self, news : NewsModel) -> bool:
        """Adds a news to the news pool. 

        Parameters
        ----------
        news : News
            _description_

        Returns
        -------
        bool
            _description_
        """

    @abstractmethod
    def update(self, news: NewsModel) -> bool:
        """Updates an existing news item.
        Parameters
        ----------
        news : NewsModel
            The news item with updated data.
        Returns
        -------
        bool
            True if update was successful.
        """
                
    @abstractmethod
    def delete(self, tag : str) -> bool:
        """Deletes a specific news by its tag. 

        Parameters
        ----------
        label : str
            _description_

        Returns
        -------
        bool
            If the deletion was successful. 
        """
        
        
    
    
